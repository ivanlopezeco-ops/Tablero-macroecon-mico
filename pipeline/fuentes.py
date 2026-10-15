"""Descarga de fuentes. Cada función devuelve un DataFrame largo:
fecha (date) | variable | valor | unidad | fuente
"""
import datetime as dt
import io
import re

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124 Safari/537.36"}
DESDE = dt.date(2024, 1, 1)
HOY = dt.date.today()
COLS = ["fecha", "variable", "valor", "unidad", "fuente"]


def _get(url, **kw):
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", 90)
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r


def _df(filas):
    df = pd.DataFrame(filas, columns=COLS)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.dropna(subset=["valor"])


# ---------------------------------------------------------------- BCRA
BCRA_VARS = {
    # id: (variable, unidad)
    1: ("reservas_brutas", "USD M"),
    5: ("tc_mayorista_a3500", "ARS/USD"),
    1187: ("banda_piso", "ARS/USD"),
    1188: ("banda_techo", "ARS/USD"),
    78: ("compras_bcra_mlc", "USD M"),
    1243: ("encajes_usd_bcra", "USD M"),
    158: ("lebac_lediv_bopreal_usd", "USD M"),
    44: ("tamar", "% TNA"),
    7: ("badlar", "% TNA"),
    12: ("tasa_plazo_fijo_30d", "% TNA"),
    11: ("baibar", "% TNA"),
    150: ("tasa_pases_terceros_1d", "% TNA"),
    15: ("base_monetaria", "ARS M"),
    197: ("m2_transaccional_privado", "ARS M"),
    117: ("prestamos_privados_pesos", "ARS M"),
    125: ("prestamos_privados_usd", "USD M"),
    108: ("depositos_privados_usd", "USD M"),
}


def bcra():
    filas = []
    for idv, (var, uni) in BCRA_VARS.items():
        url = (f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idv}"
               f"?desde={DESDE}&hasta={HOY}&limit=3000")
        for r in _get(url).json()["results"]:
            for d in r["detalle"]:
                filas.append((d["fecha"], var, d["valor"], uni, f"BCRA API v4 (id {idv})"))
    return _df(filas)


def bcra_cny():
    """Tipo de pase USD por yuan, para valuar el swap con China. Se pide en ventanas cortas."""
    filas, errores = [], []
    ini = DESDE
    while ini <= HOY:
        fin = min(ini + dt.timedelta(days=89), HOY)
        url = (f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/CNY"
               f"?fechadesde={ini}&fechahasta={fin}")
        try:
            for r in _get(url).json().get("results", []):
                for d in r["detalle"]:
                    filas.append((r["fecha"], "usd_por_cny", d["tipoPase"], "USD/CNY", "BCRA API cambiaria"))
        except Exception as e:  # noqa: BLE001
            errores.append(f"{ini}: {e}")
        ini = fin + dt.timedelta(days=1)
    if not filas:
        raise RuntimeError("; ".join(errores[:3]))
    return _df(filas)


# ---------------------------------------------------------------- Riesgo país
BCRD_URL = ("https://bcrdgdcprod.blob.core.windows.net/documents/entorno-internacional/"
            "documents/Serie_Historica_Spread_del_EMBI.xlsx")
PAISES = {"Global": "global", "LATINO": "latam", "REP DOM": "rep_dominicana", "Argentina": "argentina",
          "Bolivia": "bolivia", "Brasil": "brasil", "Chile": "chile", "Colombia": "colombia",
          "Costa Rica": "costa_rica", "Ecuador": "ecuador", "El Salvador": "el_salvador",
          "Guatemala": "guatemala", "Honduras": "honduras", "México": "mexico", "Paraguay": "paraguay",
          "Perú": "peru", "Panamá": "panama", "Uruguay": "uruguay", "Venezuela": "venezuela"}


def bcrd_embi():
    raw = pd.read_excel(io.BytesIO(_get(BCRD_URL).content), header=None)
    enc = raw.iloc[1].tolist()
    df = raw.iloc[2:].copy()
    df.columns = enc
    df = df[[c for c in df.columns if c in PAISES or c == "Fecha"]]
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df = df[df["Fecha"] >= "2020-01-01"]
    largo = df.melt(id_vars="Fecha", var_name="pais", value_name="valor")
    largo["valor"] = pd.to_numeric(largo["valor"], errors="coerce") * 100  # pp -> pb
    largo["variable"] = "riesgo_pais_" + largo["pais"].map(PAISES)
    largo["unidad"] = "pb"
    largo["fuente"] = "BCRD (JP Morgan EMBIGD)"
    largo = largo.rename(columns={"Fecha": "fecha"})
    return _df(largo[COLS].values.tolist())


