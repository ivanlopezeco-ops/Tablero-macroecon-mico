"""Tasas forward entre dos bonos de la misma curva.

Para dos bonos con plazos t1 < t2 (años) y tasas efectivas anuales y1, y2, la tasa forward entre ambos plazos es
    (1 + f) ^ (t2 - t1) = (1 + y2) ^ t2 / (1 + y1) ^ t1
y se expresa como TNA con capitalización semestral (base 180/360): 2 x ((1 + f) ^ (1 / 2) - 1).

Plazo: en los Bonares, que amortizan en cuotas, la duration de Macaulay (duration modificada x (1 + TIR));
en los Boncer cero cupón, los días al vencimiento / 365, que es su duration.
Las tasas son la TIR en dólares con precio contra cable (Bonares) y la tasa real sobre CER (Boncer).
"""
import numpy as np
import pandas as pd

PARES = {
    "forward_ao27_ao28": ("bonares", "AO27", "AO28"),
    "forward_tzx27_tzx28": ("cer", "TZX27", "TZX28"),
}
PLAZO_MIN = 0.25                  # con menos de tres meses entre los dos plazos el forward es puro ruido


def _serie(d, var):
    s = d[d["variable"] == var].set_index("fecha")["valor"]
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")].sort_index()


def forward(y1, t1, y2, t2):
    """y en % efectivo anual, t en años -> forward en % TNA base 180/360."""
    f = np.exp((t2 * np.log1p(y2 / 100) - t1 * np.log1p(y1 / 100)) / (t2 - t1)) - 1
    return 2 * ((1 + f) ** 0.5 - 1) * 100


def calcular(der, tabla_cer):
    """der: series derivadas de la corrida (formato largo); tabla_cer: tabla de inflacion.calcular() con los días.
    Devuelve una lista de DataFrames largos."""
    out = []
    for var, (tipo, a, b) in PARES.items():
        if tipo == "bonares":
            y = {k: _serie(der, f"bono_tir_{k.lower()}_ccl") for k in (a, b)}
            t = {k: _serie(der, f"bono_md_{k.lower()}_ccl") * (1 + y[k] / 100) for k in (a, b)}
            fuente = f"Cálculo propio: TIR y duration de {a} y {b} con precio contra cable (BYMA)"
        else:
            if tabla_cer is None or not len(tabla_cer):
                continue
            g = {k: tabla_cer[tabla_cer["sym"] == k].set_index("fecha") for k in (a, b)}
            y = {k: g[k]["real"] for k in (a, b)}
            t = {k: g[k]["dias"] / 365 for k in (a, b)}
            fuente = f"Cálculo propio: tasa real de {a} y {b} (precio de BYMA y CER del BCRA)"
        d = pd.DataFrame({"y1": y[a], "t1": t[a], "y2": y[b], "t2": t[b]}).dropna()
        d = d[d["t2"] - d["t1"] >= PLAZO_MIN]
        if d.empty:
            continue
        s = forward(d["y1"], d["t1"], d["y2"], d["t2"])
        f = pd.DataFrame({"fecha": s.index.date, "variable": var, "valor": s.values, "unidad": "% TNA 180/360", "fuente": fuente})
        if tipo == "bonares":   # provisorio si alguna de las dos TIR del día lo es
            fu = der[der["variable"].isin([f"bono_tir_{k.lower()}_ccl" for k in (a, b)])]
            prov = set(pd.to_datetime(fu.loc[fu["fuente"].astype(str).str.contains("provisorio"), "fecha"]))
            m = pd.to_datetime(f["fecha"]).isin(prov)
            f.loc[m, "fuente"] = f.loc[m, "fuente"] + " (provisorio)"
        out.append(f)
    return out
