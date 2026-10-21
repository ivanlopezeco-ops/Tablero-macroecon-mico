"""Carry trade y dólar futuro contra la banda cambiaria.

Para cada día y cada contrato de dólar futuro (Matba Rofex, vence el último día hábil del mes):
    devaluación implícita (TEM) = (futuro / A3500) ^ (30 / días) - 1
    tasa fija (TEM)             = curva de LECAP y BONCAP interpolada al mismo plazo, sin extrapolar
    carry (TEM)                 = (1 + tasa fija) / (1 + devaluación implícita) - 1
El carry es lo que rinde, en dólares y por mes, quedarse en tasa fija en pesos si el dólar termina donde
lo paga el futuro. Con horizontes constantes (3 y 6 meses) se interpola entre contratos.

Techo y piso de la banda proyectados: desde enero de 2026 se ajustan cada mes por la última inflación
publicada por el INDEC (la del mes T-2). El techo de fin de mes es el del mes anterior por (1 + IPC de T-2);
para los meses cuyo IPC todavía no salió se usa la mediana del REM. Contra los datos, la regla reproduce el techo
de fin de mes de feb-26 a sep-26 con diferencias menores a 0,3%.
"""
import re

import numpy as np
import pandas as pd

HORIZONTES = {"3m": 90, "6m": 180}
DIAS_MIN = 20                     # con menos días, el redondeo de precios distorsiona las tasas


def _serie(df, var):
    s = df[df["variable"] == var].set_index("fecha")["valor"]
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def _vto_futuro(var):
    """futuro_DLR122026 -> último día hábil de dic-26."""
    m = re.search(r"(\d{2})(\d{4})$", var)
    fin = pd.Timestamp(int(m.group(2)), int(m.group(1)), 1) + pd.offsets.MonthEnd(0)
    return fin - pd.offsets.BDay(0) if fin.weekday() < 5 else fin - pd.offsets.BDay(1)


def _curva_fija(df):
    """{fecha: [(vencimiento, TEM %)]} de las LECAP y BONCAP."""
    curva = {}
    for var in [v for v in df["variable"].unique() if str(v).startswith("lecap_tem_")]:
        f = str(df.loc[df["variable"] == var, "fuente"].iloc[-1])
        m = re.search(r"vence (\d{4}-\d{2}-\d{2})", f)
        if not m:
            continue
        ven = pd.Timestamp(m.group(1))
        for fecha, tem in _serie(df, var).items():
            curva.setdefault(fecha, []).append((ven, tem))
    return curva


def tasa_mensual_banda(df):
    """Tasa de ajuste de la banda de cada mes M (en %): IPC de M-2 si está publicado; si no, REM; si no, el último REM."""
    ipc = _serie(df, "ipc_nivel_general")
    var_ipc = (ipc.pct_change() * 100).dropna()
    rem = _serie(df, "rem_ipc_esperado")
    rem_sig = _serie(df, "rem_inflacion_mes_siguiente")

    def tasa(mes):
        ref = mes - pd.DateOffset(months=2)
        if ref in var_ipc.index:
            return float(var_ipc[ref]), "IPC"
        if ref in rem.index:
            return float(rem[ref]), "REM"
        return (float(rem_sig.iloc[-1]) if len(rem_sig) else 2.0), "REM"
    return tasa


