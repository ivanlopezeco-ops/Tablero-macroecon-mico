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
    1266: ("depositos_gobierno_bcra_me_ars", "ARS M"),
}


# Desde 2003 (salida de la convertibilidad); reservas y base monetaria, desde su primer dato.
BCRA_DESDE = {1: dt.date(1996, 1, 1), 15: dt.date(1996, 1, 1)}


def bcra():
    """Series monetarias del BCRA desde su primer dato (1996 para reservas), paginando de a 3000."""
    filas = []
    for idv, (var, uni) in BCRA_VARS.items():
        offset, total = 0, 1
        while offset < total:
            url = (f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idv}"
                   f"?desde={desde(BCRA_DESDE.get(idv, dt.date(2003, 1, 1)))}&hasta={HOY}&limit=3000&offset={offset}")
            j = _get(url).json()
            total = j.get("metadata", {}).get("resultset", {}).get("count", 0)
            for r in j["results"]:
                for d in r["detalle"]:
                    filas.append((d["fecha"], var, d["valor"], uni, f"BCRA API v4 (id {idv})"))
            offset += 3000
    return _df(filas)


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
         "NG=F": ("gas_natural_hh", "USD/MMBtu"), "^GSPC": ("sp500", "índice")}


def yahoo():
    filas = []
    for t, (var, uni) in YAHOO.items():
        p1 = int(dt.datetime.combine(desde(dt.date(2000, 1, 1)), dt.time()).timestamp())
        j = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}",
                 params={"period1": p1, "period2": int(dt.datetime.now().timestamp()),
                         "interval": "1d"}).json()["chart"]["result"][0]
        for ts, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]):
            if c is not None:
                filas.append((dt.datetime.utcfromtimestamp(ts).date(), var, c, uni, f"Yahoo Finance ({t})"))
    return _df(filas)


# ---------------------------------------------------------------- INDEC / datos.gob.ar
DATOS_GOB = {
    "148.3_INIVELNAL_DICI_M_26": ("ipc_nivel_general", "índice dic-16=100"),
    "148.3_INUCLEONAL_DICI_M_19": ("ipc_nucleo", "índice dic-16=100"),
    "143.3_NO_PR_2004_A_31": ("emae_desest", "índice 2004=100"),
    "74.3_IET_0_M_16": ("exportaciones", "USD M"),
    "74.3_IIT_0_M_25": ("importaciones", "USD M"),
    "452.3_RESULTADO_RIO_0_M_18_54": ("resultado_primario_spn", "ARS M"),
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


def cpi_eeuu():
    """CPI de EE.UU. (todos los ítems, desestacionalizado) del BLS; FRED como respaldo."""
    filas = []
    try:
        for ini in range(2014, HOY.year + 1, 10):
            r = requests.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", headers={**UA, "Content-Type": "application/json"},
                              data=json.dumps({"seriesid": ["CUSR0000SA0"], "startyear": str(ini), "endyear": str(min(ini + 9, HOY.year))}), timeout=60)
            for d in r.json()["Results"]["series"][0]["data"]:
                if d["period"].startswith("M") and d["period"] != "M13":
                    filas.append((dt.date(int(d["year"]), int(d["period"][1:]), 1), "cpi_eeuu", float(d["value"]), "índice 1982-84=100", "BLS (CUSR0000SA0)"))
    except Exception:  # noqa: BLE001
        t = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", timeout=150).text
        for f, v in pd.read_csv(io.StringIO(t)).values.tolist():
            if str(f) >= "2014":
                filas.append((f, "cpi_eeuu", v, "índice 1982-84=100", "FRED (CPIAUCSL)"))
    return _df(filas)


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
    """Último precio operado de los bonos (BYMA, con 20 minutos de demora), fechado hoy. Solo durante la rueda."""
    if not en_rueda():
        return _df([])
    r = requests.post(f"{BYMA}/public-bonds", json={"excludeZeroPxAndQty": True, "T2": False, "T1": True, "T0": False,
                      "Content-Type": "application/json"}, headers=BYMA_H, verify=False, timeout=60)
    data = r.json()
    data = data.get("data", data) if isinstance(data, dict) else data
    filas = []
    for d in data:
        sym = f"{d.get('symbol')} 24HS"
        if sym in BYMA_SIMBOLOS and (d.get("trade") or 0) > 0 and (d.get("volume") or 0) > 0:
            var, uni = BYMA_SIMBOLOS[sym]
            filas.append((HOY, var, d["trade"], uni, f"BYMA intradiario ({sym}) (provisorio)"))
    return _df(filas)


def bcra_a3500_hoy():
    """A3500 del día por la API cambiaria (aparece después del cierre, antes que en la API monetaria)."""
    filas = []
    for f in [HOY - dt.timedelta(days=i) for i in range(4)]:
        try:
            j = _get(f"https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones?fecha={f}").json()
        except Exception:  # noqa: BLE001
            continue
        r = j.get("results") or {}
        for d in r.get("detalle", []):
            if d.get("codigoMoneda") == "USD" and d.get("tipoCotizacion"):
                filas.append((r.get("fecha", f), "tc_mayorista_a3500", d["tipoCotizacion"], "ARS/USD", "BCRA API cambiaria (A3500)"))
    return _df(filas)


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
