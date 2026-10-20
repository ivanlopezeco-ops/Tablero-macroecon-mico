"""Flujos de fondos y TIR de los bonos soberanos en dólares.

Los cronogramas salen de las fichas técnicas de BYMA (texto de los prospectos) y quedan explícitos en
config/bonos_flujos.json: una fila por fecha de pago, con el período de devengamiento, la tasa, el saldo
sobre el que se calcula y la amortización. La TIR se calcula en base efectiva anual, con días reales / 365
para descontar, precio sucio (limpio más intereses corridos) y liquidación a 24 horas.

Valores por cada 100 de valor nominal original. Los intereses corridos usan la base de cada prospecto
(30/360 en los bonos de 2020 y los Bopreales).
"""
import datetime as dt
import json
import pathlib

import numpy as np

BASE = pathlib.Path(__file__).resolve().parents[1]
CONFIG = BASE / "config" / "bonos_flujos.json"


# ---------------------------------------------------------------- calendario
def _ult_habil(anio, mes):
    """Último día hábil del mes (sin sábado, domingo ni 31/12, no laborable bancario)."""
    f = (dt.date(anio + (mes == 12), mes % 12 + 1, 1)) - dt.timedelta(days=1)
    while f.weekday() >= 5 or (f.month == 12 and f.day == 31):
        f -= dt.timedelta(days=1)
    return f


def _meses(desde, hasta):
    a, m = desde
    while (a, m) <= hasta:
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def dias360(a, b):
    """30/360 de bonos (US): el día 31 cuenta como 30; el del final también si el del inicio es 30."""
    d1 = 30 if a.day == 31 else a.day
    d2 = 30 if (b.day == 31 and d1 == 30) else b.day
    return (b.year - a.year) * 360 + (b.month - a.month) * 30 + (d2 - d1)


# ---------------------------------------------------------------- generación de cronogramas
def _tasa_en(tramos, fecha):
    """tramos: [(desde, tasa)] ordenados; devuelve la tasa vigente al inicio del período."""
    t = tramos[0][1]
    for d, x in tramos:
        if fecha >= d:
            t = x
    return t


def _step_up(emision, vto, tramos, amort_pct, ini_amort, n_amort, mes_ini=(2021, 7)):
    """Bonos 2020 (Globales y Bonares): cupones el 9/1 y 9/7, amortización en cuotas semestrales."""
    fechas = [dt.date(a, m, 9) for a, m in _meses(mes_ini, (vto.year, vto.month)) if m in (1, 7)]
    pagos_am = [dt.date(a, m, 9) for a, m in _meses((ini_amort.year, ini_amort.month), (vto.year, vto.month)) if m in (1, 7)][:n_amort]
    am = {f: p for f, p in zip(pagos_am, amort_pct)}
    flujos, res, d0 = [], 100.0, emision
    for f in fechas:
        tasa = _tasa_en(tramos, d0)
        i = res * tasa / 100 * dias360(d0, f) / 360
        flujos.append({"f": f.isoformat(), "d0": d0.isoformat(), "tasa": tasa, "res": round(res, 6), "int": round(i, 6), "am": round(am.get(f, 0), 6)})
        res -= am.get(f, 0)
        d0 = f
    return flujos


def _igual(n, total=100.0):
    return [total / n] * n


def _bonar_mensual(emision, vto, tasa, base="30/360"):
    """Bonares en dólares 2027-2029: cupón mensual al último día hábil, amortización íntegra al vencimiento."""
    fechas = [_ult_habil(a, m) for a, m in _meses((emision.year, emision.month), (vto.year, vto.month))]
    fechas = [f for f in fechas if f > emision]
    flujos, d0 = [], emision
    for f in fechas:
        if base == "30/360":
            frac = dias360(d0, f) / 360
        else:
            frac = (f - d0).days / 365
        flujos.append({"f": f.isoformat(), "d0": d0.isoformat(), "tasa": tasa, "res": 100.0, "int": round(100 * tasa / 100 * frac, 6),
                       "am": 100.0 if f == fechas[-1] else 0.0})
        d0 = f
    return flujos


