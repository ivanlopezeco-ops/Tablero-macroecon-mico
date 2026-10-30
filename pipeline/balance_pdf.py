"""Cifras del informe, separadas del registro histórico del anexo.

No se reconstruye el ajuste por tarjetas ni se empalman ambas coberturas.
Se leen las cifras publicadas en el texto y se exige coincidencia entre repeticiones.
"""
import datetime as dt
import hashlib
import io
import pathlib
import re
import unicodedata
from pypdf import PdfReader

MESES = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()


def normalizar(texto):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).replace('“', '').replace('”', '').replace('"', '')


def unico(texto, patron, nombre):
    matches = re.findall(patron, texto)
    vals = {tuple(float(v.replace('.', '').replace(' ', '')) for v in (m if isinstance(m, tuple) else (m,))) for m in matches}
    if len(vals) != 1:
        raise ValueError(f'PDF BCRA: {nombre} ausente o no unívoco')
    return next(iter(vals))


def saldo(texto, patron, nombre):
    patrones = [patron] if isinstance(patron, str) else patron
    pares = [m for p in patrones for m in re.findall(p, texto)]
    valores = {(-1 if sentido in ('compra', 'compras', 'deficit', 'deficitaria') else 1) * float(numero.replace('.', '').replace(' ', ''))
               for sentido, numero in pares}
    if len(valores) != 1:
        raise ValueError(f'PDF BCRA: {nombre} ausente o no unívoco')
    return next(iter(valores))


def parsear(texto, fecha):
    t = normalizar(texto)
    mes = MESES[fecha.month - 1]
    if not re.search(rf'{mes}\s+(?:de\s+)?{fecha.year}', t[:3000]):
        raise ValueError('PDF BCRA: período incorrecto')
    n = r'(\d+(?:\.\s*\d{3})*)'
    personas = saldo(t, [r'personas humanas\s+realizaron (compras|ventas) netas de moneda extranjera por usd\s+' + n,
        r'personas humanas tuvieron la mayor (compra|venta) neta sectorial de moneda extranjera del mes por usd\s+' + n], 'personas humanas')
    cc = saldo(t, [r'(superavit|deficit) de (?:la )?cuenta corriente de usd\s+' + n,
        r'(superavit|deficit) de usd\s+' + n + r'\s+millones en la cuenta corriente cambiaria',
        r'cuenta corriente del balance cambiario.{0,40}?(superavit|deficit) de usd\s+' + n], 'cuenta corriente')
    cf = saldo(t, r'cuenta financiera cambiaria resulto (deficitaria|superavitaria) por usd\s+' + n, 'cuenta financiera')
    out = {'personas': personas, 'cuenta_corriente': cc, 'cuenta_financiera': cf}
    # Los sectores destacados y su orden pueden cambiar entre informes.
    nombres = {'energia': 'energia', 'alimentos, bebidas y tabaco': 'alimentos', 'mineria': 'mineria',
        'industria automotriz': 'automotriz', 'comercio': 'comercio', 'industria quimica, caucho y plastico': 'quimica',
        'maquinarias y equipos': 'maquinarias', 'metales comunes y elaboracion': 'metales',
        'informatica': 'informatica', 'transporte': 'transporte', 'comunicaciones': 'comunicaciones',
        'turismo y hoteleria': 'turismo', 'agricultura, ganaderia y otras actividades primarias': 'agricultura',
        'construccion': 'construccion', 'entretenimiento': 'entretenimiento', 'gastronomia': 'gastronomia',
        'agua': 'agua', 'industria textil y curtidos': 'textil', 'otros industria manufacturera': 'otras_industrias',
        'industria de papel, ediciones e impresiones': 'papel',
        'productos minerales no metalicos': 'minerales'}
    patron = r'(superavitarios|deficitarios) fueron\s+(.{1,350}?)\s+con\s+(?:compras (?:netas )?por\s+)?(.{1,220}?)(?:respectivamente|en ese orden|mientras que)'
    for sentido, etiquetas, cifras in re.findall(patron, t):
        sectores = sorted((etiquetas.index(nombre), key) for nombre, key in nombres.items() if nombre in etiquetas)
        montos = [float(v.replace('.', '').replace(' ', '')) for v in re.findall(r'usd\s+' + n + r'\s+millones', cifras)]
        if not sectores or len(sectores) != len(montos):
            raise ValueError('PDF BCRA: no se pudo vincular la lista de sectores con sus importes')
        for (_, key), v in zip(sectores, montos):
            valor = -v if sentido == 'deficitarios' else v
            if key in out and out[key] != valor:
                raise ValueError('PDF BCRA: resultados sectoriales contradictorios')
            out[key] = valor
    agro = re.findall(r'(?<!excluyendo )oleaginos[ao]s y cereales.{0,110}?(ventas|compras) netas por usd\s+' + n, t)
    if agro:
        out['agro'] = saldo(t, r'(?<!excluyendo )oleaginos[ao]s y cereales.{0,110}?(ventas|compras) netas por usd\s+' + n, 'oleaginosas y cereales')
    if len(out) < 4:
        raise ValueError('PDF BCRA: no se reconocieron cifras sectoriales')
    return out


def consultar(df, get):
    fecha = df.loc[df.variable.eq('bc_cuenta_corriente'), 'fecha'].max()
    url = f'https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/informe-mercado-cambios-balance-cambiario-{fecha:%Y-%m}.pdf'
    r = get(url, timeout=60, intentos=2)
    if not r.content.startswith(b'%PDF'):
        raise ValueError('BCRA: el informe no es un PDF')
    reader = PdfReader(io.BytesIO(r.content))
    texto = '\n'.join(p.extract_text() or '' for p in reader.pages)
    valores = parsear(texto, fecha)
    for nombre in ['cuenta_corriente', 'cuenta_financiera']:
        valor = float(df.loc[df.variable.eq('bc_' + nombre) & df.fecha.eq(fecha), 'valor'].iloc[0])
        if abs(valor - valores[nombre]) > 0.51:
            raise ValueError(f'PDF y anexo BCRA difieren en {nombre}')
    base = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'raw' / 'balance-pdf'
    base.mkdir(parents=True, exist_ok=True)
    path = base / f'{fecha:%Y-%m}.pdf'
    temp = path.with_suffix('.tmp'); temp.write_bytes(r.content); temp.replace(path)
    return {'fecha': str(fecha), 'url': url, 'valores': valores,
            'sha256': hashlib.sha256(r.content).hexdigest(), 'consulta_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'cobertura': 'Resultado del informe PDF, con exclusión de cancelaciones de deudas locales por tarjetas. Valores redondeados por BCRA; no se empalma con el registro del Excel.'}
