"""Descarga de fuentes. Cada función devuelve un DataFrame largo:
fecha (date) | variable | valor | unidad | fuente
"""
import datetime as dt
import io
import json
import pathlib
import re
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124 Safari/537.36"}
HOY = dt.datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()  # el runner está en UTC
# Modo histórico: baja todo lo que cada fuente tiene. Modo diario: solo una ventana reciente
# (la base acumulada conserva la historia). run.py decide el modo.
COMPLETO = True
VENTANA = 120  # días que se vuelven a pedir en modo diario (cubre revisiones)


def desde(primero):
    """Primera fecha a pedir: la más antigua disponible en modo histórico, o la ventana reciente."""
    return primero if COMPLETO else max(primero, HOY - dt.timedelta(days=VENTANA))
COLS = ["fecha", "variable", "valor", "unidad", "fuente"]


def _get(url, intentos=3, **kw):
    """GET con reintentos: las APIs públicas (BCRA sobre todo) devuelven errores 5xx transitorios."""
    import time
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", 90)
    for i in range(intentos):
        try:
            r = requests.get(url, **kw)
            if r.status_code >= 500 and i < intentos - 1:
                time.sleep(4 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout):
            if i == intentos - 1:
                raise
            time.sleep(4 * (i + 1))
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
    30: ("cer", "índice 2.2.02=1"),
    15: ("base_monetaria", "ARS M"),
    197: ("m2_transaccional_privado", "ARS M"),
    117: ("prestamos_privados_pesos", "ARS M"),
    125: ("prestamos_privados_usd", "USD M"),
    108: ("depositos_privados_usd", "USD M"),
    1266: ("depositos_gobierno_bcra_me_ars", "ARS M"),
}


# Desde 2003 (salida de la convertibilidad); reservas y base monetaria, desde su primer dato.
BCRA_DESDE = {1: dt.date(1996, 1, 1), 15: dt.date(1996, 1, 1)}


def bcra():
    """Series monetarias del BCRA desde su primer dato (1996 para reservas), paginando de a 3000."""
    filas, errores = [], []
    for idv, (var, uni) in BCRA_VARS.items():
        offset, total = 0, 1
        try:
            while offset < total:
                url = (f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idv}"
                       f"?desde={desde(BCRA_DESDE.get(idv, dt.date(2003, 1, 1)))}&hasta={HOY}&limit=3000&offset={offset}")
                j = _get(url).json()
                total = j.get("metadata", {}).get("resultset", {}).get("count", 0)
                for r in j["results"]:
                    for d in r["detalle"]:
                        # La API devuelve 0 en las tasas del día todavía sin cerrar (visto en TAMAR 16/10/26).
                        if uni == "% TNA" and not d["valor"]:
                            continue
                        filas.append((d["fecha"], var, d["valor"], uni, f"BCRA API v4 (id {idv})"))
                offset += 3000
        except Exception as e:  # noqa: BLE001
            errores.append(f"id {idv}: {e}"[:140])
    if not filas:
        raise RuntimeError("; ".join(errores[:3]))
    df = _df(filas)
    df.attrs["errores"] = errores
    return df


def bcra_cny():
    """Tipo de pase USD por yuan, para valuar el swap con China. Se pide en ventanas cortas."""
    filas, errores = [], []
    ini = desde(dt.date(2023, 12, 1))  # el swap entra en las reservas netas desde dic-23
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
    df = _df(filas)
    df.attrs["errores"] = errores[:5]
    return df


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
        if True:
            filas.append((d["fecha"], "riesgo_pais_argentina_ad", d["valor"], "pb", "ArgentinaDatos (Ámbito)"))
    for casa, var in [("bolsa", "mep_ad"), ("contadoconliqui", "ccl_ad")]:
        for d in _get(f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}").json():
            if d.get("venta"):
                filas.append((d["fecha"], var, d["venta"], "ARS/USD", "ArgentinaDatos"))
    return _df(filas)


# ---------------------------------------------------------------- BYMA
BYMA = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
BYMA_H = {**UA, "Content-Type": "application/json", "Origin": "https://open.bymadata.com.ar",
          "Referer": "https://open.bymadata.com.ar/"}
BYMA_SIMBOLOS = {"AL30 24HS": ("al30_ars", "ARS"), "AL30D 24HS": ("al30_usd_mep", "USD"),
                 "AL30C 24HS": ("al30_usd_ccl", "USD"), "GD30 24HS": ("gd30_ars", "ARS"),
                 "GD30C 24HS": ("gd30_usd_ccl", "USD"), "GD35C 24HS": ("gd35_usd_ccl", "USD")}


# Bonos soberanos en dólares: (grupo, ticker, símbolo en pesos, en dólares MEP, en dólares CCL).
# Los Bopreales pesos se listan como BPOA7 y su versión en dólares como BPA7D / BPA7C.
BONOS = [
    ("Bonares", "AO27", "AO27", "AO27D", "AO27C"), ("Bonares", "AO28", "AO28", "AO28D", "AO28C"),
    ("Bonares", "AO29", "AO29", "AO29D", "AO29C"), ("Bonares", "AN29", "AN29", "AN29D", "AN29C"),
    ("Bonares", "AL29", "AL29", "AL29D", "AL29C"), ("Bonares", "AL30", "AL30", "AL30D", "AL30C"),
    ("Bonares", "AL35", "AL35", "AL35D", "AL35C"), ("Bonares", "AE38", "AE38", "AE38D", "AE38C"),
    ("Bonares", "AL41", "AL41", "AL41D", "AL41C"),
    ("Globales", "GD29", "GD29", "GD29D", "GD29C"), ("Globales", "GD30", "GD30", "GD30D", "GD30C"),
    ("Globales", "GD35", "GD35", "GD35D", "GD35C"), ("Globales", "GD38", "GD38", "GD38D", "GD38C"),
    ("Globales", "GD41", "GD41", "GD41D", "GD41C"), ("Globales", "GD46", "GD46", "GD46D", "GD46C"),
    ("Bopreales", "BPOA7", "BPOA7", "BPA7D", "BPA7C"), ("Bopreales", "BPOB7", "BPOB7", "BPB7D", "BPB7C"),
    ("Bopreales", "BPOC7", "BPOC7", "BPC7D", "BPC7C"), ("Bopreales", "BPOD7", "BPOD7", "BPD7D", "BPD7C"),
    ("Bopreales", "BPOA8", "BPOA8", "BPA8D", "BPA8C"), ("Bopreales", "BPOB8", "BPOB8", "BPB8D", "BPB8C"),
]
BYMA_BONOS = {}
for _g, _t, _ars, _mep, _ccl in BONOS:
    for _sym, _mon, _uni in ((_ars, "ars", "ARS"), (_mep, "mep", "USD"), (_ccl, "ccl", "USD")):
        BYMA_BONOS[f"{_sym} 24HS"] = (f"bono_{_t.lower()}_{_mon}", _uni)