def _bopreal(emision, vto, tasa, fechas_pago, amort):
    """Bopreales: cupón semestral (30/04 y 31/10), base 30/360. amort: {fecha: % del nominal}."""
    flujos, res, d0 = [], 100.0, emision
    for f in fechas_pago:
        i = res * tasa / 100 * dias360(d0, f) / 360
        flujos.append({"f": f.isoformat(), "d0": d0.isoformat(), "tasa": tasa, "res": round(res, 6), "int": round(i, 6), "am": amort.get(f, 0.0)})
        res -= amort.get(f, 0.0)
        d0 = f
    return flujos


def _fechas_oct_abr(desde_ano, hasta_ano_fecha):
    out = []
    for a in range(desde_ano, hasta_ano_fecha.year + 1):
        for m, d in ((4, 30), (10, 31)):
            f = dt.date(a, m, d)
            if f <= hasta_ano_fecha:
                out.append(f)
    return out


def generar():
    E20 = dt.date(2020, 9, 4)
    d = dt.date
    T_AL30 = [(E20, 0.125), (d(2021, 7, 9), 0.5), (d(2023, 7, 9), 0.75), (d(2027, 7, 9), 1.75)]
    T_AL35 = [(E20, 0.125), (d(2021, 7, 9), 1.125), (d(2022, 7, 9), 1.5), (d(2023, 7, 9), 3.625), (d(2024, 7, 9), 4.125), (d(2027, 7, 9), 4.75), (d(2028, 7, 9), 5.0)]
    T_AE38 = [(E20, 0.125), (d(2021, 7, 9), 2.0), (d(2022, 7, 9), 3.875), (d(2023, 7, 9), 4.25), (d(2024, 7, 9), 5.0)]
    T_AL41 = [(E20, 0.125), (d(2021, 7, 9), 2.5), (d(2022, 7, 9), 3.5), (d(2029, 7, 9), 4.875)]
    T_GD46 = [(E20, 0.125), (d(2021, 7, 9), 1.125), (d(2022, 7, 9), 1.5), (d(2023, 7, 9), 3.625), (d(2024, 7, 9), 4.125), (d(2027, 7, 9), 4.375), (d(2028, 7, 9), 5.0)]
    T_AL29 = [(E20, 1.0)]
    plan = {
        "AL29": (d(2029, 7, 9), T_AL29, _igual(10), d(2025, 1, 9), 10),
        "AL30": (d(2030, 7, 9), T_AL30, [4.0] + [8.0] * 12, d(2024, 7, 9), 13),
        "AL35": (d(2035, 7, 9), T_AL35, _igual(10), d(2031, 1, 9), 10),
        "AE38": (d(2038, 1, 9), T_AE38, _igual(22), d(2027, 7, 9), 22),
        "AL41": (d(2041, 7, 9), T_AL41, _igual(28), d(2028, 1, 9), 28),
        "GD46": (d(2046, 7, 9), T_GD46, _igual(44), d(2025, 1, 9), 44),
    }
    out = {}
    for t, (vto, tr, am, ini, n) in plan.items():
        out[t] = _step_up(E20, vto, tr, am, ini, n)
    # Los Globales comparten condiciones con sus pares de ley argentina.
    out["GD29"], out["GD30"], out["GD35"], out["GD38"], out["GD41"] = out["AL29"], out["AL30"], out["AL35"], out["AE38"], out["AL41"]
    # Bonares del Tesoro 2027-2029 (base 30/360 supuesta; se contrasta contra el mercado).
    out["AO27"] = _bonar_mensual(d(2026, 2, 27), d(2027, 10, 29), 6.0)
    out["AO28"] = _bonar_mensual(d(2026, 3, 31), d(2028, 10, 31), 6.0)
    out["AO29"] = _bonar_mensual(d(2026, 7, 16), d(2029, 10, 31), 6.0)
    # AN29: semestral 30/5 y 30/11, con período irregular al 30/5/26.
    an = []
    d0 = d(2025, 12, 12)
    for f in [d(2026, 5, 30), d(2026, 11, 30), d(2027, 5, 30), d(2027, 11, 30), d(2028, 5, 30), d(2028, 11, 30), d(2029, 5, 30), d(2029, 11, 30)]:
        an.append({"f": f.isoformat(), "d0": d0.isoformat(), "tasa": 6.5, "res": 100.0, "int": round(100 * 6.5 / 100 * dias360(d0, f) / 360, 6),
                   "am": 100.0 if f == d(2029, 11, 30) else 0.0})
        d0 = f
    out["AN29"] = an
    # Bopreales Serie 1 (A, B, C, D): 5%, semestral, amortiza 50% el 30/4/27 y 50% el 31/10/27.
    am1 = {d(2027, 4, 30): 50.0, d(2027, 10, 31): 50.0}
    for t, emi in (("BPOA7", d(2024, 1, 5)), ("BPOB7", d(2024, 3, 1)), ("BPOC7", d(2024, 3, 1)), ("BPOD7", d(2024, 3, 1))):
        out[t] = _bopreal(emi, d(2027, 10, 31), 5.0, _fechas_oct_abr(2024, d(2027, 10, 31)), am1)
        out[t] = [x for x in out[t] if x["f"] >= "2024-10-31"]
    # Bopreales Serie 4 (A y B): 3%, amortiza íntegra el 31/10/28.
    for t in ("BPOA8", "BPOB8"):
        out[t] = _bopreal(d(2025, 6, 24), d(2028, 10, 31), 3.0, [f for f in _fechas_oct_abr(2025, d(2028, 10, 31)) if f >= d(2025, 10, 31)], {d(2028, 10, 31): 100.0})
    return out


