"""Aperturas del balance: mismo universo y conciliación antes de exportar."""
import datetime as dt
import io
import json
import pathlib
import pandas as pd

VERSION = 2
MLC = {
    'mlc005': 'mcc_cobros_expo', 'mlc006': 'mcc_cobros_anticipados',
    'mlc007': 'mcc_financ_locales_expo', 'mlc008': 'mcc_prefinanciaciones',
    'mlc009': 'mcc_otros_cobros_bienes',
    'mlc010': 'mcc_pagos_importaciones', 'mlc011': 'mcc_impo_anticipados', 'mlc012': 'mcc_impo_vista', 'mlc013': 'mcc_impo_diferidos',
    'mlc057': 'bc_dividendos_egresos', 'mlc058': 'bc_remuneraciones_egresos',
    'mlc059': 'bc_otras_rentas_egresos',
    'mlc079': 'mcc_deuda_ext_ing', 'mlc084': 'mcc_deuda_ext_egr',
    'mlc080': 'mcc_lineas_ing', 'mlc085': 'mcc_lineas_egr',
    'mlc081': 'mcc_financ_locales_ing', 'mlc086': 'mcc_financ_locales_egr',
    'mlc089': 'bc_spnf_billetes_ing', 'mlc090': 'bc_spnf_ide_ing', 'mlc091': 'bc_spnf_otras_ing',
    'mlc093': 'bc_spnf_billetes_egr', 'mlc094': 'bc_spnf_ide_egr', 'mlc095': 'bc_spnf_otras_egr',
}
IDENTIDADES = {
    'bc_cuenta_corriente': ['bc_bienes', 'bc_servicios', 'bc_ingreso_primario', 'bc_ingreso_secundario'],
    'bc_cuenta_financiera': ['bc_ied', 'bc_portafolio', 'bc_prestamos_titulos_deuda', 'bc_fmi',
        'bc_otros_organismos', 'bc_billetes_divisas_spnf', 'bc_canje', 'bc_fae_sector_financiero',
        'bc_fae_sector_publico', 'bc_titulos_valores', 'bc_otras_spn', 'bc_otros_movimientos', 'bc_cf_diferencia_anexo'],
    'bcs_total': ['bcs_spnf', 'bcs_financiero', 'bcs_gobierno_bcra', 'bcs_otros'],
    'bc_bienes': ['bc_cobros_exportaciones', 'bc_pagos_importaciones'],
    'bc_cobros_exportaciones': ['mcc_cobros_expo', 'mcc_cobros_anticipados', 'mcc_financ_locales_expo',
        'mcc_prefinanciaciones', 'mcc_otros_cobros_bienes'],
    'mcc_pagos_importaciones': ['mcc_impo_anticipados', 'mcc_impo_vista', 'mcc_impo_diferidos'],
    'bc_billetes_divisas_spnf': ['bc_spnf_billetes_ing', 'bc_spnf_ide_ing', 'bc_spnf_otras_ing',
        'bc_spnf_billetes_egr', 'bc_spnf_ide_egr', 'bc_spnf_otras_egr'],
    'bc_prestamos_titulos_deuda': ['mcc_deuda_ext_ing', 'mcc_deuda_ext_egr', 'mcc_lineas_ing',
        'mcc_lineas_egr', 'mcc_financ_locales_ing', 'mcc_financ_locales_egr'],
    'bc_utilidades_egresos': ['bc_dividendos_egresos', 'bc_remuneraciones_egresos', 'bc_otras_rentas_egresos'],
    'bc_rentas_egresos': ['bc_intereses_fmi', 'bc_intereses_otros_org', 'bc_intereses_otros',
        'bc_intereses_otros_gob', 'bc_dividendos_egresos', 'bc_remuneraciones_egresos', 'bc_otras_rentas_egresos'],
    'bc_var_reservas_transacciones': ['bc_cuenta_corriente', 'bc_cuenta_capital', 'bc_cuenta_financiera', 'bc_no_informado'],
    'bc_var_reservas_contable': ['bc_var_reservas_transacciones', 'bc_ajuste_valuacion'],
    'bc_viajes_pasajes_neto': ['bc_viajes_ingresos', 'bc_viajes_egresos'],
}


def conciliar(df, tolerancia=0.002):
    w = df.pivot(index='fecha', columns='variable', values='valor')
    controles = []
    for total, partes in IDENTIDADES.items():
        if not set([total, *partes]) <= set(w.columns):
            raise ValueError('Balance: faltan componentes de ' + total)
        s = w[[total, *partes]]
        # No aceptar huecos en las aperturas durante la cobertura del total.
        s = s[s[total].notna()]
        if s.isna().any().any():
            raise ValueError('Balance: apertura incompleta de ' + total)
        dif = s[total] - s[partes].sum(axis=1)
        limite = tolerancia if tolerancia is not None else 0.005 * (len(partes) + 1) + 0.000001
        if dif.abs().max() > limite:
            f = dif.abs().idxmax()
            raise ValueError(f'Balance no concilia {total} {f}: diferencia {dif.loc[f]:.6f} USD M')
        controles.append({'total': total, 'meses': len(s), 'diferencia_maxima': float(dif.abs().max())})
    return controles