def _byma_historia(simbolos, dias=800):
    """Cierre diario de cada símbolo (BYMA, 24HS). Un símbolo que falla no frena al resto."""
    t0 = int(dt.datetime.combine(desde(HOY - dt.timedelta(days=dias)), dt.time()).timestamp())
    hasta = int(dt.datetime.now().timestamp())
    filas, errores = [], []
    for sym, (var, uni) in simbolos.items():
        try:
            j = _get(f"{BYMA}/chart/historical-series/history", verify=False,
                     params={"symbol": sym, "resolution": "D", "from": t0, "to": hasta}).json()
            for t, c in zip(j.get("t", []), j.get("c", [])):
                fecha = (dt.datetime.utcfromtimestamp(t) - dt.timedelta(hours=3)).date()
                filas.append((fecha, var, c, uni, f"BYMA ({sym})"))
        except Exception as e:  # noqa: BLE001
            errores.append(f"{sym}: {e}"[:100])
    if not filas:
        raise RuntimeError("; ".join(errores[:3]))
    df = _df(filas)
    df.attrs["errores"] = errores
    return df


def bonos_historicos():
    """Cierre diario de Bonares, Globales y Bopreales en pesos, dólar MEP y dólar CCL."""
    return _byma_historia(BYMA_BONOS)


def byma_historicos():
    """BYMA ofrece unos dos años de historia diaria; lo anterior queda en la base acumulada."""
    t0 = int(dt.datetime.combine(desde(HOY - dt.timedelta(days=800)), dt.time()).timestamp())
    hasta = int(dt.datetime.now().timestamp())
    filas = []
    for sym, (var, uni) in BYMA_SIMBOLOS.items():
        j = _get(f"{BYMA}/chart/historical-series/history", verify=False,
                 params={"symbol": sym, "resolution": "D", "from": t0, "to": hasta}).json()
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
    # La tasa de caución sale de A3/MAE (con historia); la foto de BYMA queda solo como crudo.
    r = requests.post(f"{BYMA}/lebacs", json={"excludeZeroPxAndQty": False, "T1": True, "T0": False,
                      "page_number": 1, "page_size": 500}, headers=BYMA_H, verify=False, timeout=90)
    let = r.json().get("data", [])
    crudos["letras"] = let
    return _df(filas), crudos


# ---------------------------------------------------------------- Futuros
def rofex_futuros():
    """Precios de ajuste del dólar futuro. Hay datos desde 2019; se pide por trimestres y páginas de 1000."""
    filas = []
    ini = desde(dt.date(2019, 1, 1))
    while ini <= HOY:
        fin = min(ini + dt.timedelta(days=90), HOY)
        pagina, total = 1, 1
        while (pagina - 1) * 1000 < total:
            j = _get("https://apicem.matbarofex.com.ar/api/v2/closing-prices",
                     params={"product": "DLR", "from": str(ini), "to": str(fin), "version": "v2",
                             "pageSize": 1000, "page": pagina}).json()
            total = j.get("totalEntries", 0)
            for d in j.get("data", []):
                sym = d["symbol"]
                if re.fullmatch(r"DLR\d{6}", sym):
                    filas.append((d["dateTime"][:10], f"futuro_{sym}", d["settlement"], "ARS/USD", "Matba Rofex (A3)"))
            pagina += 1
        ini = fin + dt.timedelta(days=1)
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
    for anio in range(desde(dt.date(2000, 1, 1)).year, HOY.year + 1):
        url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
               f"daily-treasury-rates.csv/{anio}/all?type=daily_treasury_yield_curve"
               f"&field_tdr_date_value={anio}&page&_format=csv")
        df = pd.read_csv(io.StringIO(_get(url).text))
        for col, var in [("2 Yr", "ust_2y"), ("10 Yr", "ust_10y"), ("30 Yr", "ust_30y")]:
            if col not in df:  # el bono a 30 años no se emitió entre 2002 y 2006
                continue
            for f, v in zip(pd.to_datetime(df["Date"]), df[col]):
                filas.append((f, var, v, "%", "US Treasury"))
    return _df(filas)


YAHOO = {"^VIX": ("vix", "índice"), "BZ=F": ("brent", "USD/bbl"), "DX-Y.NYB": ("dxy", "índice"),
         "BRL=X": ("brl_usd", "BRL/USD"), "GC=F": ("oro", "USD/oz"), "ZS=F": ("soja_cbot", "USc/bu"),
         "ZW=F": ("trigo_cbot", "USc/bu"), "ZC=F": ("maiz_cbot", "USc/bu"), "HG=F": ("cobre", "USD/lb"),
         "NG=F": ("gas_natural_hh", "USD/MMBtu"), "^GSPC": ("sp500", "índice"),
         # S&P Merval: S&P lo calculó hasta el 16/10/26; desde el 19/10/26 lo reemplaza el MSCI MERVAL (byma_indices)
         "^MERV": ("merval_sp", "puntos")}
# ADR argentinos en Nueva York (USD por ADR)
ADRS = ["GGAL", "YPF", "BMA", "PAM", "VIST", "TGS", "CEPU", "LOMA", "SUPV", "BBAR", "EDN", "TEO", "CRESY", "IRS"]
YAHOO.update({t: (f"adr_{t.lower()}", "USD") for t in ADRS})


def yahoo():
    filas = []
    errores = []
    for t, (var, uni) in YAHOO.items():
        p1 = int(dt.datetime.combine(desde(dt.date(2000, 1, 1)), dt.time()).timestamp())
        try:  # un ticker que falla no frena al resto
            j = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}",
                     params={"period1": p1, "period2": int(dt.datetime.now().timestamp()),
                             "interval": "1d"}).json()["chart"]["result"][0]
        except Exception as e:  # noqa: BLE001
            errores.append(f"{t}: {e}"[:100])
            continue
        for ts, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]):
            f = dt.datetime.utcfromtimestamp(ts).date()
            if c is not None and not (var == "merval_sp" and f > MERVAL_FIN_SP):
                filas.append((f, var, c, uni, f"Yahoo Finance ({t})"))
    if not filas:
        raise RuntimeError("; ".join(errores[:3]))
    df = _df(filas)
    df.attrs["errores"] = errores
    return df


# ---------------------------------------------------------------- Merval de MSCI (desde el 19/10/26)
# BYMA pasó el cálculo de sus índices de S&P a MSCI. El MSCI MERVAL vale 100.000 el 16/10/26, último día del
# S&P Merval (base verificada en la serie histórica de Rava, que muestra 100.000 ese día). BYMA no da historia
# del índice nuevo: se acumula corrida a corrida con el panel de índices. Los dos primeros cierres se cargan acá.
MERVAL_FIN_SP = dt.date(2026, 10, 16)
MERVAL_MSCI_BASE = 100000.0
MERVAL_MSCI_SEMILLA = {dt.date(2026, 10, 16): 100000.0, dt.date(2026, 10, 19): 98165.4}  # 19/10: cierre anterior que informa BYMA el 20/10


def byma_indices():
    """MSCI MERVAL del panel de índices de BYMA: cierre si ya está, si no último valor (provisorio)."""
    r = requests.post(f"{BYMA}/index-price", json={}, headers=BYMA_H, verify=False, timeout=60)
    filas = [(f, "merval_msci", v, "puntos", "MSCI MERVAL (Rava, base 16/10/26 = 100.000)") for f, v in MERVAL_MSCI_SEMILLA.items()]
    for d in r.json().get("data", []):
        if d.get("symbol") != "MMSCI":
            continue
        f = dt.date.fromisoformat(d["date"][:10])
        if d.get("closingPrice"):
            filas.append((f, "merval_msci", d["closingPrice"], "puntos", "BYMA (MSCI MERVAL)"))
        elif d.get("price") and en_rueda():
            filas.append((f, "merval_msci", d["price"], "puntos", "BYMA (MSCI MERVAL, en la rueda) (provisorio)"))
    return _df(filas)


