"""A3/MAE: rutas de API dentro de los chunks JS de forex, cauciones e historia."""
import pathlib, re, requests
UA = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
html = requests.get("https://marketdata.mae.com.ar/", headers=UA, timeout=40).text
out = []
idx = [s for s in re.findall(r'src="([^"]+\.js)"', html)]
chunks = set()
for s in idx:
    js = requests.get("https://marketdata.mae.com.ar/" + s.lstrip("/"), headers=UA, timeout=60).text
    chunks |= set(re.findall(r'assets/(?:forex|history-service|cauciones|boletin-diario-service|historicARS|forexWidgets|index)[A-Za-z0-9_\-]*\.js', js))
for c in sorted(chunks):
    js = requests.get("https://marketdata.mae.com.ar/" + c, headers=UA, timeout=60).text
    hits = set(re.findall(r'["`\'](/?[a-z][A-Za-z0-9_\-]*/[A-Za-z0-9_\-/${}]*)["`\']', js))
    hits = [h for h in hits if not h.startswith("assets/") and "/" in h and len(h) < 70]
    ctx = [js[max(0, m.start()-80):m.end()+160] for m in re.finditer(r'get\(|fetch\(', js)][:8]
    out.append(f"## {c}\n" + "\n".join(sorted(hits)) + "\n--- ctx ---\n" + "\n...\n".join(ctx))
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_3.md").write_text("\n\n".join(out)[:60000], encoding="utf-8")