def argentinadatos():
    filas = []
    for d in _get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais").json():
        if d["fecha"] >= str(DESDE):
            filas.append((d["fecha"], "riesgo_pais_argentina_ad", d["valor"], "pb", "ArgentinaDatos (Ámbito)"))
    for casa, var in [("bolsa", "mep_ad"), ("contadoconliqui", "ccl_ad")]:
        for d in _get(f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}").json():
            if d["fecha"] >= str(DESDE):
                filas.append((d["fecha"], var, d["venta"], "ARS/USD", "ArgentinaDatos"))
    return _df(filas)


# ---------------------------------------------------------------- BYMA
BYMA = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
BYMA_H = {**UA, "Content-Type": "application/json", "Origin": "https://open.bymadata.com.ar",
          "Referer": "https://open.bymadata.com.ar/"}
BYMA_SIMBOLOS = {"AL30 24HS": ("al30_ars", "ARS"), "AL30D 24HS": ("al30_usd_mep", "USD"),
                 "AL30C 24HS": ("al30_usd_ccl", "USD"), "GD30 24HS": ("gd30_ars", "ARS"),
                 "GD30C 24HS": ("gd30_usd_ccl", "USD"), "GD35C 24HS": ("gd35_usd_ccl", "USD")}


def byma_historicos():
    desde = int(dt.datetime.combine(DESDE, dt.time()).timestamp())
    hasta = int(dt.datetime.now().timestamp())
    filas = []
    for sym, (var, uni) in BYMA_SIMBOLOS.items():
        j = _get(f"{BYMA}/chart/historical-series/history", verify=False,
                 params={"symbol": sym, "resolution": "D", "from": desde, "to": hasta}).json()
        for t, c in zip(j.get("t", []), j.get("c", [])):
            fecha = (dt.datetime.utcfromtimestamp(t) - dt.timedelta(hours=3)).date()
            filas.append((fecha, var, c, uni, f"BYMA ({sym})"))
    return _df(filas)


def byma_snapshots():
    """Cauciones y letras: solo foto del día. La historia se acumula corrida a corrida."""
    filas, crudos = [], {}
    r = requests.post(f"{BYMA}/cauciones", json={"excludeZeroPxAndQty": True, "T2": True, "T1": False,
                      "T0": False}, headers=BYMA_H, verify=False, timeout=90)
    cau = r.json()
    crudos["cauciones"] = cau
    for c in cau if isinstance(cau, list) else []:
        if str(c.get("symbol", "")).startswith("PESOS") and c.get("daysToMaturity", 99) <= 4 and c.get("vwap"):
            filas.append((HOY, f"caucion_pesos_{c['daysToMaturity']}d", c["vwap"] * 100, "% TNA",
                          f"BYMA cauciones ({c['symbol']}, precio promedio ponderado)"))
    r = requests.post(f"{BYMA}/lebacs", json={"excludeZeroPxAndQty": False, "T1": True, "T0": False,
                      "page_number": 1, "page_size": 500}, headers=BYMA_H, verify=False, timeout=90)
    let = r.json().get("data", [])
    crudos["letras"] = let
    return _df(filas), crudos


# ---------------------------------------------------------------- Futuros
def rofex_futuros():
    filas = []
    ini = max(DESDE, HOY - dt.timedelta(days=400))
    url = ("https://apicem.matbarofex.com.ar/api/v2/closing-prices"
           f"?product=DLR&from={ini}&to={HOY}&version=v2")
    for d in _get(url).json().get("data", []):
        sym = d["symbol"]
        if re.fullmatch(r"DLR\d{6}", sym):
            filas.append((d["dateTime"][:10], f"futuro_{sym}", d["settlement"], "ARS/USD", "Matba Rofex (A3)"))
    return _df(filas)


# ---------------------------------------------------------------- CAMMESA
def cammesa():
    j = _get("https://api.cammesa.com/demanda-svc/demanda/ObtieneDemandaYTemperaturaRegion?id_region=1002").json()
    ayer = [x["demAyer"] for x in j if x.get("demAyer") is not None]
    if not ayer:
        return _df([])
    mwh = sum(ayer) * 5 / 60  # potencia MW cada 5 minutos -> energía MWh
    return _df([(HOY - dt.timedelta(days=1), "demanda_electrica_diaria", mwh, "MWh",
                 "CAMMESA (región 1002)")])


# ---------------------------------------------------------------- Internacional
def treasury():
    filas = []
    for anio in sorted({DESDE.year, HOY.year - 1, HOY.year}):
        url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
               f"daily-treasury-rates.csv/{anio}/all?type=daily_treasury_yield_curve"
               f"&field_tdr_date_value={anio}&page&_format=csv")
        df = pd.read_csv(io.StringIO(_get(url).text))
        for col, var in [("2 Yr", "ust_2y"), ("10 Yr", "ust_10y"), ("30 Yr", "ust_30y")]:
            for f, v in zip(pd.to_datetime(df["Date"]), df[col]):
                filas.append((f, var, v, "%", "US Treasury"))
    return _df(filas)