# ---------------------------------------------------------------- INDEC / datos.gob.ar
DATOS_GOB = {
    "148.3_INIVELNAL_DICI_M_26": ("ipc_nivel_general", "índice dic-16=100"),
    "148.3_INUCLEONAL_DICI_M_19": ("ipc_nucleo", "índice dic-16=100"),
    "143.3_NO_PR_2004_A_31": ("emae_desest", "índice 2004=100"),
    "74.3_IET_0_M_16": ("exportaciones", "USD M"),
    "74.3_IIT_0_M_25": ("importaciones", "USD M"),
    "452.3_RESULTADO_RIO_0_M_18_54": ("resultado_primario_spn", "ARS M"),
    "452.3_INTERESES_TOS_0_M_15_62": ("intereses_netos_spn", "ARS M"),
    # (oct-26: el resultado financiero 452.3_RESULTADO_ERO_0_M_20_25 y la seguridad social 172.3_SRIDAD_IAL_M_0_0_16
    # figuran en el buscador pero la API los devuelve vacíos; el financiero se calcula como primario menos intereses)
    # Recaudación tributaria nacional (ARCA), en millones de pesos corrientes por mes
    "172.3_TL_RECAION_M_0_0_17": ("recaudacion_total", "ARS M"),
    "172.3_SOTAL_DDGI_M_0_0_12": ("recaudacion_dgi", "ARS M"),
    "172.3_SOTAL_DDGA_M_0_0_12": ("recaudacion_dga", "ARS M"),
}


def datos_gob():
    """Una consulta por serie, para que un id que cambie no frene al resto.
    La API es errática: según la combinación de parámetros a veces devuelve vacío o corta la serie
    (probado oct-26: EMAE vacío con csv y limit=1000 en una corrida y completo en otra; expo vacío con csv
    limit=1000 y completo con json). Se piden varias variantes y se unen; al final se controla que no
    queden meses salteados."""
    variantes = [{"format": "json", "limit": 1000}, {"format": "csv", "limit": 1000}, {"format": "csv", "limit": 500},
                 {"format": "json", "limit": 500}, {"format": "csv", "limit": 999, "start_date": "1990-01-01"}]
    filas, errores = [], []
    for sid, (var, uni) in DATOS_GOB.items():
        datos = {}
        for p in variantes:
            try:
                r = _get("https://apis.datos.gob.ar/series/api/series/", params={"ids": sid, **p})
                pares = (r.json().get("data", []) if p["format"] == "json"
                         else pd.read_csv(io.StringIO(r.text)).iloc[:, :2].values.tolist())
                for f, v in pares:
                    if v is not None and not pd.isna(v):
                        datos[str(f)[:10]] = v
            except Exception as e:  # noqa: BLE001
                errores.append(f"{sid} {p}: {e}"[:120])
        if not datos:
            errores.append(f"{sid}: sin datos")
            continue
        fechas = pd.to_datetime(sorted(datos))
        faltan = pd.date_range(fechas[0], fechas[-1], freq="MS").difference(fechas)
        if len(faltan):
            errores.append(f"{sid}: faltan {len(faltan)} meses (primero {faltan[0]:%Y-%m})")
        for f, v in datos.items():
            filas.append((f, var, v, uni, f"datos.gob.ar ({sid})"))
    df = _df(filas)
    df.attrs["errores"] = [e for e in errores if "faltan" in e or "sin datos" in e]
    return df


# ---------------------------------------------------------------- INDEC directo (llega antes que datos.gob.ar)
def indec_ipc():
    """IPC nacional nivel general y núcleo desde el CSV del INDEC (se actualiza el día de publicación)."""
    t = _get("https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv", verify=False).content.decode("latin-1")
    df = pd.read_csv(io.StringIO(t), sep=";", dtype=str)
    df = df[df["Region"].eq("Nacional")]
    filas = []
    for cond, var in [(df["Codigo"].eq("0"), "ipc_nivel_general"), (df["Codigo"].str.lower().str.startswith("n") & df["Clasificador"].eq("Categorias"), "ipc_nucleo")]:
        for _, r in df[cond].iterrows():
            f = dt.date(int(r["Periodo"][:4]), int(r["Periodo"][4:6]), 1)
            filas.append((f, var, float(r["Indice_IPC"].replace(",", ".")), "índice dic-16=100", "INDEC (serie_ipc_divisiones.csv)"))
    return _df(filas)


MESES = {m: i for i, m in enumerate(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                                      "Septiembre", "Octubre", "Noviembre", "Diciembre"], 1)}


def indec_emae():
    """EMAE desestacionalizado desde el Excel del INDEC (se actualiza el día de publicación;
    datos.gob.ar llega después). Respaldo: la serie de datos.gob.ar."""
    r = _get("https://www.indec.gob.ar/ftp/cuadros/economia/sh_emae_mensual_base2004.xls", verify=False)
    d = pd.read_excel(io.BytesIO(r.content), header=None)
    filas, anio = [], None
    for _, f in d.iterrows():
        if pd.notna(f[0]) and str(f[0]).strip().isdigit():
            anio = int(str(f[0]).strip())
        mes = MESES.get(str(f[1]).strip())
        if anio and mes and pd.notna(f[4]):
            filas.append((dt.date(anio, mes, 1), "emae_desest", float(f[4]), "índice 2004=100",
                          "INDEC (sh_emae_mensual_base2004.xls)"))
    if not filas:
        raise RuntimeError("EMAE: no se encontraron filas en el Excel del INDEC")
    return _df(filas)


# ---------------------------------------------------------------- industria y construcción (INDEC)
# El nombre del Excel lleva el año (sh_ipi_manufacturero_2026.xls): se toma el enlace de la página del tema
# y, si no aparece, se prueba con el año en curso y el anterior.
INDEC_PAGINAS = {"ipi": ("https://www.indec.gob.ar/Nivel4/Tema/3/6/14", r"sh_ipi_manufacturero_\d{4}\.xls"),
                 "isac": ("https://www.indec.gob.ar/Nivel4/Tema/3/3/42", r"sh_isac_\d{4}\.xls")}
# IPI, cuadro 5 (desestacionalizado por división): código CLaNAE -> variable
IPI_DIVISIONES = {"D": "ipi_desest", "15": "ipi_div_alimentos_desest", "24": "ipi_div_quimicos_desest",
                  "26": "ipi_div_minerales_no_met_desest", "27": "ipi_div_metalicas_basicas_desest",
                  "28": "ipi_div_productos_metal_desest", "29": "ipi_div_maquinaria_desest",
                  "30-33": "ipi_div_otros_equipos_desest", "34": "ipi_div_automotriz_desest"}
# IPI, cuadro 2 (serie original): subclase -> variable
IPI_SUBCLASES = {"IPI Manufacturero": "ipi_original", "Industria siderúrgica": "ipi_siderurgia",
                 "Vehículos automotores": "ipi_vehiculos", "Autopartes": "ipi_autopartes",
                 "Maquinaria agropecuaria": "ipi_maq_agricola", "Maquinaria de uso general": "ipi_maq_uso_general",
                 "Aparatos de uso doméstico": "ipi_aparatos_domesticos", "Cemento": "ipi_cemento",
                 "Productos metálicos para uso estructural": "ipi_metalicos_estructurales"}
