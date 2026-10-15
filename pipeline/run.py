"""Corrida diaria: descarga, calcula derivadas, valida y guarda.

Salidas en data/:
  series.csv       base larga acumulada (fecha, variable, valor, unidad, fuente)
  estado.json      estado de cada fuente en la última corrida
  validacion.md    controles contra datos conocidos y entre fuentes
  raw/             archivos crudos para inspección
"""
import datetime as dt
import json
import pathlib
import traceback

import pandas as pd

import fuentes as F

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
PARAM = json.loads((BASE / "config" / "parametros.json").read_text(encoding="utf-8"))
COLS = F.COLS


# ---------------------------------------------------------------- utilidades
def serie(df, var):
    s = df[df["variable"] == var].set_index("fecha")["valor"].sort_index()
    s.index = pd.to_datetime(s.index)
    return s[~s.index.duplicated(keep="last")]


def vigente(lista, fechas):
    """Parámetro escalonado: valor de la última entrada con 'desde' <= fecha."""
    t = pd.Series({pd.Timestamp(x["desde"]): x["usd_millones"] for x in lista}).sort_index()
    return t.reindex(t.index.union(fechas)).ffill().reindex(fechas)


def largo(s, var, uni, fuente):
    s = s.dropna()
    return pd.DataFrame({"fecha": s.index.date, "variable": var, "valor": s.values,
                         "unidad": uni, "fuente": fuente})


# ---------------------------------------------------------------- derivadas
def derivadas(df):
    out, notas = [], {}

    a3500 = serie(df, "tc_mayorista_a3500")
    # MEP y CCL propios con AL30
    al30 = serie(df, "al30_ars")
    mep = al30 / serie(df, "al30_usd_mep")
    ccl = al30 / serie(df, "al30_usd_ccl")
    out += [largo(mep, "mep", "ARS/USD", "Cálculo: AL30/AL30D (BYMA)"),
            largo(ccl, "ccl", "ARS/USD", "Cálculo: AL30/AL30C (BYMA)")]
    out.append(largo((ccl / a3500.reindex(ccl.index) - 1) * 100, "brecha_ccl", "%", "Cálculo: CCL/A3500-1"))
    out.append(largo((ccl / mep - 1) * 100, "canje_ccl_mep", "%", "Cálculo: CCL/MEP-1"))
    techo = serie(df, "banda_techo")
    out.append(largo((techo / a3500 - 1) * 100, "distancia_techo_banda", "%", "Cálculo: techo/A3500-1"))

    # Compras acumuladas en el año
    comp = serie(df, "compras_bcra_mlc")
    out.append(largo(comp.groupby(comp.index.year).cumsum(), "compras_bcra_acum_anio", "USD M",
                     "Cálculo: suma anual de compras BCRA"))

    # Reservas netas y súper netas (método Machado)
    brutas = serie(df, "reservas_brutas")
    f = brutas.index
    encajes = serie(df, "encajes_usd_bcra").reindex(f.union(serie(df, "encajes_usd_bcra").index)).ffill().reindex(f)
    cny = serie(df, "usd_por_cny")
    cny = cny.reindex(f.union(cny.index)).ffill().reindex(f)
    sw = PARAM["swap_china"]
    monto_cny = sw["monto_cny_millones"]
    fa = pd.Timestamp(sw["ancla"]["fecha"])
    if cny.loc[:fa].dropna().empty:
        swap = pd.Series(float(sw["ancla"]["usd_millones"]), index=f)
        notas["swap"] = "SIN tipo de pase CNY: se usa el monto fijo del ancla en USD"
    else:
        if monto_cny is None:
            monto_cny = sw["ancla"]["usd_millones"] / cny.loc[:fa].dropna().iloc[-1]
        notas["swap_cny_millones_usado"] = round(float(monto_cny), 1)
        swap = cny * monto_cny
    bis = vigente(PARAM["bis"], f)
    repos = vigente(PARAM["repos_bcra"], f)
    netas = brutas - encajes - swap - bis - repos
    bop = vigente(PARAM["bopreal_1_anio"], f)
    dep_ars = serie(df, "depositos_gobierno_bcra_me_ars")
    if not dep_ars.empty:
        dep = (dep_ars / a3500.reindex(dep_ars.index.union(a3500.index)).ffill().reindex(dep_ars.index))
        dep = dep.reindex(f.union(dep.index)).ffill().reindex(f)
        notas["dep_tesoro"] = "BCRA id 1266 (depósitos del gobierno en ME, en pesos) / A3500"
    else:
        dep = vigente(PARAM["depositos_usd_tesoro_bcra"], f)
    super_ = netas - bop - dep
    for s, v, fu in [(encajes, "res_encajes", "BCRA id 1243 (último dato disponible)"),
                     (swap, "res_swap_china", "Cálculo: CNY pactados x tipo de pase BCRA"),
                     (bis, "res_bis", "Parámetro (config)"), (repos, "res_repos", "Parámetro (config)"),
                     (bop, "res_bopreal_1a", "Parámetro (config)"), (dep, "res_dep_tesoro", notas.get("dep_tesoro", "Parámetro (config)")),
                     (netas, "reservas_netas", "Cálculo método Machado"),
                     (super_, "reservas_super_netas", "Cálculo método Machado")]:
        out.append(largo(s, v, "USD M", fu))

    # Futuros: contrato de fin del mes corriente y de diciembre
    fut = df[df["variable"].str.startswith("futuro_DLR")].copy()
    if not fut.empty:
        fut["fecha"] = pd.to_datetime(fut["fecha"])
        fut["venc"] = pd.to_datetime(fut["variable"].str[-6:], format="%m%Y") + pd.offsets.MonthEnd(0)
        vivos = fut[fut["venc"] >= fut["fecha"]]
        corto = vivos.sort_values("venc").groupby("fecha").first()["valor"]
        dic = vivos[vivos["venc"].dt.month == 12].sort_values("venc").groupby("fecha").first()["valor"]
        out += [largo(corto, "futuro_fin_mes", "ARS/USD", "Matba Rofex: contrato más corto"),
                largo(dic, "futuro_diciembre", "ARS/USD", "Matba Rofex: próximo diciembre")]

    # Tasa real ex ante: TAMAR efectiva mensual contra inflación esperada del mes siguiente (REM)
    tamar = serie(df, "tamar")
    rem_m = serie(df, "rem_inflacion_mes_siguiente")
    if not rem_m.empty and not tamar.empty:
        rem_d = rem_m.reindex(tamar.index.union(rem_m.index)).ffill().reindex(tamar.index)
        tem = ((1 + tamar / 100 * 30 / 365) - 1) * 100
        out.append(largo(((1 + tem / 100) / (1 + rem_d / 100) - 1) * 100, "tasa_real_ex_ante_tamar",
                         "% mensual", "Cálculo: TEM TAMAR vs inflación esperada próx. mes (REM)"))

    return pd.concat(out, ignore_index=True), notas


