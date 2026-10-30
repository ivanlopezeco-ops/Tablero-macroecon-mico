"""Escenarios propios de BOPREAL a doce meses; sin descargas ni mutaciones.

Nominales originales vigentes a la fecha del stock, incluidos títulos públicos.
El calendario descuenta amortizaciones pagadas sin volver a reducir el nominal.
Las cancelaciones tributarias se proyectan desde ese stock, no se dan por observadas.
"""
import datetime as dt
import json
import pathlib
from functools import lru_cache

import holidays
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
TITULOS = ("BPOA7", "BPOB7", "BPOC7", "BPOD7", "BPOA8", "BPOB8")
FUENTE = "Estimación propia BOPREAL: uso tributario 50%; intereses completos; stock BYMA fechado"


def cargar():
    return (json.loads((BASE / "config/bopreal_reservas.json").read_text(encoding="utf-8")),
            json.loads((BASE / "config/bonos_flujos.json").read_text(encoding="utf-8")))


@lru_cache(maxsize=16)
def feriados(anio):
    return holidays.country_holidays("AR", years=anio)


def habil(fecha):
    return fecha.weekday() < 5 and fecha not in feriados(fecha.year)


def pago_habil(fecha):
    while not habil(fecha):
        fecha += dt.timedelta(days=1)
    return fecha


def calcular(fecha, reglas, bonos):
    fecha = pd.Timestamp(fecha).date()
    stocks = reglas.get("stocks", [bonos["monto_nominal_usd"]])
    disponibles = [x for x in stocks if dt.date.fromisoformat(x["fecha"]) <= fecha]
    if not disponibles:
        raise ValueError("No se puede proyectar con un stock posterior a la fecha de cálculo")
    foto = max(disponibles, key=lambda x: x["fecha"])
    stock = dt.date.fromisoformat(foto["fecha"])
    hasta = (pd.Timestamp(fecha) + pd.DateOffset(years=1)).date()
    capital = intereses = elegible = 0.0
    detalle = []
    for ticker in TITULOS:
        nominal = float(foto["montos"][ticker])
        if nominal < 0:
            raise ValueError(f"Nominal negativo: {ticker}")
        flujos = bonos["bonos"][ticker]
        pagos = {pago_habil(dt.date.fromisoformat(x["f"])) for x in flujos}
        ventana = reglas["ventanas_impuestos"].get(ticker)
        primer_uso = None
        if ventana:
            inicio, fin = map(dt.date.fromisoformat, ventana)
            # El cierre del stock ya incorpora las bajas observadas hasta ese día.
            primer_uso = max(inicio, stock + dt.timedelta(days=1))
            while primer_uso <= fin and (not habil(primer_uso) or primer_uso in pagos):
                primer_uso += dt.timedelta(days=1)
            if primer_uso > fin:
                primer_uso = None
        for x in flujos:
            contractual = dt.date.fromisoformat(x["f"])
            pago = pago_habil(contractual)
            if not fecha < pago <= hasta:
                continue
            cap, inte = nominal * x["am"] / 1e8, nominal * x["int"] / 1e8
            # No anticipar el uso tributario a una cuota que vence al abrir la ventana.
            cap_elegible = cap if primer_uso and primer_uso < contractual else 0.0
            capital += cap
            intereses += inte
            elegible += cap_elegible
            detalle.append({"titulo": ticker, "pago": pago.isoformat(), "capital": cap,
                            "intereses": inte, "capital_elegible": cap_elegible})
    escenarios = []
    for p in reglas["escenarios"]:
        if not 0 <= p <= 1:
            raise ValueError("Porcentaje de uso tributario fuera de [0, 1]")
        escenarios.append({"porcentaje": int(round(100 * p)), "central": p == reglas["central"],
                           "descuento": elegible * p, "bopreal": capital + intereses - elegible * p})
    if sum(x["central"] for x in escenarios) != 1:
        raise ValueError("Debe existir exactamente un escenario central")
    return {"fecha": fecha.isoformat(), "hasta": hasta.isoformat(), "stock_fecha": stock.isoformat(),
            "desde": reglas["desde"], "capital": capital, "intereses": intereses,
            "capital_elegible": elegible, "escenarios": escenarios, "detalle": detalle}


def aplicar(df, reglas=None, bonos=None):
    """Reemplaza sólo BOPREAL/súper netas desde la vigencia y agrega sensibilidad."""
    if reglas is None or bonos is None:
        reglas, bonos = cargar()
    df = df.copy()
    fechas = pd.to_datetime(df["fecha"])
    inicio = pd.Timestamp(max(reglas["desde"], min(x["fecha"] for x in reglas.get("stocks", [bonos["monto_nominal_usd"]]))))
    objetivo = (fechas >= inicio) & df["variable"].eq("res_bopreal_1a")
    adicionales = []
    for idx in df.index[objetivo]:
        fecha = fechas.loc[idx]
        calculo = calcular(fecha, reglas, bonos)
        central = next(x["bopreal"] for x in calculo["escenarios"] if x["central"])
        antes = float(df.at[idx, "valor"])
        mascara_super = fechas.eq(fecha) & df["variable"].eq("reservas_super_netas")
        df.loc[mascara_super, "valor"] += antes - central
        df.loc[mascara_super, "fuente"] = "Cálculo propio; BOPREAL con escenario tributario central del 50%"
        df.at[idx, "valor"], df.at[idx, "fuente"] = central, FUENTE
        for esc in calculo["escenarios"]:
            adicionales.append({"fecha": df.at[idx, "fecha"], "variable": f"res_bopreal_esc_{esc['porcentaje']}",
                                "valor": esc["bopreal"], "unidad": "USD M",
                                "fuente": f"Estimación propia: uso tributario {esc['porcentaje']}%; stock {calculo['stock_fecha']}"})
    df = df[~df["variable"].str.startswith("res_bopreal_esc_")]
    return pd.concat([df, pd.DataFrame(adicionales)], ignore_index=True) if adicionales else df


def metadata(df):
    reglas, bonos = cargar()
    fechas = df.loc[df["variable"].eq("res_bopreal_1a"), "fecha"]
    if fechas.empty or pd.Timestamp(fechas.max()) < pd.Timestamp(reglas["desde"]):
        return {}
    return {**calcular(fechas.max(), reglas, bonos),
            "stocks": sorted(x["fecha"] for x in reglas.get("stocks", [bonos["monto_nominal_usd"]]))}
