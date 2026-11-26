"""Cierres de BYMA (PPT, T+1) publicados por el IAMC en el informe de cada rueda."""
import datetime as dt
import json
import math
import os
import re

from lxml import html

import fuentes as F
import pandas as pd

URL = "https://www.iamc.com.ar/"
INICIO = dt.date(2026, 11, 12)  # última rueda completa anterior a la interrupción
CANAL = "BYMA vía IAMC"


def merval_web():
    """La portada de BYMA fecha el nivel del índice, sin identificarlo como cierre."""
    doc = html.fromstring(F._get("https://www.byma.com.ar/", timeout=(6, 20), intentos=2).content)
    bloques = doc.xpath('//h3[normalize-space()="MSCI Merval"]/..')
    if len(bloques) != 1:
        raise ValueError("La portada de BYMA no identifica un único MSCI Merval")
    marcas = bloques[0].xpath('./div[starts-with(normalize-space(), "Datos al ")]/text()')
    niveles = bloques[0].xpath('./div/div[@data-number]/text()')
    if len(marcas) != 1 or len(niveles) != 1:
        raise ValueError("MSCI Merval sin nivel o fecha inequívoca en la portada de BYMA")
    fecha = dt.date.fromisoformat(marcas[0].strip().removeprefix("Datos al "))
    nivel = float(niveles[0])
    if fecha > F.HOY or not math.isfinite(nivel) or nivel <= 0:
        raise ValueError("Fecha o nivel de MSCI Merval inválido")
    return F._df([(fecha, "merval_msci", nivel, "puntos", "BYMA (MSCI MERVAL, portada) (provisorio)")])


def leer_informe(contenido, esperada=None):
    bloques = html.fromstring(contenido).xpath('//script[@id="payload"]/text()')
    if len(bloques) != 1:
        raise ValueError("Informe sin el bloque de datos del IAMC")
    datos = json.loads(bloques[0])
    tp = datos["tp"]
    fecha = dt.date.fromisoformat(tp["fecha"])
    if fecha > F.HOY or (esperada and fecha != esperada):
        raise ValueError(f"La fecha del informe ({fecha}) difiere de la rueda solicitada")
    precios, sin_volumen = {}, []
    for fila in tp["rows"] + tp["esp"]:
        # pxa es el cierre en la moneda negociada; px puede ser una valuación convertida.
        precio = fila.get("pxa")
        volumen = fila.get("vn")
        if volumen is not None and volumen >= 0 and precio and math.isfinite(precio) and precio > 0:
            precios[fila["tk"]] = precio
            if volumen == 0:
                sin_volumen.append(fila["tk"])
    if not precios:
        raise ValueError(f"Rueda {fecha} sin precios de cierre")
    mer = datos.get("mer", {})
    indice = mer.get("ult") if mer.get("fecha") == fecha.isoformat() else None
    letras, cer = {}, {}
    for fila in tp["rows"]:
        ticker = fila["tk"]
        if fila.get("me") != "ARS" or not fila.get("fe") or not fila.get("fv"):
            continue
        ficha = {"emision": fila["fe"], "vencimiento": fila["fv"]}
        if (re.fullmatch(r"[ST]\d{2}[A-Z]\d", ticker) and fila.get("seg") == "lec"
                and fila.get("ct") == "TEM" and (fila.get("cup") or 0) > 0):
            letras[ticker] = {**ficha, "tem": fila["cup"]}
        if (re.fullmatch(r"TZX[A-Z0-9]{2}|X\d{2}[A-Z]\d", ticker) and fila.get("seg") == "cer"
                and fila.get("aj") == "CER" and fila.get("est") == "Cupon Cero"):
            cer[ticker] = ficha
    return {"fecha": str(fecha), "precios": precios, "sin_volumen": sin_volumen,
            "merval": indice, "letras": letras, "cer": cer}


