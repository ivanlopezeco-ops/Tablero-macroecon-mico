"""Tercera vuelta (b): rutas reales de la API de A3/MAE buscadas en el JS de la web."""
import pathlib, re, requests
UA = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
html = requests.get("https://marketdata.mae.com.ar/", headers=UA, timeout=40).text
cand = set()
for s in re.findall(r'src="([^"]+\.js)"', html):
    u = s if s.startswith("http") else "https://marketdata.mae.com.ar/" + s.lstrip("/")
    js = requests.get(u, headers=UA, timeout=60).text
    cand |= set(re.findall(r'["`\']([a-z][A-Za-z0-9_\-]*/[A-Za-z0-9_\-/${}.?=&]*)["`\']', js))
    ctx = [js[max(0, m.start()-120):m.end()+200] for m in re.finditer(r'mercado/volumen', js)]
out = ["## candidatos", "\n".join(sorted(c for c in cand if len(c) < 80)), "## contexto mercado/volumen", "\n---\n".join(ctx)]
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_3.md").write_text("\n".join(out), encoding="utf-8")