# ISAC: cuadro 1 (nivel general) y 2.1 (insumos, serie original)
ISAC_INSUMOS = {"Cemento portland": "isac_cemento", "Hierro redondo y aceros para la construcción": "isac_hierro_redondo"}


def _excel_indec(clave):
    pagina, patron = INDEC_PAGINAS[clave]
    nombres = []
    try:
        nombres = sorted(set(re.findall(patron, _get(pagina, verify=False).text)), reverse=True)
    except Exception:  # noqa: BLE001
        pass
    base = "https://www.indec.gob.ar/ftp/cuadros/economia/"
    for n in nombres + [patron.replace(r"\d{4}\.xls", f"{a}.xls").replace("\\", "") for a in (HOY.year, HOY.year - 1)]:
        try:
            return pd.ExcelFile(io.BytesIO(_get(base + n, verify=False).content)), n
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError(f"{clave}: no se encontró el Excel del INDEC")


def _meses_indec(hoja):
    """Recorre un cuadro del INDEC con año y mes en las primeras columnas: devuelve [(fecha, fila)]."""
    anio, out = None, []
    for _, f in hoja.iterrows():
        mes = None
        for x in f.iloc[:3]:
            s = str(x).strip()
            if re.match(r"^\d{4}\*?$", s):
                anio = int(s[:4])
            elif s in MESES:
                mes = MESES[s]
        if anio and mes:
            out.append((dt.date(anio, mes, 1), f))
    return out


def indec_industria():
    """IPI manufacturero (nivel general, divisiones y subclases metalmecánicas) e ISAC, del Excel del INDEC."""
    filas, errores = [], []
    x, n = _excel_indec("ipi")
    fu = f"INDEC ({n})"
    h5 = pd.read_excel(x, "Cuadro 5", header=None)
    cod = h5.iloc[2].astype(str).str.strip().tolist()
    for c, codigo in enumerate(cod):        # cada división ocupa dos columnas: índice y variación; se toma la primera
        if codigo in IPI_DIVISIONES and cod.index(codigo) == c:
            for f, r in _meses_indec(h5):
                filas.append((f, IPI_DIVISIONES[codigo], r[c], "índice 2004=100", fu + " cuadro 5"))
    h2 = pd.read_excel(x, "Cuadro 2", header=None)
    nom = h2.iloc[3].astype(str).str.strip().tolist()
    for c, nombre in enumerate(nom):
        if nombre in IPI_SUBCLASES:
            for f, r in _meses_indec(h2):
                filas.append((f, IPI_SUBCLASES[nombre], r[c], "índice 2004=100", fu + " cuadro 2"))
    faltan = set(IPI_DIVISIONES.values()) | set(IPI_SUBCLASES.values())
    try:
        x, n = _excel_indec("isac")
        fu = f"INDEC ({n})"
        h1 = pd.read_excel(x, "Cuadro 1", header=None)
        for f, r in _meses_indec(h1):
            filas += [(f, "isac_original", r[2], "índice 2004=100", fu), (f, "isac_desest", r[6], "índice 2004=100", fu)]
        h21 = pd.read_excel(x, "Cuadro 2.1", header=None)
        nom = h21.iloc[2].astype(str).str.strip().tolist()
        for c, nombre in enumerate(nom):
            if nombre in ISAC_INSUMOS:
                for f, r in _meses_indec(h21):
                    filas.append((f, ISAC_INSUMOS[nombre], r[c], "índice 2004=100", fu + " cuadro 2.1"))
        faltan |= {"isac_original", "isac_desest"} | set(ISAC_INSUMOS.values())
    except Exception as e:  # noqa: BLE001
        errores.append(f"ISAC: {e}"[:150])
    df = _df(filas)
    sin = sorted(faltan - set(df["variable"]))
    if sin:   # el INDEC renombró una columna: se avisa en estado.json
        errores.append("sin datos: " + ", ".join(sin))
    df.attrs["errores"] = errores
    return df


# ---------------------------------------------------------------- licitaciones del Tesoro (Secretaría de Finanzas)
# Finanzas no publica una base de resultados: cada licitación es un comunicado en argentina.gob.ar con tablas
# (totales y una por tipo de instrumento). Se recorre el listado de noticias de Finanzas hasta encontrar
# comunicados ya leídos. El comunicado no informa los vencimientos, de modo que el rollover no sale de acá.
GOB = "https://www.argentina.gob.ar"
LIC_DESDE = dt.date(2024, 1, 1)


def _num_ar(s):
    """'$ 5.000.000 (***)' / 'USD 987,80' / '29,75%' -> float (None si no hay número)."""
    m = re.search(r"-?\d[\d.]*(?:,\d+)?", str(s))
    return float(m.group(0).replace(".", "").replace(",", ".")) if m else None


def _licitacion(url):
    t = _get(GOB + url).text
    texto = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)))
    # La fecha de publicación es la primera fecha del texto que no está en el futuro (el título puede nombrar un vencimiento)
    fechas = [dt.date(int(a), CAL_MESES[m.capitalize()], int(d)) for d, m, a in
              re.findall(r"(\d{1,2}) de (" + "|".join(CAL_MESES).lower() + r") de (\d{4})", texto.lower())]
    fechas = [f for f in fechas if f <= HOY]
    if not fechas:
        raise ValueError("sin fecha")
    fecha = fechas[0]
    lic = {"f": fecha.isoformat(), "url": url, "titulo": re.sub(r"\s*\|.*", "", re.search(r"<title>(.*?)</title>", t, re.S).group(1)).strip(),
           "ofertado": None, "adjudicado": None, "inst": []}
    # Totales: la frase del primer párrafo (en billones o millones de pesos, valor efectivo)
    m = re.search(r"ofertas por un total de valor efectivo de \$ ?([\d.,]+) (billones|millones).*?adjudic\w+ un total de valor efectivo (?:de )?\$ ?([\d.,]+) (billones|millones)", texto)
    if m:
        k = lambda u: 1e6 if u == "billones" else 1  # noqa: E731  (a millones de pesos)
        lic["ofertado"], lic["adjudicado"] = _num_ar(m.group(1)) * k(m.group(2)), _num_ar(m.group(3)) * k(m.group(4))
    for tabla in pd.read_html(io.StringIO(t)):
        cab = [str(c) for c in tabla.columns]
        if not re.match(r"instrumento", cab[0], re.I) or len(cab) < 6:
            continue
        i_ve = next((i for i, c in enumerate(cab) if c.lower().startswith("valor efectivo adjudicado")), None)
        i_tir = next((i for i, c in enumerate(cab) if c.upper().startswith("TIREA")), None)
        for _, r in tabla.iterrows():
            d = str(r.iloc[0])
            tk = re.search(r"\(([A-Z0-9]{4,6})\s*[-–]", d)
            lic["inst"].append({"t": tk.group(1) if tk else None, "d": d[:200], "tipo": re.sub(r"(?i)^instrumentos?\s*", "", cab[0]).strip(),
                                "ve": _num_ar(r.iloc[i_ve]) if i_ve is not None else None,
                                "tirea": _num_ar(r.iloc[i_tir]) if i_tir is not None else None})
    if lic["adjudicado"] is None and any(x["ve"] for x in lic["inst"]):   # comunicados viejos sin la frase de totales
        lic["adjudicado"] = sum(x["ve"] or 0 for x in lic["inst"])
        lic["suma_instrumentos"] = True
    return lic


