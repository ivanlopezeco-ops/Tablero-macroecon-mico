"""Exporta la base a un JSON compacto para la página (site/data.json).

Formato por serie: {"u": unidad, "f": fuente, "t": [días], "v": [valores]}
"t" lleva el primer día como número de días desde 1970-01-01 y después las diferencias
entre fechas consecutivas (1 o 3 en series diarias), para que el archivo siga liviano
con historias largas.
"""
import datetime as dt
import itertools
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
    amp_path = BASE / "data" / "ampliacion.json"
    amp = json.loads(amp_path.read_text(encoding="utf-8")) if amp_path.exists() else {}
    out.update(amp.get("series", {}))
    amp_meta = {k: v for k, v in amp.items() if k != "series"}
    site = BASE / "site"
    site.mkdir(exist_ok=True)
    cal_path = BASE / "data" / "calendario.json"
    calendario = json.loads(cal_path.read_text(encoding="utf-8")) if cal_path.exists() else []
    sd_path = BASE / "data" / "servicio_deuda.json"
    servicio_deuda = json.loads(sd_path.read_text(encoding="utf-8")) if sd_path.exists() else []
    fx_path = BASE / "data" / "curva_fx.json"
    curva_fx = json.loads(fx_path.read_text(encoding="utf-8")) if fx_path.exists() else {}
    lic_path = BASE / "data" / "licitaciones.json"
    licitaciones = json.loads(lic_path.read_text(encoding="utf-8")) if lic_path.exists() else []
    texto = json.dumps({"generado": dt.datetime.utcnow().isoformat() + "Z", "estado": estado, "series": out, "calendario": calendario,
                        "servicio_deuda": servicio_deuda, "licitaciones": licitaciones, "curva_fx": curva_fx, "ampliacion": amp_meta},
                       ensure_ascii=False, separators=(",", ":"))
    (site / "data.json").write_text(texto, encoding="utf-8")
    print("data.json:", len(out), "variables,", round(len(texto) / 1e6, 2), "MB")

    # Archivo chico para dibujar el Resumen enseguida (la página baja el completo en segundo plano)
    corte = (pd.Timestamp.now() - pd.Timedelta(days=DIAS_RESUMEN) - EPOCA).days
    chico = {}
    for var in [v for v in out if v in VARS_RESUMEN or v.startswith("riesgo_pais_")]:
        s = out[var]
        dias = list(itertools.accumulate(s["t"]))
        k = next((i for i, d in enumerate(dias) if d >= corte), len(dias))
        if k < len(dias):
            chico[var] = {**s, "t": [dias[k]] + s["t"][k + 1:], "v": s["v"][k:]}
    texto = json.dumps({"generado": dt.datetime.utcnow().isoformat() + "Z", "estado": estado, "series": chico, "calendario": calendario,
                        "licitaciones": licitaciones[-3:], "parcial": True}, ensure_ascii=False, separators=(",", ":"))
    (site / "data_resumen.json").write_text(texto, encoding="utf-8")
    print("data_resumen.json:", len(chico), "variables,", round(len(texto) / 1e6, 2), "MB")


DIAS_RESUMEN = 800
# Series que usan la pestaña Resumen y el bloque de Novedades (más los riesgos país, para el promedio regional)
VARS_RESUMEN = {"tc_mayorista_a3500", "distancia_techo_banda", "ccl", "mep", "ccl_largo", "mep_largo", "brecha_ccl", "canje_ccl_mep",
                "reservas_brutas", "reservas_netas", "reservas_super_netas", "res_encajes", "res_swap_china", "res_bis", "res_repos",
                "res_bopreal_1a", "res_dep_tesoro", "compras_bcra_mlc", "compras_bcra_acum_anio", "tamar", "caucion_a3_pesos_1d",
                "tasa_real_ex_ante_tamar", "ipc_nivel_general", "ipc_nucleo", "rem_inflacion_12m", "tcrm", "dxy", "brl_usd", "brent",
                "soja_cbot", "oro", "vix", "sp500", "ust_10y", "merval_usd", "bc_cuenta_corriente", "bc_cuenta_financiera",
                "mc_personas_humanas", "banda_techo"}


if __name__ == "__main__":
    exportar()
