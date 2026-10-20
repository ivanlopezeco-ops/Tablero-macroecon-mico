"""Arma el aviso de fallas a partir de data/estado.json. Lo usa el workflow para abrir, actualizar o cerrar
un issue de GitHub (etiqueta alerta-datos), que llega por mail.

Avisa cuando:
  - una fuente está en ERROR hace más de HORAS_ERROR horas (las caídas de una sola corrida no cuentan),
  - una serie supera su demora normal de publicación (estado.json, "atrasadas"),
  - la corrida entera se cortó (data/error.txt).
Escribe data/alerta.md y deja en GITHUB_OUTPUT hay=1|0 y una firma de los problemas: el workflow comenta
en el issue solo si la firma cambió, para no mandar un mail por hora con lo mismo.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"
HORAS_ERROR = 3
PAGINA = "https://ivanlopezeco-ops.github.io/Tablero-macroecon-mico/"


def armar():
    ruta = DATA / "estado.json"
    e = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"corrida_utc": dt.datetime.utcnow().isoformat()}
    ahora = dt.datetime.utcnow()
    caidas, recientes, parciales = [], [], []
    for k, v in e.get("fuentes", {}).items():
        if v.get("estado") == "ERROR":
            desde = dt.datetime.fromisoformat(v.get("error_desde") or e["corrida_utc"])
            horas = (ahora - desde).total_seconds() / 3600
            (caidas if horas >= HORAS_ERROR else recientes).append((k, horas, v.get("error", "")))
        elif v.get("error"):
            parciales.append((k, v["error"]))
    atrasadas = e.get("atrasadas", [])
    corte = (DATA / "error.txt").read_text(encoding="utf-8")[-1500:] if (DATA / "error.txt").exists() else ""

    L = [f"Corrida del {e['corrida_utc'][:16].replace('T', ' ')} UTC. Tablero: {PAGINA}", ""]
    if corte:
        L += ["## La corrida se cortó", "", "```", corte, "```", ""]
    if caidas:
        L += [f"## Fuentes caídas hace más de {HORAS_ERROR} horas", ""]
        L += [f"- **{k}** (hace {h:.0f} h): {err[:300]}" for k, h, err in caidas] + [""]
    if atrasadas:
        L += ["## Series atrasadas respecto de su demora normal", ""]
        L += [f"- {v}" for v in atrasadas] + ["", "El detalle (último dato y demora esperada) está en `validacion.md`, sección 0, en la rama `datos`.", ""]
    if recientes:
        L += ["## Fallas recientes (todavía no cuentan para el aviso)", ""]
        L += [f"- {k} (hace {h:.1f} h): {err[:200]}" for k, h, err in recientes] + [""]
    if parciales:
        L += ["## Fuentes con errores parciales (siguen andando)", ""]
        L += [f"- {k}: {err[:200]}" for k, err in parciales] + [""]
    L += ["Antes de tocar código, revisar `estado.json` en la rama `datos`. El issue se cierra solo cuando todo vuelve a la normalidad."]

    clave = sorted([f"caida:{k}" for k, *_ in caidas] + [f"atraso:{v}" for v in atrasadas] + (["corte"] if corte else []))
    firma = hashlib.sha1("|".join(clave).encode()).hexdigest()[:12]
    L.append(f"\n<!-- firma: {firma} -->")
    return bool(clave), firma, "\n".join(L)


if __name__ == "__main__":
    hay, firma, texto = armar()
    (DATA / "alerta.md").write_text(texto, encoding="utf-8")
    print(texto)
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"hay={int(hay)}\nfirma={firma}\n")