def licitaciones(previas):
    """Resultados de las licitaciones del Tesoro por efectivo. `previas`: lista ya guardada (data/licitaciones.json)."""
    vistas = {x["url"] for x in previas}
    nuevas, errores = [], []
    for pagina in range(60):
        t = _get(f"{GOB}/economia/finanzas/noticias?page={pagina}").text
        urls = list(dict.fromkeys(re.findall(r'href="(/noticias/resultado[^"]*licitaci[^"]*)"', t)))
        hay_noticias = "/noticias/" in t.split("Ver todo")[0] or re.search(r'href="/noticias/[^"]+"', t)
        pendientes = [u for u in urls if u not in vistas and not re.search(r"conversi|canje|segunda-vuelta|tesoro-nacional-en-dolares", u)]
        for u in pendientes:
            try:
                nuevas.append(_licitacion(u))
            except Exception as e:  # noqa: BLE001
                errores.append(f"{u[-50:]}: {e}"[:150])
        ya_vistas = any(u in vistas for u in urls)   # se llegó a lo leído en corridas anteriores
        if not hay_noticias or ya_vistas or any(x["f"] < str(LIC_DESDE) for x in nuevas):
            break
    todas = {x["url"]: x for x in previas + nuevas}
    lista = sorted((x for x in todas.values() if x["f"] >= str(LIC_DESDE) and x["adjudicado"]), key=lambda x: x["f"])
    return lista, errores


# ---------------------------------------------------------------- calendario de publicaciones del INDEC
CAL_INDEC = "https://www.indec.gob.ar/ftp/cuadros/publicaciones/calendario_{sem}sem{anio}.pdf"
CAL_MESES = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
             "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
# (texto que identifica la publicación, etiqueta corta, ¿hay una serie en el tablero?)
CAL_TEMAS = [("Índice de precios al consumidor (IPC)", "Inflación (IPC)", True),
             ("Estimador mensual de actividad económica", "Actividad (EMAE)", True),
             ("Intercambio comercial argentino", "Comercio exterior (ICA)", True),
             ("Índice de salarios", "Salarios", False),
             ("Índice de producción industrial manufacturero", "Industria (IPI manufacturero)", True),
             ("Utilización de la capacidad instalada", "Capacidad instalada", False),
             ("Sistema de índices de precios mayoristas", "Precios mayoristas", False),
             ("Indicadores de coyuntura de la actividad de la construcción", "Construcción (ISAC)", True),
             ("Informe de avance del nivel de actividad", "PIB trimestral", False),
             ("Balanza de pagos", "Balanza de pagos", False),
             ("Mercado de trabajo. Tasas e indicadores", "Mercado de trabajo (EPH)", False),
             ("Incidencia de la pobreza", "Pobreza", False),
             ("Valorización mensual de la canasta básica alimentaria", "Canastas básicas", False)]


def _parsear_calendario(texto, anio, meses_validos):
    mes, dia, items = None, None, []
    for ln in texto.split("\n"):
        ln = ln.strip()
        if ln in CAL_MESES and CAL_MESES[ln] in meses_validos:
            mes, dia = CAL_MESES[ln], None
            continue
        m = re.match(r"^(\d{1,2}) (LU|MA|MI|JU|VI|SA|DO) (.+)$", ln)
        if m and mes:
            dia = int(m.group(1))
            items.append((dt.date(anio, mes, dia), m.group(3).strip()))
        elif mes and dia and ln:
            items.append((dt.date(anio, mes, dia), ln))
    return items


def calendario_indec():
    """Fechas de publicación del INDEC (calendario anual en PDF) de las estadísticas que sigue el tablero.
    Se leen el semestre en curso y el siguiente."""
    import pypdf
    sems = [(HOY.year, 1 if HOY.month <= 6 else 2)]
    sems.append((HOY.year + 1, 1) if sems[0][1] == 2 else (HOY.year, 2))
    filas, errores = [], []
    for anio, sem in sems:
        meses = set(range(1, 7)) if sem == 1 else set(range(7, 13))
        try:
            pdf = _get(CAL_INDEC.format(sem=sem, anio=anio), verify=False).content
            texto = "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(io.BytesIO(pdf)).pages)
            for f, item in _parsear_calendario(texto, anio, meses):
                for clave, etiqueta, en_tablero in CAL_TEMAS:
                    if item.startswith(clave):
                        filas.append({"f": f.isoformat(), "t": etiqueta, "d": item, "tab": en_tablero})
                        break
        except Exception as e:  # noqa: BLE001
            if (anio, sem) == sems[0]:      # el semestre siguiente puede no estar publicado todavía
                errores.append(f"{anio} S{sem}: {e}"[:120])
    if not filas:
        raise RuntimeError("; ".join(errores) or "calendario vacío")
    filas.sort(key=lambda x: (x["f"], x["t"]))
    return filas, errores


def cpi_eeuu():
    """CPI de EE.UU. (todos los ítems, desestacionalizado) del BLS; FRED como respaldo."""
    filas, err = [], []
    for ini in range(2014, HOY.year + 1, 10):  # sin clave, el BLS da hasta 10 años por consulta
        try:
            j = _get("https://api.bls.gov/publicAPI/v2/timeseries/data/CUSR0000SA0",
                     params={"startyear": ini, "endyear": min(ini + 9, HOY.year)}, timeout=60).json()
            for d in j["Results"]["series"][0]["data"]:
                if d["period"].startswith("M") and d["period"] != "M13" and d["value"].replace(".", "", 1).isdigit():  # '-' = mes sin dato (oct-25)
                    filas.append((dt.date(int(d["year"]), int(d["period"][1:]), 1), "cpi_eeuu", float(d["value"]), "índice 1982-84=100", "BLS (CUSR0000SA0)"))
        except Exception as e:  # noqa: BLE001
            err.append(f"BLS {ini}: {e}; {str(locals().get('j', ''))[:200]}")
    if not filas:
        t = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", timeout=150, intentos=1).text
        for f, v in pd.read_csv(io.StringIO(t)).values.tolist():
            if str(f) >= "2014":
                filas.append((f, "cpi_eeuu", v, "índice 1982-84=100", "FRED (CPIAUCSL)"))
    df = _df(filas)
    if df.empty or max(df["fecha"]) < HOY - dt.timedelta(days=150):
        raise RuntimeError("CPI incompleto: " + "; ".join(err)[:300])
    df.attrs["errores"] = err
    return df


# ---------------------------------------------------------------- Datos del día (provisorios)
AR = ZoneInfo("America/Argentina/Buenos_Aires")


def en_rueda():
    """Entre la apertura y un rato después del cierre de BYMA, en días hábiles."""
    ahora = dt.datetime.now(AR)
    return ahora.weekday() < 5 and dt.time(11, 15) <= ahora.time() <= dt.time(19, 30)


