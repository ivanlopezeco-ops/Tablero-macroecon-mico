"""Fuentes aprobadas del IPOM: actualiza por bloque y conserva el último bloque válido.

Las fechas de consulta son dinámicas. Las revisiones sustituyen la historia completa;
una respuesta truncada, vacía o incompatible se rechaza sin borrar datos publicados.
"""
import datetime as dt
import io
import json
import math
import pathlib
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import openpyxl  # Inicializar el motor antes de las lecturas concurrentes de pandas.
import fuentes as F
import ipom_io as IO
import ipom_credito as C
import ipom_cnv as CNV

DATA = pathlib.Path(__file__).resolve().parents[1] / 'data'


def serie(nombre, unidad, fuente, url, filas, metodo, mensual=True):
    return {'n': nombre, 'u': unidad, 'f': fuente, 'url': url,
            'd': [[str(f)[:10], float(v)] for f, v in filas],
            'metodologia': metodo, 'frecuencia': 'mensual' if mensual else 'diaria'}


def normalizar(series):
    return {'ipom_' + k: serie(s['nombre'], s['unidad'], s['fuente'], s['url'], s['datos'],
                              s.get('metodologia', s.get('nota', s.get('tipo_dato', ''))),
                              s.get('frecuencia', 'mensual').lower() == 'mensual')
            for k, s in series.items()}


def variacion(filas, meses):
    datos = dict(filas)
    return [[f, (v / datos[a] - 1) * 100] for f, v in filas
            if (a := (pd.Timestamp(f) - pd.DateOffset(months=meses)).strftime('%Y-%m-%d')) in datos and datos[a] != 0]


def fred(codes):
    out = {}
    for code in codes:
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd=2015-01-01&coed={F.HOY}'
        contenido = IO.descargar(url, 'fred-' + code + '.csv').read_bytes()
        if zipfile.is_zipfile(io.BytesIO(contenido)):
            with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                frames = [pd.read_csv(z.open(n)) for n in z.namelist() if n.endswith('.csv')]
                d = next(x for x in frames if code in x.columns)
        else:
            d = pd.read_csv(io.BytesIO(contenido))
        d[code] = pd.to_numeric(d[code], errors='coerce')
        d = d[d.observation_date.between('2015-01-01', str(F.HOY))].dropna(subset=[code])
        out[code] = [[f, float(v)] for f, v in zip(d.observation_date, d[code])]
    return out


def fed():
    raw = fred(['DFEDTARL', 'DFEDTARU'])
    low, high = dict(raw['DFEDTARL']), dict(raw['DFEDTARU'])
    if low.keys() != high.keys() or any(low[f] > high[f] or low[f] < 0 for f in low):
        raise ValueError('Fed: límites incompatibles')
    return {'ipom_' + k: serie(n, '% anual', 'Federal Reserve Board, vía FRED',
            'https://fred.stlouisfed.org/series/' + code, raw[code],
            'Límites del rango objetivo de fondos federales. Valores oficiales diarios, incluidos ceros.', False)
            for code, k, n in [('DFEDTARL', 'fed_piso', 'Límite inferior'), ('DFEDTARU', 'fed_techo', 'Límite superior')]}


def pce():
    raw = fred(['PCEPI', 'PCEPILFE']); out = {}
    for code, k, nombre in [('PCEPI', 'pce_general', 'PCE general'), ('PCEPILFE', 'pce_nucleo', 'PCE sin alimentos ni energía')]:
        url = 'https://fred.stlouisfed.org/series/' + code
        out['ipom_' + k] = serie(nombre, 'Índice 2017=100', 'BEA, vía FRED', url, raw[code],
            'Índice encadenado de precios del consumo personal, desestacionalizado por BEA. Sujeto a revisiones oficiales.')
        for meses, suf, label in [(1, 'mensual', 'mensual'), (12, 'ia', 'interanual')]:
            out['ipom_' + k + '_' + suf] = serie(nombre, '% ' + label, 'Cálculo sobre BEA, vía FRED', url,
                variacion(raw[code], meses), f'Variación {label}: (índice t / índice t−{meses} − 1) × 100. Fechas exactas, sin imputar meses ni anualizar.')
    return out


def brasil():
    out = {}
    for idv, k, n, fuente in [(24364, 'br_ibc', 'Actividad económica de Brasil (IBC-Br)', 'Banco Central do Brasil, SGS 24364'),
                             (28505, 'br_industria', 'Producción manufacturera de Brasil', 'IBGE, PIM-PF; distribución BCB, SGS 28505')]:
        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{idv}/dados?formato=json&dataInicial=01/01/2015&dataFinal={F.HOY:%d/%m/%Y}'
        raw = json.loads(IO.descargar(url, f'brasil-{idv}.json').read_bytes())
        filas = sorted([[dt.datetime.strptime(r['data'], '%d/%m/%Y').strftime('%Y-%m-%d'), float(r['valor'])] for r in raw])
        if any(v <= 0 for _, v in filas):
            raise ValueError('Brasil: índice no positivo')
        out['ipom_' + k] = serie(n, 'Índice 2022=100, desestacionalizado', fuente, url, filas,
            'Base 2022=100 y ajuste estacional oficial. IBC-Br no equivale al PIB. Manufactura excluye extracción. No se realizan empalmes propios.')
    return out


