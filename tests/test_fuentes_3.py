"""Tercera vuelta: parámetros de la API interna de A3/MAE."""
import itertools, pathlib, requests
UA = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api"
rutas = ["forex/historico", "forex/indice-ars-historico", "cauciones/historico", "boletindiario/ventas-totales", "forex/ofertas"]
params = [{}, {"fechaDesde": "2026-10-01", "fechaHasta": "2026-10-14"}, {"desde": "2026-10-01", "hasta": "2026-10-14"},
          {"fecha": "2026-10-14"}, {"fechaDesde": "01/10/2026", "fechaHasta": "14/10/2026"}, {"from": "2026-10-01", "to": "2026-10-14"}]
out = []
for r, p in itertools.product(rutas, params):
    try:
        x = requests.get(f"{B}/{r}", params=p, headers=UA, timeout=40)
        out.append(f"## {r} {p}\n{x.status_code} {x.text[:500]}\n")
    except Exception as e:
        out.append(f"## {r} {p}\nERROR {e}\n")
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_3.md").write_text("\n".join(out), encoding="utf-8")
