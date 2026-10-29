"""Reservas (flujos), liquidez y empleo/ingresos. Fuentes oficiales y cálculos acordados.

Datos separados de la base original: no cambia reservas netas ni rellena observaciones.
Cachea fuentes por 3/12 horas y conserva el último dato ante una falla, con aviso visible.
"""
import concurrent.futures
import datetime as dt
import io
import json
import math
import pathlib
import re
from urllib.parse import urljoin

import pandas as pd
import fuentes as F

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
IDS = [19, 91, *range(46, 60), *range(77, 83), 44, 7, *range(110, 118)]
SALARIOS = "https://www.indec.gob.ar/ftp/cuadros/sociedad/indice_salarios.csv"
EMPLEO = "https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado"
MESES = {m: i + 1 for i, m in enumerate("ene feb mar abr may jun jul ago sep oct nov dic".split())}


def bcra(previo):
    def leer(i):
        viejo = previo.get(str(i), {})
        desde = max(dt.date(2023, 12, 1), F.HOY - dt.timedelta(days=120)) if viejo else dt.date(2023, 12, 1)
        url = f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{i}"
        nuevos, offset, count = {}, 0, 1
        while offset < count:
            j = F._get(f"{url}?desde={desde}&hasta={F.HOY}&limit=3000&offset={offset}", verify=False).json()
            count = j.get("metadata", {}).get("resultset", {}).get("count", 0)
            for r in j.get("results", []):
                for d in r.get("detalle", []):
                    valor = float(d["valor"])
                    if not math.isfinite(valor):
                        raise ValueError(f"BCRA {i}: valor no finito")
                    if i in (7, 44) and valor == 0:  # tasa del día aún sin cerrar
                        continue
                    nuevos[d["fecha"][:10]] = valor
            offset += 3000
        if not nuevos:
            raise ValueError(f"BCRA {i}: respuesta vacía")
        return str(i), {**viejo, **nuevos}

    datos, errores = dict(previo), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(leer, i): i for i in IDS}
        for f in concurrent.futures.as_completed(futures):
            try:
                k, v = f.result()
                datos[k] = v
            except Exception as e:
                errores.append(f"BCRA {futures[f]}: {e}"[:160])
    return datos, errores


def parsear_salarios(contenido):
    df = pd.read_csv(io.BytesIO(contenido), sep=";", decimal=",")
    fechas = pd.to_datetime(df["periodo"], dayfirst=True).dt.strftime("%Y-%m-%d")
    out = {}
    for nombre, col in [("salario_privado", "IS_sector_privado_registrado"), ("salario_publico", "IS_sector_publico")]:
        out[nombre] = {f: float(x) for f, x in zip(fechas, df[col]) if pd.notna(x)}
        if "2023-12-01" not in out[nombre]:
            raise ValueError("Salarios: falta la base diciembre de 2023")
    return out