def cargar_ruedas(cache):
    """Conserva las ruedas verificadas. La última se relee para admitir revisiones."""
    cache.mkdir(parents=True, exist_ok=True)
    ruedas, errores = {}, []
    try:
        indice = F._get(URL + "h/indice.json", timeout=(6, 20), intentos=2).json()
        ultima = dt.date.fromisoformat(indice["ultimo"])
        fechas = sorted({dt.date.fromisoformat(f) for f in indice["ruedas"]} | {ultima})
    except Exception as e:
        errores.append(f"Índice de ruedas: {e}")
        ultima, fechas = None, []

    # La portada puede adelantarse al índice, o seguir disponible si este falla.
    try:
        portada = leer_informe(F._get(URL, timeout=(6, 30), intentos=2).content)
        ruedas[portada["fecha"]] = portada
    except Exception as e:
        errores.append(f"Último informe: {e}")

    for fecha in sorted(set(fechas) | {dt.date.fromisoformat(f) for f in ruedas}):
        if fecha < INICIO or fecha > F.HOY:
            continue
        clave = str(fecha)
        archivo = cache / (clave + ".json")
        guardada = None
        if archivo.is_file():
            try:
                local = json.loads(archivo.read_text(encoding="utf-8"))
                if local.get("fecha") == clave and local.get("precios") and "sin_volumen" in local:
                    guardada = local
            except (ValueError, OSError):
                pass  # se vuelve a descargar una copia incompleta
        try:
            if clave in ruedas:
                rueda = ruedas[clave]
            elif guardada and fecha != ultima:
                ruedas[clave] = guardada
                continue
            else:
                rueda = leer_informe(F._get(f"{URL}h/{clave}/", timeout=(6, 30), intentos=2).content, fecha)
            ruedas[clave] = rueda
            if rueda != guardada:
                tmp = archivo.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_text(json.dumps(rueda, ensure_ascii=False), encoding="utf-8")
                tmp.replace(archivo)
        except Exception as e:
            errores.append(f"{clave}: {e}")
            if guardada:
                ruedas.setdefault(clave, guardada)
    if not ruedas:
        raise ValueError("Sin cierres IAMC. " + " | ".join(errores))
    return ruedas, errores


def cotizaciones(cache, letras, cer, tem_lic):
    ruedas, errores = cargar_ruedas(cache)
    filas = []
    for clave, rueda in sorted(ruedas.items()):
        fecha = dt.date.fromisoformat(clave)
        if not INICIO <= fecha <= F.HOY:
            continue
        precios = rueda["precios"]
        canales = {t: f"{CANAL} (rueda sin volumen)" if t in rueda["sin_volumen"] else CANAL for t in precios}
        for tabla in (F.BYMA_SIMBOLOS, F.BYMA_BONOS):
            for simbolo, (var, unidad) in tabla.items():
                ticker = simbolo.split()[0]
                if ticker in precios:
                    filas.append((fecha, var, precios[ticker], unidad, f"{canales[ticker]} ({simbolo})"))
        for ticker, ficha in (rueda["cer"] | cer).items():
            if ticker in precios and ficha["emision"] <= clave < ficha["vencimiento"]:
                filas.append((fecha, f"cer_px_{ticker}", precios[ticker], "ARS por 100 VN",
                              f"{canales[ticker]} ({ticker} 24HS) (emisión {ficha['emision']}, vence {ficha['vencimiento']})"))
        for ticker, ficha in (rueda["letras"] | letras).items():
            if ticker in precios and ficha.get("emision", "~") <= clave < ficha.get("vencimiento", ""):
                tasa = F.tasa_emision(ticker, ficha, tem_lic)
                if tasa:
                    fila = F.tem_de_cierre(ticker, ficha, tasa, fecha, precios[ticker], canales[ticker])
                    if fila:
                        filas.append(fila)
        if rueda.get("merval") and math.isfinite(rueda["merval"]) and rueda["merval"] > 0:
            filas.append((fecha, "merval_msci", rueda["merval"], "puntos", f"{CANAL} (MSCI MERVAL)"))
    df = F._df(filas)
    if df.empty:
        raise ValueError("El informe no contiene series del tablero")
    df.attrs["errores"] = errores
    return df


def incorporar(base, cierres):
    """El cierre primario prevalece sobre el informe y ambos sobre el intradiario, incluso entre corridas."""
    variables = set(cierres["variable"]) | set(base.loc[base.fuente.str.contains(CANAL, regex=False), "variable"])
    mercado = base.variable.isin(variables)
    datos = pd.concat([base.loc[mercado], cierres], ignore_index=True)
    informe = datos.fuente.str.contains(CANAL, regex=False)
    prov = datos.fuente.str.contains("provisorio", regex=False)
    ordenados = pd.concat([datos[prov], datos[informe & ~prov], datos[~informe & ~prov]])
    return pd.concat([base.loc[~mercado], ordenados.drop_duplicates(["fecha", "variable"], keep="last")],
                     ignore_index=True)