# Saldo de capital vigente según BYMA (montoResidual / montoNominal de la ficha técnica), consultado el 20/10/2026.
SALDO_BYMA = {"AL29": 0.6, "GD29": 0.6, "AL30": 0.64, "GD30": 0.64, "GD46": 0.9092}
FECHA_SALDO_BYMA = "2026-10-20"


def guardar():
    CONFIG.parent.mkdir(exist_ok=True)
    doc = {"origen": "Fichas técnicas de BYMA (texto de los prospectos), consultadas el 20/10/2026. Valores por 100 de nominal original.",
           "base_tir": "efectiva anual, días reales / 365, precio limpio más intereses corridos, liquidación 24 hs (T+1 hábil)",
           "saldo_byma": {"fecha": FECHA_SALDO_BYMA, "ratio": SALDO_BYMA, "nota": "los demás bonos, 1,0: sin amortizaciones pagadas"},
           "bonos": generar()}
    CONFIG.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- matemática financiera
def cargar():
    return json.loads(CONFIG.read_text(encoding="utf-8"))["bonos"]


def _fecha(s):
    return dt.date.fromisoformat(s)


def intereses_corridos(flujos, liq, base="30/360"):
    for x in flujos:
        d0, f = _fecha(x["d0"]), _fecha(x["f"])
        if d0 <= liq < f:
            frac = dias360(d0, liq) / 360 if base == "30/360" else (liq - d0).days / 365
            return x["res"] * x["tasa"] / 100 * frac
    return 0.0


def _pv(flujos, liq, y):
    total = 0.0
    for x in flujos:
        f = _fecha(x["f"])
        if f > liq:
            total += (x["int"] + x["am"]) / (1 + y) ** ((f - liq).days / 365)
    return total


def tir(flujos, precio_limpio, liq, base="30/360"):
    """TIR efectiva anual (en %) o None si no converge."""
    sucio = precio_limpio + intereses_corridos(flujos, liq, base)
    if not any(_fecha(x["f"]) > liq for x in flujos) or sucio <= 0:
        return None
    lo, hi = -0.9, 20.0
    if (_pv(flujos, liq, lo) - sucio) * (_pv(flujos, liq, hi) - sucio) > 0:
        return None
    for _ in range(200):
        m = (lo + hi) / 2
        if _pv(flujos, liq, m) > sucio:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2 * 100


def duracion_convexidad(flujos, precio_limpio, liq, base="30/360"):
    """Duration modificada (años) y convexidad. Ambas a la TIR del precio."""
    y = tir(flujos, precio_limpio, liq, base)
    if y is None:
        return None, None
    y /= 100
    sucio = precio_limpio + intereses_corridos(flujos, liq, base)
    mac = cx = 0.0
    for x in flujos:
        f = _fecha(x["f"])
        if f > liq:
            t = (f - liq).days / 365
            c = x["int"] + x["am"]
            mac += c * t / (1 + y) ** t
            cx += c * t * (t + 1) / (1 + y) ** (t + 2)
    return mac / sucio / (1 + y), cx / sucio


def saldo(flujos, liq):
    """Saldo de capital vigente a la fecha de liquidación (por 100 de nominal original)."""
    for x in flujos:
        if _fecha(x["d0"]) <= liq < _fecha(x["f"]):
            return x["res"]
    return 0.0