# ---------------------------------------------------------------- validación
def validar(df, notas, estado):
    L = [f"# Validación — corrida {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]

    L.append("## 1. Reservas vs tabla de Machado\n")
    L.append("| fecha | componente | nuestro | Machado | dif |\n|---|---|---:|---:|---:|")
    mapa = {"brutas": "reservas_brutas", "encajes": "res_encajes", "swap": "res_swap_china",
            "netas": "reservas_netas", "dep_tesoro": "res_dep_tesoro", "super_netas": "reservas_super_netas"}
    for ref in PARAM["validacion_machado"]:
        for k, var in mapa.items():
            s = serie(df, var)
            v = s.get(pd.Timestamp(ref["fecha"]))
            if v is None or pd.isna(v):
                L.append(f"| {ref['fecha']} | {k} | s/d | {ref[k]:,} | |")
            else:
                L.append(f"| {ref['fecha']} | {k} | {v:,.0f} | {ref[k]:,} | {v - ref[k]:+,.0f} |")
    L.append(f"\nSwap: {notas.get('swap_cny_millones_usado')} millones de CNY. {notas.get('swap', '')}\n")

    dig = BASE / "config" / "machado_digitalizado_mensual.csv"
    if dig.exists():
        g = pd.read_csv(dig, parse_dates=["fecha"]).set_index("fecha")
        nuestro = pd.DataFrame({"netas": serie(df, "reservas_netas"), "super": serie(df, "reservas_super_netas")}).resample("ME").mean()
        j = g.join(nuestro, lsuffix="_machado", rsuffix="_nuestro", how="inner").dropna()
        L.append("## 1c. Historia: promedio mensual nuestro vs gráfico de Machado (digitalizado)\n")
        L.append("| mes | netas nuestro | netas Machado | súper nuestro | súper Machado |\n|---|---:|---:|---:|---:|")
        for f, r in j.iterrows():
            L.append(f"| {f:%Y-%m} | {r['netas_nuestro']:,.0f} | {r['netas_machado']:,.0f} | {r['super_nuestro']:,.0f} | {r['super_machado']:,.0f} |")
        L.append("")

    def cruce(a, b, titulo, n=10, fmt="{:,.1f}"):
        sa, sb = serie(df, a), serie(df, b)
        j = pd.concat([sa, sb], axis=1, keys=[a, b]).dropna().tail(n)
        L.append(f"## {titulo}\n")
        if j.empty:
            L.append("Sin fechas en común.\n")
            return
        L.append(f"| fecha | {a} | {b} | dif |\n|---|---:|---:|---:|")
        for f, r in j.iterrows():
            L.append(f"| {f:%Y-%m-%d} | {fmt.format(r[a])} | {fmt.format(r[b])} | {fmt.format(r[a] - r[b])} |")
        L.append("")

    cruce("bc_billetes_divisas_spnf", "mc_personas_humanas", "1b. Balance cambiario: billetes y divisas SPNF vs personas humanas (mensual)", n=4)
    cruce("riesgo_pais_argentina", "riesgo_pais_argentina_ad", "2. Riesgo país: BCRD vs ArgentinaDatos", fmt="{:,.0f}")
    cruce("mep", "mep_ad", "3. MEP: cálculo propio (AL30) vs ArgentinaDatos")
    cruce("ccl", "ccl_ad", "4. CCL: cálculo propio (AL30) vs ArgentinaDatos")
    cruce("tamar", "badlar", "5. Control de rango: TAMAR vs BADLAR", n=5)
    cruce("caucion_pesos_1d", "tasa_pases_terceros_1d", "5b. Caución 1 día (BYMA) vs pases entre terceros (BCRA)", n=5)

    L.append("## 6. Último dato por variable\n\n| variable | último dato | valor | días de rezago |\n|---|---|---:|---:|")
    ult = df.sort_values("fecha").groupby("variable").last()
    hoy = dt.date.today()
    for var, r in ult.iterrows():
        if var.startswith("futuro_DLR"):
            continue
        L.append(f"| {var} | {r['fecha']} | {r['valor']:,.2f} | {(hoy - r['fecha']).days} |")

    L.append("\n## 7. Estado de fuentes\n\n| fuente | estado | filas | detalle |\n|---|---|---:|---|")
    for k, v in estado.items():
        L.append(f"| {k} | {v['estado']} | {v.get('filas', 0)} | {v.get('error', '')[:150]} |")
    (DATA / "validacion.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    estado, partes = {}, []
    for nombre, fn in [("bcra", F.bcra), ("bcra_cny", F.bcra_cny), ("bcrd_embi", F.bcrd_embi),
                       ("argentinadatos", F.argentinadatos), ("byma_historicos", F.byma_historicos),
                       ("rofex_futuros", F.rofex_futuros), ("cammesa", F.cammesa),
                       ("treasury", F.treasury), ("yahoo", F.yahoo), ("datos_gob", F.datos_gob),
                       ("rem", F.rem), ("itcrm", F.itcrm),
                       ("balance_cambiario", F.balance_cambiario)]:
        try:
            d = fn()
            partes.append(d)
            estado[nombre] = {"estado": "ok", "filas": len(d)}
            if d.attrs.get("errores"):
                estado[nombre]["error"] = " | ".join(d.attrs["errores"])
        except Exception as e:  # noqa: BLE001
            estado[nombre] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}",
                              "traza": traceback.format_exc()[-800:]}
        print(nombre, estado[nombre]["estado"], estado[nombre].get("filas", ""))

    try:
        d, crudos = F.byma_snapshots()
        partes.append(d)
        (RAW / "byma_snapshots.json").write_text(json.dumps(crudos, ensure_ascii=False)[:2_000_000], encoding="utf-8")
        estado["byma_snapshots"] = {"estado": "ok", "filas": len(d)}
    except Exception as e:  # noqa: BLE001
        estado["byma_snapshots"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"}

    for nombre, url in F.ARCHIVOS.items():
        try:
            (RAW / nombre).write_bytes(F._get(url).content)
            estado[f"archivo_{nombre}"] = {"estado": "ok"}
        except Exception as e:  # noqa: BLE001
            estado[f"archivo_{nombre}"] = {"estado": "ERROR", "error": str(e)}

    (RAW / "datos_gob_busqueda.json").write_text(json.dumps(F.datos_gob_buscar([
        "ipc nucleo nivel nacional", "exportaciones total mensual intercambio comercial",
        "importaciones total mensual intercambio comercial", "resultado primario base caja sector publico nacional",
    ]), ensure_ascii=False, indent=1), encoding="utf-8")

    nuevo = pd.concat(partes, ignore_index=True)
    archivo = DATA / "series.csv"
    if archivo.exists():
        viejo = pd.read_csv(archivo, parse_dates=["fecha"])
        viejo["fecha"] = viejo["fecha"].dt.date
        base = pd.concat([viejo, nuevo], ignore_index=True)  # lo nuevo pisa a lo viejo en la misma fecha
    else:
        base = nuevo
    base = base[~base["variable"].isin(["reservas_netas", "reservas_super_netas", "caucion_pesos_1d_vwap"])]
    base = base.drop_duplicates(["fecha", "variable"], keep="last")

    notas = {}
    try:
        der, notas = derivadas(base)
        base = pd.concat([base[~base["variable"].isin(der["variable"].unique())], der], ignore_index=True)
    except Exception:  # noqa: BLE001
        estado["derivadas"] = {"estado": "ERROR", "error": traceback.format_exc()[-1500:]}
    base = base.drop_duplicates(["fecha", "variable"], keep="last").sort_values(["variable", "fecha"])
    base[COLS].to_csv(archivo, index=False)

    (DATA / "estado.json").write_text(json.dumps({"corrida_utc": dt.datetime.utcnow().isoformat(),
                                                  "fuentes": estado, "notas": notas},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        validar(base, notas, estado)
    except Exception:  # noqa: BLE001
        (DATA / "validacion.md").write_text("ERROR en validación\n\n" + traceback.format_exc(), encoding="utf-8")
    print("filas totales:", len(base), "variables:", base["variable"].nunique())


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        DATA.mkdir(exist_ok=True)
        (DATA / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc())