def fecha_empleo(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%Y-%m-%d")
    m = re.match(r"^([a-z]{3})-(\d{2})", str(v).strip().lower())
    if m and m[1] in MESES:
        return f"20{m[2]}-{MESES[m[1]]:02d}-01"
    return None


def parsear_empleo(contenido):
    df = pd.read_excel(io.BytesIO(contenido), sheet_name="T.2.2", header=None)
    titulo = str(df.iloc[0, 0]).lower()
    if "sin estacionalidad" not in titulo or "sector privado" not in str(df.iloc[1, 1]).lower():
        raise ValueError("SIPA: cambió la estructura del cuadro T.2.2")
    out = {fecha_empleo(r[0]): float(r[1]) for _, r in df.iterrows()
           if fecha_empleo(r[0]) and isinstance(r[1], (float, int)) and pd.notna(r[1])}
    if len(out) < 24:
        raise ValueError("SIPA: serie incompleta")
    return {"empleo_privado_desest": out}


def descargar_empleo():
    pagina = F._get(EMPLEO).text
    links = re.findall(r'(?:https://[^\s"\'<>]+|/sites/default/files/[^\s"\'<>]+)trabajoregistrado_\d{4}_estadisticas\.xlsx', pagina)
    if not links:
        raise ValueError("SIPA: no se encontró el archivo de estadísticas en la página oficial")
    url = urljoin(EMPLEO, max(links, key=lambda x: re.search(r'_(\d{4})_', x)[1]))
    return parsear_empleo(F._get(url).content), url


def mensual(serie, promedio=False):
    s = pd.Series(serie, dtype=float).sort_index()
    s.index = pd.to_datetime(s.index)
    r = s.resample("MS").mean() if promedio else s.resample("MS").sum(min_count=1)
    return {f.strftime("%Y-%m-%d"): float(v) for f, v in r.items() if pd.notna(v)}


def comunes(datos, ids):
    if any(not datos.get(str(i)) for i in ids):
        raise ValueError("Faltan series requeridas: " + str(ids))
    return sorted(set.intersection(*(set(datos[str(i)]) for i in ids)))


def construir(raw, ipc, hoy):
    out = {"series": {}, "cobertura": {}, "controles": {}}
    def put(k, valores, unidad, fuente):
        filas = sorted([[f, float(v)] for f, v in valores.items() if math.isfinite(v)])
        if not filas:
            raise ValueError("Serie vacía: " + k)
        out["series"]["amp_" + k] = {"d": filas, "u": unidad, "f": fuente}
    b = raw["bcra"]
    for i in IDS:
        if str(i) in b:
            put("b" + str(i), b[str(i)], "USD M" if 77 <= i <= 82 else "% TNA" if i in (7, 44) else "ARS M", f"BCRA API v4, serie {i}")
    for total, parts, nombre in [(77, list(range(78, 83)), "reservas"), (46, list(range(47, 60)), "base")]:
        fechas = comunes(b, [total] + parts)
        if not fechas:
            raise ValueError("Sin fechas comunes: " + nombre)
        u = "USD M" if total == 77 else "ARS M"
        residual = {f: b[str(total)][f] - sum(b[str(i)][f] for i in parts) for f in fechas}
        diferencia = max(abs(v) for v in residual.values())
        # La publicación oficial redondea a cuatro decimales. No ocultar diferencias materiales.
        if diferencia > 0.01:
            raise ValueError(f"{nombre}: componentes no concilian, diferencia {diferencia} {u}")
        out["controles"][nombre] = {"n": len(fechas), "maxDiferenciaDiaria": diferencia}
        out["cobertura"][nombre] = {"desde": fechas[0], "hasta": fechas[-1]}
        put(nombre + "_diferencia", mensual(residual), u, "Diferencia entre total y suma de componentes BCRA")
        for i in [total] + parts:
            put("m" + str(i), mensual({f: b[str(i)][f] for f in fechas}), u, f"BCRA API v4, serie {i}; suma mensual sobre fechas comunes")
    for nombre, ids in [("tesoro", [48, 49, 50, 51]), ("instrumentos", list(range(52, 59)))]:
        fechas = comunes(b, list(range(46, 60)))
        put("base_" + nombre, mensual({f: sum(b[str(i)][f] for i in ids) for f in fechas}), "ARS M", "BCRA: suma de factores " + str(ids))
    put("liquidez", {f: 100 * b["19"][f] / b["91"][f] for f in comunes(b, [19, 91]) if b["91"][f] > 0}, "%", "BCRA: cuenta corriente / depósitos en pesos × 100; fechas exactas")
    ref = "2023-12-01"
    if not ipc.get(ref):
        raise ValueError("Falta IPC de diciembre de 2023")
    for k, nom in raw["salarios"].items():
        put(k, {f: (v / ipc[f]) / (nom[ref] / ipc[ref]) * 100 for f, v in nom.items() if f in ipc and f >= ref}, "Índice real dic-2023=100", "INDEC: salarios registrados / IPC del mismo mes")
    for k, v in raw["empleo"].items():
        put(k, v, "Miles de personas", "Secretaría de Trabajo, SIPA, cuadro T.2.2; ajuste estacional oficial")
    for i in range(110, 118):
        # Meses cerrados y comunes con IPC. Un faltante nunca se convierte en cero.
        prom = mensual(b[str(i)], promedio=True)
        put("credito_real_" + str(i), {f: (v / ipc[f]) / (prom[ref] / ipc[ref]) * 100 for f, v in prom.items() if f in ipc and ref <= f < hoy.strftime("%Y-%m-01")}, "Índice real dic-2023=100", f"BCRA serie {i}: promedio mensual de saldos / IPC nacional")
    return out


def actualizar(base, force=False):
    DATA.mkdir(exist_ok=True)
    cachepath = DATA / "raw" / "ampliacion-cache.json"
    cachepath.parent.mkdir(exist_ok=True)
    cache = json.loads(cachepath.read_text(encoding="utf8")) if cachepath.exists() else {}
    ahora = dt.datetime.now(dt.timezone.utc)
    errores = []
    for nombre, horas in [("bcra", 3), ("salarios", 12), ("empleo", 12)]:
        anterior = cache.get(nombre, {})
        reciente = anterior.get("ok_utc") and (ahora - dt.datetime.fromisoformat(anterior["ok_utc"])).total_seconds() < horas * 3600
        if reciente and not force and not anterior.get("errores"):
            continue
        try:
            if nombre == "bcra":
                valores, fallas = bcra(anterior.get("series", {})); url = "https://www.bcra.gob.ar/estadisticas-e-indicadores/"
            elif nombre == "salarios":
                valores, fallas, url = parsear_salarios(F._get(SALARIOS, verify=False).content), [], SALARIOS
            else:
                valores, url = descargar_empleo(); fallas = []
            cache[nombre] = {"series": valores, "url": url, "ok_utc": ahora.isoformat(), "errores": fallas}
            errores.extend(fallas)
        except Exception as e:
            mensaje = f"{nombre}: {type(e).__name__}: {e}"[:300]
            cache[nombre] = {**anterior, "errores": [mensaje]}
            errores.append(mensaje)
    cachepath.write_text(json.dumps(cache, ensure_ascii=False, allow_nan=False), encoding="utf8")
    ipc = base[base["variable"] == "ipc_nivel_general"].copy()
    ipc = {str(f)[:10]: float(v) for f, v in zip(ipc["fecha"], ipc["valor"])}
    resultado = construir({k: v.get("series", {}) for k, v in cache.items()}, ipc, F.HOY)
    resultado["fuentes"] = {k: {a: b for a, b in v.items() if a != "series"} for k, v in cache.items()}
    resultado["calculado_utc"] = ahora.isoformat()
    (DATA / "ampliacion.json").write_text(json.dumps(resultado, ensure_ascii=False, allow_nan=False), encoding="utf8")
    return len(resultado["series"]), errores