YAHOO = {"^VIX": ("vix", "índice"), "BZ=F": ("brent", "USD/bbl"), "DX-Y.NYB": ("dxy", "índice"),
         "BRL=X": ("brl_usd", "BRL/USD"), "GC=F": ("oro", "USD/oz"), "ZS=F": ("soja_cbot", "USc/bu")}


def yahoo():
    filas = []
    for t, (var, uni) in YAHOO.items():
        j = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}",
                 params={"range": "3y", "interval": "1d"}).json()["chart"]["result"][0]
        for ts, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]):
            if c is not None:
                filas.append((dt.datetime.utcfromtimestamp(ts).date(), var, c, uni, f"Yahoo Finance ({t})"))
    return _df(filas)


# ---------------------------------------------------------------- INDEC / datos.gob.ar
DATOS_GOB = {
    "148.3_INIVELNAL_DICI_M_26": ("ipc_nivel_general", "índice dic-16=100"),
    "148.3_INUCLEONAL_DICI_M_19": ("ipc_nucleo", "índice dic-16=100"),
    "143.3_NO_PR_2004_A_31": ("emae_desest", "índice 2004=100"),
}


def datos_gob():
    filas = []
    j = _get("https://apis.datos.gob.ar/series/api/series/",
             params={"ids": ",".join(DATOS_GOB), "start_date": "2018-01-01", "limit": 1000,
                     "format": "json"}).json()
    ids = list(DATOS_GOB)
    for fila in j["data"]:
        f = fila[0]
        for sid, v in zip(ids, fila[1:]):
            var, uni = DATOS_GOB[sid]
            filas.append((f, var, v, uni, f"INDEC vía datos.gob.ar ({sid})"))
    return _df(filas)


def datos_gob_buscar(consultas):
    out = {}
    for q in consultas:
        try:
            j = _get("https://apis.datos.gob.ar/series/api/search/", params={"q": q, "limit": 8}).json()
            out[q] = [(x["field"]["id"], x["field"].get("description"), x["field"].get("time_index_end"))
                      for x in j.get("data", [])]
        except Exception as e:  # noqa: BLE001
            out[q] = str(e)
    return out


# ---------------------------------------------------------------- Archivos para inspeccionar
ARCHIVOS = {
    "balance_cambiario.xlsx": "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/anexo-estadistico-mercado-cambios-balance-cambiario.xlsx",
}


# ---------------------------------------------------------------- BCRA: archivos Excel
def rem():
    """Expectativas del REM (mediana): inflación próximos 12 meses y del mes siguiente, TC fin de año."""
    url = F_REM
    df = pd.read_excel(io.BytesIO(_get(url).content), sheet_name="Base de Datos Completa", header=1)
    df["Fecha de pronóstico"] = pd.to_datetime(df["Fecha de pronóstico"], errors="coerce")
    filas = []
    ipc = df[df["Variable"].eq("Precios minoristas (IPC nivel general; INDEC)")]
    for _, r in ipc[ipc["Período"].astype(str).eq("Próx. 12 meses")].iterrows():
        filas.append((r["Fecha de pronóstico"], "rem_inflacion_12m", r["Mediana"], "% i.a.", "BCRA REM (mediana)"))
    men = ipc[ipc["Referencia"].astype(str).str.contains("mensual")].copy()
    men["per"] = pd.to_datetime(men["Período"], errors="coerce")
    men = men[men["per"] > men["Fecha de pronóstico"]].sort_values("per").groupby("Fecha de pronóstico").first()
    for f, r in men.iterrows():
        filas.append((f, "rem_inflacion_mes_siguiente", r["Mediana"], "% mensual", "BCRA REM (mediana)"))
    tc = df[df["Variable"].eq("Tipo de cambio nominal")].copy()
    tc["per"] = pd.to_datetime(tc["Período"], errors="coerce")
    tc = tc[tc["per"].dt.month.eq(12) & tc["per"].dt.year.eq(tc["Fecha de pronóstico"].dt.year)]
    for _, r in tc.iterrows():
        filas.append((r["Fecha de pronóstico"], "rem_tc_fin_de_anio", r["Mediana"], "ARS/USD", "BCRA REM (mediana)"))
    return _df(filas)


F_REM = ("https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/"
         "relevamiento-expectativas-mercado-historico.xlsx")
F_ITCRM = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/ITCRMSerie.xlsx"


def itcrm():
    df = pd.read_excel(io.BytesIO(_get(F_ITCRM).content), sheet_name="ITCRM y bilaterales", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    df["Período"] = pd.to_datetime(df["Período"], errors="coerce")
    df = df[df["Período"] >= pd.Timestamp(DESDE)]
    filas = []
    for col, var in [("ITCRM", "tcrm"), ("ITCRB Brasil", "tcr_brasil"), ("ITCRB Estados Unidos", "tcr_eeuu")]:
        for f, v in zip(df["Período"], df[col]):
            filas.append((f, var, v, "índice 17-12-15=100", "BCRA ITCRM"))
    return _df(filas)
