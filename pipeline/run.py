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
import re
import traceback

import numpy as np
import pandas as pd

import bonos as B
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


def serie_def(df, var):
    """Como serie(), sin los datos provisorios del día (para que no se arrastren de una corrida a otra)."""
    d = df[(df["variable"] == var) & ~df["fuente"].astype(str).str.contains("provisorio")]
    return serie(d, var)


def provisorio(frame, fechas):
    """Marca como provisorias las filas de esas fechas."""
    if len(frame) and len(fechas):
        m = pd.to_datetime(frame["fecha"]).isin(pd.to_datetime(list(fechas)))
        frame.loc[m, "fuente"] = frame.loc[m, "fuente"] + " (provisorio)"
    return frame


def diario_desde_mensual(m, extra_meses=0, tasa_extra=None):
    """Índice mensual (fechado el día 1) -> diario, interpolando en logaritmos entre los días 15.
    Se extiende extra_meses con la tasa mensual tasa_extra(mes) (en %). Devuelve (diario, primer mes estimado)."""
    m = m.dropna().sort_index()
    m.index = m.index.to_period("M").to_timestamp()
    est = None
    for _ in range(extra_meses):
        sig = m.index[-1] + pd.offsets.MonthBegin(1)
        r = tasa_extra(sig) if tasa_extra else 0
        m.loc[sig] = m.iloc[-1] * (1 + r / 100)
        est = est or sig
    mid = pd.Series(m.values, index=m.index + pd.Timedelta(days=14))
    dias = pd.date_range(m.index[0], m.index[-1] + pd.offsets.MonthEnd(0), freq="D")
    import numpy as np
    lg = pd.Series(np.log(mid.values), index=mid.index).reindex(dias.union(mid.index)).interpolate(method="time", limit_direction="both")
    # fuera de los extremos, se extrapola con la pendiente del último tramo
    d = np.exp(lg.reindex(dias))
    if len(mid) > 1:
        pend = (np.log(mid.iloc[-1]) - np.log(mid.iloc[-2])) / (mid.index[-1] - mid.index[-2]).days
        tras = dias[dias > mid.index[-1]]
        d.loc[tras] = np.exp(np.log(mid.iloc[-1]) + pend * (tras - mid.index[-1]).days)
    return d, est


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
    fu = df["fuente"].astype(str)
    prov_byma = set(df.loc[df["variable"].isin(["al30_ars", "al30_usd_mep", "al30_usd_ccl"]) & fu.str.contains("provisorio"), "fecha"])
    P = lambda frame: provisorio(frame, prov_byma)  # noqa: E731
    # MEP y CCL propios con AL30
    al30 = serie(df, "al30_ars")
    mep = al30 / serie(df, "al30_usd_mep")
    ccl = al30 / serie(df, "al30_usd_ccl")
    out += [P(largo(mep, "mep", "ARS/USD", "Cálculo: AL30/AL30D (BYMA)")),
            P(largo(ccl, "ccl", "ARS/USD", "Cálculo: AL30/AL30C (BYMA)"))]
    # Riesgo país de Argentina: EMBIGD del BCRD y, para los días que el BCRD todavía no publicó, Ámbito
    rp = serie_def(df, "riesgo_pais_argentina")
    amb = serie(df, "riesgo_pais_argentina_ambito")
    cola = amb[amb.index > rp.index.max()] if not rp.empty else amb.iloc[0:0]
    out += [largo(rp, "riesgo_pais_argentina", "pb", "BCRD (JP Morgan EMBIGD)"),
            largo(cola, "riesgo_pais_argentina", "pb", "Ámbito (provisorio)")]
    df = pd.concat([df[df["variable"] != "riesgo_pais_argentina"], out[-2], out[-1]], ignore_index=True)
    # Series largas: antes del primer dato propio (BYMA da unos dos años), ArgentinaDatos
    tmp = pd.concat([df, largo(mep, "mep", "", ""), largo(ccl, "ccl", "", "")], ignore_index=True)
    ccl_l, mep_l = empalmar(tmp, "ccl", "ccl_ad"), empalmar(tmp, "mep", "mep_ad")
    out += [P(largo(ccl_l, "ccl_largo", "ARS/USD", "Cálculo propio (AL30); antes, ArgentinaDatos")),
            P(largo(mep_l, "mep_largo", "ARS/USD", "Cálculo propio (AL30); antes, ArgentinaDatos"))]
    a3500_ff = a3500.reindex(a3500.index.union(ccl_l.index)).ffill()  # en la rueda, el CCL del día contra el último A3500
    out.append(P(largo((ccl_l / a3500_ff.reindex(ccl_l.index) - 1) * 100, "brecha_ccl", "%", "Cálculo: CCL/A3500-1")))
    out.append(P(largo((ccl_l / mep_l - 1) * 100, "canje_ccl_mep", "%", "Cálculo: CCL/MEP-1")))
    rpl = largo(empalmar(df, "riesgo_pais_argentina", "riesgo_pais_argentina_ad"), "riesgo_pais_argentina_largo", "pb",
                "BCRD (EMBIGD); antes de 2007, ArgentinaDatos (Ámbito)")
    out.append(provisorio(rpl, set(cola.index.date)))
    # Merval: S&P Merval hasta el 16/10/26 y MSCI MERVAL empalmado desde ahí (los dos valen lo mismo ese día
    # en la serie empalmada); en dólares, dividido por el CCL del mismo día.
    sp, msci = serie(df, "merval_sp"), serie(df, "merval_msci")
    if not sp.empty:
        sp = sp[sp.index <= pd.Timestamp(F.MERVAL_FIN_SP)]
        k = sp.get(pd.Timestamp(F.MERVAL_FIN_SP))
        nuevo = msci[msci.index > pd.Timestamp(F.MERVAL_FIN_SP)] * k / F.MERVAL_MSCI_BASE if k else msci.iloc[0:0]
        merval = pd.concat([sp, nuevo])
        prov_m = set(df.loc[(df["variable"] == "merval_msci") & fu.str.contains("provisorio"), "fecha"]) | prov_byma
        fu_m = "S&P Merval (Yahoo Finance) hasta el 16/10/26; desde el 19/10/26, MSCI MERVAL (BYMA) empalmado"
        out.append(provisorio(largo(merval, "merval", "puntos", fu_m), prov_m))
        usd = (merval / ccl_l.reindex(merval.index)).dropna()
        out.append(provisorio(largo(usd, "merval_usd", "USD", "Cálculo: Merval / CCL. " + fu_m), prov_m))
    techo = serie(df, "banda_techo")
    out.append(largo((techo / a3500 - 1) * 100, "distancia_techo_banda", "%", "Cálculo: techo/A3500-1"))

    # Tipo de cambio real con bandas
    ipc, cpi = serie(df, "ipc_nivel_general"), serie(df, "cpi_eeuu")
    if not ipc.empty and not cpi.empty and not a3500.empty:
        rem_m = serie(df, "rem_inflacion_mes_siguiente")
        def tasa_ar(mes):  # REM relevado el mes anterior; si no hay, el último
            r = rem_m[(rem_m.index.to_period("M") == (mes - pd.offsets.MonthBegin(1)).to_period("M"))]
            return float(r.iloc[-1] if len(r) else rem_m.iloc[-1]) if len(rem_m) else 2.0
        hoy_m = pd.Timestamp(F.HOY).to_period("M").to_timestamp()
        n_ar = max(0, (hoy_m.year - ipc.index[-1].year) * 12 + hoy_m.month - ipc.index[-1].month + 1)
        p_ar, est_ar = diario_desde_mensual(ipc, n_ar, tasa_ar)
        tasas_us = (cpi.pct_change() * 100).dropna().tail(6).mean()
        n_us = max(0, (hoy_m.year - cpi.index[-1].year) * 12 + hoy_m.month - cpi.index[-1].month + 1)
        p_us, _ = diario_desde_mensual(cpi, n_us, lambda m: tasas_us)
        base = ipc.index[-1] + pd.Timedelta(days=14)            # precios del último mes con IPC publicado
        k = (p_ar.loc[base] / p_ar) * (p_us / p_us.loc[base])     # multiplica un tipo de cambio nominal
        mes_base = f"{ipc.index[-1]:%Y-%m}"
        desde_est = f"{(ipc.index[-1] + pd.offsets.MonthBegin(1)):%Y-%m-%d}"
        fu_r = f"Cálculo: A3500 x CPI EE.UU. / IPC, a precios de {mes_base}; desde {desde_est}, IPC estimado con el REM"
        for v, nom in [(a3500, "tcr_bilateral"), (serie(df, "banda_techo"), "tcr_bilateral_techo"), (serie(df, "banda_piso"), "tcr_bilateral_piso")]:
            out.append(largo(v * k.reindex(v.index), nom, f"ARS/USD de {mes_base}", fu_r))
        notas["tcr_base"] = mes_base
    tcrm = serie(df, "tcrm")
    if not tcrm.empty:
        for v, nom in [(serie(df, "banda_techo"), "tcrm_techo"), (serie(df, "banda_piso"), "tcrm_piso")]:
            r = (tcrm * v / a3500.reindex(a3500.index.union(tcrm.index)).ffill().reindex(tcrm.index)).dropna()
            out.append(largo(r, nom, "índice 17-12-15=100", "Cálculo: ITCRM x banda / A3500"))

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

    # TIR, duration modificada y convexidad de los bonos soberanos (flujos de la ficha técnica de BYMA)
    try:
        flujos = B.cargar()
        for _g, t, *_ in F.BONOS:
            for mon in ("mep", "ccl"):
                v = f"bono_{t.lower()}_{mon}"
                s = serie(df, v)
                s = s[s > 0]
                if s.empty:
                    continue
                fe = s.index.values.astype("datetime64[D]")
                r = B.calcular(flujos[t], fe, B.precio_crudo(flujos[t], fe, s.values))
                prov = set(df.loc[(df["variable"] == v) & df["fuente"].astype(str).str.contains("provisorio"), "fecha"])
                for k, (pref, uni) in enumerate([("bono_tir", "% TEA"), ("bono_md", "años"), ("bono_cx", "años²")]):
                    ser = pd.Series(r[:, k], index=s.index).dropna()
                    out.append(provisorio(largo(ser, f"{pref}_{t.lower()}_{mon}", uni,
                                                "Cálculo propio: flujos de la ficha técnica de BYMA y precio de BYMA"), prov))
    except Exception:  # noqa: BLE001
        notas["bonos_tir"] = "ERROR: " + traceback.format_exc()[-300:]

    # Inflación implícita: bonos CER contra la curva de LECAP y BONCAP
    tabla_inf = None
    try:
        import inflacion
        partes_inf, tabla_inf = inflacion.calcular(df)
        out += partes_inf
        if len(tabla_inf):
            notas["inflacion_implicita_puntos"] = int(tabla_inf["mensual"].notna().sum())
    except Exception:  # noqa: BLE001
        notas["inflacion_implicita"] = "ERROR: " + traceback.format_exc()[-300:]

    # Tasas forward 2027/2028: Bonares (TIR contra cable) y Boncer (tasa real)
    try:
        import forwards
        out += forwards.calcular(pd.concat(out, ignore_index=True), tabla_inf)
    except Exception:  # noqa: BLE001
        notas["forwards"] = "ERROR: " + traceback.format_exc()[-300:]

    # Carry trade y dólar futuro contra la banda proyectada (la foto del día va a data/curva_fx.json)
    try:
        import carry
        partes_c, foto = carry.calcular(df)
        out += partes_c
        (DATA / "curva_fx.json").write_text(json.dumps(foto, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        notas["carry"] = "ERROR: " + traceback.format_exc()[-300:]

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

    try:
        cfg = json.loads(B.CONFIG.read_text(encoding="utf-8"))
        flujos, ref = cfg["bonos"], cfg["saldo_byma"]
        L.append(f"## 5e. Bonos: flujos y TIR contra fuentes externas\n\n"
                 f"Saldo de capital de los flujos contra BYMA ({ref['fecha']}) y TIR propia contra la que publica El Dashboard "
                 f"(precios del 20/10/26 12:17 hs, liquidación {B.FECHA_DASHBOARD}). ⚠ marca desvíos de más de 0,001 en el saldo "
                 "o de más de 0,15 puntos en la TIR.\n\n"
                 "| bono | saldo flujos | saldo BYMA | TIR propia | TIR Dashboard | dif | TIR MEP hoy | TIR CCL hoy | duration MEP |\n"
                 "|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        liq = dt.date.fromisoformat(ref["fecha"])
        liq_d = dt.date.fromisoformat(B.FECHA_DASHBOARD)
        u = lambda var: (serie(df, var).iloc[-1] if len(serie(df, var)) else float("nan"))  # noqa: E731
        for _g, t, *_ in F.BONOS:
            sa = B.saldo(flujos[t], liq) / 100
            sb = ref["ratio"].get(t, 1.0)
            px, ty, _md = B.DASHBOARD[t]
            mia = B.tir(flujos[t], px, liq_d)
            marca = "" if mia is not None and abs(mia - ty) <= 0.15 else " ⚠"
            L.append(f"| {t} | {sa:.4f} | {sb:.4f}{' ⚠' if abs(sa - sb) > 0.001 else ''} | {mia:.2f} | {ty:.2f} | "
                     f"{mia - ty:+.2f}{marca} | {u('bono_tir_' + t.lower() + '_mep'):.2f} | {u('bono_tir_' + t.lower() + '_ccl'):.2f} | "
                     f"{u('bono_md_' + t.lower() + '_mep'):.2f} |")
        L.append("\nEl precio de BYMA incluye los intereses corridos. Base efectiva anual con días reales sobre 365 y liquidación a 24 hs. "
                 "La serie histórica de BYMA viene ajustada por cada pago desde febrero de 2025 y precio_crudo() deshace el ajuste: "
                 "el 2/2/2026 reproduce los precios de Portfolio Personal (AN29D 94,69 contra 94,7). "
                 "También coinciden Bonistas.com (GD29, GD30 y GD38) y Portfolio Personal (TIR del AN29). "
                 "En los Bopreales Serie 1 la TIR no incluye la opción de rescate del tenedor.\n")
    except Exception:  # noqa: BLE001
        L.append("## 5e. Bonos\n\nERROR: " + traceback.format_exc()[-300:] + "\n")

    L.append("## 6. Último dato por variable"+"\n"+"\n"+"Rezago en días hábiles (h) para series diarias y en días corridos desde el inicio del período (d) para las mensuales. "
             "El límite es el rezago normal de publicación de cada fuente; solo se marca lo que lo supera."+"\n"+"\n"+
             "| variable | último dato | valor | rezago | límite | estado |"+"\n"+"|---|---|---:|---:|---:|---|")
    for r in evaluar_rezagos(df):
        L.append(f"| {r['variable']} | {r['fecha']} | {r['valor']:,.2f} | {r['txt_rez']} | {r['txt_lim']} | "
                 f"{'**ATRASADA**' if r['atrasada'] else 'al día'} |")

    L.append("\n## 7. Estado de fuentes\n\n| fuente | estado | filas | detalle |\n|---|---|---:|---|")
    for k, v in estado.items():
        L.append(f"| {k} | {v['estado']} | {v.get('filas', 0)} | {v.get('error', '')[:150]} |")
    atr = [r for r in evaluar_rezagos(df) if r["atrasada"]]
    cab = [f"## 0. Alertas de rezago ({len(atr)})\n"]
    cab += [f"- {r['variable']}: último dato {r['fecha']}, rezago {r['txt_rez']} (demora normal: {r['txt_lim']})" for r in atr] or ["- Sin series atrasadas."]
    cab.append("")
    L[1:1] = cab
    (DATA / "validacion.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- rezagos esperados
# (prefijos, unidad, límite). "h" = días hábiles desde la fecha del dato hasta hoy (sin feriados: un feriado
# suma un día de más). "d" = días corridos desde la fecha del dato. "m" = serie mensual: el límite es la
# demora normal de publicación, en días desde el inicio del período; está atrasada solo si el período
# siguiente ya debería haber salido. Los límites de las mensuales son aproximados: se ajustan con lo observado.
REZAGO_ESPERADO = [
    (("ipc_", "cpi_eeuu"), "m", 50),
    (("emae_",), "m", 85),
    (("ipi_", "isac_"), "m", 75),
    (("exportaciones", "importaciones"), "m", 55),
    (("resultado_primario", "intereses_netos"), "m", 85),
    (("recaudacion_",), "m", 20),
    (("bc_", "bcs_", "mc_", "mcc_"), "m", 75),
    (("rem_",), "d", 45),
    (("reservas_", "res_", "base_monetaria", "m2_", "prestamos_", "depositos_", "encajes_", "lebac_", "compras_bcra"), "h", 4),
    (("tcrm", "tcr_brasil", "tcr_eeuu"), "h", 5),
    (("demanda_electrica",), "h", 3),
    (("gd30_",), "h", 2),  # solo histórico de BYMA; el intradiario trae AL30 pero no GD30
    (("badlar", "baibar", "tamar", "tasa_", "carry_", "devaluacion_implicita_"), "h", 2),
    (("riesgo_pais_argentina",), "h", 1),
    (("riesgo_pais_",), "h", 2),
]
REZAGO_DEFECTO = ("h", 1)


def rezago_de(var, fecha, hoy):
    """Devuelve (rezago, unidad, límite, atrasada) para una variable."""
    unidad, limite = REZAGO_DEFECTO
    for pref, u, lim in REZAGO_ESPERADO:
        if var.startswith(pref):
            unidad, limite = u, lim
            break
    if unidad == "h":
        rez = int(np.busday_count(fecha, hoy)) if fecha <= hoy else 0
        return rez, unidad, limite, rez > limite
    rez = (hoy - fecha).days
    if unidad == "m":
        siguiente = (pd.Timestamp(fecha) + pd.offsets.MonthBegin(1)).date()
        return rez, unidad, limite, hoy > siguiente + dt.timedelta(days=limite)
    return rez, unidad, limite, rez > limite


def evaluar_rezagos(df):
    """Una fila por variable: último dato, rezago, límite esperado y si está atrasada."""
    ult = df.sort_values("fecha").groupby("variable").last()
    filas = []
    for var, r in ult.iterrows():
        if var in ("merval_sp", "rem_ipc_esperado"):   # S&P Merval terminó el 16/10/26; el REM esperado está fechado a futuro
            continue
        if var.startswith("futuro_DLR") or var.startswith("lecap_tem_") or var.startswith(("cer_px_", "cer_tir_real_")):
            continue
        if var.startswith("inflacion_implicita_") and var[20:] not in ("2m", "4m", "6m"):
            continue          # por bono: terminan solas al acercarse el vencimiento
        f = pd.Timestamp(r["fecha"]).date()
        rez, u, lim, atr = rezago_de(var, f, F.HOY)
        if u == "m":
            esperado = (pd.Timestamp(f) + pd.offsets.MonthBegin(1)).date() + dt.timedelta(days=lim)
            txt_rez, txt_lim = f"{rez}d", f"próximo dato ~{esperado:%d/%m}"
        else:
            txt_rez, txt_lim = f"{rez}{u}", f"{lim}{u}"
        filas.append({"variable": var, "fecha": f, "valor": r["valor"], "rezago": rez, "unidad": u,
                      "limite": lim, "atrasada": atr, "txt_rez": txt_rez, "txt_lim": txt_lim})
    return filas


# ---------------------------------------------------------------- main
VERSION_HISTORIA = 6  # 6: historia de la curva de tasa fija (letras vencidas) para el carry. subir este número fuerza una descarga histórica completa en la próxima corrida


def modo_completo():
    """Histórico completo si nunca se hizo con esta versión, una vez cada sábado (revisiones) o a pedido."""
    marca = RAW / "historia.json"
    m = json.loads(marca.read_text()) if marca.exists() else {}
    sabado = F.HOY.weekday() == 5 and m.get("fecha") != str(F.HOY)
    return m.get("version", 0) < VERSION_HISTORIA or sabado or os.environ.get("HISTORIA") == "1"


# Cada cuántas horas se vuelve a pedir cada fuente (0 = en todas las corridas). Las mensuales o lentas
# no hace falta bajarlas cada hora; si una falla, se reintenta en la corrida siguiente.
FRECUENCIA_H = {"bcrd_embi": 2, "treasury": 3, "itcrm": 3, "datos_gob": 6, "indec_ipc": 3, "indec_emae": 3, "indec_industria": 6, "indec_ica": 3, "bls_cpi": 12,
                "rem": 12, "balance_cambiario": 12, "cammesa": 6, "argentinadatos": 2, "bonos_historicos": 2, "calendario_indec": 6}


def toca(nombre, previo):
    h = FRECUENCIA_H.get(nombre, 0)
    p = previo.get(nombre, {})
    if F.COMPLETO or not h or p.get("estado") != "ok" or not p.get("ok_utc"):
        return True
    return (dt.datetime.utcnow() - dt.datetime.fromisoformat(p["ok_utc"])).total_seconds() / 3600 >= h - 0.25


def main():
    F.COMPLETO = modo_completo()
    print("modo:", "histórico completo" if F.COMPLETO else f"diario (últimos {F.VENTANA} días)")
    estado, partes = {}, []
    prev_e = DATA / "estado.json"
    previo = json.loads(prev_e.read_text(encoding="utf-8")).get("fuentes", {}) if prev_e.exists() else {}
    # Orden: lo provisorio del día primero, para que lo definitivo de la misma fecha lo pise.
    for nombre, fn in [("byma_intradia", F.byma_intradia), ("ambito_riesgo", F.ambito_riesgo),
                       ("bcra", F.bcra), ("bcra_cny", F.bcra_cny), ("bcrd_embi", F.bcrd_embi),
                       ("argentinadatos", F.argentinadatos), ("byma_historicos", F.byma_historicos),
                       ("bonos_historicos", F.bonos_historicos),
                       ("rofex_futuros", F.rofex_futuros), ("cammesa", F.cammesa),
                       ("treasury", F.treasury), ("yahoo", F.yahoo), ("byma_indices", F.byma_indices),("datos_gob", F.datos_gob), ("indec_ipc", F.indec_ipc),
                       ("indec_emae", F.indec_emae), ("indec_industria", F.indec_industria), ("indec_ica", F.indec_ica), ("bls_cpi", F.cpi_eeuu), ("rem", F.rem), ("itcrm", F.itcrm),
                       ("balance_cambiario", F.balance_cambiario), ("a3_mae", F.a3_mae)]:
        if not toca(nombre, previo):
            estado[nombre] = {**previo[nombre], "omitida": True}
            print(nombre, "omitida (frecuencia)")
            continue
        try:
            d = fn()
            partes.append(d)
            estado[nombre] = {"estado": "ok", "filas": len(d), "ok_utc": dt.datetime.utcnow().isoformat()}
            if d.attrs.get("errores"):
                estado[nombre]["error"] = " | ".join(d.attrs["errores"])
        except Exception as e:  # noqa: BLE001
            estado[nombre] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}",
                              "traza": traceback.format_exc()[-800:]}
        print(nombre, estado[nombre]["estado"], estado[nombre].get("filas", ""))

    # Servicio de deuda en dólares de los bonos soberanos: no es una serie; exportar.py lo suma a data.json
    try:
        grupos = {x[1]: x[0] for x in F.BONOS}
        sd = B.servicio_deuda(B.cargar(), grupos, F.HOY)
        (DATA / "servicio_deuda.json").write_text(json.dumps(sd, ensure_ascii=False), encoding="utf-8")
        estado["servicio_deuda"] = {"estado": "ok", "filas": len(sd), "ok_utc": dt.datetime.utcnow().isoformat()}
    except Exception as e:  # noqa: BLE001
        estado["servicio_deuda"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"[:300]}

    # Calendario de publicaciones del INDEC: no es una serie; se guarda aparte y exportar.py lo suma a data.json
    if toca("calendario_indec", previo):
        try:
            cal, errores = F.calendario_indec()
            for nombre, fn in (("BCRA", F.calendario_bcra), ("licitación", F.proxima_licitacion)):
                try:
                    cal += fn()
                except Exception as e:  # noqa: BLE001
                    errores.append(f"{nombre}: {e}"[:120])
            cal.sort(key=lambda x: (x["f"], x["t"]))
            (DATA / "calendario.json").write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
            estado["calendario_indec"] = {"estado": "ok", "filas": len(cal), "ok_utc": dt.datetime.utcnow().isoformat()}
            if errores:
                estado["calendario_indec"]["error"] = " | ".join(errores)
        except Exception as e:  # noqa: BLE001
            estado["calendario_indec"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"[:300]}
    elif "calendario_indec" in previo:
        estado["calendario_indec"] = {**previo["calendario_indec"], "omitida": True}
    print("calendario_indec", estado.get("calendario_indec", {}).get("estado"))

    # Licitaciones del Tesoro: no es una serie; se acumula en data/licitaciones.json y exportar.py la suma a data.json
    lpath = DATA / "licitaciones.json"
    try:
        previas = json.loads(lpath.read_text(encoding="utf-8")) if lpath.exists() else []
        lic, errores = F.licitaciones(previas)
        lpath.write_text(json.dumps(lic, ensure_ascii=False), encoding="utf-8")
        estado["licitaciones"] = {"estado": "ok", "filas": len(lic), "ok_utc": dt.datetime.utcnow().isoformat()}
        if errores:
            estado["licitaciones"]["error"] = " | ".join(errores)[:500]
    except Exception as e:  # noqa: BLE001
        estado["licitaciones"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"[:300]}
    print("licitaciones", estado["licitaciones"]["estado"])

    fpath = RAW / "lecap_fichas.json"
    fichas = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else {}
    try:
        lic_path = DATA / "licitaciones.json"
        tem_lic = F.tem_licitaciones(json.loads(lic_path.read_text(encoding="utf-8"))) if lic_path.exists() else {}
        hist = sorted({i["t"] for x in (json.loads(lic_path.read_text(encoding="utf-8")) if lic_path.exists() else [])
                       for i in x.get("inst", []) if i.get("t") and re.fullmatch(r"[ST]\d{2}[A-Z]\d", i["t"])})
        if F.COMPLETO and lic_path.exists():   # letras vencidas sin ficha en BYMA: ficha armada con los comunicados
            for sym, fi in F.fichas_desde_licitaciones(json.loads(lic_path.read_text(encoding="utf-8"))).items():
                if not fichas.get(sym, {}).get("tem"):
                    fichas[sym] = fi
        d = F.lecaps(fichas, tem_lic, hist)
        partes.append(d)
        estado["lecaps"] = {"estado": "ok", "filas": len(d)}
        fpath.write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        estado["lecaps"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"}

    fpath2 = RAW / "cer_fichas.json"
    fichas_cer = json.loads(fpath2.read_text(encoding="utf-8")) if fpath2.exists() else {}
    try:
        d = F.cer_bonos(fichas_cer)
        partes.append(d)
        estado["cer_bonos"] = {"estado": "ok", "filas": len(d), "ok_utc": dt.datetime.utcnow().isoformat()}
        if d.attrs.get("errores"):
            estado["cer_bonos"]["error"] = " | ".join(d.attrs["errores"])
        fpath2.write_text(json.dumps(fichas_cer, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        estado["cer_bonos"] = {"estado": "ERROR", "error": f"{type(e).__name__}: {e}"[:300]}

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
    # (oct-26: se probó el A3500 de la API cambiaria del BCRA; da otra cotización redondeada, no el A3500, y se descartó)
    archivo = DATA / "series.csv"
    if archivo.exists():
        viejo = pd.read_csv(archivo, parse_dates=["fecha"])
        viejo["fecha"] = viejo["fecha"].dt.date
        base = pd.concat([viejo, nuevo], ignore_index=True)  # lo nuevo pisa a lo viejo en la misma fecha
    else:
        base = nuevo
    if F.COMPLETO:  # la curva de cada letra que se volvió a bajar se recalcula entera; las demás conservan su historia
        rehechas = set(nuevo.loc[nuevo["variable"].str.startswith("lecap_tem_"), "variable"])
        base = base[~base["variable"].isin(rehechas) | base.index.isin(base.index[len(base) - len(nuevo):])]
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

    # Desde cuándo falla cada fuente: alerta.py avisa solo si la falla dura varias horas (las APIs públicas
    # tienen caídas de una corrida que se arreglan solas).
    ahora = dt.datetime.utcnow().isoformat()
    for k, v in estado.items():
        if v.get("estado") == "ERROR":
            p = previo.get(k, {})
            v["error_desde"] = p.get("error_desde", ahora) if p.get("estado") == "ERROR" else ahora
    (DATA / "estado.json").write_text(json.dumps({"corrida_utc": dt.datetime.utcnow().isoformat(), "modo": "completo" if F.COMPLETO else "diario",
                                                  "fuentes": estado, "notas": notas,
                                                  "atrasadas": [r["variable"] for r in evaluar_rezagos(base) if r["atrasada"]]},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        validar(base, notas, estado)
    except Exception:  # noqa: BLE001
        (DATA / "validacion.md").write_text("ERROR en validación\n\n" + traceback.format_exc(), encoding="utf-8")
    (DATA / "error.txt").unlink(missing_ok=True)  # el corte de una corrida anterior ya no corre
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
