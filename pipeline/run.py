"""Corrida diaria: descarga, calcula derivadas, valida y guarda.

Salidas en data/:
  series.csv       base larga acumulada (fecha, variable, valor, unidad, fuente)
  estado.json      estado de cada fuente en la última corrida
  validacion.md    controles contra datos conocidos y entre fuentes
  raw/             archivos crudos para inspección
"""
import datetime as dt
import json
import os
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


def empalmar(df, principal, previa):
    """Serie principal completada hacia atrás con otra fuente (solo antes del primer dato propio)."""
    a, b = serie(df, principal), serie(df, previa)
    if a.empty:
        return b
    return pd.concat([b[b.index < a.index.min()], a])


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
    # Series largas: antes del primer dato propio (BYMA da unos dos años), ArgentinaDatos
    tmp = pd.concat([df, largo(mep, "mep", "", ""), largo(ccl, "ccl", "", "")], ignore_index=True)
    ccl_l, mep_l = empalmar(tmp, "ccl", "ccl_ad"), empalmar(tmp, "mep", "mep_ad")
    out += [largo(ccl_l, "ccl_largo", "ARS/USD", "Cálculo propio (AL30); antes, ArgentinaDatos"),
            largo(mep_l, "mep_largo", "ARS/USD", "Cálculo propio (AL30); antes, ArgentinaDatos")]
    out.append(largo((ccl_l / a3500.reindex(ccl_l.index) - 1) * 100, "brecha_ccl", "%", "Cálculo: CCL/A3500-1"))
    out.append(largo((ccl_l / mep_l - 1) * 100, "canje_ccl_mep", "%", "Cálculo: CCL/MEP-1"))
    out += [largo(empalmar(df, "riesgo_pais_argentina", "riesgo_pais_argentina_ad"), "riesgo_pais_argentina_largo", "pb",
                  "BCRD (EMBIGD); antes de 2007, ArgentinaDatos (Ámbito)"),
]
    techo = serie(df, "banda_techo")
    out.append(largo((techo / a3500 - 1) * 100, "distancia_techo_banda", "%", "Cálculo: techo/A3500-1"))

    # Compras acumuladas en el año
    comp = serie(df, "compras_bcra_mlc")
    out.append(largo(comp.groupby(comp.index.year).cumsum(), "compras_bcra_acum_anio", "USD M",
                     "Cálculo: suma anual de compras BCRA"))

    vol = serie(df, "volumen_mlc")
    if not vol.empty:
        pct = comp / vol.where(vol > 100) * 100
        out.append(largo(pct.where(pct.abs() < 100), "compras_bcra_pct_volumen", "%", "Cálculo: compras BCRA / volumen MLC (A3)"))

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
    rem_m = serie(df, "rem_inflacion_mes_siguiente")
    for tasa in ["tamar", "badlar"]:  # BADLAR da la historia larga (REM desde 2016); TAMAR existe desde oct-24
        t = serie(df, tasa)
        if rem_m.empty or t.empty:
            continue
        t = t[t.index >= rem_m.index.min()]
        rem_d = rem_m.reindex(t.index.union(rem_m.index)).ffill().reindex(t.index)
        tem = t / 100 * 30 / 365 * 100
        out.append(largo(((1 + tem / 100) / (1 + rem_d / 100) - 1) * 100, f"tasa_real_ex_ante_{tasa}",
                         "% mensual", f"Cálculo: TEM {tasa.upper()} vs inflación esperada próx. mes (REM)"))

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
    def solape(a, b, titulo):
        sa, sb = serie(df, a), serie(df, b)
        j = pd.concat([sa, sb], axis=1, keys=[a, b]).dropna()
        L.append(f"## {titulo}\n")
        if j.empty:
            L.append("Sin fechas en común.\n")
            return
        d = j[a] - j[b]
        L.append(f"{len(j)} fechas en común ({j.index.min():%Y-%m-%d} a {j.index.max():%Y-%m-%d}). "
                 f"Diferencia media {d.mean():+,.1f}, mediana absoluta {d.abs().median():,.1f}, máxima absoluta {d.abs().max():,.1f}.\n")
        for anio, g in d.groupby(d.index.year):
            L.append(f"- {anio}: media {g.mean():+,.1f} · máx. abs. {g.abs().max():,.1f}")
        L.append("")

    solape("riesgo_pais_argentina", "riesgo_pais_argentina_ad", "2b. Empalme riesgo país Argentina: BCRD vs ArgentinaDatos en el período común")
    solape("ccl", "ccl_ad", "4b. Empalme CCL: propio vs ArgentinaDatos en el período común")
    solape("mep", "mep_ad", "4c. Empalme MEP: propio vs ArgentinaDatos en el período común")
    cruce("tamar", "badlar", "5. Control de rango: TAMAR vs BADLAR", n=5)
    cruce("caucion_a3_pesos_1d", "tasa_pases_terceros_1d", "5b. Caución 1 día (A3) vs pases entre terceros (BCRA)", n=5)
    cruce("compras_bcra_mlc", "volumen_mlc", "5d. Compras del BCRA vs volumen del MLC (A3)", n=5)

    lec = df[df["variable"].str.startswith("lecap_tem_")]
    if not lec.empty:
        ult_f = lec["fecha"].max()
        c = lec[lec["fecha"] == ult_f].sort_values("variable")
        L.append(f"## 5c. Curva LECAP/BONCAP al {ult_f} (TEM %)\n\n| letra | TEM | fuente |\n|---|---:|---|")
        for _, r in c.iterrows():
            L.append(f"| {r['variable'][10:]} | {r['valor']:.2f} | {r['fuente']} |")
        L.append("")

    L.append("## 6. Último dato por variable\n\n| variable | último dato | valor | días de rezago |\n|---|---|---:|---:|")
    ult = df.sort_values("fecha").groupby("variable").last()
    hoy = F.HOY
    for var, r in ult.iterrows():
        if var.startswith("futuro_DLR") or var.startswith("lecap_tem_"):
            continue
        L.append(f"| {var} | {r['fecha']} | {r['valor']:,.2f} | {(hoy - r['fecha']).days} |")

    L.append("\n## 7. Estado de fuentes\n\n| fuente | estado | filas | detalle |\n|---|---|---:|---|")
    for k, v in estado.items():
        L.append(f"| {k} | {v['estado']} | {v.get('filas', 0)} | {v.get('error', '')[:150]} |")
    (DATA / "validacion.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- main
VERSION_HISTORIA = 3  # subir este número fuerza una descarga histórica completa en la próxima corrida


def modo_completo():
    """Histórico completo si nunca se hizo con esta versión, los sábados (para tomar revisiones) o a pedido."""
    marca = RAW / "historia.json"
    hecho = json.loads(marca.read_text())["version"] if marca.exists() else 0
    return hecho < VERSION_HISTORIA or F.HOY.weekday() == 5 or os.environ.get("HISTORIA") == "1"


def main():
    F.COMPLETO = modo_completo()
    print("modo:", "histórico completo" if F.COMPLETO else f"diario (últimos {F.VENTANA} días)")
    estado, partes = {}, []
    for nombre, fn in [("bcra", F.bcra), ("bcra_cny", F.bcra_cny), ("bcrd_embi", F.bcrd_embi),
                       ("argentinadatos", F.argentinadatos), ("byma_historicos", F.byma_historicos),
                       ("rofex_futuros", F.rofex_futuros), ("cammesa", F.cammesa),
                       ("treasury", F.treasury), ("yahoo", F.yahoo), ("datos_gob", F.datos_gob),
                       ("rem", F.rem), ("itcrm", F.itcrm),
                       ("balance_cambiario", F.balance_cambiario), ("a3_mae", F.a3_mae)]:
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

    fpath = RAW / "lecap_fichas.json"
    fichas = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else {}
    try:
        d = F.lecaps(fichas)
        partes.append(d)
        estado["lecaps"] = {"estado": "ok", "filas": len(d)}
        fpath.write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        estado["lecaps"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"}

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


    nuevo = pd.concat(partes, ignore_index=True)
    archivo = DATA / "series.csv"
    if archivo.exists():
        viejo = pd.read_csv(archivo, parse_dates=["fecha"])
        viejo["fecha"] = viejo["fecha"].dt.date
        base = pd.concat([viejo, nuevo], ignore_index=True)  # lo nuevo pisa a lo viejo en la misma fecha
    else:
        base = nuevo
    if F.COMPLETO:  # la curva LECAP se recalcula entera con la historia de cada letra
        base = base[~base["variable"].str.startswith("lecap_tem_") | base.index.isin(base.index[len(base) - len(nuevo):])]
    # Variables descartadas: foto de caución de BYMA (la reemplaza A3) y EMBIG del BCRP (no empalma con el EMBIGD)
    base = base[~base["variable"].str.match(r"caucion_pesos_\d+d$|riesgo_pais_.*_bcrp$|riesgo_pais_latam_largo$")]
    base = base[~base["variable"].isin(["reservas_netas", "reservas_super_netas", "caucion_pesos_1d_vwap", "compras_bcra_pct_volumen"])]
    base = base.drop_duplicates(["fecha", "variable"], keep="last")

    notas = {}
    try:
        der, notas = derivadas(base)
        base = pd.concat([base[~base["variable"].isin(der["variable"].unique())], der], ignore_index=True)
    except Exception:  # noqa: BLE001
        estado["derivadas"] = {"estado": "ERROR", "error": traceback.format_exc()[-1500:]}
    base = base.drop_duplicates(["fecha", "variable"], keep="last").sort_values(["variable", "fecha"])
    base[COLS].to_csv(archivo, index=False)
    if F.COMPLETO and not any(v["estado"] == "ERROR" for v in estado.values()):
        (RAW / "historia.json").write_text(json.dumps({"version": VERSION_HISTORIA, "fecha": str(F.HOY)}))

    (DATA / "estado.json").write_text(json.dumps({"corrida_utc": dt.datetime.utcnow().isoformat(), "modo": "completo" if F.COMPLETO else "diario",
                                                  "fuentes": estado, "notas": notas},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        validar(base, notas, estado)
    except Exception:  # noqa: BLE001
        (DATA / "validacion.md").write_text("ERROR en validación\n\n" + traceback.format_exc(), encoding="utf-8")
    print("filas totales:", len(base), "variables:", base["variable"].nunique())
    import exportar
    exportar.exportar()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        DATA.mkdir(exist_ok=True)
        (DATA / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc())
