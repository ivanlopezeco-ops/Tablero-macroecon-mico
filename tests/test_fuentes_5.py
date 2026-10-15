"""datos.gob.ar: qué combinación de parámetros devuelve la serie completa."""
import io, pathlib, time, requests
UA = {"User-Agent": "Mozilla/5.0"}
U = "https://apis.datos.gob.ar/series/api/series/"
out = []
for sid in ["143.3_NO_PR_2004_A_31", "74.3_IET_0_M_16"]:
    for nombre, p in [("csv lim1000", {"format": "csv", "limit": 1000}), ("json lim1000", {"format": "json", "limit": 1000}),
                      ("csv lim500", {"format": "csv", "limit": 500}), ("csv start2012-05", {"format": "csv", "start_date": "2012-05-01"}),
                      ("csv start2012-05 end2020", {"format": "csv", "start_date": "2012-05-01", "end_date": "2020-12-01"}),
                      ("csv start2012", {"format": "csv", "start_date": "2012"}), ("csv desc", {"format": "csv", "sort": "desc"}),
                      ("csv lim1000 start2004", {"format": "csv", "limit": 1000, "start_date": "2004-01-01"}),
                      ("csv offset100", {"format": "csv", "start": 100}), ("csv offset200", {"format": "csv", "start": 200})]:
        for intento in range(2):
            r = requests.get(U, params={"ids": sid, **p}, headers=UA, timeout=60)
            t = r.text
            n = len(t.strip().splitlines()) - 1 if "csv" in nombre else len(r.json().get("data", [])) if r.ok else -1
            out.append(f"{sid} | {nombre} | intento {intento} | {r.status_code} | n={n} | {t[:120]!r}")
            time.sleep(1)
pathlib.Path("results").mkdir(exist_ok=True)
pathlib.Path("results/test_report_5.md").write_text("\n".join(out), encoding="utf-8")