def ambito_riesgo():
    """Riesgo país de Argentina en el día (Ámbito, en base a JP Morgan). Se reemplaza por el del BCRD cuando sale."""
    filas = []
    j = _get("https://mercados.ambito.com//riesgopais/variacion").json()
    f = dt.datetime.strptime(j["fecha"], "%d-%m-%Y").date()
    filas.append((f, "riesgo_pais_argentina_ambito", float(str(j["ultimo"]).replace(".", "").replace(",", ".")), "pb", "Ámbito (en el día)"))
    h = _get(f"https://mercados.ambito.com//riesgopais/historico-general/{HOY - dt.timedelta(days=40)}/{HOY}").json()
    for fila in h[1:]:
        filas.append((dt.datetime.strptime(fila[0], "%d-%m-%Y").date(), "riesgo_pais_argentina_ambito",
                      float(str(fila[1]).replace(".", "").replace(",", ".")), "pb", "Ámbito"))
    df = _df(filas).drop_duplicates(["fecha", "variable"], keep="first")
    return df


def byma_intradia():
    """Último precio operado de los bonos (BYMA, con 20 minutos de demora), fechado hoy. Solo durante la rueda.
    BYMA no lista los Globales en este endpoint; esos precios en pesos salen de A3/MAE."""
    if not en_rueda():
        return _df([])
    # Un símbolo puede alimentar dos variables (la serie propia del MEP/CCL y la del panel de bonos).
    simbolos = {}
    for tabla in (BYMA_SIMBOLOS, BYMA_BONOS):
        for sym, destino in tabla.items():
            simbolos.setdefault(sym, []).append(destino)
    r = requests.post(f"{BYMA}/public-bonds", json={"excludeZeroPxAndQty": True, "T2": False, "T1": True, "T0": False,
                      "Content-Type": "application/json"}, headers=BYMA_H, verify=False, timeout=60)
    data = r.json()
    data = data.get("data", data) if isinstance(data, dict) else data
    filas, vistos = [], set()
    for d in data:
        sym = f"{d.get('symbol')} 24HS"
        if sym in simbolos and (d.get("trade") or 0) > 0 and (d.get("volume") or 0) > 0:
            for var, uni in simbolos[sym]:
                filas.append((HOY, var, d["trade"], uni, f"BYMA intradiario ({sym}) (provisorio)"))
                vistos.add(var)
    errores = []
    try:
        for d in _get(MAE + "mercado/datos/RF", headers=MAE_H).json():
            sym = str(d.get("ticker", "")).replace("/24hs", " 24HS")
            if sym in simbolos and d.get("moneda") == "$" and (d.get("ultimo") or 0) > 0 and (d.get("volumen") or 0) > 0:
                for var, uni in simbolos[sym]:
                    if var not in vistos:
                        filas.append((HOY, var, d["ultimo"], uni, f"A3/MAE intradiario ({sym}) (provisorio)"))
                        vistos.add(var)
    except Exception as e:  # noqa: BLE001
        errores.append(f"A3/MAE renta fija: {e}"[:120])
    df = _df(filas)
    df.attrs["errores"] = errores
    return df


# ---------------------------------------------------------------- Archivos para inspeccionar
ARCHIVOS = {}


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
    filas = []
    for col, var in [("ITCRM", "tcrm"), ("ITCRB Brasil", "tcr_brasil"), ("ITCRB Estados Unidos", "tcr_eeuu")]:
        for f, v in zip(df["Período"], df[col]):
            filas.append((f, var, v, "índice 17-12-15=100", "BCRA ITCRM"))
    return _df(filas)


# ---------------------------------------------------------------- Balance cambiario (mensual)
F_BC = ("https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/"
        "anexo-estadistico-mercado-cambios-balance-cambiario.xlsx")
# Códigos de columna de la hoja "Balance Cambiario" (fila de códigos bal0xx). Netos en USD M.
BC_CODIGOS = {
    "bal001": "bc_cuenta_corriente", "bal002": "bc_bienes", "bal003": "bc_cobros_exportaciones",
    "bal004": "bc_pagos_importaciones", "bal005": "bc_servicios", "bal009": "bc_intereses",
    "bal012": "bc_intereses_fmi", "bal016": "bc_utilidades_dividendos", "bal024": "bc_cuenta_financiera",
    "bal025": "bc_ied", "bal028": "bc_portafolio", "bal031": "bc_prestamos_titulos_deuda",
    "bal034": "bc_fmi", "bal037": "bc_otros_organismos", "bal040": "bc_billetes_divisas_spnf",
    "bal050": "bc_var_reservas_transacciones",
    # ampliación oct-26: brutos y componentes de la cuenta financiera
    "bal006": "bc_servicios_ingresos", "bal007": "bc_servicios_egresos", "bal008": "bc_ingreso_primario",
    "bal013": "bc_intereses_otros_org", "bal014": "bc_intereses_otros", "bal015": "bc_intereses_otros_gob",
    "bal017": "bc_utilidades_ingresos", "bal018": "bc_utilidades_egresos", "bal019": "bc_ingreso_secundario",
    "bal023": "bc_cuenta_capital", "bal026": "bc_ied_ingresos", "bal027": "bc_ied_egresos",
    "bal029": "bc_portafolio_ingresos", "bal030": "bc_portafolio_egresos",
    "bal032": "bc_prestamos_ingresos", "bal033": "bc_prestamos_egresos",
    "bal035": "bc_fmi_ingresos", "bal036": "bc_fmi_egresos", "bal038": "bc_otros_org_ingresos", "bal039": "bc_otros_org_egresos",
    "bal041": "bc_billetes_ventas", "bal042": "bc_billetes_compras", "bal043": "bc_canje",
    "bal044": "bc_fae_sector_financiero", "bal045": "bc_fae_sector_publico", "bal046": "bc_titulos_valores",
    "bal047": "bc_otras_spn", "bal048": "bc_otros_movimientos", "bal049": "bc_no_informado",
    "bal051": "bc_var_reservas_contable", "bal052": "bc_ajuste_valuacion", "bal053": "bc_tarjetas_exterior",
}
# Hoja "Cta. Financiera por sector"
BC_FIN_SECTOR = {"cap001": "bcs_total", "cap002": "bcs_spnf", "cap003": "bcs_financiero", "cap004": "bcs_gobierno_bcra", "cap005": "bcs_otros"}
# Hoja "Anexo tarjetas y viajes"
BC_VIAJES = {"viajes001": "bc_tarjetas_neto", "viajes026": "bc_viajes_pasajes_neto", "viajes024": "bc_viajes_ingresos",
             "viajes025": "bc_viajes_egresos", "viajes019": "bc_pasajes_egresos"}
# Hoja "MC por concepto": hojas de último nivel (USD; con signo)
BC_CONCEPTOS = {"Cobros anticipados de exportaciones": "mcc_cobros_anticipados", "Cobros de exportaciones": "mcc_cobros_expo",
                "Financiaciones locales de exportaciones": "mcc_financ_locales_expo", "Prefinanciaciones de exportaciones del exterior": "mcc_prefinanciaciones",
                "Pagos a la vista de importaciones": "mcc_impo_vista", "Pagos anticipados de importaciones": "mcc_impo_anticipados",
                "Pagos diferidos de importaciones y otros egresos por bienes": "mcc_impo_diferidos", "Billetes - Ingresos": "mcc_billetes_ventas",
                "Divisas - Ingresos": "mcc_divisas_ventas", "Billetes - Egresos": "mcc_billetes_compras",
                "Inversiones directas de residentes en el exterior": "mcc_ide_residentes", "Otras inversiones": "mcc_otras_inversiones",
                "Financiaciones locales - Ingresos": "mcc_financ_locales_ing", "Financiaciones locales - Egresos": "mcc_financ_locales_egr",
                "Otros préstamos del exterior y títulos de deuda - Ingresos": "mcc_deuda_ext_ing",
                "Otros préstamos del exterior y títulos de deuda - Egresos": "mcc_deuda_ext_egr",
                "Inversión directa - Ingresos": "mcc_ied_ing", "Inversión directa - Egresos": "mcc_ied_egr",
                "Inversión de portafolio - Ingresos": "mcc_portafolio_ing", "Inversión de portafolio - Egresos": "mcc_portafolio_egr"}
