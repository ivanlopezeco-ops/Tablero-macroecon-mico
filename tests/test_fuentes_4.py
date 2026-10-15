"""Profundidad histórica de cada fuente."""
import datetime as dt, io, json, pathlib, traceback
import requests, urllib3
urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
out = []


def T(nombre, fn):
    try:
        out.append(f"## {nombre}\n{fn()}\n")
    except Exception:
        out.append(f"## {nombre}\nERROR {traceback.format_exc()[-600:]}\n")


def bcra(idv, desde, extra=""):
    r = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idv}?desde={desde}&hasta=2026-10-14&limit=3000{extra}", headers=UA, timeout=90)
    j = r.json()
    det = j["results"][0]["detalle"] if j.get("results") else []
    return f"{r.status_code} meta={j.get('metadata')} n={len(det)} primero={det[-1] if det else None} ultimo={det[0] if det else None}"


T("bcra id1 1996 limit3000", lambda: bcra(1, "1996-01-01"))
T("bcra id1 1996 offset3000", lambda: bcra(1, "1996-01-01", "&offset=3000"))
T("bcra id78 2003", lambda: bcra(78, "2003-01-01"))


def mae(ruta, fd, fh):
    H = {**UA, "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
    r = requests.get("https://api.marketdata.mae.com.ar/api/" + ruta, params={"oTitulo": json.dumps({"fechaDesde": fd, "fechaHasta": fh})}, headers=H, timeout=60)
    j = r.json()
    return f"{r.status_code} n={len(j) if isinstance(j, list) else j} primero={str(j[0])[:200] if isinstance(j, list) and j else ''}"


for anio in [2016, 2018, 2019, 2020, 2022, 2023]:
    for ruta in ["mercado/titulo/historicoforex/volumenoperado", "mercado/titulo/historicocauciones", "mercado/titulo/historicorepo"]:
        T(f"mae {ruta} {anio}", lambda ruta=ruta, anio=anio: mae(ruta, f"{anio}-03-01", f"{anio}-03-30"))


def rofex(fd, fh, extra=""):
    r = requests.get(f"https://apicem.matbarofex.com.ar/api/v2/closing-prices?product=DLR&from={fd}&to={fh}&version=v2{extra}", headers=UA, timeout=60)
    j = r.json()
    d = j.get("data", [])
    return f"{r.status_code} keys={list(j.keys())} meta={ {k: v for k, v in j.items() if k != 'data'} } n={len(d)} f0={d[0]['dateTime'] if d else ''} fN={d[-1]['dateTime'] if d else ''}"


T("rofex 2024 ene-mar", lambda: rofex("2024-01-01", "2024-03-01"))
T("rofex 2024 ene 10 dias", lambda: rofex("2024-01-02", "2024-01-12"))
T("rofex page2", lambda: rofex("2024-01-01", "2024-03-01", "&page=2"))
T("rofex pageSize", lambda: rofex("2024-01-01", "2024-03-01", "&pageSize=1000"))
T("rofex 2018", lambda: rofex("2018-01-02", "2018-01-12"))
T("rofex 2010", lambda: rofex("2010-01-04", "2010-01-12"))


def byma(sym, desde):
    t0 = int(dt.datetime(*desde).timestamp())
    r = requests.get("https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/chart/historical-series/history",
                     params={"symbol": sym, "resolution": "D", "from": t0, "to": int(dt.datetime.now().timestamp())}, headers=UA, verify=False, timeout=90)
    j = r.json(); t = j.get("t", [])
    return f"{r.status_code} n={len(t)} primero={dt.datetime.utcfromtimestamp(t[0]) if t else None}"


T("byma AL30 2020", lambda: byma("AL30 24HS", (2020, 1, 1)))
T("byma AL30D 2020", lambda: byma("AL30D 24HS", (2020, 1, 1)))
T("byma AL30C 2020", lambda: byma("AL30C 24HS", (2020, 1, 1)))
T("byma AY24 2017", lambda: byma("AY24 48HS", (2017, 1, 1)))


def dgob(sid, start, extra=None):
    p = {"ids": sid, "start_date": start, "format": "csv"}
    p.update(extra or {})
    r = requests.get("https://apis.datos.gob.ar/series/api/series/", params=p, headers=UA, timeout=90)
    lines = r.text.strip().splitlines()
    return f"{r.status_code} n={len(lines) - 1} primero={lines[1] if len(lines) > 1 else ''} ultimo={lines[-1]}"


for sid in ["148.3_INIVELNAL_DICI_M_26", "143.3_NO_PR_2004_A_31", "74.3_IET_0_M_16", "452.3_RESULTADO_RIO_0_M_18_54"]:
    T(f"datosgob {sid} 1990 sin limit", lambda sid=sid: dgob(sid, "1990-01-01"))
    T(f"datosgob {sid} 1990 limit1000", lambda sid=sid: dgob(sid, "1990-01-01", {"limit": 1000}))


def ad(path):
    j = requests.get("https://api.argentinadatos.com/v1/" + path, headers=UA, timeout=90).json()
    return f"n={len(j)} primero={j[0]} ultimo={j[-1]}"


T("AD riesgo pais", lambda: ad("finanzas/indices/riesgo-pais"))
T("AD bolsa", lambda: ad("cotizaciones/dolares/bolsa"))
T("AD ccl", lambda: ad("cotizaciones/dolares/contadoconliqui"))
T("AD blue", lambda: ad("cotizaciones/dolares/blue"))


def cny(fd, fh):
    r = requests.get(f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/CNY?fechadesde={fd}&fechahasta={fh}", headers=UA, timeout=60)
    j = r.json()
    return f"{r.status_code} n={len(j.get('results', []))} {str(j.get('results', [])[:1])[:200]}"


T("cny 2015", lambda: cny("2015-03-01", "2015-03-30"))
T("cny 2010", lambda: cny("2010-03-01", "2010-03-30"))


def yahoo(t):
    j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"range": "max", "interval": "1d"}, headers=UA, timeout=60).json()["chart"]["result"][0]
    ts = j["timestamp"]
    return f"n={len(ts)} primero={dt.datetime.utcfromtimestamp(ts[0])} paso={(ts[-1] - ts[-2]) / 86400:.1f}d"


for t in ["^VIX", "BZ=F", "DX-Y.NYB", "BRL=X", "GC=F", "ZS=F"]:
    T(f"yahoo {t}", lambda t=t: yahoo(t))


def bcrp(ids, d, h):
    r = requests.get(f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{ids}/json/{d}/{h}", headers=UA, timeout=90)
    j = r.json()
    p = j.get("periods", [])
    return f"{r.status_code} n={len(p)} primero={p[0] if p else None} ultimo={p[-1] if p else None}"


T("bcrp EMBIG Arg/LatAm 1998-2008", lambda: bcrp("PD04710XD-PD04708XD", "1998-01-01", "2008-01-01"))


def treas(a):
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
           f"daily-treasury-rates.csv/{a}/all?type=daily_treasury_yield_curve&field_tdr_date_value={a}&page&_format=csv")
    t = requests.get(url, headers=UA, timeout=60).text.splitlines()
    return f"n={len(t)} enc={t[0][:150]} ult={t[-1][:80]}"


T("treasury 2007", lambda: treas(2007))
T("treasury 1995", lambda: treas(1995))

pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_4.md").write_text("\n".join(out), encoding="utf-8")