def calcular(df):
    """Devuelve (lista de DataFrames largos para series.csv, foto del último día por contrato)."""
    a3500 = _serie(df, "tc_mayorista_a3500")
    fut = {v: _serie(df, v) for v in df["variable"].unique() if str(v).startswith("futuro_DLR")}
    if a3500.empty or not fut:
        return [], {}
    curva = _curva_fija(df)
    filas = []
    for var, s in fut.items():
        vto = _vto_futuro(var)
        for f, precio in s.items():
            dias = (vto - f).days
            spot = a3500.get(f)
            if dias < DIAS_MIN or not precio or spot is None or pd.isna(spot):
                continue
            dev = ((precio / spot) ** (30 / dias) - 1) * 100
            fija = None
            pts = sorted(((v - (f + pd.offsets.BDay(1))).days, t) for v, t in curva.get(f, []))
            if len(pts) >= 2 and pts[0][0] <= dias <= pts[-1][0]:
                fija = float(np.interp(dias, [p[0] for p in pts], [p[1] for p in pts]))
            filas.append({"fecha": f, "contrato": var[7:], "vto": vto, "dias": dias, "futuro": precio, "spot": spot,
                          "dev": dev, "fija": fija, "carry": None if fija is None else ((1 + fija / 100) / (1 + dev / 100) - 1) * 100})
    if not filas:
        return [], {}
    t = pd.DataFrame(filas)
    fu = "Cálculo propio: dólar futuro (Matba Rofex), A3500 y curva de LECAP y BONCAP (BYMA)"
    hz = []
    for fecha, g in t.groupby("fecha"):
        g = g.sort_values("dias")
        for nombre, h in HORIZONTES.items():
            if len(g) >= 2 and g["dias"].iloc[0] <= h <= g["dias"].iloc[-1]:
                hz.append((fecha.date(), f"devaluacion_implicita_{nombre}", float(np.interp(h, g["dias"], g["dev"])), "% TEM", f"{fu} (interpolado a {h} días)"))
                c = g.dropna(subset=["carry"])
                if len(c) >= 2 and c["dias"].iloc[0] <= h <= c["dias"].iloc[-1]:
                    hz.append((fecha.date(), f"tasa_fija_{nombre}", float(np.interp(h, c["dias"], c["fija"])), "% TEM", f"{fu} (interpolado a {h} días)"))
                    hz.append((fecha.date(), f"carry_{nombre}", float(np.interp(h, c["dias"], c["carry"])), "% TEM", f"{fu} (interpolado a {h} días)"))
    out = [pd.DataFrame(hz, columns=["fecha", "variable", "valor", "unidad", "fuente"])] if hz else []

    # Foto del último día: curva de futuros, tasa fija, dólar que empata la LECAP y banda proyectada
    # último día con futuros y curva de tasa fija a la vez (los futuros del día llegan antes que la curva de cierre)
    con_carry = t.dropna(subset=["carry"])
    f_foto = con_carry["fecha"].max() if len(con_carry) else t["fecha"].max()
    ult = t[t["fecha"] == f_foto].sort_values("dias")
    techo, piso = _serie(df, "banda_techo"), _serie(df, "banda_piso")
    tasa = tasa_mensual_banda(df)
    proy, fuentes = {}, {}
    if len(techo):
        mes0 = techo.index[-1].to_period("M").to_timestamp()
        t_fin = techo[techo.index < mes0].iloc[-1] if (techo.index < mes0).any() else techo.iloc[-1]
        p_fin = piso[piso.index < mes0].iloc[-1] if (piso.index < mes0).any() else piso.iloc[-1]
        mes = mes0
        while mes <= ult["vto"].max():
            r, origen = tasa(mes)
            t_fin, p_fin = t_fin * (1 + r / 100), p_fin * (1 - r / 100)
            proy[mes.strftime("%Y-%m")] = (t_fin, p_fin, r, origen)
            mes += pd.DateOffset(months=1)
    foto = {"fecha": str(ult["fecha"].iloc[0].date()), "spot": float(ult["spot"].iloc[0]), "contratos": []}
    for _, r in ult.iterrows():
        b = proy.get(r["vto"].strftime("%Y-%m"))
        foto["contratos"].append({
            "c": r["contrato"], "vto": str(r["vto"].date()), "dias": int(r["dias"]), "futuro": float(r["futuro"]),
            "dev": round(float(r["dev"]), 4), "fija": None if r["fija"] is None or pd.isna(r["fija"]) else round(float(r["fija"]), 4),
            "carry": None if r["carry"] is None or pd.isna(r["carry"]) else round(float(r["carry"]), 4),
            "empate": None if r["fija"] is None or pd.isna(r["fija"]) else round(float(r["spot"] * (1 + r["fija"] / 100) ** (r["dias"] / 30)), 2),
            "techo": None if not b else round(float(b[0]), 2), "piso": None if not b else round(float(b[1]), 2),
            "ajuste": None if not b else round(float(b[2]), 3), "origen": None if not b else b[3]})
    return out, foto
