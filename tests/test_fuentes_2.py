"""Segunda vuelta de tests: lo que quedó pendiente en la primera."""
import datetime as dt
import json
import pathlib
import re

import requests
import urllib3

urllib3.disable_warnings()

OUT = pathlib.Path("results")
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
rep = []


def log(titulo, texto):
    rep.append(f"## {titulo}\n```\n{str(texto)[:3000]}\n```\n")
    print("==", titulo)


def get(url, **kw):
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", 60)
    return requests.get(url, **kw)


# 1) Lista completa de variables del BCRA v4
try:
    todas = []
    offset = 0
    while True:
        r = get(f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias?limit=1000&offset={offset}").json()
        todas += r["results"]
        offset += 1000
        if offset >= r["metadata"]["resultset"]["count"]:
            break
    (OUT / "bcra_variables.json").write_text(json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8")
    pat = re.compile(r"banda|compra|divisa|efectivo m|encaje|cuenta corriente|d[oó]lares|moneda extranjera|tesoro|gobierno|m2", re.I)
    lineas = [f"{v['idVariable']} | {v['descripcion'][:100]} | {v['periodicidad']} | {v['ultFechaInformada']}"
              for v in todas if pat.search(v["descripcion"]) and v["periodicidad"] == "D"]
    log(f"BCRA v4: {len(todas)} variables. Filtradas (diarias)", "\n".join(lineas))
except Exception as e:  # noqa: BLE001
    log("BCRA v4 lista completa ERROR", e)

# 2) BYMA panel de bonos con distintos cuerpos + históricos clave
BYMA = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
H = {**UA, "Content-Type": "application/json", "Origin": "https://open.bymadata.com.ar",
     "Referer": "https://open.bymadata.com.ar/"}
for body in [{"T1": True, "T0": False, "Content-Type": "application/json"},
             {"excludeZeroPxAndQty": False, "T2": True, "T1": False, "T0": False},
             {"excludeZeroPxAndQty": False, "T1": True, "T0": False, "page_number": 1, "page_size": 500}]:
    for ep in ["public-bonds", "lebacs"]:
        try:
            r = requests.post(f"{BYMA}/{ep}", json=body, headers=H, verify=False, timeout=60)
            j = r.json()
            n = len(j.get("data", j)) if isinstance(j, (dict, list)) else 0
            syms = [x.get("symbol") for x in (j.get("data", []) if isinstance(j, dict) else j)][:40]
            log(f"BYMA {ep} body={body}", f"status {r.status_code} n={n}\n{syms}")
        except Exception as e:  # noqa: BLE001
            log(f"BYMA {ep} ERROR", e)

desde = int(dt.datetime(2026, 9, 25).timestamp())
hasta = int(dt.datetime.now().timestamp())
for sym in ["AL30 24HS", "AL30D 24HS", "AL30C 24HS", "GD30 24HS", "GD30C 24HS", "GD35C 24HS", "S30O6 24HS", "MERV"]:
    try:
        r = get(f"{BYMA}/chart/historical-series/history", params={"symbol": sym, "resolution": "D",
                "from": desde, "to": hasta}, verify=False)
        j = r.json()
        log(f"BYMA histórico {sym}", f"{j.get('s')} n={len(j.get('t', []))} cierres={j.get('c', [])[-5:]}")
    except Exception as e:  # noqa: BLE001
        log(f"BYMA histórico {sym} ERROR", e)

# 3) Yahoo Finance como alternativa a FRED/Stooq (fuente de terceros)
for t in ["^VIX", "BZ=F", "DX-Y.NYB", "BRL=X", "GC=F", "ZS=F", "^TNX"]:
    try:
        r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"range": "1mo", "interval": "1d"})
        res = r.json()["chart"]["result"][0]
        ts = [dt.date.fromtimestamp(x).isoformat() for x in res["timestamp"][-3:]]
        cl = res["indicators"]["quote"][0]["close"][-3:]
        log(f"Yahoo {t}", f"status {r.status_code} {list(zip(ts, cl))}")
    except Exception as e:  # noqa: BLE001
        log(f"Yahoo {t} ERROR", e)

try:
    r = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2026-09-20", timeout=120)
    log("FRED reintento 120s", f"{r.status_code} {r.text[:300]}")
except Exception as e:  # noqa: BLE001
    log("FRED reintento ERROR", e)

# 4) API interna de A3/MAE: buscar rutas en el JS de la web
try:
    html = get("https://marketdata.mae.com.ar/").text
    rutas = set()
    for s in re.findall(r'src="([^"]+\.js)"', html):
        u = s if s.startswith("http") else "https://marketdata.mae.com.ar/" + s.lstrip("/")
        js = get(u).text
        rutas |= set(re.findall(r'["`](/?api/[A-Za-z0-9_/\-{}$.]+)["`]', js))
        rutas |= set(re.findall(r'["`](/[a-z]+(?:/[A-Za-z0-9_\-]+){1,4})["`]', js))
    log("A3/MAE rutas en JS", "\n".join(sorted(rutas)[:200]))
except Exception as e:  # noqa: BLE001
    log("A3/MAE JS ERROR", e)

for ruta in ["mercado/forex", "forex", "mercado/boletin", "cotizaciones/forex", "renta-fija", "mercado/volumen"]:
    try:
        r = get(f"https://api.marketdata.mae.com.ar/api/{ruta}")
        log(f"MAE api/{ruta}", f"{r.status_code} {r.text[:400]}")
    except Exception as e:  # noqa: BLE001
        log(f"MAE api/{ruta} ERROR", e)


# 5) Páginas del BCRA y Mecon: links a archivos descargables
def links(url):
    try:
        r = get(url)
        ls = re.findall(r'href="([^"]+\.(?:xls|xlsx|xlsm|csv|zip|pdf))"', r.text, re.I)
        return f"status {r.status_code}\n" + "\n".join(sorted(set(ls))[:60])
    except Exception as e:  # noqa: BLE001
        return f"ERROR {e}"


for nombre, url in [
    ("BCRA mercado de cambios", "https://www.bcra.gob.ar/estadisticas-estandarizadas-sobre-la-evolucion-del-mercado-de-cambios/"),
    ("BCRA ITCRM", "https://www.bcra.gob.ar/indices-de-tipo-de-cambio-multilateral/"),
    ("BCRA REM", "https://www.bcra.gob.ar/relevamiento-de-expectativas-de-mercado-rem/"),
    ("BCRA REM (asp)", "https://www.bcra.gob.ar/PublicacionesEstadisticas/Relevamiento_Expectativas_de_Mercado.asp"),
    ("BCRA balance semanal", "https://www.bcra.gob.ar/PublicacionesEstadisticas/Balances_semanales.asp"),
    ("BCRA serie diaria txt", "https://www.bcra.gob.ar/consulta-de-series-estadisticas-en-formato-txt/"),
    ("Mecon licitaciones (node 83197)", "https://www.argentina.gob.ar/node/83197"),
    ("Mecon finanzas", "https://www.argentina.gob.ar/economia/finanzas"),
    ("indicadores.ar licitaciones", "https://indicadores.ar/licitaciones-tesoro"),
]:
    log(f"Links: {nombre}", links(url))

(OUT / "test_report_2.md").write_text(f"# Test 2 — {dt.datetime.utcnow().isoformat()}Z\n\n" + "\n".join(rep), encoding="utf-8")