BC_SECTORES = {"Personas Humanas": "mc_personas_humanas", "Oleaginosos y Cerealeros": "mc_oleaginosos_cerealeros",
               "Petróleo": "mc_petroleo", "Mineria": "mc_mineria", "Total general": "mc_total",
               "Electricidad (Generación, Transporte, Distribución)": "mc_electricidad",
               "Gas (Extracción, Transporte, Distribución)": "mc_gas", "Industria Automotriz": "mc_automotriz",
               "Maquinarias y Equipos": "mc_maquinarias", "Metales Comunes y Elaboración": "mc_metales_comunes",
               "Industria Química, Caucho y Plástico": "mc_quimica", "Alimentos, Bebidas y Tabaco": "mc_alimentos",
               "Comercio": "mc_comercio", "Sector Público": "mc_sector_publico",
               "Entidades financieras y cambiarias": "mc_entidades_financieras", "Informática": "mc_informatica",
               "Turismo y Hotelería": "mc_turismo", "Transporte": "mc_transporte", "Comunicaciones": "mc_comunicaciones"}


def balance_cambiario():
    contenido = _get(F_BC).content
    b = pd.read_excel(io.BytesIO(contenido), sheet_name="Balance Cambiario", header=None)
    codigos = b.iloc[10].tolist()
    filas = []
    meses = b[b[0].apply(lambda x: isinstance(x, (dt.datetime, pd.Timestamp)))]
    meses = meses[pd.to_datetime(meses[0]) >= pd.Timestamp("2003-01-01")]
    # En la hoja los egresos van con signo positivo; acá se pasan a negativo para que todo sume con su signo.
    egresos = {"bal004", "bal007", "bal011", "bal012", "bal013", "bal014", "bal015", "bal018", "bal021", "bal027",
               "bal030", "bal033", "bal036", "bal039", "bal042"}
    for col, cod in enumerate(codigos):
        if cod in BC_CODIGOS:
            sg = -1 if cod in egresos else 1
            for f, v in zip(meses[0], meses[col]):
                filas.append((f, BC_CODIGOS[cod], pd.to_numeric(v, errors="coerce") * sg, "USD M", f"BCRA balance cambiario ({cod})"))
    s = pd.read_excel(io.BytesIO(contenido), sheet_name="MC por sector", header=None)
    fila_fechas = s.index[s[0].astype(str).str.strip().eq("Sector")][0]
    fechas = s.iloc[fila_fechas].tolist()
    for _, r in s.iloc[fila_fechas + 1:].iterrows():
        nombre = str(r[0]).strip()
        if nombre in BC_SECTORES:
            for f, v in zip(fechas[1:], r.tolist()[1:]):
                if isinstance(f, (dt.datetime, pd.Timestamp)) and f >= dt.datetime(2003, 1, 1):
                    filas.append((f, BC_SECTORES[nombre], pd.to_numeric(v, errors="coerce") / 1e6, "USD M",
                                  "BCRA mercado de cambios por sector (neto)"))
    for hoja, mapa, fu in [("Cta. Financiera por sector", BC_FIN_SECTOR, "BCRA cuenta financiera por sector"),
                           ("Anexo tarjetas y viajes", BC_VIAJES, "BCRA anexo tarjetas y viajes")]:
        h = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja, header=None)
        fila_cod = h.index[h[0].astype(str).str.strip().isin(["cap000", "mes000"])][0]
        cods = h.iloc[fila_cod].tolist()
        ms = h[h[0].apply(lambda x: isinstance(x, (dt.datetime, pd.Timestamp)))]
        for col, cod in enumerate(cods):
            if cod in mapa:
                for f, v in zip(ms[0], ms[col]):
                    filas.append((f, mapa[cod], v, "USD M", f"{fu} ({cod})"))
    c = pd.read_excel(io.BytesIO(contenido), sheet_name="MC por concepto", header=None)
    fila_f = c.index[c.iloc[:, 4].apply(lambda x: isinstance(x, (dt.datetime, pd.Timestamp)))][0]
    fechas = c.iloc[fila_f].tolist()
    for _, r in c.iloc[fila_f + 1:].iterrows():
        hoja = next((str(x).strip() for x in r.tolist()[3::-1] if str(x).strip() not in ("nan", "")), "")
        if hoja in BC_CONCEPTOS and str(r[3]).strip() not in ("nan", ""):
            for f, v in zip(fechas[4:], r.tolist()[4:]):
                if isinstance(f, (dt.datetime, pd.Timestamp)):
                    filas.append((f, BC_CONCEPTOS[hoja], pd.to_numeric(v, errors="coerce") / 1e6, "USD M",
                                  "BCRA mercado de cambios por concepto"))
    return _df(filas)


# ---------------------------------------------------------------- LECAP / BONCAP (tasa fija)
FICHAS = None  # caché en memoria; se persiste en data/raw/lecap_fichas.json desde run.py


def _ficha(sym):
    r = requests.post(f"{BYMA}/bnown/fichatecnica/especies/general",
                      json={"symbol": sym, "Content-Type": "application/json"},
                      headers=BYMA_H, verify=False, timeout=60)
    d = r.json()["data"][0]
    m = re.search(r"(\d+[.,]\d+)\s*%", d.get("interes", ""))
    return {"tem": float(m.group(1).replace(",", ".")) / 100 if m else None,
            "emision": d["fechaEmision"][:10], "vencimiento": d["fechaVencimiento"][:10],
            "denominacion": d.get("denominacion", ""), "interes": d.get("interes", "")[:300],
            "crudo": None if m else {k: v for k, v in d.items() if isinstance(v, (str, int, float)) and len(str(v)) < 300}}


def _dias360(a, b):
    """Convención 30E/360, la que usa el Tesoro para contar los meses de capitalización de las LECAP."""
    d1, d2 = min(a.day, 30), min(b.day, 30)
    return (b.year - a.year) * 360 + (b.month - a.month) * 30 + (d2 - d1)


try:
    TEM_MANUAL = {k: v for k, v in json.loads((pathlib.Path(__file__).resolve().parents[1] / "config" / "lecap_tem.json")
                                               .read_text(encoding="utf-8")).items() if not k.startswith("_") and v}
except Exception:  # noqa: BLE001
    TEM_MANUAL = {}


