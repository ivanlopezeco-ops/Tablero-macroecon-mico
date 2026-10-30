"""Fuentes CNV automáticas: flujos mensuales en pesos corrientes.

La planilla PyME publica montos mensuales y total por instrumento. El total
del mercado se toma del resumen de cada informe mensual (mes corriente),
no de sus acumulados ni de sus gráficos históricos a precios constantes.
No se convierten monedas ni se agregan las emisiones individuales de ON.
"""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
from ipom_io import RAW, descargar
PYME_URL = "https://www.cnv.gov.ar/descargas/informes/blob/a516e7cb-7ca6-4d8c-9a55-192bb68c6e7d"
INDEX_URL = "https://docs.google.com/spreadsheets/d/1zOYFDMMSTZ7e6mgDSCMQ7Jwd5qFCmfJ76AI-uzHN-Bk/export?format=csv"
PAGE_URL = "https://www.argentina.gob.ar/cnv/informes-del-mercado-de-capitales"
MONTHS = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
INSTRUMENTOS = {
    "cnv_on": ("Obligaciones negociables", r"Se\s+emitieron\s+[\d.]+\s+obligaciones\s+negociables\s+por\s*\$\s*([\d.,]+)\s*millones"),
    "cnv_cpd": ("Cheques de pago diferido", r"volumen\s+nominal\s+negociado\s+de\s+Cheques\s+de\s+Pago\s+Diferido\s+ascendi[oó]\s+a\s*\$\s*([\d.,]+)\s*millones"),
    "cnv_pagares": ("Pagarés", r"negociaci[oó]n\s+de\s+pagar[eé]s\s+en\s+\w+\s+alcanz[oó]\s+el\s+valor\s+de\s*\$\s*([\d.,]+)\s*millones"),
    "cnv_ff": ("Fideicomisos financieros", r"Se\s+colocaron\s+[\d.]+\s+fideicomisos\s+financieros\s+por\s+un\s+monto\s+de\s*\$\s*([\d.,]+)\s*millones"),
    "cnv_fce": ("Facturas de crédito electrónicas", r"Se\s+negociaron\s+[\d.]+\s+facturas\s+de\s+cr[eé]dito\s+electr[oó]nicas\s+por\s*\$\s*([\d.,]+)\s*millones"),
}


def monto(text):
    # Informes expresados en millones enteros: en mayo-2024 el cuerpo usa
    # 1,299.707, pero resumen y panel usan 1.299.707. Ambos son grupos de miles.
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", text):
        return float(re.sub(r"[.,]", "", text))
    return float(text.replace(".", "").replace(",", "."))


def download(url, name):
    # Revisar PDF históricos semanalmente; los tres últimos meses, en cada consulta.
    reciente = name >= 'cnv-informe-' + (pd.Timestamp.now()-pd.DateOffset(months=3)).strftime('%Y-%m')
    horas = 168 if name.endswith('.pdf') and not reciente else 0
    return descargar(url, name, horas)

def enlaces_vigentes():
    global INDEX_URL, PYME_URL
    pagina = download(PAGE_URL, 'cnv-informes.html').read_text('utf-8')
    match = re.search(r'"idSpread"\s*:\s*"([\w-]+)"', pagina)
    if not match:
        raise ValueError('CNV: no se encontró el listado oficial de informes')
    INDEX_URL = 'https://docs.google.com/spreadsheets/d/' + match[1] + '/export?format=csv'
    from lxml import html
    doc = html.fromstring(download('https://www.cnv.gov.ar/sitioWeb/Informes?columna=2', 'cnv-series.html').read_bytes())
    enlaces = doc.xpath('//tr[td[contains(., "Financiamiento PyME por instrumento")]]//a/@href')
    if len(enlaces) != 1 or not enlaces[0].startswith('https://www.cnv.gov.ar/descargas/'):
        raise ValueError('CNV: enlace PyME no reconocido')
    PYME_URL = enlaces[0]


