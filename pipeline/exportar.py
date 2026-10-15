"""Exporta la base a un JSON compacto para la página (site/data.json)."""
import datetime as dt
import json
import pathlib

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]


def _redondear(v):
    if pd.isna(v):
        return None
    a = abs(v)
    return round(float(v), 4 if a < 10 else 2 if a < 10000 else 0)


def exportar():
    df = pd.read_csv(BASE / "data" / "series.csv")
    df = df[~df["variable"].str.startswith("futuro_DLR")]
    out = {}
    for var, g in df.sort_values("fecha").groupby("variable"):
        out[var] = {"u": g["unidad"].iloc[-1], "f": g["fuente"].iloc[-1],
                    "d": [[f, _redondear(v)] for f, v in zip(g["fecha"], g["valor"])]}
    estado = json.loads((BASE / "data" / "estado.json").read_text(encoding="utf-8"))
    site = BASE / "site"
    site.mkdir(exist_ok=True)
    (site / "data.json").write_text(json.dumps({"generado": dt.datetime.utcnow().isoformat() + "Z",
                                                "estado": estado, "series": out},
                                               ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("data.json:", len(out), "variables")


if __name__ == "__main__":
    exportar()
