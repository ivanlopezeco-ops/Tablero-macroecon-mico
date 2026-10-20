"""Inflación implícita en los bonos ajustados por CER.

Para cada bono CER cero cupón (TZX..., letras X...) se calcula la tasa real implícita en su precio:
    precio = 100 x CER(liquidación - 10 días hábiles) / CER(emisión - 10 días hábiles) x (1 + r) ^ (-días / 365)
y, contra la tasa nominal de la curva de LECAP y BONCAP al mismo vencimiento, la inflación que iguala ambas:
    (1 + TEA nominal) / (1 + r) - 1
expresada en promedio mensual: ((1 + inflación anual) ^ (1 / 12) - 1).

La tasa nominal se interpola entre las letras a tasa fija del día, sin extrapolar: un bono CER solo da una
inflación implícita si su vencimiento cae dentro del tramo que cubre la curva nominal. Incluye la prima de
plazo y de liquidez de ambas curvas, de modo que no es una expectativa pura.
"""
import re

import numpy as np
import pandas as pd

DIAS_MIN = 20                     # con menos días, el redondeo de precios distorsiona la tasa
HORIZONTES = {"2m": 60, "4m": 120, "6m": 180}


def _serie(df, var):
    s = df[df["variable"] == var].set_index("fecha")["valor"]
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def _fechas_fuente(df, var):
    f = str(df.loc[df["variable"] == var, "fuente"].iloc[-1])
    emi = re.search(r"emisi[oó]n (\d{4}-\d{2}-\d{2})", f)
    ven = re.search(r"vence (\d{4}-\d{2}-\d{2})", f)
    return (pd.Timestamp(emi.group(1)) if emi else None), (pd.Timestamp(ven.group(1)) if ven else None)


def calcular(df):
    """Devuelve (lista de DataFrames largos para series.csv, tabla de puntos por fecha e instrumento)."""
    cer = _serie(df, "cer")
    if cer.empty:
        return [], pd.DataFrame()
    bd10 = pd.offsets.BDay(10)
    # curva nominal: por fecha, vencimiento y TEA de cada letra o BONCAP
    curva = {}
    for var in [v for v in df["variable"].unique() if str(v).startswith("lecap_tem_")]:
        _, ven = _fechas_fuente(df, var)
        if ven is None:
            continue
        for f, tem in _serie(df, var).items():
            curva.setdefault(f, []).append((ven, (1 + tem / 100) ** (365 / 30) - 1))
    filas = []
    for var in [v for v in df["variable"].unique() if str(v).startswith("cer_px_")]:
        sym = var[7:]
        emi, ven = _fechas_fuente(df, var)
        if emi is None or ven is None:
            continue
        base = cer.asof(emi - bd10)
        if pd.isna(base):
            continue
        for f, precio in _serie(df, var).items():
            if precio <= 0 or f not in curva:
                continue
            liq = f + pd.offsets.BDay(1)
            dias = (ven - liq).days
            puntos = sorted(((v - liq).days, t) for v, t in curva[f])
            if dias < DIAS_MIN or len(puntos) < 2 or not (puntos[0][0] <= dias <= puntos[-1][0]):
                continue
            vt = 100 * cer.asof(liq - bd10) / base
            real = (vt / precio) ** (365 / dias) - 1
            nominal = float(np.interp(dias, [p[0] for p in puntos], [p[1] for p in puntos]))
            implicita = (1 + nominal) / (1 + real) - 1
            filas.append({"fecha": f, "sym": sym, "dias": dias, "real": real * 100, "nominal": nominal * 100,
                          "mensual": ((1 + implicita) ** (1 / 12) - 1) * 100})
    if not filas:
        return [], pd.DataFrame()
    t = pd.DataFrame(filas)
    fuente = "Cálculo propio: bonos CER (BYMA) contra la curva de LECAP y BONCAP"
    out = []
    for sym, g in t.groupby("sym"):
        g = g.set_index("fecha")
        for col, var, uni in (("real", f"cer_tir_real_{sym}", "% TEA real"), ("mensual", f"inflacion_implicita_{sym}", "% mensual")):
            out.append(pd.DataFrame({"fecha": g.index.date, "variable": var, "valor": g[col].values, "unidad": uni, "fuente": fuente}))
    # horizontes constantes: interpolación entre los bonos que rodean cada horizonte
    hz = []
    for fecha, g in t.groupby("fecha"):
        g = g.sort_values("dias")
        for nombre, h in HORIZONTES.items():
            if len(g) >= 2 and g["dias"].iloc[0] <= h <= g["dias"].iloc[-1]:
                hz.append((fecha.date(), f"inflacion_implicita_{nombre}", float(np.interp(h, g["dias"], g["mensual"])), "% mensual",
                           f"{fuente} (interpolado a {h} días)"))
    if hz:
        out.append(pd.DataFrame(hz, columns=["fecha", "variable", "valor", "unidad", "fuente"]))
    return out, t
