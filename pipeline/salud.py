"""Estado operativo: conserva la antigüedad de fallas completas y parciales."""


def normalizar(estado, previo, ahora):
    for nombre, actual in estado.items():
        problema = actual.get("estado") in ("ERROR", "PARCIAL") or bool(actual.get("error"))
        if not problema:
            actual.pop("error_desde", None)
            continue
        if actual.get("estado") != "ERROR":
            actual["estado"] = "ERROR" if actual.get("filas") == 0 else "PARCIAL"
        anterior = previo.get(nombre, {})
        if anterior.get("estado") in ("ERROR", "PARCIAL") or anterior.get("error"):
            actual["error_desde"] = anterior.get("error_desde") or anterior.get("ok_utc") or ahora
        else:
            actual["error_desde"] = ahora
    return estado
