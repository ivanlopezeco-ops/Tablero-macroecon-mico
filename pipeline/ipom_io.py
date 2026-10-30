"""Descargas trazables y reemplazos atómicos de las nuevas fuentes."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import fuentes as F

RAW = Path(__file__).resolve().parents[1] / 'data' / 'raw' / 'ipom'
FORCE = False


def guardar_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def descargar(url, nombre, horas=0, timeout=60, intentos=2):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / nombre
    meta = RAW / (nombre + '.meta.json')
    anterior = json.loads(meta.read_text('utf-8')) if meta.exists() else {}
    ahora = dt.datetime.now(dt.timezone.utc)
    if (not FORCE and horas and path.exists() and anterior.get('url') == url
            and anterior.get('descargado_utc')
            and (ahora - dt.datetime.fromisoformat(anterior['descargado_utc'])).total_seconds() < horas * 3600):
        return path
    contenido = F._get(url, timeout=timeout, intentos=intentos).content
    if not contenido:
        raise ValueError('Descarga vacía: ' + nombre)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(contenido)
    temp.replace(path)
    guardar_json(meta, {'url': url, 'descargado_utc': ahora.isoformat(),
                        'sha256': hashlib.sha256(contenido).hexdigest()})
    return path
