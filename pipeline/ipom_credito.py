"""Lectores de tasas mensuales y cartera irregular del BCRA."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from ipom_io import RAW

import pandas as pd

TASAS_URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/preser_tas.xls"
BANCOS_URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/informe-bancos-anexo.xlsx"
TASAS_PAGINA = "https://www.bcra.gob.ar/tasas-de-interes/"
BANCOS_PAGINA = "https://www.bcra.gob.ar/informe-sobre-bancos/"
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def serie(nombre, unidad, fuente, url, datos, frecuencia, metodologia, **extras):
    datos = sorted(datos)
    if not datos:
        raise ValueError("Serie vacía: " + nombre)
    fechas = [f for f, _ in datos]
    if len(fechas) != len(set(fechas)):
        raise ValueError("Fechas duplicadas: " + nombre)
    for f, v in datos:
        dt.date.fromisoformat(f)
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"Valor inválido {nombre}: {f}, {v}")
    return dict(nombre=nombre, unidad=unidad, fuente=fuente, url=url,
                datos=datos, frecuencia=frecuencia, metodologia=metodologia,
                desde=datos[0][0], hasta=datos[-1][0], **extras)


def mensuales_tasas():
    d = pd.read_excel(RAW / "credito-tasas.xls", sheet_name="Tasas_sector_privado", header=None)
    # Celdas comprobadas en el encabezado multirenglón: D, R, AX.
    assert "Adelantos en cuenta corriente" in str(d.iloc[18, 3])
    assert "Documentos descontados" in str(d.iloc[18, 17])
    assert "Personales" == str(d.iloc[19, 49]).strip()
    assert "moneda nacional" in str(d.iloc[17, 3])
    cols = {"tasa_adelantos_mensual": (3, "Adelantos en cuenta corriente"),
            "tasa_documentos_mensual": (17, "Documentos descontados"),
            "tasa_personales_mensual": (49, "Préstamos personales")}
    datos = {k: [] for k in cols}
    anio = None
    for _, r in d.iloc[25:].iterrows():
        try:
            n = float(r.iloc[0])
            if math.isfinite(n) and 1900 <= n < 2101:
                anio = int(n)
        except (TypeError, ValueError):
            pass
        mes = MESES.get(str(r.iloc[1]).lower().strip()[:3])
        if not mes or not anio or anio < 2016:
            continue
        fecha = f"{anio:04d}-{mes:02d}-01"
        for key, (col, _) in cols.items():
            v = pd.to_numeric(r.iloc[col], errors="coerce")
            if pd.notna(v):
                datos[key].append([fecha, float(v)])
    metodo = ("Tasas nominales anuales oficiales, promedio ponderado por monto operado. "
              "Préstamos a tasa fija o repactable en moneda nacional al sector privado no financiero; "
              "total de entidades. Adelantos: ponderación por saldos diarios; personales y documentos: "
              "capital desembolsado. No es CFT ni tasa efectiva. No se imputa el mes sin publicación. "
              "La línea describe el producto financiero, no el destino final del crédito.")
    return {k: serie(n, "% TNA", "BCRA, tasas de interés por préstamos, serie mensual",
                     TASAS_URL, datos[k], "Mensual", metodo,
                     pagina_fuente=TASAS_PAGINA, hoja="Tasas_sector_privado", columna_excel=col + 1)
            for k, (col, n) in cols.items()}


def morosidad():
    d = pd.read_excel(RAW / "credito-bancos.xlsx", sheet_name="Calidad de Cartera (por líneas)", header=None)
    config = {"mora_total": (3, 5, 6, 19, "Total privado"),
              "mora_familias": (55, 57, 58, 68, "Familias"),
              "mora_empresas": (99, 101, 102, 113, "Empresas")}
    datos, saldos = {}, {}
    for key, (grupo, fechas, fila, saldo, nombre) in config.items():
        assert "Ratio de irregularidad" in str(d.iloc[fechas-1, 0])
        assert "En porcentaje" in str(d.iloc[fechas, 0])
        assert "Cartera irregular total" == str(d.iloc[fila, 0]).strip()
        assert ("Privado" if key == "mora_total" else nombre) in str(d.iloc[grupo, 0])
        datos[key], saldos[key] = [], {}
        for col in range(1, d.shape[1]):
            fecha, valor = d.iloc[fechas, col], d.iloc[fila, col]
            if isinstance(fecha, dt.datetime) and pd.notna(valor):
                f = fecha.strftime("%Y-%m-01")
                datos[key].append([f, float(valor)])
                saldos[key][f] = float(d.iloc[saldo, col])
    mapas = {k: dict(v) for k, v in datos.items()}
    errores = []
    contraste = pd.read_excel(RAW / "credito-bancos.xlsx", sheet_name="Calidad de Cartera", header=None)
    total_alternativo = {contraste.iloc[3,c].strftime("%Y-%m-01"): float(contraste.iloc[8,c])
                        for c in range(1,contraste.shape[1]) if isinstance(contraste.iloc[3,c],dt.datetime)
                        and pd.notna(contraste.iloc[8,c])}
    diferencias_ponderacion = []
    for f in mapas["mora_total"]:
        total = saldos["mora_total"][f]
        suma = saldos["mora_familias"][f] + saldos["mora_empresas"][f]
        if abs(total-suma) > max(0.02, total * 1e-7):
            raise ValueError("Saldos familias y empresas no concilian: " + f)
        ponderado = sum(mapas[k][f] * saldos[k][f] for k in ["mora_familias", "mora_empresas"]) / total
        diferencias_ponderacion.append(abs(ponderado - mapas["mora_total"][f]))
        errores.append(abs(total_alternativo[f] - mapas["mora_total"][f]))
    if max(errores) > 1e-6:
        raise ValueError("Total publicado difiere entre las dos hojas oficiales")
    metodo = ("Ratio oficial de cartera irregular / financiaciones, en porcentaje del saldo; "
              "no mide el porcentaje de personas en mora. Sistema financiero. Empresas: personas "
              "jurídicas y financiamiento comercial a personas humanas. Familias: personas humanas "
              "excepto destino comercial. Excluye residentes en el exterior. Datos de fin de período "
              "sujetos a revisión, en especial el último mes. Conservar las modificaciones regulatorias "
              "de clasificación de deudores al interpretar la historia, incluido el alivio por COVID-19. "
              "Una reducción del ratio puede reflejar aumento del denominador; no acredita por sí sola "
              "una reducción del saldo irregular.")
    out = {k: serie(c[4], "% de la cartera", "BCRA, Anexo del Informe sobre Bancos", BANCOS_URL,
                    datos[k], "Mensual", metodo, pagina_fuente=BANCOS_PAGINA,
                    hoja="Calidad de Cartera (por líneas)", fila_excel=c[2]+1,
                    ultimo_provisorio=True) for k, c in config.items()}
    return out, {"meses_conciliados": len(errores), "max_diferencia_ratio_pp": max(errores),
                 "control": "Total coincide en las hojas Calidad de Cartera y Calidad de Cartera (por líneas)",
                 "max_diferencia_ponderacion_saldos_publicados_pp": max(diferencias_ponderacion),
                 "nota": "Se preservan los tres ratios oficiales. No se reconstruye el total ponderando "
                         "por los saldos publicados: en algunos períodos históricos esa reconstrucción "
                         "no coincide exactamente con el ratio total oficial."}