def comercio():
    url = 'https://www.indec.gob.ar/ftp/cuadros/economia/serie_mensual_indices_comex.xls'
    d = pd.read_excel(IO.descargar(url, 'comercio.xls'), header=None)
    if 'base 2004=100' not in str(d.iloc[0, 0]):
        raise ValueError('INDEC: cambió la base de los índices de comercio')
    meses = {n: i + 1 for i, n in enumerate('ene feb mar abr may jun jul ago sep oct nov dic'.split())}
    config = {'expo_valor': (2, 'Valor exportado'), 'expo_precio': (3, 'Precios de exportación'),
              'expo_cantidad': (4, 'Cantidades exportadas'), 'impo_valor': (6, 'Valor importado'),
              'impo_precio': (7, 'Precios de importación'), 'impo_cantidad': (8, 'Cantidades importadas')}
    filas = {k: [] for k in config}; anio = None
    for _, r in d.iterrows():
        match = re.match(r'^(20\d\d)', str(r[0]))
        if match:
            anio = int(match[1])
        mes = meses.get(str(r[1]).strip().lower()[:3])
        if not anio or not mes:
            continue
        for k, (c, _) in config.items():
            if isinstance(r[c], (int, float)) and pd.notna(r[c]):
                filas[k].append([f'{anio}-{mes:02d}-01', float(r[c])])
    out = {'ipom_' + k: serie(n, 'Índice 2004=100', 'INDEC, índices del comercio exterior', url, filas[k],
            'Serie mensual original, sin desestacionalizar. Los datos recientes son provisorios y se revisan. Cantidades son índices, no toneladas.') for k, (_, n) in config.items()}
    px, pm = dict(filas['expo_precio']), dict(filas['impo_precio'])
    if px.keys() != pm.keys() or any(v <= 0 for v in pm.values()):
        raise ValueError('INDEC: precios sin fechas comunes o denominador no positivo')
    out['ipom_terminos_intercambio'] = serie('Términos del intercambio', 'Índice 2004=100', 'Cálculo sobre índices de precios del INDEC', url,
        [[f, 100 * px[f] / pm[f]] for f in sorted(px)], 'Índice de precios de exportación / índice de precios de importación × 100, mismos meses y base 2004=100.')
    for k in ['expo_cantidad', 'impo_cantidad']:
        out['ipom_' + k + '_ia'] = serie(config[k][1], '% interanual', 'Cálculo sobre índices del INDEC', url, variacion(filas[k], 12),
            '(Índice del mes / índice del mismo mes del año anterior − 1) × 100. Serie original; sin completar meses.')
    return out


def tasas_mensuales():
    IO.descargar(C.TASAS_URL, 'credito-tasas.xls')
    return normalizar(C.mensuales_tasas())


def mora():
    IO.descargar(C.BANCOS_URL, 'credito-bancos.xlsx')
    series, control = C.morosidad()
    IO.guardar_json(IO.RAW / 'morosidad-control.json', control)
    return normalizar(series)


def tasas_diarias():
    out = {}
    for idv, key, nombre in [(13, 'tasa_adelantos_diaria', 'Adelantos a empresas, 1 a 7 días'), (14, 'tasa_personales_diaria', 'Préstamos personales')]:
        registros = []; offset = 0; total = 1
        baseurl = f'https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idv}'
        while offset < total:
            url = f'{baseurl}?desde=2016-01-01&hasta={F.HOY}&limit=3000&offset={offset}'
            j = json.loads(IO.descargar(url, f'tasas-{idv}-{offset}.json').read_bytes())
            total = j['metadata']['resultset']['count']
            pagina = [r for v in j['results'] for r in v['detalle']]
            if not pagina:
                raise ValueError(f'BCRA {idv}: página vacía antes de completar la respuesta')
            registros.extend(pagina); offset += len(pagina)
        if len(registros) != total:
            raise ValueError(f'BCRA {idv}: paginación incompleta')
        filas = sorted([[r['fecha'][:10], float(r['valor'])] for r in registros if float(r['valor']) != 0])
        out['ipom_' + key] = serie(nombre, '% TNA', f'BCRA, serie monetaria {idv}', baseurl, filas,
            'Tasa nominal anual. Adelantos: empresas, acuerdo de 1 a 7 días, $10 millones o más; no empalmar con adelantos mensuales totales. Se omiten ceros de tasas aún sin cerrar, como en las referencias bancarias existentes.', False)
    return out


