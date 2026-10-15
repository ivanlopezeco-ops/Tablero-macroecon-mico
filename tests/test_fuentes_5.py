"""Diagnóstico del volumen del MLC (A3/MAE): ¿por qué el último día da otro número según la ventana?"""
import json, pathlib, requests
H = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
out = []
def q(ruta, a, b):
    r = requests.get(B + ruta, params={"oTitulo": json.dumps({"fechaDesde": a, "fechaHasta": b})}, headers=H, timeout=60)
    return r.json()
for a, b in [("2026-10-14", "2026-10-14"), ("2026-10-13", "2026-10-14"), ("2026-10-08", "2026-10-14"), ("2026-09-15", "2026-10-14"), ("2026-10-01", "2026-10-13")]:
    j = q("mercado/titulo/historicoforex/volumenoperado", a, b)
    out.append(f"## volumenoperado {a}..{b}\n" + "\n".join(json.dumps(x) for x in (j or [])[-6:]))
for a, b in [("2026-10-14", "2026-10-14"), ("2026-10-10", "2026-10-14")]:
    j = q("mercado/titulo/historicoforex", a, b)
    out.append(f"## historicoforex {a}..{b}\n" + json.dumps(j)[:4000])
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_5.md").write_text("\n\n".join(out), encoding="utf-8")