# ---------------------------------------------------------------- versión vectorizada (series históricas)
def _ymd(a):
    a = a.astype("datetime64[D]")
    y = a.astype("datetime64[Y]").astype(int) + 1970
    m = a.astype("datetime64[M]").astype(int) % 12 + 1
    d = (a - a.astype("datetime64[M]")).astype(int) + 1
    return y, m, d


def _dias360_v(a, b):
    ya, ma, da = _ymd(a)
    yb, mb, db = _ymd(b)
    d1 = np.where(da == 31, 30, da)
    d2 = np.where((db == 31) & (d1 == 30), 30, db)
    return (yb - ya) * 360 + (mb - ma) * 30 + (d2 - d1)


def calcular(flujos, fechas, precios):
    """TIR (%), duration modificada (años) y convexidad para cada fecha y precio limpio.
    fechas: array de fechas de operación; la liquidación es el siguiente día hábil (24 hs)."""
    fechas = np.asarray(fechas, dtype="datetime64[D]")
    precios = np.asarray(precios, dtype=float)
    liq = np.busday_offset(fechas, 1, roll="forward")
    F = np.array([x["f"] for x in flujos], dtype="datetime64[D]")
    D0 = np.array([x["d0"] for x in flujos], dtype="datetime64[D]")
    C = np.array([x["int"] + x["am"] for x in flujos], dtype=float)
    RT = np.array([x["res"] * x["tasa"] / 100 for x in flujos], dtype=float)
    L = liq[:, None]
    periodo = (D0[None, :] <= L) & (L < F[None, :])
    dias = _dias360_v(np.broadcast_to(D0[None, :], periodo.shape), np.broadcast_to(L, periodo.shape))
    corrido = (periodo * RT[None, :] * dias / 360).sum(axis=1)
    sucio = precios + corrido
    futuro = F[None, :] > L
    t = np.where(futuro, (F[None, :] - L).astype(float) / 365, 0.0)
    Cm = C[None, :] * futuro

    def pv(y):
        return (Cm / (1 + y[:, None]) ** t).sum(axis=1)

    lo, hi = np.full(len(fechas), -0.9), np.full(len(fechas), 20.0)
    valido = (futuro.any(axis=1)) & (sucio > 0) & ((pv(lo) - sucio) * (pv(hi) - sucio) <= 0)
    for _ in range(60):
        m = (lo + hi) / 2
        arriba = pv(m) > sucio
        lo = np.where(arriba, m, lo)
        hi = np.where(arriba, hi, m)
    y = (lo + hi) / 2
    mac = (Cm * t / (1 + y[:, None]) ** t).sum(axis=1) / sucio
    cx = (Cm * t * (t + 1) / (1 + y[:, None]) ** (t + 2)).sum(axis=1) / sucio
    out = np.column_stack([y * 100, mac / (1 + y), cx])
    out[~valido] = np.nan
    return out


# La serie histórica de BYMA viene ajustada por las amortizaciones posteriores: cada precio está expresado por
# unidad de capital vigente hoy, de modo que no cae el día que se paga una cuota (verificado en AL30, AL29 con
# la hipótesis serie x saldo(t) / saldo(hoy): TIR coherente con el riesgo país y continua entre fechas de pago).
# Antes de esta fecha el ajuste de BYMA no es uniforme (el 8/1/2025 el AL30 muestra la caída de la cuota), por lo
# que la TIR histórica de los bonos amortizables arranca después.
AJUSTE_DESDE = np.datetime64("2025-01-09")


def precio_real(flujos, fechas, precios):
    """Deshace el ajuste de BYMA: precio por unidad de capital vigente en cada fecha (liquidación T+1)."""
    fechas = np.asarray(fechas, dtype="datetime64[D]")
    liq = np.busday_offset(fechas, 1, roll="forward")
    saldos = np.array([saldo(flujos, x.astype(dt.date)) for x in liq])
    ultimo = saldos[np.argmax(fechas)] or 1.0
    esc = saldos / ultimo
    if np.allclose(esc, 1.0):
        return np.asarray(precios, dtype=float), np.ones(len(fechas), dtype=bool)
    ok = fechas >= AJUSTE_DESDE
    return np.asarray(precios, dtype=float) * esc, ok


if __name__ == "__main__":
    guardar()
    print("guardado", CONFIG)