def cnv():
    result = CNV.construir()
    IO.guardar_json(IO.RAW / 'cnv-control.json', result['validacion'])
    return normalizar(result['series'])


# Intervalos técnicos de consulta, sin cambiar el cron del tablero.
FUENTES = {'fed': (fed, 3, 2), 'pce': (pce, 12, 6), 'brasil': (brasil, 12, 2),
           'comercio': (comercio, 12, 9), 'tasas_mensuales': (tasas_mensuales, 12, 3),
           'tasas_diarias': (tasas_diarias, 3, 2), 'mora': (mora, 12, 3), 'cnv': (cnv, 12, 13)}


def validar(series, previo=None, esperadas=None):
    if not series or (esperadas is not None and len(series) != esperadas):
        raise ValueError('Cantidad de series incompleta')
    if previo and set(previo) != set(series):
        raise ValueError('Cambió la cobertura de variables')
    for k, s in series.items():
        filas = s['d']; fechas = [f for f, _ in filas]
        if not filas or fechas != sorted(set(fechas)):
            raise ValueError(k + ': fechas vacías, duplicadas o desordenadas')
        if len(filas) < 12:
            raise ValueError(k + ': historia incompleta (menos de 12 observaciones)')
        if any(not math.isfinite(v) for _, v in filas) or fechas[-1] > str(F.HOY):
            raise ValueError(k + ': valores no finitos o fechas futuras')
        for f in fechas:
            dt.date.fromisoformat(f)
        if s['frecuencia'] == 'mensual':
            expected = pd.date_range(fechas[0], fechas[-1], freq='MS').strftime('%Y-%m-%d').tolist()
            if fechas != expected:
                raise ValueError(k + ': meses faltantes o fecha no mensual')
        if previo and not set(f for f, _ in previo[k]['d']).issubset(fechas):
            raise ValueError(k + ': la descarga recortó observaciones existentes')


def actualizar(force=False):
    DATA.mkdir(parents=True, exist_ok=True)
    IO.RAW = DATA / 'raw' / 'ipom'; C.RAW = CNV.RAW = IO.RAW
    IO.FORCE = force
    path = DATA / 'ipom.json'
    previo = json.loads(path.read_text('utf-8')) if path.exists() else {}
    series = dict(previo.get('series', {})); estados = {}; ahora = dt.datetime.now(dt.timezone.utc)
    def consultar(nombre):
        fn, horas, esperadas = FUENTES[nombre]
        old = previo.get('fuentes', {}).get(nombre, {})
        viejas = {k: series[k] for k in old.get('variables', []) if k in series}
        reciente = old.get('ok_utc') and (ahora - dt.datetime.fromisoformat(old['ok_utc'])).total_seconds() < horas * 3600
        if reciente and old.get('estado') == 'ok' and len(viejas) == esperadas and not force:
            return nombre, viejas, {**old, 'cache': True}
        try:
            nuevas = fn(); validar(nuevas, viejas, esperadas)
            return nombre, nuevas, {'estado': 'ok', 'filas': sum(len(s['d']) for s in nuevas.values()), 'variables': sorted(nuevas),
                                    'ok_utc': ahora.isoformat(), 'cache': False,
                                    'hasta': {k: s['d'][-1][0] for k, s in nuevas.items()}}
        except Exception as exc:
            return nombre, viejas, {**old, 'estado': 'PARCIAL' if viejas else 'ERROR', 'cache': bool(viejas),
                'filas': sum(len(s['d']) for s in viejas.values()), 'error': f'{type(exc).__name__}: {exc}'[:650]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(consultar, n) for n in FUENTES]):
            n, nuevas, estado = future.result(); series.update(nuevas); estados[n] = estado
            print('ipom_' + n, estado['estado'], estado.get('error', ''), flush=True)
    resultado = {'series': series, 'fuentes': estados, 'calculado_utc': ahora.isoformat()}
    IO.guardar_json(path, resultado)
    return {'ipom_' + n: estado for n, estado in estados.items()}


def verificar_archivo(path):
    obj = json.loads(path.read_text('utf-8'))
    series = {k: s for k, s in obj['series'].items() if k.startswith('ipom_')}
    validar(series, esperadas=sum(v[2] for v in FUENTES.values()))
    return len(series)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--force', action='store_true'); p.add_argument('--verificar', type=pathlib.Path)
    args = p.parse_args()
    if args.verificar:
        print('Series IPOM verificadas:', verificar_archivo(args.verificar))
    else:
        estados = actualizar(args.force)
        if any(s['estado'] != 'ok' for s in estados.values()):
            raise SystemExit(1)