def lecaps(fichas):
    """TEM de mercado de cada LECAP/BONCAP: pago final (100 capitalizado a la TEM de emisión) vs precio."""
    r = requests.post(f"{BYMA}/lebacs", json={"excludeZeroPxAndQty": False, "T1": True, "T0": False,
                      "page_number": 1, "page_size": 500}, headers=BYMA_H, verify=False, timeout=90)
    syms = {x["symbol"] for x in r.json().get("data", [])
            if re.fullmatch(r"[ST]\d{2}[A-Z]\d", x["symbol"]) and x.get("denominationCcy") == "ARS"
            and x.get("maturityDate") and x["maturityDate"] > str(HOY)}
    # El panel de BYMA no lista los BONCAP largos (T15E7, T30A7, T30J7, T31Y7): se suman los que lista A3
    try:
        for x in _get(MAE + "mercado/datos/RF", headers=MAE_H).json():
            t = str(x.get("ticker", "")).split("/")[0]
            if re.fullmatch(r"[ST]\d{2}[A-Z]\d", t):
                syms.add(t)
    except Exception:  # noqa: BLE001
        pass
    # De noche el panel lista pocas letras: se suman las ya conocidas que no vencieron
    syms = sorted(syms | {k for k, v in fichas.items() if v.get("vencimiento", "") > str(HOY)})
    filas = []
    t0 = int(dt.datetime.combine(desde(HOY - dt.timedelta(days=800)), dt.time()).timestamp())
    for sym in syms:
        try:
            if sym not in fichas or not fichas[sym].get("tem"):
                fichas[sym] = _ficha(sym)
            fi = fichas[sym]
            if not fi["tem"] and TEM_MANUAL.get(sym):  # la ficha no trae la tasa: se toma de config/lecap_tem.json
                fi = {**fi, "tem": TEM_MANUAL[sym] / 100}
            if not fi["tem"]:
                continue
            emi, ven = pd.Timestamp(fi["emision"]), pd.Timestamp(fi["vencimiento"])
            pago = 100 * (1 + fi["tem"]) ** (_dias360(emi, ven) / 30)
            j = _get(f"{BYMA}/chart/historical-series/history", verify=False,
                     params={"symbol": f"{sym} 24HS", "resolution": "D", "from": t0,
                             "to": int(dt.datetime.now().timestamp())}).json()
            for t, c in zip(j.get("t", []), j.get("c", [])):
                f = (dt.datetime.utcfromtimestamp(t) - dt.timedelta(hours=3)).date()
                liq = pd.Timestamp(f) + pd.offsets.BDay(1)
                dias = (ven - liq).days
                if c and dias >= 10:  # con menos de 10 días el redondeo distorsiona la tasa
                    tem = ((pago / c) ** (30 / dias) - 1) * 100
                    filas.append((f, f"lecap_tem_{sym}", tem, "% TEM",
                                  f"Cálculo: BYMA {sym} (vence {fi['vencimiento']}, TEM emisión {fi['tem']*100:.2f}%)"))
        except Exception:  # noqa: BLE001
            continue
    return _df(filas)


# ---------------------------------------------------------------- Bonos y letras ajustados por CER
def cer_bonos(fichas):
    """Precio diario (BYMA, 24 hs) de los Boncer cero cupón (TZX...) y las letras CER (X...) que lista A3.
    La ficha da la fecha de emisión y de vencimiento; el pipeline calcula después la tasa real implícita."""
    syms = set()
    for x in _get(MAE + "mercado/datos/RF", headers=MAE_H).json():
        t = str(x.get("ticker", "")).split("/")[0]
        if re.fullmatch(r"TZX[A-Z0-9]{2}|X\d{2}[A-Z]\d", t):
            syms.add(t)
    syms |= {k for k, v in fichas.items() if v.get("vencimiento", "") > str(HOY)}
    t0 = int(dt.datetime.combine(desde(HOY - dt.timedelta(days=800)), dt.time()).timestamp())
    filas, errores = [], []
    for sym in sorted(syms):
        try:
            if sym not in fichas:
                fi = _ficha(sym)
                fichas[sym] = {"emision": fi["emision"], "vencimiento": fi["vencimiento"], "denominacion": fi["denominacion"]}
            fi = fichas[sym]
            if fi["vencimiento"] <= str(HOY):
                continue
            j = _get(f"{BYMA}/chart/historical-series/history", verify=False,
                     params={"symbol": f"{sym} 24HS", "resolution": "D", "from": t0, "to": int(dt.datetime.now().timestamp())}).json()
            for t, c in zip(j.get("t", []), j.get("c", [])):
                f = (dt.datetime.utcfromtimestamp(t) - dt.timedelta(hours=3)).date()
                if c:
                    filas.append((f, f"cer_px_{sym}", c, "ARS por 100 VN", f"BYMA ({sym} 24HS) (emisión {fi['emision']}, vence {fi['vencimiento']})"))
        except Exception as e:  # noqa: BLE001
            errores.append(f"{sym}: {e}"[:100])
    if not filas:
        raise RuntimeError("; ".join(errores[:3]) or "sin bonos CER")
    df = _df(filas)
    df.attrs["errores"] = errores
    return df


# ---------------------------------------------------------------- A3 / MAE (API de la web pública)
MAE = "https://api.marketdata.mae.com.ar/api/"
MAE_H = {**UA, "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}


def _mae(ruta, ini, fin):
    import json as _json
    return _get(MAE + ruta, headers=MAE_H, params={"oTitulo": _json.dumps({"fechaDesde": str(ini), "fechaHasta": str(fin)})}).json()


def a3_mae():
    """Volumen del mercado de cambios (FOREX MAE) y tasas de caución y repo a 1 día, por ventanas de 30 días."""
    filas = []
    tope = desde(dt.date(2016, 1, 1))  # volumen y repo desde 2016; cauciones desde 2023
    fin = HOY
    while fin >= tope:  # ventanas completas de 30 días hacia atrás (una ventana de 1 día devuelve otro agregado)
        ini = fin - dt.timedelta(days=29)
        for d in _mae("mercado/titulo/historicoforex/volumenoperado", ini, fin) or []:
            filas.append((d["fecha"][:10], "volumen_mlc", d["cant_Millones"], "USD M", "A3/MAE FOREX (volumen operado)"))
        for d in _mae("mercado/titulo/historicocauciones", ini, fin) or []:
            for x in d.get("details", []):
                if x.get("plazo") == "001" and x.get("ticker") in ("CAARS", "CAUSD") and x.get("tasaPP"):
                    var = "caucion_a3_pesos_1d" if x["ticker"] == "CAARS" else "caucion_a3_usd_1d"
                    filas.append((x["fecha"][:10], var, x["tasaPP"], "% TNA", f"A3/MAE cauciones ({x['ticker']})"))
        for d in _mae("mercado/titulo/historicorepo", ini, fin) or []:
            for x in d.get("details", []):
                if x.get("plazo") == "001" and x.get("rueda") == "REPO" and x.get("moneda") == "$" and x.get("tasaPP"):
                    filas.append((x["fecha"][:10], "repo_a3_pesos_1d", x["tasaPP"], "% TNA", "A3/MAE repo (rueda REPO)"))
        fin = ini - dt.timedelta(days=1)
    df = _df(filas).drop_duplicates(["fecha", "variable"], keep="first")
    # Control: una ventana de varios días a veces devuelve el último día multiplicado (visto el 14/10/26:
    # 4 x 588). Los últimos días se vuelven a pedir de a uno, que da el valor correcto.
    for f in sorted(df.loc[df["variable"] == "volumen_mlc", "fecha"].unique())[-5:]:
        try:
            uno = _mae("mercado/titulo/historicoforex/volumenoperado", f, f) or []
            if uno:
                df.loc[(df["variable"] == "volumen_mlc") & (df["fecha"] == f), "valor"] = uno[0]["cant_Millones"]
        except Exception:  # noqa: BLE001
            pass
    return df
