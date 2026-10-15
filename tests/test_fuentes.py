"""Prueba de fuentes del tablero macro.

Corre cada endpoint, registra estado HTTP, tamaño y una muestra de la respuesta,
y escribe el resultado en results/test_report.md y results/samples/.
"""
import datetime as dt
import json
import pathlib
import re
import traceback

import requests
import urllib3

urllib3.disable_warnings()

OUT = pathlib.Path("results")
SAMPLES = OUT / "samples"
SAMPLES.mkdir(parents=True, exist_ok=True)

HOY = dt.date.today()
DESDE = (HOY - dt.timedelta(days=20)).isoformat()
HASTA = HOY.isoformat()
UA = {"User-Agent": "Mozilla/5.0 (tablero-macro test)"}

TESTS = []


def test(nombre, url, method="GET", verify=True, **kw):
    TESTS.append((nombre, url, method, verify, kw))


# --- BCRA ---
test("BCRA v4 lista de variables", "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias")
test("BCRA v4 reservas (id 1)", f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/1?desde={DESDE}&hasta={HASTA}")
test("BCRA cambiarias cotizaciones", "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones")
test("BCRA series.xlsm", "https://www.bcra.gob.ar/Pdfs/PublicacionesEstadisticas/series.xlsm")

# --- Riesgo país ---
test("BCRD EMBI xlsx", "https://bcrdgdcprod.blob.core.windows.net/documents/entorno-internacional/documents/Serie_Historica_Spread_del_EMBI.xlsx")
test("BCRP EMBIG Arg/LatAm", f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04710XD-PD04708XD/json/{DESDE}/{HASTA}")
test("ArgentinaDatos riesgo país último", "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo")
test("ArgentinaDatos dólar MEP", "https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa")
test("ArgentinaDatos dólar CCL", "https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui")

# --- BYMA open data (no documentado) ---
BYMA = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
BODY = {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False, "Content-Type": "application/json"}
for ep in ["public-bonds", "lebacs", "short-term-government-bonds", "cauciones", "negociable-obligations"]:
    test(f"BYMA {ep}", f"{BYMA}/{ep}", method="POST", verify=False, json=BODY,
         headers={**UA, "Content-Type": "application/json"})
test("BYMA histórico AL30", f"{BYMA}/chart/historical-series/history?symbol=AL30%2024HS&resolution=D"
     f"&from={int(dt.datetime(2026, 9, 1).timestamp())}&to={int(dt.datetime.now().timestamp())}", verify=False)

# --- A3 / Matba Rofex / MAE ---
test("Matba Rofex API CEM", "https://apicem.matbarofex.com.ar/api/v2/closing-prices?product=DLR"
     f"&from={DESDE}&to={HASTA}&version=v2")
test("A3 MAE marketdata home", "https://marketdata.mae.com.ar/")

# --- CAMMESA ---
test("CAMMESA demanda región", "https://api.cammesa.com/demanda-svc/demanda/ObtieneDemandaYTemperaturaRegion?id_region=1002")

# --- Internacional ---
test("Tesoro EE.UU. curva CSV", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
     f"daily-treasury-rates.csv/{HOY.year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={HOY.year}&page&_format=csv")
test("FRED VIX/Brent/DXY/BRL", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS,DCOILBRENTEU,DTWEXBGS,DEXBZUS"
     f"&cosd={DESDE}")
test("Stooq oro", "https://stooq.com/q/d/l/?s=xauusd&i=d")
test("Stooq soja", "https://stooq.com/q/d/l/?s=zs.f&i=d")

# --- INDEC / Mecon ---
test("datos.gob.ar IPC", "https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26&last=3")
test("Mecon licitaciones", "https://www.argentina.gob.ar/economia/finanzas/licitaciones")


def correr():
    filas = []
    for i, (nombre, url, method, verify, kw) in enumerate(TESTS):
        kw.setdefault("headers", UA)
        try:
            r = requests.request(method, url, timeout=40, verify=verify, **kw)
            ct = r.headers.get("content-type", "")
            body = r.content
            ext = "json" if "json" in ct else ("csv" if "csv" in ct else ("html" if "html" in ct else "bin"))
            (SAMPLES / f"{i:02d}.{ext}").write_bytes(body[:200_000])
            if "json" in ct or "csv" in ct or "text" in ct:
                muestra = r.text[:600].replace("\n", " ")
            else:
                muestra = f"[binario {len(body)} bytes]"
            estado = r.status_code
        except Exception as e:  # noqa: BLE001
            estado, ct, body, muestra = "ERROR", "", b"", f"{type(e).__name__}: {e}"[:400]
        filas.append((i, nombre, estado, len(body), ct, muestra))
        print(i, nombre, estado, len(body))

    # Extras: endpoints de la web de A3 (para encontrar la API que alimenta la página)
    extra = ""
    try:
        html = (SAMPLES / f"{[f[0] for f in filas if f[1]=='A3 MAE marketdata home'][0]:02d}.html").read_text(errors="ignore")
        scripts = re.findall(r'src="([^"]+\.js)"', html)
        urls = set()
        for s in scripts[:6]:
            u = s if s.startswith("http") else "https://marketdata.mae.com.ar/" + s.lstrip("/")
            js = requests.get(u, timeout=40, headers=UA).text
            urls |= set(re.findall(r'https?://[a-zA-Z0-9./_-]*api[a-zA-Z0-9./_-]*', js))
        extra = "\n".join(sorted(urls))
    except Exception:  # noqa: BLE001
        extra = traceback.format_exc()[-500:]

    with open(OUT / "test_report.md", "w", encoding="utf-8") as f:
        f.write(f"# Test de fuentes — {dt.datetime.utcnow().isoformat()}Z\n\n")
        for i, n, e, size, ct, m in filas:
            f.write(f"## {i:02d}. {n}\n- estado: {e} | bytes: {size} | tipo: {ct}\n- muestra: `{m}`\n\n")
        f.write("## URLs de API encontradas en la web de A3\n```\n" + extra + "\n```\n")


if __name__ == "__main__":
    correr()