def completar(contenido, df):
    h = pd.read_excel(io.BytesIO(contenido), sheet_name='Mercado de Cambios', header=None)
    codigos = h.iloc[10].tolist()
    if not set(MLC) <= set(str(c) for c in codigos):
        raise ValueError('BCRA: cambió la estructura de Mercado de Cambios')
    meses = h[h[0].apply(lambda f: isinstance(f, (dt.datetime, pd.Timestamp)))]
    filas = [(f.date(), MLC[c], float(v), 'USD M', f'BCRA Mercado de Cambios ({c}); universo oficial de la cuenta')
             for col, c in enumerate(codigos) if c in MLC
             for f, v in zip(meses[0], meses[col]) if pd.notna(v)]
    extra = pd.DataFrame(filas, columns=df.columns)
    out = pd.concat([df[~df.variable.isin(MLC.values())], extra], ignore_index=True)
    # Egresos de intereses (bal011) más egresos de utilidades, remuneraciones y otras rentas.
    b = pd.read_excel(io.BytesIO(contenido), sheet_name='Balance Cambiario', header=None)
    cod = b.iloc[10].tolist(); ms = b[b[0].apply(lambda f: isinstance(f, (dt.datetime, pd.Timestamp)))]
    pagos = [(f.date(), 'bc_rentas_egresos', -float(i)-float(r), 'USD M', 'BCRA balance cambiario: -(bal011 + bal018)')
             for f, i, r in zip(ms[0], ms[cod.index('bal011')], ms[cod.index('bal018')])]
    out = pd.concat([out, pd.DataFrame(pagos, columns=df.columns)], ignore_index=True)
    w = out.pivot(index='fecha', columns='variable', values='valor')
    partes = [v for v in IDENTIDADES['bc_cuenta_financiera'] if v != 'bc_cf_diferencia_anexo']
    diferencia = w['bc_cuenta_financiera'] - w[partes].sum(axis=1)
    # El anexo vigente tiene diferencias internas en 2019-2022, hasta USD 5,1543 M.
    # Exponerlas conserva los totales oficiales y no inventa una atribución económica.
    # No aceptar nuevas diferencias en los últimos 24 meses como si fueran históricas.
    reciente = diferencia[pd.to_datetime(diferencia.index) >= pd.Timestamp(diferencia.index.max()) - pd.DateOffset(months=23)]
    if reciente.abs().max() > 0.002:
        raise ValueError('BCRA: la cuenta financiera reciente no concilia; requiere revisión del anexo')
    ajustes = [(f, 'bc_cf_diferencia_anexo', float(v) if abs(v) > 0.002 else 0.0, 'USD M',
                'Diferencia aritmética entre total y componentes del anexo BCRA; sin atribución económica')
               for f, v in diferencia.items()]
    out = pd.concat([out, pd.DataFrame(ajustes, columns=df.columns)], ignore_index=True)
    controles = conciliar(out)
    out.attrs.update(version_fuente=VERSION, conciliaciones=controles)
    return out


def verificar(path):
    obj = json.loads(pathlib.Path(path).read_text(encoding='utf8'))
    meta = obj['estado']['fuentes']['balance_cambiario']
    if meta.get('version_fuente') != VERSION or meta['estado'] != 'ok':
        raise ValueError('Balance corregido sin actualización válida')
    filas = []
    variables = set(IDENTIDADES) | {v for ps in IDENTIDADES.values() for v in ps}
    for v in variables:
        s = obj['series'][v]; dia = 0
        for delta, valor in zip(s['t'], s['v']):
            dia += delta
            filas.append((dt.date(1970, 1, 1) + dt.timedelta(days=dia), v, valor))
    # Cada importe del balance se exporta con dos decimales: límite de redondeo por componente.
    df = pd.DataFrame(filas, columns=['fecha', 'variable', 'valor'])
    pdf = meta.get('resumen_pdf', {})
    ultima = df.loc[df.variable.eq('bc_cuenta_corriente'), 'fecha'].max()
    if pdf.get('fecha') != str(ultima) or not pdf.get('sha256') or 'personas' not in pdf.get('valores', {}):
        raise ValueError('Informe PDF ausente o de un período distinto del anexo')
    for nombre in ['cuenta_corriente', 'cuenta_financiera']:
        valor = df.loc[df.variable.eq('bc_' + nombre) & df.fecha.eq(ultima), 'valor'].iloc[0]
        if abs(valor - pdf['valores'][nombre]) > 0.51:
            raise ValueError('Balance publicado no coincide con PDF: ' + nombre)
    return conciliar(df, tolerancia=None)


if __name__ == '__main__':
    import sys
    print(json.dumps(verificar(sys.argv[1]), ensure_ascii=False))
