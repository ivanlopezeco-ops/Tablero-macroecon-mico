"""Exporta la base a un JSON compacto para la página (site/data.json).

Formato por serie: {"u": unidad, "f": fuente, "t": [días], "v": [valores]}
"t" lleva el primer día como número de días desde 1970-01-01 y después las diferencias
entre fechas consecutivas (1 o 3 en series diarias), para que el archivo siga liviano
con historias largas.
"""
import datetime as dt
import json
import pathlib

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
EPOCA = pd.Timestamp("1970-01-01")


def _redondear(v):
    if pd.isna(v):
        return None
    a = abs(v)
    r = round(float(v), 4 if a < 10 else 2 if a < 10000 else 0)
    return int(r) if r == int(r) else r


def exportar():
    df = pd.read_csv(BASE / "data" / "series.csv", parse_dates=["fecha"])
    df = df[~df["variable"].str.startswith("futuro_DLR")]
    df = df[~df["variable"].str.match(r"caucion_pesos_\d+d$")]  # foto BYMA de una rueda: la reemplaza A3
    out = {}
    for var, g in df.sort_values("fecha").groupby("variable"):
        dias = ((g["fecha"] - EPOCA).dt.days).tolist()
        t = [dias[0]] + [b - a for a, b in zip(dias, dias[1:])]
        out[var] = {"u": g["unidad"].iloc[-1], "f": g["fuente"].iloc[-1],
                    "t": t, "v": [_redondear(v) for v in g["valor"]]}
        prov = g.loc[g["fuente"].astype(str).str.contains("provisorio"), "fecha"]
        if len(prov):  # primer dato provisorio (del día, se reemplaza por el definitivo)
            out[var]["p"] = f"{prov.min():%Y-%m-%d}"
    estado = json.loads((BASE / "data" / "estado.json").read_text(encoding="utf-8"))
    site = BASE / "site"
    site.mkdir(exist_ok=True)
    cal_path = BASE / "data" / "calendario.json"
    calendario = json.loads(cal_path.read_text(encoding="utf-8")) if cal_path.exists() else []
    texto = json.dumps({"generado": dt.datetime.utcnow().isoformat() + "Z", "estado": estado, "series": out, "calendario": calendario},
                       ensure_ascii=False, separators=(",", ":"))
    (site / "data.json").write_text(texto, encoding="utf-8")
    print("data.json:", len(out), "variables,", round(len(texto) / 1e6, 2), "MB")


if __name__ == "__main__":
    exportar()
