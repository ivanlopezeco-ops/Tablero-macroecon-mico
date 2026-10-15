"""A3/MAE: probar rutas históricas encontradas en el JS."""
import json, pathlib, requests
UA = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
out = []
for ruta in ["mercado/titulo/historicoforex", "mercado/titulo/historicoforex/volumenoperado",
             "mercado/titulo/historicocauciones", "mercado/titulo/historicorepo"]:
    for fd, fh in [("2026-10-01", "2026-10-14"), ("01/10/2026", "14/10/2026")]:
        try:
            r = requests.get(B + ruta, params={"oTitulo": json.dumps({"fechaDesde": fd, "fechaHasta": fh})}, headers=UA, timeout=40)
            out.append(f"## {ruta} {fd}\n{r.status_code} {r.text[:1200]}\n")
        except Exception as e:
            out.append(f"## {ruta} {fd}\nERROR {e}\n")
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_3.md").write_text("\n".join(out), encoding="utf-8")