def report_list():
    path = download(INDEX_URL, "cnv-listado.csv")
    reports = []
    for row in csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))):
        if len(row) < 3 or not row[0].isdigit() or int(row[0]) < 2025:
            continue
        month = MONTHS.get(row[1].strip().lower())
        if not month:
            continue
        date = f"{row[0]}-{month:02d}-01"
        reports.append((date, row[2].strip()))
    return sorted(reports)


def extract_report(report):
    date, url = report
    path = download(url, f"cnv-informe-{date[:7]}.pdf")
    reader = PdfReader(path)
    # Executive summary before instrument chapters; preserve the source excerpt.
    text = " ".join(p.extract_text() or "" for p in reader.pages[1:6])
    text = re.sub(r"\s+", " ", text)
    match = re.search(r"financiamiento\s+total\s+(?:(?:de\s+\w+|del\s+primer\s+mes\s+del\s+año)\s+)?(?:ascendi[oó]\s+a|alcanz[oó](?:\s+los)?)\s*\$\s*([\d.,]+)\s*millones", text, re.I)
    if not match:
        match = re.search(r"financiamiento\s+total\s+obtenido\s+(?:durante|en)\s+\w+\s+(?:de\s+\d{4}\s+)?(?:ascendi[oó]\s+a|fue\s+de)\s*\$\s*([\d.,]+)\s*millones", text, re.I)
    if not match:
        (RAW / f"cnv-no-extraido-{date[:7]}.txt").write_text(text, encoding="utf-8")
        return {"fecha": date, "url": url, "error": "No se reconoció el total mensual; requiere revisión"}
    value = monto(match.group(1))
    other = re.search(r"(?:argentino\s+ascendi[oó]\s+a|TOTAL\s+FINANCIAMIENTO)\s*\$?\s*([\d.,]+)\s*millones", text, re.I)
    check = monto(other.group(1)) if other else None
    if check is None or abs(check-value) > 1:
        raise ValueError(f"No coincide el total del resumen con el cuerpo: {date}: {value} / {check}")
    selected = {}
    summary = re.sub(r"\s+", " ", reader.pages[2].extract_text() or "")
    for key, (_, pattern) in INSTRUMENTOS.items():
        found = re.search(pattern, summary, re.I)
        if not found:
            raise ValueError(f"No se reconoció el instrumento {key} en {date}")
        selected[key] = monto(found.group(1))
    if sum(selected.values()) > value + 3:
        raise ValueError(f"Instrumentos superan el total publicado: {date}")
    return {"fecha": date, "url": url, "valor": value, "instrumentos": selected, "resto_no_desagregado": value-sum(selected.values()), "control_total_cuerpo": check, "extracto": text[max(0,match.start()-40):match.end()+150], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def construir():
    enlaces_vigentes()
    path = download(PYME_URL, "cnv-pyme.xlsx")
    raw = pd.read_excel(path, header=None)
    if "millones de pesos corrientes" not in str(raw.iloc[1,0]).lower():
        raise ValueError("Cambió la unidad del Excel PyME")
    frame = raw.iloc[7:].copy()
    frame = frame[frame.iloc[:,1].apply(lambda value: isinstance(value, (dt.datetime, pd.Timestamp)))]
    if frame.empty:
        raise ValueError("Planilla PyME sin datos mensuales")
    dates = [value.strftime("%Y-%m-%d") for value in frame.iloc[:,1]]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("Fechas PyME repetidas o desordenadas")
    expected = pd.date_range(dates[0], dates[-1], freq="MS").strftime("%Y-%m-%d").tolist()
    if dates != expected:
        raise ValueError("Faltan meses en la planilla PyME")
    values = frame.iloc[:,2:9].astype(float)
    residual = (values.iloc[:,:6].sum(axis=1) - values.iloc[:,6]).abs().max()
    if residual > 0.000001 or not values.map(math.isfinite).all().all() or (values < 0).any().any():
        raise ValueError("No concilia la planilla PyME o tiene valores inválidos")
    mapping = [
        ("cnv_pyme_on", "PyME: obligaciones negociables"),
        ("cnv_pyme_ff", "PyME: fideicomisos financieros"),
        ("cnv_pyme_cpd_avalados", "PyME: cheques avalados"),
        ("cnv_pyme_cpd_directos", "PyME: cheques directos"),
        ("cnv_pyme_pagares", "PyME: pagarés"),
        ("cnv_pyme_fce", "PyME: facturas de crédito electrónicas"),
        ("cnv_pyme_total", "Financiamiento PyME total"),
    ]
    series = {}
    for col, (key, title) in enumerate(mapping):
        series[key] = {"nombre": title, "unidad": "Millones de pesos corrientes", "fuente": "CNV, Financiamiento PyME por instrumento", "url": PYME_URL, "frecuencia": "mensual", "datos": [[f, float(v)] for f,v in zip(dates, values.iloc[:,col])], "tipo_dato": "Flujo mensual nominal"}
    with ThreadPoolExecutor(max_workers=5) as pool:
        reports = list(pool.map(extract_report, report_list()))
    good = [x for x in reports if "valor" in x]
    errors = [x for x in reports if "error" in x]
    if errors:
        raise ValueError(f"Informes sin total reconocido: {errors}")
    total_dates = [x["fecha"] for x in good]
    if total_dates != pd.date_range(total_dates[0], total_dates[-1], freq="MS").strftime("%Y-%m-%d").tolist():
        raise ValueError("Meses faltantes en el total del mercado")
    pyme_by_date = dict(series["cnv_pyme_total"]["datos"])
    if any(pyme_by_date[x["fecha"]] > x["valor"] for x in good if x["fecha"] in pyme_by_date):
        raise ValueError("PyME supera el total del mercado")
    series["cnv_total"] = {"nombre": "Financiamiento total en el mercado de capitales", "unidad": "Millones de pesos corrientes", "fuente": "CNV, informe mensual de financiamiento; total del mes de cada edición", "url": PAGE_URL, "frecuencia": "mensual", "datos": [[x["fecha"],x["valor"]] for x in good], "tipo_dato": "Flujo mensual nominal", "urls_por_periodo": {x["fecha"]:x["url"] for x in good}}
    for key, (title, _) in INSTRUMENTOS.items():
        series[key] = {**series["cnv_total"], "nombre": title, "datos": [[x["fecha"],x["instrumentos"][key]] for x in good], "fuente": "CNV, resumen ejecutivo de cada informe mensual; instrumentos seleccionados"}
    result = {"series": series, "notas": [
        "Montos mensuales, no acumulados. Valores nominales en millones de pesos corrientes; no miden crecimiento real.",
        "El financiamiento PyME es parte del total del mercado: no se suma a este ni a los saldos de crédito bancario.",
        "PyME por instrumento reproduce la planilla oficial de la CNV; las seis categorías concilian con el total publicado.",
        "El total del mercado se extrae del resumen ejecutivo de cada informe mensual. El valor del mes en pesos constantes de ese mismo mes equivale a pesos corrientes; no se utilizan acumulados reexpresados ni conversiones cambiarias propias.",
        "No se reconstruye el total con la base de ON por emisión, que mezcla monedas nominales."
        ,"La serie total comienza en enero de 2025. En la exploración de 2024 se detectó una discrepancia interna en julio (resumen: 2.603.255; cuerpo: 2.603.655 millones); no se incorporó 2024 ni se resolvió esa diferencia por cuenta propia."
        ,"Instrumentos del mercado total: se muestran ON, CPD, pagarés, fideicomisos financieros y FCE. Acciones y fondos cerrados están incluidos en el total publicado, pero no se desagregan: la suma de las cinco líneas no siempre coincide con el total."
    ], "validacion": {"pyme_meses":len(dates),"pyme_desde":dates[0],"pyme_hasta":dates[-1],"pyme_residuo_max_millones":float(residual),"total_meses":len(good),"total_desde":total_dates[0],"total_hasta":total_dates[-1],"total_controles_cuerpo":sum(x["control_total_cuerpo"] is not None for x in good),"errores_extraccion":errors,"total_fuentes":reports,"sha256_pyme":hashlib.sha256(path.read_bytes()).hexdigest()}}

    return result
