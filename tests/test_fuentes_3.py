"""Tercera vuelta: ficha técnica de LECAP en BYMA y rutas reales de la API de A3/MAE."""
import json, pathlib, re, requests, urllib3
urllib3.disable_warnings()
out = []
BY = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"
H = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json", "Origin": "https://open.bymadata.com.ar",
     "Referer": "https://open.bymadata.com.ar/"}
for ep in ["bnown/fichatecnica/especies/general", "bnown/fichatecnica/especies/flujo", "bnown/fichatecnica/especies/amortizacion",
           "bnown/fichatecnica/especies/interes"]:
    for sym in ["S30O6", "S29E7"]:
        try:
            r = requests.post(f"{BY}/{ep}", json={"symbol": sym, "Content-Type": "application/json"}, headers=H, verify=False, timeout=40)
            out.append(f"## BYMA {ep} {sym}\n{r.status_code} {r.text[:1500]}\n")
        except Exception as e:
            out.append(f"## BYMA {ep} {sym}\nERROR {e}\n")
UA = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
try:
    html = requests.get("https://marketdata.mae.com.ar/", headers=UA, timeout=40).text
    cand, ctx = set(), []
    for s in re.findall(r'src="([^"]+\.js)"', html):
        u = s if s.startswith("http") else "https://marketdata.mae.com.ar/" + s.lstrip("/")
        js = requests.get(u, headers=UA, timeout=60).text
        cand |= set(re.findall(r'["`\']([a-z][A-Za-z0-9_\-]*/[A-Za-z0-9_\-/${}.?=&]*)["`\']', js))
        ctx += [js[max(0, m.start()-150):m.end()+250] for m in re.finditer(r'mercado/volumen', js)]
    out.append("## A3 candidatos\n" + "\n".join(sorted(c for c in cand if len(c) < 80)))
    out.append("## A3 contexto mercado/volumen\n" + "\n---\n".join(ctx))
except Exception as e:
    out.append(f"## A3 ERROR {e}")
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_3.md").write_text("\n".join(out), encoding="utf-8")
