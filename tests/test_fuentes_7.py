"""Fuentes candidatas: IPC INDEC directo, CPI EE.UU., filas diarias de series.xlsm (compras y reservas)."""
import datetime as dt, io, pathlib, traceback
import pandas as pd, requests, urllib3
urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
out = [f"# Test 7 — {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n"]


def caso(n, f):
    out.append(f"\n## {n}")
    try:
        out.append(str(f())[:4000])
    except Exception:  # noqa: BLE001
        out.append("ERROR " + traceback.format_exc()[-700:])


def indec():
    res = []
    for u in ["https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls",
              "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_06_26.xls",
              "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv",
              "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv"]:
        r = requests.get(u, headers=UA, timeout=60, verify=False)
        res.append(f"{u} -> {r.status_code} {len(r.content)} {r.headers.get('last-modified')}")
        if r.ok and u.endswith(".csv"):
            t = r.content.decode("latin-1")
            ls = t.splitlines()
            res.append("\n".join(ls[:3]))
            res.append("\n".join([x for x in ls if x.startswith('"0"') or x.startswith("0;") or "Nacional" in x][-3:]))
    return "\n".join(res)


caso("INDEC IPC", indec)


def fred():
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL", headers=UA, timeout=60)
    return f"{r.status_code}\n" + "\n".join(r.text.splitlines()[-4:])


caso("FRED CPIAUCSL", fred)


def bls():
    r = requests.get("https://api.bls.gov/publicAPI/v2/timeseries/data/CUSR0000SA0", headers=UA, timeout=60)
    return r.text[:600]


caso("BLS CPI", bls)


def xlsm():
    r = requests.get("https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/series.xlsm", headers=UA, timeout=120, verify=False)
    res = []
    for h in ["BASE MONETARIA", "RESERVAS"]:
        df = pd.read_excel(io.BytesIO(r.content), sheet_name=h, header=None)
        res.append(f"=== {h} {df.shape}")
        for i in range(0, 12):
            res.append(f"{i} " + " | ".join(str(x)[:28] for x in df.iloc[i, :16].tolist()))
        f = pd.to_datetime(df[0], errors="coerce")
        diarias = df[f.notna() & (f.dt.day != 1) | (f.notna() & f.dt.year.ge(2026) & f.dt.month.ge(9))]
        res.append("--- últimas filas diarias")
        for _, x in diarias.tail(6).iterrows():
            res.append(" | ".join(str(v)[:14] for v in x.tolist()[:16]))
    return "\n".join(res)


caso("BCRA series.xlsm filas diarias", xlsm)


def bcra_cat():
    j = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/monetarias", headers=UA, timeout=60, verify=False).json()
    return "\n".join(f"{r['idVariable']}: {r.get('descripcion','')[:90]} | {r.get('ultFechaInformada')}" for r in j["results"]
                     if any(k in r.get("descripcion", "").lower() for k in ["compra", "reserva", "divisa"]))


caso("BCRA catálogo: compras/reservas", bcra_cat)
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_7.md").write_text("\n".join(out), encoding="utf-8")
