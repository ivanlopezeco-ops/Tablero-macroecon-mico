/* Tablero macro · Argentina. Lee data.json (generado por el pipeline) y arma secciones y gráficos. */
"use strict";

let D = null;              // series
// Período general (encabezado). Cada tarjeta arranca con una copia y puede cambiar el suyo.
const R = { dias: 365, desde: null, hasta: null };
let TAB = "resumen";
const charts = [];         // instancias ECharts vivas

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const COL = () => ({ azul: css("--azul"), celeste: css("--celeste"), gris: css("--gris"), naranja: css("--naranja"),
  verde: css("--verde"), violeta: css("--violeta"), ocre: css("--ocre"), rojo: css("--rojo"), turquesa: css("--turquesa"), marron: css("--marron"),
  tinta: css("--tinta"), texto2: css("--texto2"), nota: css("--nota"), grilla: css("--grilla"), eje: css("--eje"), card: css("--card"), borde: css("--borde") });
const PALETA = ["azul", "gris", "celeste", "naranja", "verde", "violeta", "ocre", "turquesa", "rojo", "marron"];

// ------------------------------------------------------------------ formato
const nf = (dec) => new Intl.NumberFormat("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const fmt = (v, dec = 0) => (v == null || isNaN(v) ? "s/d" : nf(dec).format(v));
const fmtS = (v, dec = 0) => (v == null || isNaN(v) ? "s/d" : (v > 0 ? "+" : "") + nf(dec).format(v));
function textoDistanciaTecho(v) {
  if (v == null || !Number.isFinite(v)) return "No hay un dato de distancia al techo de la banda";
  if (v < 0) return `El mayorista tendría que bajar ${fmt(Math.abs(v), 1)}% para volver al techo de la banda`;
  if (v === 0) return "El mayorista está en el techo de la banda";
  return `El mayorista tendría que subir ${fmt(v, 1)}% para alcanzar el techo de la banda`;
}
const fechaCorta = (s) => { const [y, m, d] = s.split("-"); return `${+d}-${MESES[+m - 1]}-${y.slice(2)}`; };
const mesCorto = (s) => { const [y, m] = s.split("-"); return `${MESES[+m - 1]}-${y.slice(2)}`; };

// ------------------------------------------------------------------ datos
const S = (v) => (D.series[v] ? D.series[v].d : []);
const meta = (v) => D.series[v] || { u: "", f: "" };
const ult = (v) => { const s = S(v); return s.length ? s[s.length - 1] : [null, null]; };
const prev = (v) => { const s = S(v); return s.length > 1 ? s[s.length - 2] : [null, null]; };
const esProv = (v) => { const p = meta(v).p; const f = ult(v)[0]; return !!(p && f && f >= p); };
const valEn = (v, f) => { const s = S(v); for (let i = s.length - 1; i >= 0; i--) if (s[i][0] <= f) return s[i][1]; return null; };
const iso = (t) => new Date(t).toISOString().slice(0, 10);
const hoy = () => new Date().toLocaleDateString("sv-SE", { timeZone: "America/Argentina/Buenos_Aires" });   // fecha de Argentina, no UTC
function rango(r = R) {            // [desde, hasta] en ISO
  if (r.desde) return [r.desde, r.hasta || hoy()];
  return [r.dias ? iso(Date.now() - r.dias * 864e5) : "1900-01-01", hoy()];
}
function ventana(r, mensual) {     // como rango(), con al menos dos años para series mensuales
  let [a, b] = rango(r);
  if (mensual && (Date.parse(b) - Date.parse(a)) / 864e5 < 730) a = iso(Date.parse(b) - 730 * 864e5);
  return [a, b];
}
function aMensual(serie, modo) {   // diaria -> mensual (suma o promedio), fechada el día 1
  const g = new Map();
  serie.forEach(([f, x]) => { if (x == null) return; const k = f.slice(0, 7) + "-01"; const o = g.get(k) || [0, 0]; o[0] += x; o[1]++; g.set(k, o); });
  return [...g].map(([k, [s, n]]) => [k, modo === "suma" ? s : s / n]);
}
function varMensual(v) {           // índice -> variación % mensual
  const s = S(v); const out = [];
  for (let i = 1; i < s.length; i++) out.push([s[i][0], (s[i][1] / s[i - 1][1] - 1) * 100]);
  return out;
}
const mesAtras = (f, n) => { const [y, m] = f.split("-").map(Number); const t = y * 12 + m - 1 - n; return `${Math.floor(t / 12)}-${String(t % 12 + 1).padStart(2, "0")}-01`; };
function varIA(v, real) {          // serie mensual -> variación % interanual; real: deflactada por el IPC nacional
  const m = new Map(S(v)); const ipc = new Map(S("ipc_nivel_general"));
  return S(v).map(([f, x]) => {
    const y = m.get(mesAtras(f, 12)); if (y == null || !y) return [f, null];
    if (!real) return [f, (x / y - 1) * 100];
    const p1 = ipc.get(f), p0 = ipc.get(mesAtras(f, 12));
    return [f, p1 && p0 ? ((x / y) / (p1 / p0) - 1) * 100 : null];
  }).filter((p) => p[1] != null);
}
function deflactar(v) {            // serie diaria nominal -> a precios del último IPC (solo desde el inicio del IPC, dic-16)
  const ipc = S("ipc_nivel_general"); if (!ipc.length) return [];
  const base = ipc[ipc.length - 1][1]; let j = 0;
  return S(v).filter(([f]) => f.slice(0, 7) >= ipc[0][0].slice(0, 7)).map(([f, x]) => {
    while (j + 1 < ipc.length && ipc[j + 1][0].slice(0, 7) <= f.slice(0, 7)) j++;
    return [f, x * base / ipc[j][1]];
  });
}
function restar(a, b) {            // a - b por fecha (b tomada al último dato disponible)
  const sb = S(b); let j = 0;
  return S(a).map(([f, x]) => { while (j + 1 < sb.length && sb[j + 1][0] <= f) j++; return sb[j] && sb[j][0] <= f ? [f, x - sb[j][1]] : [f, null]; })
    .filter((p) => p[1] != null);
}
function sumar(vs, factor = 1) {   // suma por fecha de varias series mensuales
  const g = new Map();
  vs.forEach((v) => S(v).forEach(([f, x]) => { if (x != null) g.set(f, (g.get(f) || 0) + x * factor); }));
  return [...g].sort((p, q) => (p[0] < q[0] ? -1 : 1));
}
const tmp = (nombre, d) => { D.series[nombre] = { u: "", f: "", d }; return nombre; };

// ------------------------------------------------------------------ gráfico de líneas / barras
// cfg.series: [{v | datos, nombre, color, escala, estimadoAntes, estimadoDesde, eje2, stack, tipo}]
// cfg.agregar: "suma" | "prom" pasa barras diarias a mensuales cuando el período supera dos años.
// cfg.base100: cada serie = 100 al inicio del período visible. cfg.leyenda: leyenda arriba en vez de etiquetas.
// El período sale de la tarjeta (card._r). Debajo del gráfico va un selector con asas propio.
function grafico(el, cfg) {
  el._cfg = cfg;
  const c = COL();
  const card = el.closest(".card");
  const r = cfg.r || (card && card._r) || R;
  const ch = echarts.init(el, null, { renderer: "canvas" });
  charts.push(ch);
  const series = [];
  const ancho = el.clientWidth || 600;
  const chica = ancho < 420;
  const [ra, rb] = ventana(r, cfg.mensual);
  el._ventana = [ra, rb];
  const agregado = cfg.agregar && !cfg.mensual && (Date.parse(rb) - Date.parse(ra)) / 864e5 > 730;
  const mensual = cfg.mensual || agregado;
  const dosEjes = cfg.series.some((s) => s.eje2);
  const hayBarras = (cfg.tipo === "bar") || cfg.series.some((s) => s.tipo === "bar");  // las barras siempre arrancan en cero
  const leyenda = cfg.leyenda || dosEjes;
  const sinEtq = cfg.sinEtiquetas || leyenda;
  const margen = sinEtq ? 16 : Math.round(Math.min(cfg.margenDer || 150, Math.max(84, ancho * 0.3)));
  let fMin = null, fMax = null; const visibles = [[], []];
  const prepar = cfg.series.map((s) => {
    let datos = s.datos || S(s.v);
    if (s.escala) datos = datos.map(([f, x]) => [f, x * s.escala]);
    if (agregado) datos = aMensual(datos, s.agregar || cfg.agregar);
    if (cfg.base100) {
      const p0 = datos.find((p) => p[0] >= ra && p[1] != null);
      datos = p0 ? datos.map(([f, x]) => [f, x == null ? null : (x / p0[1]) * 100]) : [];
    }
    return datos;
  });
  const muestraV = (prepar[0].filter((p) => p[0] >= ra && p[0] <= rb).slice(-1)[0] || prepar[0].slice(-1)[0] || [0, 0])[1];
  const dec = cfg.dec ?? (Math.abs(muestraV || 0) >= 1000 ? 0 : 1);
  // Suma o promedio del período visible (series de flujo). cfg.resumen: "suma" | "prom" | {modo, solo: [nombres]}
  el._resumen = "";
  if (cfg.resumen) {
    const modo = cfg.resumen.modo || cfg.resumen, solo = cfg.resumen.solo;
    const partes = cfg.series.filter((s) => !solo || solo.includes(s.nombre)).map((s) => {
      const xs = (s.datos || S(s.v)).filter((p) => p[0] >= ra && p[0] <= rb && p[1] != null).map((p) => p[1] * (s.escala || 1));
      if (!xs.length) return null;
      const tot = xs.reduce((a, b) => a + b, 0);
      return `${cfg.series.length > 1 ? s.nombre + " " : ""}<b>${(modo === "suma" ? fmtS : fmt)(modo === "suma" ? tot : tot / xs.length, cfg.decResumen ?? (modo === "suma" ? 0 : dec))}</b>`;
    }).filter(Boolean);
    const per = `${mensual ? mesCorto(ra) : fechaCorta(ra)} a ${mensual ? mesCorto(rb) : fechaCorta(rb)}`;
    if (partes.length) el._resumen = `${modo === "suma" ? "Acumulado" : (cfg.mensual ? "Promedio mensual" : "Promedio diario")} del ${per}: ${partes.join(" · ")}`;
  }
  // Variaciones en el tooltip: "pct" (niveles) o "dif" (tasas, spreads). Por defecto se deduce de la unidad de la serie.
  const tipoVar = (s) => {
    if (cfg.base100 || cfg.resumen || agregado || (s.tipo || cfg.tipo) === "bar") return null;
    if (s.vt !== undefined || cfg.varTooltip !== undefined) return s.vt !== undefined ? s.vt : cfg.varTooltip;
    const u = s.v ? meta(s.v).u || "" : "";
    return !u ? null : /%|pb/.test(u) ? "dif" : /^(USD|ARS) M$/.test(u) ? "mixto" : "pct";
  };
  const vts = cfg.series.map(tipoVar);
  const porNombre = new Map(cfg.series.map((s, i) => [s.nombre, i]));
  const valorAntes = (datos, f) => { for (let k = datos.length - 1; k >= 0; k--) if (datos[k][0] <= f && datos[k][1] != null) return datos[k][1]; return null; };
  const unidadDif = (s) => (/pb/.test(meta(s.v).u || "") ? " pb" : " pp");
  const variaciones = (i, f, x) => {
    const vt = vts[i]; if (!vt || x == null) return "";
    const datos = prepar[i], s = cfg.series[i];
    const atras = mensual ? [[mesAtras(f, 1), "mes ant."], [mesAtras(f, 12), "i.a."]] : [[iso(Date.parse(f) - 30 * 864e5), "30 d"], [iso(Date.parse(f) - 365 * 864e5), "i.a."]];
    const out = atras.map(([f0, et]) => {
      const y = valorAntes(datos, f0); if (y == null || (vt === "pct" && !y)) return null;
      if (datos[0][0] > f0) return null;
      if (vt === "mixto") return `${et} ${fmtS(x - y, 0)} M${y > 0 && x > 0 ? ` (${fmtS((x / y - 1) * 100, 1)}%)` : ""}`;
      return `${et} ${vt === "pct" ? fmtS((x / y - 1) * 100, 1) + "%" : fmtS(x - y, /pb/.test(meta(s.v).u || "") ? 0 : 2) + unidadDif(s)}`;
    }).filter(Boolean);
    return out.length ? ` <span style="color:${c.nota}">· ${out.join(" · ")}</span>` : "";
  };
  cfg.series.forEach((s, i) => {
    const datos = prepar[i];
    const enVentana = datos.filter((p) => p[0] >= ra && p[0] <= rb);
    enVentana.forEach((p) => { if (p[1] != null) visibles[s.eje2 ? 1 : 0].push(p[1]); });
    if (datos.length) { fMin = fMin && fMin < datos[0][0] ? fMin : datos[0][0]; fMax = fMax && fMax > datos.at(-1)[0] ? fMax : datos.at(-1)[0]; }
    const color = c[s.color || PALETA[i % PALETA.length]];
    const tipo = s.tipo || cfg.tipo || "line";
    const grosor = i === 0 ? 2.4 : 1.6;
    const etiqueta = {
      show: !sinEtq, formatter: (p) => `${s.nombre} ${fmt(p.value[1], dec)}`,
      color, fontWeight: 600, fontSize: chica ? 10 : 11, fontFamily: "Poppins", distance: 6,
    };
    const base = {
      name: s.nombre, type: tipo, step: s.step, showSymbol: !!cfg.mensual && tipo !== "bar" && enVentana.length < 80,
      symbol: "emptyCircle", symbolSize: 5, itemStyle: { color, borderColor: color }, lineStyle: { width: grosor, color },
      emphasis: { disabled: true }, z: 10 - i, barMaxWidth: 14, labelLayout: { moveOverlap: "shiftY" }, yAxisIndex: s.eje2 ? 1 : 0,
      sampling: datos.length > 1500 && tipo === "line" ? "lttb" : undefined, large: datos.length > 3000 && tipo === "bar", stack: s.stack,
    };
    if (tipo === "bar" && !s.stack && cfg.negGris) base.itemStyle = { color: (p) => (p.value[1] < 0 && cfg.negGris ? c.gris : color) };
    const corte = s.estimadoAntes || s.estimadoDesde;
    if (corte) {     // tramo estimado u otra fuente, punteado
      const antes = datos.filter((p) => p[0] < corte), despues = datos.filter((p) => p[0] >= corte);
      const [pun, lleno] = s.estimadoAntes ? [antes, despues] : [despues, antes];
      if (s.estimadoAntes && antes.length && despues.length) antes.push(despues[0]);
      if (s.estimadoDesde && antes.length && despues.length) despues.unshift(antes.at(-1));
      const finalEsPunteado = s.estimadoDesde ? !!despues.length : !despues.length;
      series.push({ ...base, data: lleno, endLabel: { ...etiqueta, show: !finalEsPunteado && !sinEtq } });
      series.push({ ...base, name: s.nombre + " (estimado)", data: pun, lineStyle: { ...base.lineStyle, type: [5, 4] }, endLabel: { ...etiqueta, show: finalEsPunteado && !sinEtq } });
    } else {
      series.push({ ...base, data: datos, endLabel: tipo === "line" ? etiqueta : undefined });
    }
  });
  if (cfg.cero || cfg.lineas) {
    const ml = [];
    if (cfg.cero) ml.push({ yAxis: cfg.base100 ? 100 : 0, lineStyle: { color: c.eje, type: "solid", width: 1 }, label: { show: false } });
    (cfg.lineas || []).filter((l) => l.x >= (fMin || "") && l.x <= (fMax || "9")).forEach((l) => ml.push({ xAxis: l.x, lineStyle: { color: c.nota, type: [3, 3] },
      label: { formatter: l.txt, color: c.nota, fontSize: 10, position: "insideEndTop" } }));
    series[0].markLine = { symbol: "none", silent: true, data: ml, animation: false };
  }
  const anios = (Date.parse(rb) - Date.parse(ra > (fMin || ra) ? ra : (fMin || ra))) / 864e5 / 365;
  el.dataset.agregado = agregado ? cfg.agregar : "";
  let techo;   // recorte de picos: si unos pocos días aplastan la escala, el eje se corta en el percentil 97
  if (cfg.recortePicos && visibles[0].length > 20) {
    const o = [...visibles[0]].sort((a, b) => a - b); const p97 = o[Math.floor(o.length * 0.97)];
    if (p97 > 0 && o.at(-1) > p97 * 1.5) techo = Math.ceil((p97 * 1.25) / 10) * 10;
  }
  el.dataset.recorte = techo ?? "";
  // niveles de precios en pesos: si en el período el valor se multiplica más de 10 veces, escala logarítmica
  const vis = visibles[0];
  const log = cfg.logAuto && vis.length && Math.min(...vis) > 0 && Math.max(...vis) / Math.min(...vis) > 10;
  el.dataset.log = log ? "1" : "";
  const ejeY = (i) => ({
    type: log && i === 0 ? "log" : "value", logBase: 10, scale: !cfg.desdeCero && !hayBarras, max: i === 0 ? techo : undefined,
    axisLine: { show: dosEjes, lineStyle: { color: dosEjes ? c[cfg.series.find((s) => !!s.eje2 === (i === 1))?.color || (i ? "gris" : "azul")] : c.eje } },
    axisTick: { show: false }, splitLine: { show: i === 0, lineStyle: { color: c.grilla } },
    axisLabel: { color: dosEjes ? c[cfg.series.find((s) => !!s.eje2 === (i === 1))?.color || (i ? "gris" : "azul")] : c.texto2, fontSize: 11, formatter: (v) => fmt(v, cfg.decEje ?? 0) },
  });
  const t0 = fMin ? Date.parse(fMin) : Date.parse(ra), t1 = Math.max(fMax ? Date.parse(fMax) : Date.now(), Date.now() - 864e5);
  const zoomA = Math.max(Date.parse(ra), t0), zoomB = Math.min(Date.parse(rb) + 864e5, t1 + 864e5);
  ch.setOption({
    animation: false, textStyle: { fontFamily: "Poppins" },
    legend: leyenda ? { top: 0, left: 0, itemGap: 18, itemWidth: 14, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11, fontFamily: "Poppins" }, data: cfg.series.map((s) => s.nombre) } : undefined,
    grid: { left: 8, right: margen, top: leyenda ? 10 + 20 * Math.ceil(cfg.series.reduce((t, s) => t + s.nombre.length * 6.6 + 34, 0) / Math.max(200, ancho - 16)) : 14, bottom: 46, containLabel: true },
    tooltip: {
      trigger: "axis", backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => {
        const f = ps[0].value[0];
        const filas = ps.filter((p) => p.value[1] != null && (!p.seriesName.endsWith("(estimado)") || !ps.some((q) => q.seriesName === p.seriesName.replace(" (estimado)", "") && q.value[0] === f)))
          .map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName.replace(" (estimado)", "*")}: <b>${fmt(p.value[1], dec)}</b>` +
            variaciones(porNombre.get(p.seriesName.replace(" (estimado)", "")), p.value[0], p.value[1]));
        return `<div style="font-size:11px;color:${c.texto2}">${mensual ? mesCorto(f) : fechaCorta(f)}</div>${filas.join("<br>")}`;
      },
    },
    xAxis: {
      type: "time", axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false }, splitLine: { show: false },
      splitNumber: Math.max(3, Math.floor((ancho - margen) / 95)),
      axisLabel: { color: c.texto2, fontSize: 11, hideOverlap: true, formatter: (v) => { const d = new Date(v);
        return anios > 4 ? String(d.getFullYear()) : `${MESES[d.getMonth()]}-${String(d.getFullYear()).slice(2)}`; } },
    },
    yAxis: dosEjes ? [ejeY(0), ejeY(1)] : ejeY(0),
    dataZoom: cfg.sinZoom ? undefined : [{ type: "slider", xAxisIndex: 0, filterMode: "weakFilter", realtime: false, height: 16, bottom: 4, left: 46, right: Math.max(46, margen - 10),
      startValue: zoomA, endValue: zoomB, brushSelect: false, borderColor: c.borde, backgroundColor: "transparent", fillerColor: c.azul + "1f",
      dataBackground: { lineStyle: { color: c.gris, width: 1 }, areaStyle: { color: c.gris, opacity: 0.1 } },
      selectedDataBackground: { lineStyle: { color: c.azul, width: 1 }, areaStyle: { color: c.azul, opacity: 0.12 } },
      handleSize: "120%", handleStyle: { color: c.card, borderColor: c.azul }, moveHandleSize: 0, showDetail: true,
      textStyle: { color: c.texto2, fontSize: 10, fontFamily: "Poppins" }, labelFormatter: (v) => (v ? (mensual ? mesCorto(iso(v)) : fechaCorta(iso(v))) : "") }],
    series,
  });
  if (!cfg.sinZoom && card) {
    ch.on("datazoom", () => {
      const z = ch.getOption().dataZoom[0];
      if (z.startValue == null) return;
      const a = iso(z.startValue), b = iso(z.endValue);
      card._r = { dias: null, desde: a, hasta: b >= iso(Date.now() - 2 * 864e5) ? null : b };
      clearTimeout(card._tz); card._tz = setTimeout(() => card._redibujar(), 30);
    });
  }
  return ch;
}

// ------------------------------------------------------------------ tarjetas
const RANGOS_D = [["1M", 30], ["3M", 90], ["6M", 180], ["1A", 365], ["2A", 730], ["5A", 1826], ["Todo", 0]];
const RANGOS_M = [["2A", 730], ["5A", 1826], ["10A", 3652], ["Todo", 0]];

// ------------------------------------------------------------------ descargas (CSV de las series visibles y PNG de la tarjeta)
function descargar(nombre, blob) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nombre;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const slug = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);

function csvDe(el, card) {
  const cfg = el._cfg; const [a, b] = el._ventana;
  const series = cfg.series.map((x) => ({ n: x.nombre, d: new Map((x.datos || S(x.v)).filter((p) => p[0] >= a && p[0] <= b).map(([f, v]) => [f, v == null ? null : (x.escala ? v * x.escala : v)])) }));
  const fechas = [...new Set(series.flatMap((x) => [...x.d.keys()]))].sort();
  const num = (v) => (v == null ? "" : String(Math.round(v * 1e6) / 1e6).replace(".", ","));
  const filas = [["fecha", ...series.map((x) => x.n)].join(";"), ...fechas.map((f) => [f, ...series.map((x) => num(x.d.get(f)))].join(";"))];
  const titulo = card.querySelector("h3 .tit").textContent;
  filas.push("", `Fuente;${card.querySelector(".fuente").textContent.replace(/;/g, ",")}`, `Tablero;${titulo.replace(/;/g, ",")}`);
  descargar(`${slug(titulo)}.csv`, new Blob(["\ufeff" + filas.join("\r\n")], { type: "text/csv;charset=utf-8" }));
}

function envolver(ctx, texto, ancho) {
  const out = []; let linea = "";
  texto.split(" ").forEach((w) => { const t = linea ? linea + " " + w : w; if (ctx.measureText(t).width > ancho && linea) { out.push(linea); linea = w; } else linea = t; });
  if (linea) out.push(linea); return out;
}

function pngDe(el, card) {
  const ch = echarts.getInstanceByDom(el); if (!ch) return;
  const c = COL(); const k = 2;
  const img = new Image();
  img.onload = () => {
    const W = img.width, M = 28 * k;
    const cv = document.createElement("canvas"); const ctx = cv.getContext("2d");
    const titulo = card.querySelector("h3 .tit").textContent, baj = card.querySelector(".bajada").textContent, fu = card.querySelector(".fuente").textContent;
    cv.width = W;
    const medir = (fuente, texto, ancho) => { ctx.font = fuente; return envolver(ctx, texto, ancho); };
    const lt = medir(`600 ${20 * k}px Poppins, sans-serif`, titulo, W - 2 * M), lb = medir(`400 ${12 * k}px Poppins, sans-serif`, baj, W - 2 * M), lf = medir(`400 ${10 * k}px Poppins, sans-serif`, fu, W - 2 * M);
    const alto = M + lt.length * 26 * k + lb.length * 17 * k + 10 * k + img.height + lf.length * 14 * k + M;
    cv.height = alto; ctx.fillStyle = c.card; ctx.fillRect(0, 0, W, alto); ctx.textBaseline = "top";
    let y = M;
    ctx.font = `600 ${20 * k}px Poppins, sans-serif`; ctx.fillStyle = c.tinta; lt.forEach((l) => { ctx.fillText(l, M, y); y += 26 * k; });
    ctx.font = `400 ${12 * k}px Poppins, sans-serif`; ctx.fillStyle = c.texto2; lb.forEach((l) => { ctx.fillText(l, M, y); y += 17 * k; });
    y += 10 * k; ctx.drawImage(img, 0, y); y += img.height;
    ctx.font = `400 ${10 * k}px Poppins, sans-serif`; ctx.fillStyle = c.nota; lf.forEach((l) => { ctx.fillText(l, M, y); y += 14 * k; });
    cv.toBlob((b) => descargar(`${slug(titulo)}.png`, b), "image/png");
  };
  const hayZoom = !!(ch.getOption().dataZoom || []).length;
  if (hayZoom) ch.setOption({ dataZoom: [{ show: false }] });     // el selector de período no va en la imagen
  img.src = ch.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: c.card });
  if (hayZoom) ch.setOption({ dataZoom: [{ show: true }] });
}

function botonesDescarga(card, el) {
  const cont = card.querySelector(".descargas"); if (!cont) return;
  cont.innerHTML = "";
  const conCsv = !!(el._cfg && el._cfg.series && el._cfg.series.length), conPng = !!echarts.getInstanceByDom(el);
  if (conCsv) { const b = document.createElement("button"); b.textContent = "CSV"; b.title = "Descargar las series del período visible"; b.onclick = () => csvDe(el, card); cont.appendChild(b); }
  if (conPng) { const b = document.createElement("button"); b.textContent = "PNG"; b.title = "Descargar el gráfico con título y fuente"; b.onclick = () => pngDe(el, card); cont.appendChild(b); }
}

function etiquetaTipo(clave) {
  const t = clave && TIPO[clave];
  return t ? `<span class="tipo" title="${TIPOS[t]}">${t}</span>` : "";
}

function desplegableMide(clave) {
  const t = clave && MIDE[clave];
  if (!t) return "";
  return `<details class="mide"><summary>Qué estamos midiendo</summary>${(Array.isArray(t) ? t : [t]).map((x) => `<p>${x}</p>`).join("")}</details>`;
}

function tarjeta(cont, cfg) {
  const card = document.createElement("section");
  card.className = "card" + (cfg.ancha ? " ancha" : "");
  card._r = { ...R };
  const conRango = !cfg.sinRango && (cfg.series || cfg.conRango);
  card.innerHTML = `<div class="card-top"><h3><span class="tit"></span>${cfg.badge ? `<span class="badge">${cfg.badge}</span>` : ""}${etiquetaTipo(cfg.mide)}</h3>${conRango ? '<div class="mini-rangos" role="group" aria-label="Período de este gráfico"></div>' : ""}</div>
    <p class="bajada"></p><div class="chips"></div><div class="chart"></div><div class="extras">${desplegableMide(cfg.mide)}<span class="descargas"></span></div><p class="fuente">${cfg.fuente}</p>`;
  cont.appendChild(card);
  if (!cfg.chips) card.querySelector(".chips").remove();
  const el = card.querySelector(".chart");
  if (cfg.alto) el.style.height = cfg.alto + "px";
  const botones = card.querySelector(".mini-rangos");
  if (botones) {
    (cfg.mensual ? RANGOS_M : RANGOS_D).forEach(([t, d]) => {
      const b = document.createElement("button"); b.textContent = t; b.dataset.r = d;
      b.onclick = () => { card._r = { dias: d, desde: null, hasta: null }; card._redibujar(); };
      botones.appendChild(b);
    });
  }
  const baj = card.querySelector(".bajada");
  card._redibujar = () => {
    card.querySelectorAll(".chart, .chart *").forEach((n) => { const i = echarts.getInstanceByDom(n); if (i) { const k = charts.indexOf(i); if (k >= 0) charts.splice(k, 1); i.dispose(); } });
    el.innerHTML = ""; el.removeAttribute("style"); if (cfg.alto) el.style.height = cfg.alto + "px";
    const chips = card.querySelector(".chips"); if (chips) chips.innerHTML = "";
    if (cfg.render) cfg.render(el, card); else grafico(el, cfg);
    if (botones) botones.querySelectorAll("button").forEach((b) => b.classList.toggle("on", !card._r.desde && +b.dataset.r === card._r.dias));
    botonesDescarga(card, el);
    card.querySelector("h3 .tit").innerHTML = typeof cfg.titulo === "function" ? cfg.titulo(card._r) : cfg.titulo;
    baj.innerHTML = typeof cfg.bajada === "function" ? cfg.bajada() : (cfg.bajada || "");
    if (el.dataset.log) baj.innerHTML += " · Escala logarítmica";
    if (el.dataset.recorte) baj.innerHTML += ` · Eje cortado en ${el.dataset.recorte}: hay picos fuera de escala`;
    if (el.dataset.agregado) baj.innerHTML += el.dataset.agregado === "suma" ? " · Sumas mensuales" : " · Promedios mensuales";
    let res = card.querySelector(".resumen-periodo");
    if (el._resumen) {
      if (!res) { res = document.createElement("p"); res.className = "resumen-periodo"; baj.after(res); }
      res.innerHTML = el._resumen;
    } else if (res) res.remove();
    if (cfg.series && cfg.series[0].v) {   // aviso si la serie principal dejó de actualizarse, o si el último dato es del día
      const v0 = cfg.series[0].v; const f = ult(v0)[0]; const dias = f ? (Date.now() - Date.parse(f)) / 864e5 : 0;
      if (f && dias > (cfg.mensual ? 110 : 10)) baj.insertAdjacentHTML("beforeend", ` · <span class="viejo">último dato: ${cfg.mensual ? mesCorto(f) : fechaCorta(f)}</span>`);
      if (esProv(v0)) baj.insertAdjacentHTML("beforeend", ` · <span class="prov" title="${meta(v0).f}">dato del día, provisorio</span>`);
    }
  };
  card._redibujar();
  return card;
}

function kpi(cont, k) {
  const [f, v] = ult(k.v); const [, vp] = prev(k.v);
  const d = v != null && vp != null ? v - vp : null;
  const el = document.createElement("div");
  el.className = "kpi";
  const val = k.valor ? k.valor(v) : fmt(v, k.dec ?? 0);
  const dt = d == null ? "" : `${d > 0 ? "▲" : d < 0 ? "▼" : "="} ${fmt(Math.abs(d), k.decD ?? k.dec ?? 0)}`;
  const atraso = f ? Math.round((Date.now() - Date.parse(f)) / 864e5) : 0;
  const viejo = f && (D.estado?.atrasadas || []).includes(k.v);
  const pv = esProv(k.v);
  el.innerHTML = `<div class="lbl">${k.lbl}</div><div class="val">${val}<small>${k.u || ""}</small></div>
    <div class="meta"><span>${dt}</span><span class="${viejo ? "viejo" : pv ? "prov" : ""}" title="${viejo ? `Último dato hace ${atraso} días` : pv ? "Dato del día, provisorio" : ""}">${f ? (k.mensual ? mesCorto(f) : fechaCorta(f)) + (pv ? " ·prov." : "") : ""}</span></div><div class="spark"></div>`;
  cont.appendChild(el);
  const s = S(k.v).slice(-(k.n || 90)); const c = COL();
  const ch = echarts.init(el.querySelector(".spark")); charts.push(ch);
  ch.setOption({ animation: false, grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: "category", show: false, data: s.map((p) => p[0]) }, yAxis: { type: "value", show: false, scale: true },
    series: [{ type: "line", data: s.map((p) => p[1]), showSymbol: false, lineStyle: { width: 1.5, color: c.azul },
      areaStyle: { color: c.azul, opacity: 0.06 } }] });
}

// ------------------------------------------------------------------ tabla de reservas con fechas a elección
const FILAS_RES = [["Reservas brutas", "reservas_brutas", 1], ["Encajes", "res_encajes", -1], ["Swap China", "res_swap_china", -1],
  ["OOII (BIS)", "res_bis", -1, "2026-07-01"], ["Repos a 1 año", "res_repos", -1, "2026-07-01"], ["Reservas netas", "reservas_netas", 0],
  ["Bopreal a 1 año", "res_bopreal_1a", -1, "2026-09-30"], ["Depósitos USD del Tesoro", "res_dep_tesoro", -1], ["Súper netas", "reservas_super_netas", 0]];
const RES_SEL = { a: null, b: null };   // fechas elegidas, compartidas entre Resumen y Reservas

function escenariosBopreal(fecha) {
  const m = D.bopreal_reservas;
  if (!m || !m.desde || fecha < m.desde) return "";
  const stockFecha = (m.stocks || [m.stock_fecha]).filter((f) => f <= fecha).at(-1);
  const central = valEn("res_bopreal_1a", fecha), sn = valEn("reservas_super_netas", fecha);
  const filas = m.escenarios.map((e) => {
    // Exigir la fecha exacta: nunca presentar un escenario viejo como recalculado.
    const punto = S(`res_bopreal_esc_${e.porcentaje}`).find((p) => p[0] === fecha);
    if (!punto) return "";
    const bop = punto[1], superN = sn == null || central == null ? null : sn + central - bop;
    return `<tr class="${e.central ? "total" : ""}"><th scope="row">${e.porcentaje}%${e.central ? " · Central" : ""}</th><td>${fmt(bop)}</td><td>${fmt(superN)}</td></tr>`;
  }).join("");
  if (!filas) return "";
  return `<section class="bop-escenarios" aria-label="Escenarios de BOPREAL">
    <h3>BOPREAL: tres escenarios de uso tributario</h3>
    <p>Al ${fechaCorta(fecha)} · Millones de USD. La tabla principal usa el escenario del 50%.</p>
    <div class="tw"><table class="tabla"><thead><tr><th scope="col">Uso para impuestos</th><th scope="col">BOPREAL a un año</th><th scope="col">Súper netas</th></tr></thead><tbody>${filas}</tbody></table></div>
    <p>Cuanto mayor sea el uso para impuestos y la cancelación posterior, menor sería el pago en dólares y mayores las reservas súper netas. Son escenarios propios, no porcentajes observados.</p>
    <details><summary>Supuestos y fuentes del cálculo</summary>
      <p>Capital e intereses de los próximos doce meses. Se aplica el 30%, 50% o 70% sólo al capital con posibilidad de uso tributario antes de su vencimiento. Para la cuota de abril de 2027, el ajuste futuro corresponde a la serie B. La primera cuota de C se cuenta completa; su ventana tributaria comienza el día de esa cuota. D y 4B no tienen ajuste tributario; 4A sólo puede afectarlo desde su ventana de 2028.</p>
      <p>Se supone que los bonos utilizados para impuestos se cancelan antes del pago de capital. Se mantienen los intereses contractuales completos. No se agrega un descuento por tenencias del Tesoro sin verificar; las bajas ya incluidas en el stock no se descuentan otra vez.</p>
      <p>Stock de referencia: ${fechaCorta(stockFecha)} (BYMA). Los nominales requieren actualización manual; el horizonte de vencimientos se recalcula con cada fecha. Las cancelaciones supuestas no se convierten en datos observados.</p>
      <p>Desde ${fechaCorta(m.desde)} se usa este supuesto propio. El cambio de metodología también afecta las variaciones de súper netas que cruzan esa fecha.</p>
      <p><a href="https://www.bcra.gob.ar/archivos/Pdfs/comytexord/B12695.pdf" target="_blank" rel="noopener">Condiciones de la serie 1 · BCRA</a> · <a href="https://arca.gob.ar/comoPagarImpuestos/bopreal/asignacion-cancelacion-obligaciones.asp" target="_blank" rel="noopener">Ventanas tributarias · ARCA</a></p>
    </details>
  </section>`;
}

function tablaReservas(el) {
  const fechas = S("reservas_netas").map((p) => p[0]);
  el.style.height = "auto";
  if (!fechas.length) { el.textContent = "Sin datos."; return; }
  const ultima = fechas.at(-1);
  const snap = (f) => fechas.filter((x) => x <= f).at(-1) || fechas[0];
  const finMesAnt = (f) => snap(f.slice(0, 7) + "-00");
  const finAnioAnt = (f) => snap(f.slice(0, 4) + "-00");
  const diaAnt = (f) => fechas.filter((x) => x < f).at(-1) || fechas[0];
  RES_SEL.a = RES_SEL.a || ultima; RES_SEL.b = RES_SEL.b || finMesAnt(ultima);
  el.innerHTML = `<div class="reserva-fechas">
      <label>Fecha <input type="date" data-k="a" min="${fechas[0]}" max="${ultima}"></label>
      <label>Contra <input type="date" data-k="b" min="${fechas[0]}" max="${ultima}"></label>
      <span><button data-c="dia">Día anterior</button> <button data-c="mes">Fin de mes anterior</button> <button data-c="anio">Fin de año anterior</button></span>
    </div><div class="tw res-composicion"></div><div class="res-escenarios"></div>`;
  const val = (v, f) => { const s = S(v); for (let i = s.length - 1; i >= 0; i--) if (s[i][0] <= f) return s[i][1]; return null; };
  const dibujar = () => {
    const a = snap(RES_SEL.a), b = snap(RES_SEL.b);
    el.querySelector('[data-k="a"]').value = a; el.querySelector('[data-k="b"]').value = b;
    let hayEst = false;
    const celdas = FILAS_RES.map(([n, v, sg, real]) => {
      const x = (f) => { const y = val(v, f); return y == null ? null : sg === -1 ? -y : y; };
      const est = (f) => (real && f < real ? (hayEst = true, '<span class="est">*</span>') : "");
      const va = x(a), vb = x(b), d = va != null && vb != null ? va - vb : null;
      const cls = d == null || Math.abs(d) < 0.5 ? "" : d > 0 ? "dif-pos" : "dif-neg";
      return `<tr class="${sg === 0 ? "total" : ""}"><td>${n}</td><td>${fmt(vb)}${est(b)}</td><td>${fmt(va)}${est(a)}</td><td class="${cls}">${d == null ? "" : (d > 0 ? "+" : "") + fmt(d)}</td></tr>`;
    }).join("");
    el.querySelector(".res-composicion").innerHTML = `<table class="tabla"><tr><th>Millones de USD</th><th>${fechaCorta(b)}</th><th>${fechaCorta(a)}</th><th>Dif.</th></tr>${celdas}</table>` +
      (hayEst ? '<p class="fuente">*Estimado por calibración contra el gráfico de F. Machado.</p>' : "");
    const desde = D.bopreal_reservas?.desde;
    el.querySelector(".res-escenarios").innerHTML =
      (desde && Math.min(Date.parse(a), Date.parse(b)) < Date.parse(desde) && Math.max(Date.parse(a), Date.parse(b)) >= Date.parse(desde)
        ? `<p class="bop-cambio">La diferencia de súper netas incluye el cambio al supuesto propio de BOPREAL desde ${fechaCorta(desde)}.</p>` : "") + escenariosBopreal(a);
  };
  el.querySelectorAll("input").forEach((i) => i.onchange = () => { if (i.value) { RES_SEL[i.dataset.k] = i.value; dibujar(); } });
  el.querySelectorAll("button").forEach((btn) => btn.onclick = () => {
    const a = snap(RES_SEL.a); RES_SEL.b = { dia: diaAnt, mes: finMesAnt, anio: finAnioAnt }[btn.dataset.c](a); dibujar(); });
  dibujar();
}

// ------------------------------------------------------------------ secciones
const inicio = (v) => (S(v)[0] || [""])[0];
const NOTA_AD = "*Tramo punteado: ArgentinaDatos, antes del primer dato propio con AL30.";
const F = {
  bcra: "Fuente: elaboración propia en base a BCRA.",
  byma: "Fuente: elaboración propia en base a BYMA.",
  a3: "Fuente: elaboración propia en base a A3 Mercados (MAE y Matba Rofex).",
  bcrd: "Fuente: elaboración propia en base a JP Morgan (EMBI Global Diversified) publicado por el BCRD. Dato del día de Argentina: Ámbito, provisorio hasta que publica el BCRD.",
  indec: "Fuente: elaboración propia en base a INDEC.",
  yahoo: "Fuente: elaboración propia en base a Yahoo Finance.",
  bc: "Fuente: elaboración propia en base a BCRA (balance cambiario).",
};

const CARD_TABLA_RES = { mide: "tabla_reservas", titulo: "De reservas brutas a súper netas", bajada: "Composición por fecha · En millones de USD",
  fuente: F.bcra + " Swap, encajes y depósitos del Tesoro valuados al día.", render: tablaReservas };

const SECCIONES = [
  { id: "resumen", nombre: "Resumen", armar: resumen },
  { id: "cambiario", nombre: "Cambiario", armar: cambiario },
  { id: "reservas", nombre: "Reservas", armar: reservas },
  { id: "tasas", nombre: "Tasas", armar: tasas },
  { id: "bonos", nombre: "Bonos", armar: bonos },
  { id: "acciones", nombre: "Acciones", armar: acciones },
  { id: "riesgo", nombre: "Riesgo país", armar: riesgo },
  { id: "dinero", nombre: "Dinero y crédito", armar: dinero },
  { id: "fiscal", nombre: "Fiscal", armar: fiscal },
  { id: "actividad", nombre: "Precios y actividad", armar: actividad },
  { id: "industria", nombre: "Industria", armar: industria },
  { id: "bc", nombre: "Balance cambiario", armar: balance },
  { id: "internacional", nombre: "Internacional", armar: internacional },
];

function grilla(main) { const g = document.createElement("div"); g.className = "grilla"; main.appendChild(g); return g; }

// ------------------------------------------------------------------ novedades en palabras (reglas fijas, sin IA)
function pctVar(v, f0) {            // variación % entre el último dato y el valor vigente en f0
  const [, x] = ult(v); const y = valEn(v, f0); return x != null && y ? (x / y - 1) * 100 : null;
}
function difVar(v, f0) { const [, x] = ult(v); const y = valEn(v, f0); return x != null && y != null ? x - y : null; }
const finMesAnt = (f) => f.slice(0, 7) + "-00";
function extremoDesde(v) {          // ¿el último dato es el más alto / bajo desde cuándo? (solo si pasaron más de 3 meses)
  const s = S(v); if (s.length < 30) return null;
  const [f, x] = s.at(-1);
  let i = s.length - 2; while (i >= 0 && s[i][1] < x) i--;
  const alto = i < 0 ? "inicio" : s[i][0];
  let j = s.length - 2; while (j >= 0 && s[j][1] > x) j--;
  const bajo = j < 0 ? "inicio" : s[j][0];
  const lejos = (g) => (g === "inicio" && !D.parcial) || (g !== "inicio" && (Date.parse(f) - Date.parse(g)) / 864e5 > 90);   // con el archivo chico no se sabe si es "de toda la serie"
  if (lejos(alto)) return { tipo: "alto", desde: alto };
  if (lejos(bajo)) return { tipo: "bajo", desde: bajo };
  return null;
}
const desdeTxt = (e, mens) => (e.desde === "inicio" ? "de toda la serie" : `desde ${mens ? mesCorto(e.desde) : fechaCorta(e.desde)}`);

function novedades() {
  const L = [];
  const [fA, a] = ult("tc_mayorista_a3500");
  if (a) {
    const dD = pctVar("tc_mayorista_a3500", prev("tc_mayorista_a3500")[0]);
    const dM = pctVar("tc_mayorista_a3500", finMesAnt(fA));
    L.push(`El <b>dólar mayorista</b> (A3500) cerró a $${fmt(a, 2)} el ${fechaCorta(fA)}, con una variación de ${fmtS(dD, 2)}% en el día y de ${fmtS(dM, 1)}% en el mes. ${textoDistanciaTecho(ult("distancia_techo_banda")[1])}.`);
  }
  const [fC, ccl] = ult("ccl");
  if (ccl) {
    const pv = esProv("ccl") ? " (precios del día, con 20 minutos de demora)" : "";
    L.push(`El <b>contado con liqui</b> cotiza a $${fmt(ccl, 0)} y el MEP a $${fmt(ult("mep")[1], 0)}${pv}. La brecha con el mayorista es de ${fmt(ult("brecha_ccl")[1], 1)}% y el canje, de ${fmt(ult("canje_ccl_mep")[1], 1)}%.`);
  }
  const [fR, rp] = ult("riesgo_pais_argentina");
  if (rp) {
    const d1 = difVar("riesgo_pais_argentina", prev("riesgo_pais_argentina")[0]);
    const d30 = difVar("riesgo_pais_argentina", iso(Date.parse(fR) - 30 * 864e5));
    const e = extremoDesde("riesgo_pais_argentina");
    const gl = promedioGrupo("latam"); const g30 = difVar(gl, iso(Date.parse(fR) - 30 * 864e5));
    L.push(`El <b>riesgo país</b> marca ${fmt(rp)} puntos${esProv("riesgo_pais_argentina") ? " (dato del día de Ámbito)" : ""}, ${fmtS(d1)} contra la rueda anterior y ${fmtS(d30)} en 30 días. En el mismo lapso, el promedio de la región sin Venezuela ni Argentina varió ${fmtS(g30)} puntos.${e ? ` Es el nivel más ${e.tipo} ${desdeTxt(e)}.` : ""}`);
  }
  const [fB, brutas] = ult("reservas_brutas");
  if (brutas) {
    const dN = difVar("reservas_netas", finMesAnt(fB));
    L.push(`Las <b>reservas brutas</b> suman USD ${fmt(brutas)} millones al ${fechaCorta(fB)} y las netas, USD ${fmt(ult("reservas_netas")[1])} millones, ${fmtS(dN)} millones contra el cierre del mes anterior.`);
  }
  const [fK, comp] = ult("compras_bcra_mlc");
  if (comp != null) {
    const mes = S("compras_bcra_mlc").filter((p) => p[0].slice(0, 7) === fK.slice(0, 7)).reduce((s, p) => s + p[1], 0);
    L.push(`El <b>BCRA</b> ${comp >= 0 ? "compró" : "vendió"} USD ${fmt(Math.abs(comp))} millones en la última rueda informada (${fechaCorta(fK)}). En el mes acumula ${fmtS(mes)} millones y en el año, ${fmtS(ult("compras_bcra_acum_anio")[1])} millones. El BCRA publica este dato con unos cuatro días hábiles de rezago.`);
  }
  const cau = ult("caucion_a3_pesos_1d")[1], tam = ult("tamar")[1], tr = ult("tasa_real_ex_ante_tamar")[1];
  if (cau != null) L.push(`En <b>tasas</b>, la caución a un día rinde ${fmt(cau, 1)}% anual y la TAMAR, ${fmt(tam, 1)}%. La tasa real esperada es de ${fmt(tr, 2)}% mensual.`);
  const im = varMensual("ipc_nivel_general"), nm = varMensual("ipc_nucleo");
  if (im.length) {
    const [fi, x] = im.at(-1); const y = (nm.at(-1) || [])[1];
    L.push(`La <b>inflación</b> de ${mesCorto(fi)} fue de ${fmt(x, 1)}% (núcleo ${fmt(y, 1)}%), y el REM espera ${fmt(ult("rem_inflacion_12m")[1], 1)}% para los próximos 12 meses.`);
  }
  const [fT, tcrm] = ult("tcrm");
  if (tcrm) L.push(`El <b>tipo de cambio real multilateral</b> está en ${fmt(tcrm, 1)} puntos, ${fmtS(pctVar("tcrm", iso(Date.parse(fT) - 365 * 864e5)), 1)}% interanual.`);
  const mov = [["dxy", "el DXY", 1, 0.8], ["brl_usd", "el real", 1, 1.5], ["brent", "el Brent", 1, 2.5], ["soja_cbot", "la soja", 1, 2], ["oro", "el oro", 1, 2],
    ["vix", "el VIX", 1, 10], ["sp500", "el S&P 500", 1, 1.5]].map(([v, n, , u]) => [n, pctVar(v, prev(v)[0]), u]).filter(([, x, u]) => x != null && Math.abs(x) >= u);
  const ust = difVar("ust_10y", prev("ust_10y")[0]);
  const partes = mov.map(([n, x]) => `${n} ${x > 0 ? "sube" : "baja"} ${fmt(Math.abs(x), 1)}%`);
  if (ust != null && Math.abs(ust) >= 0.08) partes.push(`la tasa del Tesoro a 10 años ${ust > 0 ? "sube" : "baja"} ${fmt(Math.abs(ust) * 100)} puntos básicos`);
  L.push(partes.length ? `En los <b>mercados internacionales</b>, ${partes.join(", ").replace(/, ([^,]*)$/, " y $1")} en la última rueda.` : "Los <b>mercados internacionales</b> se movieron poco en la última rueda.");
  const [fMv, mv] = ult("merval_usd");
  if (mv) L.push(`El <b>Merval</b> vale USD ${fmt(mv)} al contado con liqui${esProv("merval_usd") ? " (dato del día)" : ""}, ${fmtS(pctVar("merval_usd", prev("merval_usd")[0]), 1)}% en el día y ${fmtS(pctVar("merval_usd", iso(Date.parse(fMv) - 30 * 864e5)), 1)}% en 30 días.`);
  const lic = (D.licitaciones || []).at(-1);
  if (lic && (Date.now() - Date.parse(lic.f)) / 864e5 < 20) L.push(`En la <b>licitación del Tesoro</b> del ${fechaCorta(lic.f)} se adjudicaron $${fmt(lic.adjudicado / 1e6, 2)} billones${lic.ofertado ? ` sobre ofertas por $${fmt(lic.ofertado / 1e6, 2)} billones` : ""}.`);
  const [fbc, cc] = ult("bc_cuenta_corriente");
  if (cc != null) L.push(`En el <b>balance cambiario</b> de ${mesCorto(fbc)}, la cuenta corriente dio ${fmtS(cc)} millones de USD, la financiera ${fmtS(ult("bc_cuenta_financiera")[1])} millones y las personas humanas hicieron compras netas por USD ${fmt(-ult("mc_personas_humanas")[1])} millones.`);
  return L;
}

const DIAS_SEM = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
function tablaCalendario(el) {
  el.style.height = "auto";
  const prox = (D.calendario || []).filter((x) => x.f >= hoy()).slice(0, 12);
  if (!prox.length) { el.innerHTML = '<p class="seccion-intro" style="margin:24px 0">Sin fechas cargadas.</p>'; return; }
  const periodo = (d) => { const m = d.match(/\. ([^.]+ de \d{4})$/); return m ? m[1] : ""; };
  const filas = prox.map((x) => {
    const dia = DIAS_SEM[new Date(x.f + "T12:00:00Z").getUTCDay()];
    const cuando = x.f === hoy() ? "hoy" : "";
    return `<tr><td>${fechaCorta(x.f)} <span class="est">${dia}${cuando ? " · " + cuando : ""}</span></td><td class="izq">${x.t}</td><td class="izq">${periodo(x.d)}</td><td class="izq">${x.tab ? '<span class="marca">En el tablero</span>' : ""}</td></tr>`;
  }).join("");
  const tw = document.createElement("div"); tw.className = "tw";
  tw.innerHTML = `<table class="tabla"><tr><th>Fecha</th><th class="izq">Publicación</th><th class="izq">Período</th><th></th></tr>${filas}</table>`;
  el.appendChild(tw);
}

function resumen(main) {
  const n = document.createElement("section"); n.className = "card ancha novedades"; main.appendChild(n);
  n.innerHTML = `<h3>Novedades</h3><ul>${novedades().map((x) => `<li>${x}</li>`).join("")}</ul>
    <p class="fuente">Texto armado automáticamente con reglas fijas a partir de los últimos datos de cada serie.</p>`;
  const k = document.createElement("div"); k.className = "kpis"; main.appendChild(k);
  tmp("_ipc_m", varMensual("ipc_nivel_general"));
  [
    { lbl: "Dólar mayorista (A3500)", v: "tc_mayorista_a3500", dec: 1, u: " $" },
    { lbl: "Contado con liqui", v: "ccl", dec: 1, u: " $" },
    { lbl: "Brecha CCL / A3500", v: "brecha_ccl", dec: 1, u: " %" },
    { lbl: "Distancia al techo de la banda", v: "distancia_techo_banda", dec: 1, u: " %" },
    { lbl: "Riesgo país", v: "riesgo_pais_argentina", u: " pb" },
    { lbl: "Reservas brutas", v: "reservas_brutas", u: " M USD" },
    { lbl: "Reservas netas", v: "reservas_netas", u: " M USD" },
    { lbl: "Compras BCRA en el año", v: "compras_bcra_acum_anio", u: " M USD" },
    { lbl: "TAMAR", v: "tamar", dec: 2, u: " % TNA" },
    { lbl: "Caución 1 día", v: "caucion_a3_pesos_1d", dec: 2, u: " % TNA" },
    { lbl: "Tasa real ex ante", v: "tasa_real_ex_ante_tamar", dec: 2, u: " % mens." },
    { lbl: "Inflación mensual (IPC)", v: "_ipc_m", dec: 1, u: " %", n: 24, mensual: true },
  ].forEach((x) => kpi(k, x));
  const g = grilla(main);
  tarjeta(g, { mide: "reservas_netas", titulo: () => `Las reservas netas suman USD ${fmt(ult("reservas_netas")[1])} millones`,
    bajada: "Netas y súper netas · En millones de USD", fuente: F.bcra + " *Tramo estimado por calibración. Desde el 20/10/26, BOPREAL usa un supuesto propio de uso tributario del 50%; el cambio también afecta la serie de súper netas.",
    cero: true, series: [{ v: "reservas_netas", nombre: "Netas", estimadoAntes: "2026-07-01" },
      { v: "reservas_super_netas", nombre: "Súper netas", estimadoAntes: "2026-09-30", color: "celeste" }] });
  tarjeta(g, CARD_TABLA_RES);
  tarjeta(g, { mide: "ccl_mep", titulo: () => `La brecha con el contado con liqui es de ${fmt(ult("brecha_ccl")[1], 1)}%`,
    bajada: "Tipo de cambio mayorista, MEP y CCL · En pesos por dólar", fuente: F.byma + " A3500 del BCRA. " + NOTA_AD, logAuto: true,
    series: [{ v: "ccl_largo", nombre: "CCL", estimadoAntes: inicio("ccl") }, { v: "tc_mayorista_a3500", nombre: "A3500" }, { v: "mep_largo", nombre: "MEP", color: "celeste", estimadoAntes: inicio("mep") }] });
  tarjeta(g, { mide: "riesgo_ppal", titulo: () => `El riesgo país está en ${fmt(ult("riesgo_pais_argentina")[1])} puntos`,
    bajada: "Argentina (eje izquierdo) y promedio simple de América Latina sin Venezuela ni Argentina (eje derecho) · En puntos básicos", fuente: F.bcrd,
    dec: 0, leyenda: true, series: [{ v: "riesgo_pais_argentina", nombre: "Argentina", color: "azul" }, { v: promedioGrupo("latam"), nombre: "LATAM sin VZ y ARG", color: "ocre", eje2: true }] });
  tarjeta(g, { mide: "calendario", ancha: true, titulo: "Próximas publicaciones", bajada: "INDEC, BCRA y licitaciones del Tesoro · Las marcadas alimentan series del tablero",
    fuente: "Fuente: elaboración propia en base a los calendarios de difusión del INDEC y del BCRA y a los llamados a licitación de la Secretaría de Finanzas.", render: tablaCalendario });
}

function estimadoDesdeFuente(v) { return ((meta(v).f || "").match(/desde (\d{4}-\d{2}-\d{2})/) || [])[1]; }

function cambiario(main) {
  const g = grilla(main);
  tarjeta(g, { mide: "banda", titulo: () => textoDistanciaTecho(ult("distancia_techo_banda")[1]),
    bajada: "A3500 y límites de la banda cambiaria · En pesos por dólar corrientes", fuente: F.bcra, logAuto: true,
    series: [{ v: "tc_mayorista_a3500", nombre: "A3500" }, { v: "banda_techo", nombre: "Techo" }, { v: "banda_piso", nombre: "Piso", color: "gris" }] });
  const base = (meta("tcr_bilateral").u.match(/de (\d{4}-\d{2})/) || [])[1];
  const est = estimadoDesdeFuente("tcr_bilateral");
  tarjeta(g, { mide: "tcr_bilateral", titulo: () => `En términos reales, el mayorista vale $${fmt(ult("tcr_bilateral")[1], 0)} a precios de ${base ? mesCorto(base + "-01") : ""}`,
    bajada: `Tipo de cambio real bilateral con EE.UU. y bandas en términos reales · En pesos por dólar de ${base ? mesCorto(base + "-01") : ""}`,
    fuente: F.bcra + " Deflactado por IPC (INDEC) y CPI de EE.UU. (BLS), interpolados por día. *Tramo punteado: inflación del mes en curso estimada con el REM.",
    logAuto: true, series: [{ v: "tcr_bilateral", nombre: "A3500 real", estimadoDesde: est }, { v: "tcr_bilateral_techo", nombre: "Techo", estimadoDesde: est },
      { v: "tcr_bilateral_piso", nombre: "Piso", color: "gris", estimadoDesde: est }] });
  tarjeta(g, { mide: "tcrm", titulo: () => `El tipo de cambio real multilateral está en ${fmt(ult("tcrm")[1], 1)} puntos`,
    bajada: "ITCRM y bandas cambiarias llevadas a la misma escala · Índice 17-12-15 = 100", fuente: F.bcra + " Las bandas se expresan como ITCRM x banda / A3500 del día.", dec: 1,
    series: [{ v: "tcrm", nombre: "ITCRM" }, { v: "tcrm_techo", nombre: "Techo" }, { v: "tcrm_piso", nombre: "Piso", color: "gris" }] });
  tarjeta(g, { mide: "ccl_mep", titulo: () => `El CCL cotiza a $${fmt(ult("ccl")[1], 0)} y el MEP a $${fmt(ult("mep")[1], 0)}`,
    bajada: "Dólares financieros calculados con el AL30 · En pesos por dólar", fuente: F.byma + " En la rueda, último precio operado con 20 minutos de demora. " + NOTA_AD, logAuto: true,
    series: [{ v: "ccl_largo", nombre: "CCL", estimadoAntes: inicio("ccl") }, { v: "mep_largo", nombre: "MEP", color: "celeste", estimadoAntes: inicio("mep") }, { v: "tc_mayorista_a3500", nombre: "A3500", color: "gris" }] });
  tarjeta(g, { mide: "brecha_canje", titulo: () => `La brecha es de ${fmt(ult("brecha_ccl")[1], 1)}% y el canje de ${fmt(ult("canje_ccl_mep")[1], 1)}%`,
    bajada: "Brecha CCL / A3500 y canje CCL / MEP · En %", fuente: F.byma + ` Antes de ${mesCorto(inicio("ccl") || "2024-10")}, CCL y MEP de ArgentinaDatos.`, cero: true,
    series: [{ v: "brecha_ccl", nombre: "Brecha" }, { v: "canje_ccl_mep", nombre: "Canje", color: "celeste" }] });
  tarjeta(g, { mide: "futuro", titulo: () => `El mercado paga $${fmt(ult("futuro_diciembre")[1], 0)} por el dólar de diciembre`,
    bajada: "Dólar futuro: contrato más corto y diciembre, contra el A3500 · En pesos por dólar", fuente: F.a3, logAuto: true,
    series: [{ v: "futuro_diciembre", nombre: "Diciembre" }, { v: "futuro_fin_mes", nombre: "Fin de mes", color: "celeste" }, { v: "tc_mayorista_a3500", nombre: "A3500", color: "gris" }] });
  const fx = D.curva_fx || {};
  const cs = fx.contratos || [];
  if (S("carry_3m").length) {
    tarjeta(g, { mide: "carry", titulo: () => `El carry a tres meses rinde ${fmt(ult("carry_3m")[1], 2)}% mensual en dólares`,
      bajada: "Tasa fija en pesos menos devaluación implícita en los futuros, a plazo constante · En % mensual (TEM)", fuente: F.a3 + " Curva de LECAP y BONCAP de BYMA.",
      dec: 2, decEje: 1, cero: true, leyenda: true,
      series: [{ v: "carry_3m", nombre: "Carry a 3 meses" }, { v: "carry_6m", nombre: "Carry a 6 meses", color: "naranja" }] });
  }
  if (cs.length) {
    const conFija = cs.filter((x) => x.fija != null);
    tarjeta(g, { mide: "carry_curva", titulo: () => { const d = conFija.find((x) => x.c.slice(3, 5) === "12") || conFija.at(-1);
        return d ? `Hasta ${mesCorto(d.vto)}, la LECAP le gana al futuro si el dólar queda por debajo de $${fmt(d.empate)}` : "Tasa fija contra devaluación implícita"; },
      bajada: () => `Por vencimiento de cada futuro, al ${fechaCorta(fx.fecha)} · En % mensual (TEM)`, fuente: F.a3 + " Curva de LECAP y BONCAP de BYMA, interpolada al plazo de cada futuro, sin extrapolar.",
      sinRango: true, alto: 320, render: (el) => carryCurva(el, cs) });
    tarjeta(g, { mide: "futuros_banda", ancha: true, sinRango: true, alto: 340,
      titulo: () => { const d = cs.find((x) => x.c.slice(3, 5) === "12") || cs[0]; return `El dólar de ${mesCorto(d.vto)} cotiza ${fmt((1 - d.futuro / d.techo) * 100, 1)}% por debajo del techo de la banda`; },
      bajada: () => `Futuros por vencimiento, techo proyectado y dólar que empata la tasa fija, al ${fechaCorta(fx.fecha)} · En pesos por dólar`,
      fuente: F.a3 + " Techo según la regla del BCRA (ajuste mensual por la inflación de dos meses antes): IPC del INDEC publicado y, para lo que falta, mediana del REM.",
      render: (el) => futurosBanda(el, cs, fx) });
  }
  tarjeta(g, { mide: "volumen_mlc", ancha: true, titulo: () => `En el MLC se operaron USD ${fmt(ult("volumen_mlc")[1])} millones en la última rueda`,
    bajada: "Volumen diario operado en el mercado de cambios · En millones de USD", fuente: F.a3, tipo: "bar", sinEtiquetas: true, desdeCero: true, agregar: "prom", resumen: "prom",
    series: [{ v: "volumen_mlc", nombre: "Volumen" }] });
}

// ------------------------------------------------------------------ carry trade y futuros contra la banda (foto del día, data/curva_fx.json)
function carryCurva(el, cs) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const pts = cs.filter((x) => x.fija != null);
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" },
    legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11 } },
    grid: { left: 8, right: 16, top: 34, bottom: 24, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => { const x = pts[ps[0].dataIndex];
        return `<b>Futuro ${mesCorto(x.vto)}</b> · ${x.dias} días<br>Tasa fija: <b>${fmt(x.fija, 2)}%</b> · devaluación implícita: <b>${fmt(x.dev, 2)}%</b><br>Carry: <b>${fmtS(x.carry, 2)}%</b> mensual<br>Futuro $${fmt(x.futuro, 1)} · empata la LECAP en $${fmt(x.empate, 1)}`; } },
    xAxis: { type: "category", data: pts.map((x) => mesCorto(x.vto)), axisLabel: { color: c.texto2, fontSize: 11 }, axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v, 1) } },
    series: [{ name: "Tasa fija", type: "bar", barMaxWidth: 16, itemStyle: { color: c.azul }, data: pts.map((x) => x.fija) },
      { name: "Devaluación implícita", type: "bar", barMaxWidth: 16, itemStyle: { color: c.naranja }, data: pts.map((x) => x.dev) },
      { name: "Carry", type: "line", symbolSize: 6, lineStyle: { color: c.gris, width: 2 }, itemStyle: { color: c.gris }, data: pts.map((x) => x.carry) }] });
}

function futurosBanda(el, cs, fx) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const eje = [fx.fecha, ...cs.map((x) => x.vto)];
  const linea = (nombre, datos, color, punteada) => ({ name: nombre, type: "line", data: datos, symbolSize: 6, connectNulls: true,
    lineStyle: { color, width: 2, type: punteada ? [5, 4] : "solid" }, itemStyle: { color } });
  const techoHoy = valEn("banda_techo", fx.fecha);
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" },
    legend: { top: 0, left: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11 } },
    grid: { left: 8, right: 16, top: 34, bottom: 24, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => { const i = ps[0].dataIndex; if (i === 0) return `<b>Hoy</b> (${fechaCorta(fx.fecha)})<br>A3500: $${fmt(fx.spot, 1)} · techo: $${fmt(techoHoy, 1)}`;
        const x = cs[i - 1];
        return `<b>Futuro ${mesCorto(x.vto)}</b><br>Futuro: <b>$${fmt(x.futuro, 1)}</b> (${fmt((1 - x.futuro / x.techo) * 100, 1)}% bajo el techo)<br>Techo proyectado: $${fmt(x.techo, 1)} <span style="color:${c.nota}">(ajuste del mes ${fmt(x.ajuste, 2)}%, ${x.origen})</span>` +
          (x.empate ? `<br>Empata la LECAP: $${fmt(x.empate, 1)}` : ""); } },
    xAxis: { type: "category", data: eje.map((f, i) => (i === 0 ? "Hoy" : mesCorto(f))), axisLabel: { color: c.texto2, fontSize: 11 }, axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false } },
    yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v) } },
    series: [linea("Dólar futuro", [fx.spot, ...cs.map((x) => x.futuro)], c.azul),
      linea("Techo de la banda (proyectado)", [techoHoy, ...cs.map((x) => x.techo)], c.naranja, true),
      linea("Dólar que empata la tasa fija", [fx.spot, ...cs.map((x) => x.empate)], c.gris)] });
}

function reservas(main) {
  const g = grilla(main);
  tarjeta(g, { mide: "reservas_netas", ancha: true, titulo: () => `Las reservas netas suman USD ${fmt(ult("reservas_netas")[1])} millones y las súper netas USD ${fmt(ult("reservas_super_netas")[1])} millones`,
    bajada: "Brutas menos pasivos de corto plazo · En millones de USD", fuente: F.bcra + " *Tramo discontinuo: BIS, repos y Bopreal estimados por calibración contra el gráfico de F. Machado. Desde el 20/10/26, BOPREAL usa un supuesto propio de uso tributario del 50%; el cambio también afecta la serie de súper netas. El BCRA publica las reservas con dos o tres días hábiles de rezago.",
    cero: true, series: [{ v: "reservas_netas", nombre: "Netas", estimadoAntes: "2026-07-01" },
      { v: "reservas_super_netas", nombre: "Súper netas", estimadoAntes: "2026-09-30", color: "celeste" }] });
  tarjeta(g, CARD_TABLA_RES);
  tarjeta(g, { mide: "reservas_brutas", titulo: () => `Las reservas brutas suman USD ${fmt(ult("reservas_brutas")[1])} millones`,
    bajada: "Stock diario · En millones de USD", fuente: F.bcra, series: [{ v: "reservas_brutas", nombre: "Brutas" }] });
  tarjeta(g, { mide: "compras", titulo: () => `El BCRA compró USD ${fmt(ult("compras_bcra_acum_anio")[1])} millones en el año`,
    bajada: "Compras diarias en el mercado de cambios · En millones de USD", fuente: F.bcra + " El BCRA publica este dato con unos cuatro días hábiles de rezago.", tipo: "bar", sinEtiquetas: true, cero: true, agregar: "suma", negGris: true, resumen: "suma",
    series: [{ v: "compras_bcra_mlc", nombre: "Compras" }] });
  tarjeta(g, { mide: "compras_pct", titulo: () => `Las compras equivalen al ${fmt(ult("compras_bcra_pct_volumen")[1], 1)}% del volumen del MLC`,
    bajada: "Compras del BCRA sobre volumen operado · En %", fuente: F.bcra + " Volumen de A3 Mercados.", tipo: "bar", sinEtiquetas: true, cero: true, agregar: "prom", resumen: "prom", decResumen: 1,
    series: [{ v: "compras_bcra_pct_volumen", nombre: "Compras / volumen" }] });
  tarjeta(g, { mide: "dep_tesoro", titulo: () => `El Tesoro tiene USD ${fmt(ult("res_dep_tesoro")[1])} millones depositados en el BCRA`,
    bajada: "Depósitos del gobierno en moneda extranjera · En millones de USD", fuente: F.bcra,
    series: [{ v: "res_dep_tesoro", nombre: "Depósitos" }] });
  ampReservas(main);
}

const GLOSARIO_TASAS = [
  ["TAMAR", "Tasa promedio que pagan los bancos privados por plazos fijos de $1.000 millones o más, a 30-35 días. Es la tasa mayorista de referencia: ajusta muchos préstamos a empresas y los bonos del Tesoro a tasa TAMAR."],
  ["BADLAR", "Tasa promedio que pagan los bancos privados por plazos fijos de más de $1 millón, a 30-35 días. Fue la referencia mayorista hasta la creación de la TAMAR y tiene historia larga."],
  ["Plazo fijo 30 días", "Tasa promedio de los depósitos a 30 días del sistema, de todos los montos. Es la más cercana a lo que recibe un ahorrista minorista."],
  ["BAIBAR", "Tasa de los préstamos entre bancos privados (call interbancario), en su mayoría a un día. Muestra cuánto cuesta la liquidez entre entidades."],
  ["Caución", "Préstamo de un día entre inversores en el mercado de capitales, garantizado con títulos. Es la tasa de corto plazo de los fondos y las empresas que colocan pesos en la bolsa."],
  ["Pases y repo", "Préstamos de un día entre entidades garantizados con títulos públicos (pases entre terceros que informa el BCRA y rueda REPO de A3). Junto con la caución marcan la tasa overnight."],
  ["LECAP y BONCAP", "Letras y bonos del Tesoro a tasa fija que capitalizan intereses y pagan todo al vencimiento. La curva muestra la TEM de mercado de cada una según su precio."],
  ["Tasa real ex ante", "TEM de la TAMAR o la BADLAR descontada la inflación que el REM espera para el mes siguiente. Positiva: la tasa le gana a la inflación esperada."],
  ["TNA, TEA y TEM", "TNA: tasa nominal anual, sin capitalizar (la que publican los bancos). TEA: efectiva anual, con capitalización. TEM: efectiva mensual, comparable con la inflación del mes. Una TNA de 30% a 30 días equivale a una TEM de 2,47% y una TEA de 34,5%."],
];

function tasas(main) {
  const glos = document.createElement("details"); glos.className = "card ancha glosario";
  glos.innerHTML = `<summary>Qué es cada tasa</summary><dl>${GLOSARIO_TASAS.map(([t, d]) => `<dt>${t}</dt><dd>${d}</dd>`).join("")}</dl>`;
  main.appendChild(glos);
  const g = grilla(main);
  const hayInfl = Object.keys(D.series).some((k) => k.startsWith("inflacion_implicita_"));
  tarjeta(g, { mide: "tasas_bancos", titulo: () => `La TAMAR se ubica en ${fmt(ult("tamar")[1], 1)}% anual`,
    bajada: "Tasas de bancos privados · En % TNA", fuente: F.bcra, dec: 1, recortePicos: true,
    series: [{ v: "tamar", nombre: "TAMAR" }, { v: "badlar", nombre: "BADLAR" }, { v: "tasa_plazo_fijo_30d", nombre: "Plazo fijo", color: "celeste" }, { v: "baibar", nombre: "BAIBAR", color: "naranja" }] });
  tarjeta(g, { mide: "caucion", titulo: () => `La caución a un día rinde ${fmt(ult("caucion_a3_pesos_1d")[1], 1)}% anual`,
    bajada: "Tasas de corto plazo en pesos · En % TNA", fuente: F.a3 + " Pases entre terceros del BCRA.", dec: 1, recortePicos: true,
    series: [{ v: "caucion_a3_pesos_1d", nombre: "Caución" }, { v: "tasa_pases_terceros_1d", nombre: "Pases" }, { v: "repo_a3_pesos_1d", nombre: "Repo", color: "celeste" }] });
  tarjeta(g, { mide: "tasa_real", titulo: () => `La tasa real esperada es de ${fmt(ult("tasa_real_ex_ante_tamar")[1], 2)}% mensual`,
    bajada: "TAMAR y BADLAR efectivas mensuales contra inflación esperada del mes siguiente (REM) · En %", fuente: F.bcra, dec: 2, decEje: 1, cero: true,
    series: [{ v: "tasa_real_ex_ante_tamar", nombre: "TAMAR" }, { v: "tasa_real_ex_ante_badlar", nombre: "BADLAR" }] });
  tarjeta(g, { mide: "curva_lecap", titulo: "Curva de tasa fija", badge: "en validación",
    bajada: () => `TEM de mercado de LECAP y BONCAP al ${fechaCorta(Object.keys(D.series).filter((k) => k.startsWith("lecap_tem_")).map((k) => ult(k)[0]).sort().pop() || "2000-01-01")}, ordenadas por vencimiento · En % mensual`, fuente: F.byma + " Pago final según TEM de emisión de la ficha técnica.",
    render: (el) => {
      const ls = Object.keys(D.series).filter((k) => k.startsWith("lecap_tem_"));
      const f = ls.map((k) => ult(k)[0]).sort().pop();
      const venc = (k) => ((meta(k).f.match(/vence (\d{4}-\d{2}-\d{2})/) || [])[1] || k);
      const pts = ls.filter((k) => ult(k)[0] === f).sort((a, b) => (venc(a) < venc(b) ? -1 : 1)).map((k) => [k.slice(10), ult(k)]);
      const c = COL(); const ch = echarts.init(el); charts.push(ch);
      ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" }, grid: { left: 8, right: 16, top: 14, bottom: 22, containLabel: true },
        tooltip: { trigger: "axis", formatter: (p) => `${p[0].name}: <b>${fmt(p[0].value, 2)}%</b>` },
        xAxis: { type: "category", data: pts.map((p) => p[0]), axisLabel: { color: c.texto2 }, axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false } },
        yAxis: { type: "value", splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, formatter: (v) => fmt(v, 1) } },
        series: [{ type: "bar", data: pts.map((p) => p[1][1]), itemStyle: { color: c.azul }, barMaxWidth: 28,
          label: { show: true, position: "top", color: c.azul, fontSize: 11, formatter: (p) => fmt(p.value, 2) } }] });
    } });
  if (!hayInfl) return;
  tarjeta(g, { mide: "inflacion_implicita", titulo: () => `El mercado descuenta ${fmt(ult("inflacion_implicita_6m")[1], 1)}% de inflación mensual a seis meses`,
    bajada: "Bonos CER contra LECAP y BONCAP a igual plazo, a 2, 4 y 6 meses, y REM del mes siguiente · En % mensual", fuente: F.byma + " Tasas reales de los Boncer cero cupón (TZX) y letras CER; CER del BCRA.", dec: 2, decEje: 1, leyenda: true,
    series: [{ v: "inflacion_implicita_2m", nombre: "A 2 meses" }, { v: "inflacion_implicita_4m", nombre: "A 4 meses", color: "celeste" }, { v: "inflacion_implicita_6m", nombre: "A 6 meses", color: "naranja" },
      { v: "rem_inflacion_mes_siguiente", nombre: "REM mes siguiente", color: "gris" }] });
  tarjeta(g, { mide: "curva_inflacion", titulo: "Inflación implícita por vencimiento", sinRango: true, alto: 320,
    bajada: () => `Promedio mensual hasta el vencimiento de cada bono CER, al ${fechaCorta((puntosInflacion()[0] || { f: "2000-01-01" }).f)} · En % mensual`,
    fuente: F.byma + " Solo hay inflación implícita donde la curva de tasa fija tiene plazo comparable.", render: curvaInflacion });
}

// ------------------------------------------------------------------ inflación implícita (bonos CER contra tasa fija)
const INF_HORIZ = ["2m", "4m", "6m"];
function puntosInflacion() {
  const ks = Object.keys(D.series).filter((k) => k.startsWith("inflacion_implicita_") && !INF_HORIZ.includes(k.slice(20)));
  const f = ks.map((k) => ult(k)[0]).filter(Boolean).sort().pop();
  return ks.filter((k) => ult(k)[0] === f).map((k) => {
    const sym = k.slice(20), venc = ((meta("cer_px_" + sym).f.match(/vence (\d{4}-\d{2}-\d{2})/) || [])[1]) || "";
    return { sym, venc, f, infl: ult(k)[1], real: ult("cer_tir_real_" + sym)[1] };
  }).sort((a, b) => (a.venc < b.venc ? -1 : 1));
}

function curvaInflacion(el) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const pts = puntosInflacion();
  const rem = (1 + (ult("rem_inflacion_12m")[1] || 0) / 100) ** (1 / 12) * 100 - 100;
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" }, grid: { left: 8, right: 16, top: 24, bottom: 36, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 },
      formatter: (ps) => { const x = pts[ps[0].dataIndex]; return `<b>${x.sym}</b> · vence ${fechaCorta(x.venc)}<br>Inflación implícita: <b>${fmt(x.infl, 2)}%</b> mensual<br>Tasa real: ${fmt(x.real, 1)}% anual`; } },
    xAxis: { type: "category", data: pts.map((x) => `${x.sym}\n${mesCorto(x.venc)}`), axisLabel: { color: c.texto2, fontSize: 10, interval: 0 }, axisTick: { show: false }, axisLine: { lineStyle: { color: c.eje } } },
    yAxis: { type: "value", scale: true, min: (v) => Math.floor((Math.min(v.min, rem) - 0.1) * 10) / 10, splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v, 1) + "%" } },
    series: [{ type: "bar", data: pts.map((x) => x.infl), barMaxWidth: 28, itemStyle: { color: c.azul },
      label: { show: true, position: "top", color: c.azul, fontSize: 11, formatter: (p) => fmt(p.value, 2) },
      markLine: { symbol: "none", silent: true, label: { formatter: `REM 12 meses: ${fmt(rem, 2)}% mensual`, color: c.nota, fontSize: 10, position: "insideEndTop" },
        lineStyle: { color: c.naranja, type: [4, 3] }, data: [{ yAxis: rem }] } }] });
}

// ------------------------------------------------------------------ bonos soberanos
const BONOS_GRUPOS = [["Bonares", ["AO27", "AO28", "AO29", "AN29", "AL29", "AL30", "AL35", "AE38", "AL41"]],
  ["Globales", ["GD29", "GD30", "GD35", "GD38", "GD41", "GD46"]],
  ["Bopreales", ["BPOA7", "BPOB7", "BPOC7", "BPOD7", "BPOA8", "BPOB8"]]];
const BONOS_MON = [["ars", "Pesos"], ["mep", "USD MEP"], ["ccl", "USD CCL"]];
const BONOS_SEL = { mon: "mep" };
const BONOS_RESCATE = { BPOA7: "30/4/25", BPOB7: "30/4/26", BPOC7: "30/4/27" };
const bonoV = (t, mon) => `bono_${t.toLowerCase()}_${mon}`;
// TIR y duration se calculan con el precio en dólares; en la vista en pesos se usa el dólar MEP.
const bonoMonUsd = () => (BONOS_SEL.mon === "ccl" ? "ccl" : "mep");
const bonoM = (pref, t) => `${pref}_${t.toLowerCase()}_${bonoMonUsd()}`;

function tablaBonos(el, card) {
  el.style.height = "auto";
  const mon = BONOS_SEL.mon;
  const filas = []; let hayProv = false;
  BONOS_GRUPOS.forEach(([g, ts]) => {
    filas.push(`<tr class="grupo"><td colspan="8">${g}</td></tr>`);
    ts.forEach((t) => {
      const v = bonoV(t, mon), s = S(v);
      if (!s.length) { filas.push(`<tr><td>${t}</td><td colspan="7">s/d</td></tr>`); return; }
      const [f, x] = s.at(-1), xp = s.length > 1 ? s.at(-2)[1] : null;
      const desde = (dias) => { const b = valEn(v, iso(Date.parse(f) - dias * 864e5)); return b ? (x / b - 1) * 100 : null; };
      const cel = (d) => (d == null ? "<td></td>" : `<td class="${Math.abs(d) < 0.005 ? "" : d > 0 ? "dif-pos" : "dif-neg"}">${fmtS(d, 2)}%</td>`);
      const prov = esProv(v); if (prov) hayProv = true;
      const tir = ult(bonoM("bono_tir", t))[1], md = ult(bonoM("bono_md", t))[1];
      const rescate = BONOS_RESCATE[t] ? ` <span class="est" title="Opción de rescate del tenedor desde el ${BONOS_RESCATE[t]}, en pesos al A3500. La TIR no la incluye.">†</span>` : "";
      filas.push(`<tr><td>${t}${rescate}</td><td>${fmt(x, mon === "ars" ? 0 : 2)}</td>${cel(xp ? (x / xp - 1) * 100 : null)}${cel(desde(7))}${cel(desde(30))}` +
        `<td>${tir == null ? "" : fmt(tir, 2) + "%"}</td><td>${md == null ? "" : fmt(md, 2)}</td>` +
        `<td class="${prov ? "est" : ""}">${fechaCorta(f)}${prov ? " *" : ""}</td></tr>`);
    });
  });
  const tw = document.createElement("div"); tw.className = "tw";
  tw.innerHTML = `<table class="tabla"><tr><th>Bono</th><th>Precio</th><th>Día</th><th>7 días</th><th>30 días</th><th>TIR</th><th>Duration</th><th>Dato</th></tr>${filas.join("")}</table>` +
    (hayProv ? '<p class="fuente">*Dato del día, provisorio: último precio operado con 20 minutos de demora, hasta que sale el cierre.</p>' : "") +
    '<p class="fuente">† Bopreal Serie 1 con opción de rescate del tenedor, en pesos al tipo de cambio A3500: la TIR no la incluye.</p>';
  el.appendChild(tw);
}

function curvaBonos(el) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const color = { Bonares: c.azul, Globales: c.celeste, Bopreales: c.naranja };
  const series = BONOS_GRUPOS.map(([g, ts]) => ({
    name: g, type: "scatter", symbolSize: 9, itemStyle: { color: color[g] },
    data: ts.map((t) => ({ name: t, value: [ult(bonoM("bono_md", t))[1], ult(bonoM("bono_tir", t))[1]] })).filter((p) => p.value[0] != null && p.value[1] != null),
    label: { show: true, position: "top", formatter: (p) => p.name, color: color[g], fontSize: 10, fontWeight: 600 },
    labelLayout: { hideOverlap: true },
    emphasis: { label: { show: true } },
  }));
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" },
    legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11 } },
    grid: { left: 8, right: 16, top: 34, bottom: 24, containLabel: true },
    tooltip: { trigger: "item", backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 },
      formatter: (p) => `<b>${p.name}</b><br>TIR ${fmt(p.value[1], 2)}% · duration ${fmt(p.value[0], 2)} años` },
    xAxis: { type: "value", name: "Duration modificada (años)", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: c.texto2, fontSize: 11 },
      axisLabel: { color: c.texto2, fontSize: 11 }, axisLine: { lineStyle: { color: c.eje } }, splitLine: { show: false } },
    yAxis: { type: "value", scale: true, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v, 0) + "%" }, splitLine: { lineStyle: { color: c.grilla } } },
    series });
}

function servicioDeudaGrafico(el) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const sd = (D.servicio_deuda || []);
  const meses = sd.map((x) => mesCorto(x.m + "-01"));
  const color = { Bonares: c.azul, Globales: c.celeste, Bopreales: c.naranja };
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" },
    legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11 } },
    grid: { left: 8, right: 16, top: 34, bottom: 28, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => { const x = sd[ps[0].dataIndex]; const tot = x.Bonares + x.Globales + x.Bopreales;
        return `<div style="font-size:11px;color:${c.texto2}">${ps[0].axisValue}</div>` + ps.filter((p) => p.value).map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: <b>${fmt(p.value)}</b>`).join("<br>") +
          `<br><b>Total ${fmt(tot)}</b> · capital ${fmt(x.capital)} · intereses ${fmt(x.intereses)}`; } },
    xAxis: { type: "category", data: meses, axisLabel: { color: c.texto2, fontSize: 11, hideOverlap: true }, axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v) } },
    series: ["Bonares", "Globales", "Bopreales"].map((g) => ({ name: g, type: "bar", stack: "s", barMaxWidth: 22, itemStyle: { color: color[g] }, data: sd.map((x) => x[g]) })) });
}

function bonos(main) {
  const barra = document.createElement("div"); barra.className = "barra";
  barra.innerHTML = '<span>Moneda de referencia</span>';
  botonera(barra, BONOS_MON, BONOS_SEL.mon, (k) => { BONOS_SEL.mon = k; render(); });
  main.appendChild(barra);
  const g = grilla(main);
  const F_B = F.byma + " Los Globales en pesos del día salen de A3 Mercados. Precios por cada 100 nominales, plazo de liquidación 24 hs.";
  const F_T = F_B + " TIR efectiva anual con el precio de BYMA, que incluye los intereses corridos; flujos de las fichas técnicas de BYMA, sin ajuste por feriados ni opciones de rescate. La serie histórica de BYMA viene ajustada por cada pago y el cálculo deshace ese ajuste.";
  const monTxt = () => (bonoMonUsd() === "ccl" ? "dólar CCL" : "dólar MEP");
  tarjeta(g, { mide: "curva_bonos", titulo: () => {
      const t = BONOS_GRUPOS.slice(0, 2).flatMap(([, ts]) => ts).map((x) => ult(bonoM("bono_tir", x))[1]).filter((x) => x != null);
      return `La curva de Bonares y Globales rinde entre ${fmt(Math.min(...t), 1)}% y ${fmt(Math.max(...t), 1)}%`; },
    bajada: () => `TIR contra duration modificada, con el ${monTxt()} · En % efectivo anual y en años`, fuente: F_T, sinRango: true, alto: 340, render: curvaBonos });
  tarjeta(g, { mide: "tir_2030", titulo: () => `El AL30 rinde ${fmt(ult(bonoM("bono_tir", "AL30"))[1], 1)}% y el GD30 ${fmt(ult(bonoM("bono_tir", "GD30"))[1], 1)}%`,
    bajada: () => `TIR de los bonos 2030 con el ${monTxt()} · En % efectivo anual`, fuente: F_T, dec: 1,
    series: [{ v: bonoM("bono_tir", "AL30"), nombre: "AL30" }, { v: bonoM("bono_tir", "GD30"), nombre: "GD30", color: "celeste" }] });
  tarjeta(g, { mide: "tir_largos", titulo: () => `El GD35 rinde ${fmt(ult(bonoM("bono_tir", "GD35"))[1], 1)}% y el GD41 ${fmt(ult(bonoM("bono_tir", "GD41"))[1], 1)}%`,
    bajada: () => `TIR de los Globales largos con el ${monTxt()} · En % efectivo anual`, fuente: F_T, dec: 1, leyenda: true,
    series: [{ v: bonoM("bono_tir", "GD35"), nombre: "GD35" }, { v: bonoM("bono_tir", "GD38"), nombre: "GD38", color: "celeste" },
      { v: bonoM("bono_tir", "GD41"), nombre: "GD41", color: "naranja" }, { v: bonoM("bono_tir", "GD46"), nombre: "GD46", color: "gris" }] });
  tarjeta(g, { mide: "forward_2728", titulo: () => `La tasa forward 2027/2028 es de ${fmt(ult("forward_ao27_ao28")[1], 1)}% en Bonares y de ${fmt(ult("forward_tzx27_tzx28")[1], 1)}% real en CER`,
    bajada: "Tasa entre los vencimientos 2027 y 2028 implícita en cada par de bonos · Bonares siempre con el dólar CCL · En % TNA base 180/360",
    fuente: F.byma + " CER del BCRA. Bonares: TIR con el precio contra cable y duration de Macaulay como plazo. Boncer: tasa real de los cero cupón y días al vencimiento como plazo.", dec: 1, leyenda: true,
    series: [{ v: "forward_ao27_ao28", nombre: "AO27-AO28 (USD, cable)" }, { v: "forward_tzx27_tzx28", nombre: "TZX27-TZX28 (real, CER)", color: "naranja" }] });
  tarjeta(g, { mide: "precio_2030", titulo: () => `El AL30 cotiza a USD ${fmt(ult("bono_al30_mep")[1], 2)} y el GD30 a USD ${fmt(ult("bono_gd30_mep")[1], 2)}`,
    bajada: "Bonar y Global 2030 en dólar MEP · En USD por cada 100 nominales", fuente: F_B, dec: 1,
    series: [{ v: "bono_al30_mep", nombre: "AL30" }, { v: "bono_gd30_mep", nombre: "GD30", color: "celeste" }] });
  tarjeta(g, { mide: "precio_largos", titulo: () => `El GD35 cotiza a USD ${fmt(ult("bono_gd35_mep")[1], 2)}`,
    bajada: "Globales largos en dólar MEP · En USD por cada 100 nominales", fuente: F_B, dec: 1, leyenda: true,
    series: [{ v: "bono_gd35_mep", nombre: "GD35" }, { v: "bono_gd38_mep", nombre: "GD38", color: "celeste" },
      { v: "bono_gd41_mep", nombre: "GD41", color: "naranja" }, { v: "bono_gd46_mep", nombre: "GD46", color: "gris" }] });
  tarjeta(g, { mide: "precio_bopreales", titulo: () => `El BPOD7 cotiza a USD ${fmt(ult("bono_bpod7_mep")[1], 2)}`,
    bajada: "Bopreales en dólar MEP · En USD por cada 100 nominales", fuente: F_B, dec: 1, leyenda: true,
    series: [{ v: "bono_bpoa7_mep", nombre: "BPOA7" }, { v: "bono_bpob7_mep", nombre: "BPOB7", color: "celeste" }, { v: "bono_bpoc7_mep", nombre: "BPOC7", color: "naranja" },
      { v: "bono_bpod7_mep", nombre: "BPOD7", color: "gris" }, { v: "bono_bpoa8_mep", nombre: "BPOA8", color: "verde" }, { v: "bono_bpob8_mep", nombre: "BPOB8", color: "violeta" }] });
  const sdTotal = () => (D.servicio_deuda || []).slice(0, 12).reduce((t, x) => t + x.Bonares + x.Globales + x.Bopreales, 0);
  tarjeta(g, { mide: "servicio_deuda", ancha: true, alto: 340, sinRango: true,
    titulo: () => `En los próximos 12 meses se pagan USD ${fmt(sdTotal())} millones de bonos en dólares`,
    bajada: () => `Capital e intereses de Bonares, Globales y Bopreales por mes · En millones de USD · Los próximos 12 meses equivalen a ${fmt(sdTotal() / ult("reservas_netas")[1] * 100)}% de las reservas netas`,
    fuente: F.byma + " Montos nominales en circulación según las fichas técnicas de BYMA al 20/10/26, incluidos los que tiene el sector público. No incluye FMI, otros organismos ni bonos en pesos.", render: servicioDeudaGrafico });
  tarjeta(g, { mide: "tabla_bonos", ancha: true, titulo: "Detalle por bono", bajada: () => `Precio, variación, TIR y duration de cada bono · Por cada 100 nominales · Moneda elegida arriba · TIR y duration con el ${monTxt()}`,
    fuente: F_T, render: tablaBonos });
}

// ------------------------------------------------------------------ riesgo país
const PAISES ={ brasil: "Brasil", chile: "Chile", colombia: "Colombia", ecuador: "Ecuador", mexico: "México", peru: "Perú",
  uruguay: "Uruguay", paraguay: "Paraguay", bolivia: "Bolivia", el_salvador: "El Salvador", panama: "Panamá",
  costa_rica: "Costa Rica", guatemala: "Guatemala", honduras: "Honduras", rep_dominicana: "Rep. Dominicana", venezuela: "Venezuela" };
// Grupos de comparación: promedios simples calculados acá con los spreads por país (no tienen el quiebre
// metodológico del 4/9/26, que afectó sobre todo a los agregados que publica JP Morgan).
const GRUPOS = {
  latam: { nombre: "Promedio LATAM sin VZ y ARG", corto: "LATAM sin VZ y ARG",
    paises: ["bolivia", "brasil", "chile", "colombia", "costa_rica", "ecuador", "el_salvador", "guatemala", "honduras", "mexico", "panama", "paraguay", "peru", "rep_dominicana", "uruguay"] },
  alto: { nombre: "Promedio spread alto (EC, BO, SV)", corto: "Spread alto", paises: ["ecuador", "bolivia", "el_salvador"] },
  bajo: { nombre: "Promedio spread bajo (CL, UY, PE, PA, PY, GT)", corto: "Spread bajo", paises: ["chile", "uruguay", "peru", "panama", "paraguay", "guatemala"] },
  oficial: { nombre: "EMBI América Latina (JP Morgan)", corto: "EMBI LATAM oficial", v: "riesgo_pais_latam" },
};
const RIESGO = { sel: ["ecuador"], grupo: "latam", vista: "dosejes", glob: "vix" };
const VISTAS = [["dosejes", "Dos ejes"], ["niveles", "Mismo eje"], ["base100", "Base 100"], ["dif", "Diferencia con el grupo"]];

function promedioGrupo(k) {        // promedio simple por fecha; exige al menos 70% de los países del grupo con dato
  const gr = GRUPOS[k];
  const nombre = "_grp_" + k;
  if (D.series[nombre]) return nombre;
  if (gr.v) return tmp(nombre, S(gr.v));
  const m = new Map();
  gr.paises.forEach((p) => S("riesgo_pais_" + p).forEach(([f, x]) => { if (x == null) return; const o = m.get(f) || [0, 0]; o[0] += x; o[1]++; m.set(f, o); }));
  const min = Math.ceil(gr.paises.length * 0.7);
  return tmp(nombre, [...m].filter(([, [, n]]) => n >= min).map(([f, [s, n]]) => [f, s / n]).sort((a, b) => (a[0] < b[0] ? -1 : 1)));
}

function botonera(cont, opciones, actual, alElegir, clase = "segmento") {
  const seg = document.createElement("div"); seg.className = clase;
  opciones.forEach(([k, n]) => { const b = document.createElement("button"); b.textContent = n; if (k === actual) b.className = "on"; b.onclick = () => alElegir(k); seg.appendChild(b); });
  cont.appendChild(seg); return seg;
}
function chipsPaises(chips, card, max = 3) {
  Object.entries(PAISES).filter(([k]) => k !== "venezuela").forEach(([k, n]) => {
    const b = document.createElement("button"); b.textContent = n; if (RIESGO.sel.includes(k)) b.className = "on";
    b.onclick = () => { if (RIESGO.sel.includes(k)) RIESGO.sel = RIESGO.sel.filter((x) => x !== k); else { RIESGO.sel.push(k); if (RIESGO.sel.length > max) RIESGO.sel.shift(); } card._redibujar(); };
    chips.appendChild(b);
  });
}
const OPC_GRUPOS = () => Object.entries(GRUPOS).map(([k, g]) => [k, g.corto]);

// Alinea series por fecha (solo fechas con dato en la primera; las demás se toman al último dato disponible, hasta 4 días)
function alinear(vs) {
  const base = S(vs[0]);
  const otras = vs.slice(1).map((v) => S(v));
  const idx = otras.map(() => 0);
  const out = [];
  base.forEach(([f, x]) => {
    const fila = [f, x];
    for (let k = 0; k < otras.length; k++) {
      const s = otras[k]; while (idx[k] + 1 < s.length && s[idx[k] + 1][0] <= f) idx[k]++;
      const p = s[idx[k]]; fila.push(p && p[0] <= f && (Date.parse(f) - Date.parse(p[0])) / 864e5 <= 4 ? p[1] : null);
    }
    if (fila.every((v) => v != null)) out.push(fila);
  });
  return out;
}

// MCO con constante: y = a + b·X. Devuelve coeficientes y R².
function mco(X, y) {
  const n = y.length, k = X[0].length + 1;
  const A = Array.from({ length: k }, () => Array(k).fill(0)), b = Array(k).fill(0);
  for (let i = 0; i < n; i++) { const xi = [1, ...X[i]]; for (let r = 0; r < k; r++) { b[r] += xi[r] * y[i]; for (let c = 0; c < k; c++) A[r][c] += xi[r] * xi[c]; } }
  for (let c = 0; c < k; c++) {            // Gauss-Jordan
    let p = c; for (let r = c + 1; r < k; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
    [A[c], A[p]] = [A[p], A[c]]; [b[c], b[p]] = [b[p], b[c]];
    if (Math.abs(A[c][c]) < 1e-12) return null;
    for (let r = 0; r < k; r++) if (r !== c) { const f = A[r][c] / A[c][c]; for (let j = c; j < k; j++) A[r][j] -= f * A[c][j]; b[r] -= f * b[c]; }
  }
  const beta = b.map((v, i) => v / A[i][i]);
  const my = y.reduce((s, v) => s + v, 0) / n;
  let sr = 0, st = 0; for (let i = 0; i < n; i++) { const e = y[i] - beta[0] - X[i].reduce((s, v, j) => s + v * beta[j + 1], 0); sr += e * e; st += (y[i] - my) ** 2; }
  return { beta, r2: 1 - sr / st };
}

// Descompone la variación del riesgo país de Argentina en el período: región (grupo elegido), factor global (VIX y
// Tesoro a 10 años) y propio de Argentina (residuo + constante). Coeficientes estimados con variaciones diarias del
// mismo período (si tiene menos de 60 ruedas, con las últimas 250).
function descomponer(r) {
  const g = promedioGrupo(RIESGO.grupo);
  const filas = alinear(["riesgo_pais_argentina", g, "vix", "ust_10y"]);
  const d = []; for (let i = 1; i < filas.length; i++) d.push([filas[i][0], ...filas[i].slice(1).map((v, j) => v - filas[i - 1][j + 1])]);
  const [a, b] = rango(r);
  const per = d.filter((x) => x[0] > a && x[0] <= b);
  const est = per.length >= 60 ? per : d.filter((x) => x[0] <= b).slice(-250);
  if (est.length < 30 || !per.length) return null;
  const m = mco(est.map((x) => [x[2], x[3], x[4] * 100]), est.map((x) => x[1]));
  if (!m) return null;
  const [c, bR, bV, bT] = m.beta;
  let ac = [0, 0, 0, 0]; const serie = { total: [], region: [], global: [], propio: [] };
  per.forEach(([f, dA, dG, dV, dT]) => {
    const reg = bR * dG, glo = bV * dV + bT * dT * 100;
    ac = [ac[0] + dA, ac[1] + reg, ac[2] + glo, ac[3] + dA - reg - glo];
    serie.total.push([f, ac[0]]); serie.region.push([f, ac[1]]); serie.global.push([f, ac[2]]); serie.propio.push([f, ac[3]]);
  });
  return { serie, ac, m, n: est.length, propioEst: est === per };
}

function riesgo(main) {
  const g = grilla(main);
  // 1. Argentina frente a un grupo de comparación, en dos ejes (al estilo del gráfico de 1816)
  tarjeta(g, { mide: "riesgo_ppal", ancha: true, chips: true, conRango: true, alto: 380,
    titulo: () => `El riesgo país de Argentina está en ${fmt(ult("riesgo_pais_argentina")[1])} puntos`,
    bajada: () => ({ dosejes: `Argentina${RIESGO.sel.length ? " y países elegidos" : ""} en el eje izquierdo; ${GRUPOS[RIESGO.grupo].nombre} en el derecho · En puntos básicos`,
      niveles: "Todos en el mismo eje · En puntos básicos", base100: "Cada serie = 100 al inicio del período elegido",
      dif: `Spread de cada país menos el ${GRUPOS[RIESGO.grupo].nombre} · En puntos básicos` })[RIESGO.vista],
    fuente: F.bcrd + " Promedios simples calculados con los spreads por país del EMBIGD. El EMBI LATAM oficial tiene un quiebre el 4/9/26 por el cambio metodológico de JP Morgan.",
    render: (el, card) => {
      const chips = card.querySelector(".chips");
      const fila1 = document.createElement("div"); fila1.className = "fila-controles"; chips.appendChild(fila1);
      botonera(fila1, OPC_GRUPOS(), RIESGO.grupo, (k) => { RIESGO.grupo = k; card._redibujar(); });
      botonera(fila1, VISTAS, RIESGO.vista, (k) => { RIESGO.vista = k; card._redibujar(); });
      chipsPaises(chips, card);
      const v = RIESGO.vista, grp = promedioGrupo(RIESGO.grupo);
      const colores = ["naranja", "celeste", "verde"];
      let series = [{ v: "riesgo_pais_argentina", nombre: "Argentina", color: "azul" },
        ...RIESGO.sel.map((p, i) => ({ v: "riesgo_pais_" + p, nombre: PAISES[p], color: colores[i] }))];
      if (v === "dif") series = series.map((s) => ({ ...s, v: undefined, datos: restar(s.v, grp) }));
      else series.push({ v: grp, nombre: GRUPOS[RIESGO.grupo].corto, color: "ocre", eje2: v === "dosejes" });
      if (v === "dosejes" && !series.some((s) => s.eje2)) series[series.length - 1].eje2 = true;
      grafico(el, { dec: v === "base100" ? 1 : 0, base100: v === "base100", cero: v === "base100" || v === "dif", series, leyenda: true,
        lineas: v === "dif" || RIESGO.grupo === "oficial" ? [{ x: "2026-09-04", txt: "cambio metodológico" }] : undefined });
    } });

  // 2. Descomposición: región, contexto global y propio de Argentina
  tarjeta(g, { mide: "riesgo_desc", ancha: true, chips: true, conRango: true,
    titulo: (r) => { const x = descomponer(r); return x ? `De los ${fmtS(x.ac[0])} pb del período, ${fmtS(x.ac[1] + x.ac[2])} se explican por la región y el contexto global` : "Qué explica las variaciones del riesgo país"; },
    bajada: () => "Variación acumulada del riesgo país de Argentina en el período, separada por factores · En puntos básicos",
    fuente: F.bcrd + " VIX: Yahoo Finance; Tesoro a 10 años: US Treasury. Regresión de las variaciones diarias de Argentina contra el grupo elegido, el VIX y la tasa a 10 años; lo propio de Argentina es el residuo.",
    render: (el, card) => {
      const chips = card.querySelector(".chips");
      botonera(chips, OPC_GRUPOS(), RIESGO.grupo, (k) => { RIESGO.grupo = k; card._redibujar(); });
      const x = descomponer(card._r);
      if (!x) { el.style.height = "auto"; el.innerHTML = '<p class="seccion-intro" style="margin:24px 0">No hay datos suficientes para el período elegido.</p>'; return; }
      const [, bR, bV, bT] = x.m.beta;
      const info = document.createElement("p"); info.className = "nota-metodo";
      info.innerHTML = `Por cada punto que sube el ${GRUPOS[RIESGO.grupo].corto}, Argentina sube en promedio <b>${fmt(bR, 2)}</b> pb; por punto de VIX, <b>${fmt(bV, 1)}</b> pb; por punto básico de la tasa a 10 años, <b>${fmt(bT, 2)}</b> pb · R² ${fmt(x.m.r2, 2)} con ${x.n} ruedas${x.propioEst ? " del período" : " (últimas 250: el período es corto)"} · Resultado: total ${fmtS(x.ac[0])}, región ${fmtS(x.ac[1])}, global ${fmtS(x.ac[2])}, propio ${fmtS(x.ac[3])}.`;
      chips.appendChild(info);
      grafico(el, { dec: 0, cero: true, leyenda: true, sinZoom: false, series: [
        { datos: x.serie.total, nombre: "Variación total", color: "azul" },
        { datos: x.serie.region, nombre: "Región", color: "ocre" },
        { datos: x.serie.global, nombre: "Contexto global", color: "gris" },
        { datos: x.serie.propio, nombre: "Propio de Argentina", color: "naranja" }] });
    } });

  // 3. Argentina y el contexto global
  const GLOB = [["vix", "VIX"], ["ust_10y", "Tesoro 10 años"], ["dxy", "DXY"]];
  tarjeta(g, { mide: "riesgo_global", chips: true, conRango: true,
    titulo: "Argentina y el contexto global",
    bajada: () => `Riesgo país de Argentina (eje izquierdo) y ${GLOB.find((x) => x[0] === RIESGO.glob)[1]} (eje derecho)`,
    fuente: F.bcrd + " VIX y DXY: Yahoo Finance; Tesoro: US Treasury.",
    render: (el, card) => {
      botonera(card.querySelector(".chips"), GLOB, RIESGO.glob, (k) => { RIESGO.glob = k; card._redibujar(); });
      const [, nom] = GLOB.find((x) => x[0] === RIESGO.glob);
      grafico(el, { dec: RIESGO.glob === "ust_10y" ? 2 : 1, decEje: RIESGO.glob === "ust_10y" ? 1 : 0, leyenda: true, series: [
        { v: "riesgo_pais_argentina", nombre: "Argentina (pb)", color: "azul" }, { v: RIESGO.glob, nombre: nom, color: "gris", eje2: true }] });
    } });

  // Argentina y América Latina en la serie larga
  tarjeta(g, { mide: "riesgo_largo", titulo: "Argentina y la región en la serie larga",
    bajada: "EMBI Global Diversified · En puntos básicos", fuente: F.bcrd + " *Tramo punteado (antes de oct-07): ArgentinaDatos (Ámbito).",
    dec: 0, series: [{ v: "riesgo_pais_argentina_largo", nombre: "Argentina", estimadoAntes: inicio("riesgo_pais_argentina") }, { v: promedioGrupo("latam"), nombre: "LATAM sin VZ y ARG", color: "ocre" }] });

  // 4. Tabla de variaciones (secundaria)
  tarjeta(g, { mide: "riesgo_tabla", ancha: true, conRango: true, titulo: "Variación del riesgo país por país",
    bajada: () => "En puntos básicos · Ordenado por la variación en el período elegido", fuente: F.bcrd,
    render: (el, card) => {
      el.style.height = "auto";
      const [a] = rango(card._r);
      const filas = [["Argentina", "riesgo_pais_argentina"], ...Object.entries(GRUPOS).map(([k, gr]) => [gr.nombre, promedioGrupo(k), true]),
        ...Object.entries(PAISES).filter(([k]) => k !== "venezuela").map(([k, n]) => [n, "riesgo_pais_" + k])];
      const datos = filas.map(([n, v, grp]) => {
        const [f, x] = ult(v);
        const d = (dias) => { const y = valEn(v, iso(Date.parse(f) - dias * 864e5)); return x != null && y != null ? x - y : null; };
        const y0 = valEn(v, a);
        return { n, grp, x, f, d7: d(7), d30: d(30), dp: x != null && y0 != null ? x - y0 : null, pp: x != null && y0 ? (x / y0 - 1) * 100 : null };
      }).sort((p, q) => (q.dp ?? -1e9) - (p.dp ?? -1e9));
      const c = (v, dec = 0, pct) => `<td class="${v == null || Math.abs(v) < 0.5 ? "" : v > 0 ? "dif-neg" : "dif-pos"}">${v == null ? "s/d" : fmtS(v, dec) + (pct ? "%" : "")}</td>`;
      el.innerHTML = `<div class="tw"><table class="tabla"><tr><th>País o grupo</th><th>Último</th><th>1 semana</th><th>1 mes</th><th>Desde ${fechaCorta(a)}</th><th>%</th></tr>` +
        datos.map((r) => `<tr class="${r.n === "Argentina" ? "total" : r.grp ? "grupo" : ""}"><td>${r.n}</td><td>${fmt(r.x)}</td>${c(r.d7)}${c(r.d30)}${c(r.dp)}${c(r.pp, 1, true)}</tr>`).join("") + "</table></div>";
    } });

  tarjeta(g, { mide: "riesgo_ranking", ancha: true, titulo: "Ranking regional de riesgo país", alto: 380,
    bajada: () => "Último dato de cada país · En puntos básicos", fuente: F.bcrd + " Venezuela fuera de escala, excluida del gráfico.",
    render: (el) => {
      const ks = Object.keys(D.series).filter((k) => k.startsWith("riesgo_pais_") && !["riesgo_pais_venezuela", "riesgo_pais_global"].includes(k) && !/_(ad|bcrp|largo|ambito)$/.test(k));
      const pts = ks.map((k) => [k === "riesgo_pais_latam" ? "EMBI LATAM oficial" : (PAISES[k.slice(12)] || "Argentina"), ult(k)[1]]).sort((a, b) => a[1] - b[1]);
      const c = COL(); const ch = echarts.init(el); charts.push(ch);
      ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" }, grid: { left: 16, right: 50, top: 6, bottom: 6, containLabel: true },
        xAxis: { type: "value", show: false }, yAxis: { type: "category", data: pts.map((p) => p[0]), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: c.texto2, width: 130, overflow: "none" } },
        series: [{ type: "bar", data: pts.map((p) => ({ value: p[1], itemStyle: { color: p[0] === "Argentina" ? c.azul : p[0].startsWith("EMBI") ? c.ocre : c.gris } })),
          barMaxWidth: 16, label: { show: true, position: "right", color: c.texto2, fontSize: 11, formatter: (p) => fmt(p.value) } }] });
    } });
}

function dinero(main) {
  const g = grilla(main);
  const ultIpc = ult("ipc_nivel_general")[0];
  const aPrecios = ultIpc ? `a precios de ${mesCorto(ultIpc)} · Desde dic-16 (inicio del IPC nacional)` : "";
  tmp("_m2r", deflactar("m2_transaccional_privado").map(([f, x]) => [f, x / 1e6]));
  tmp("_bmr", deflactar("base_monetaria").map(([f, x]) => [f, x / 1e6]));
  tmp("_prr", deflactar("prestamos_privados_pesos").map(([f, x]) => [f, x / 1e6]));
  tarjeta(g, { mide: "m2", titulo: "Demanda de dinero: M2 privado transaccional en términos reales",
    bajada: `En billones de pesos ${aPrecios}`, fuente: F.bcra + " Deflactado por IPC del INDEC.", dec: 1, decEje: 0,
    series: [{ v: "_m2r", nombre: "M2 transaccional" }, { v: "_bmr", nombre: "Base monetaria" }] });
  tarjeta(g, { mide: "prestamos", titulo: "Préstamos en pesos al sector privado en términos reales",
    bajada: `En billones de pesos ${aPrecios}`, fuente: F.bcra + " Deflactado por IPC del INDEC.", dec: 1,
    series: [{ v: "_prr", nombre: "Préstamos" }] });
  tarjeta(g, { mide: "depositos_usd", titulo: () => `Los depósitos privados en dólares suman USD ${fmt(ult("depositos_privados_usd")[1])} millones`,
    bajada: "Depósitos y préstamos en dólares del sector privado · En millones de USD", fuente: F.bcra,
    series: [{ v: "depositos_privados_usd", nombre: "Depósitos" }, { v: "prestamos_privados_usd", nombre: "Préstamos", color: "celeste" }] });
}

function actividad(main) {
  const g = grilla(main);
  tmp("_ipc_m", varMensual("ipc_nivel_general"));
  tmp("_nuc_m", varMensual("ipc_nucleo"));
  tarjeta(g, { mide: "ipc", titulo: () => `La inflación de ${mesCorto(ult("_ipc_m")[0])} fue de ${fmt(ult("_ipc_m")[1], 1)}%`,
    bajada: "IPC nivel general y núcleo · Variación % mensual", fuente: F.indec, mensual: true, dec: 1, decEje: 1,
    series: [{ v: "_ipc_m", nombre: "General" }, { v: "_nuc_m", nombre: "Núcleo", color: "celeste" }] });
  tarjeta(g, { mide: "rem", titulo: () => `El mercado espera ${fmt(ult("rem_inflacion_12m")[1], 1)}% de inflación a 12 meses`,
    bajada: "Relevamiento de Expectativas de Mercado (REM), mediana · En % interanual", fuente: F.bcra, mensual: true, dec: 1,
    series: [{ v: "rem_inflacion_12m", nombre: "Próximos 12 meses" }] });
  tarjeta(g, { mide: "emae", titulo: "Actividad económica (EMAE)", bajada: "Serie desestacionalizada · Índice 2004 = 100", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: "emae_desest", nombre: "EMAE" }] });
  const nDem = S("demanda_electrica_diaria").length;
  tarjeta(g, { mide: "demanda_elec", titulo: "Demanda eléctrica diaria", badge: nDem < 30 ? "acumulando historia" : "",
    bajada: "Energía demandada en el sistema · En MWh por día", fuente: "Fuente: elaboración propia en base a CAMMESA. CAMMESA publica solo el día anterior: la serie se acumula desde oct-26.",
    series: [{ v: "demanda_electrica_diaria", nombre: "Demanda" }],
    render: nDem < 10 ? (el) => { el.style.height = "auto"; el.innerHTML = `<p class="seccion-intro" style="margin:24px 0">${nDem === 1 ? "Hay un día registrado" : `Hay ${nDem} días registrados`} (último: ${fmt(ult("demanda_electrica_diaria")[1])} MWh). El gráfico aparece con diez días de historia.</p>`; } : undefined });
  tarjeta(g, { mide: "comercio", titulo: () => `En ${mesCorto(ult("exportaciones")[0])} se exportaron USD ${fmt(ult("exportaciones")[1])} millones`,
    bajada: "Intercambio comercial de bienes · En millones de USD", fuente: F.indec, mensual: true,
    series: [{ v: "exportaciones", nombre: "Expo" }, { v: "importaciones", nombre: "Impo" }] });
  tarjeta(g, { mide: "tcrm_bilat", ancha: true, titulo: () => `El tipo de cambio real multilateral está en ${fmt(ult("tcrm")[1], 1)}`,
    bajada: "Índice de tipo de cambio real multilateral y bilaterales · Base 17-12-15 = 100", fuente: F.bcra, dec: 1,
    series: [{ v: "tcrm", nombre: "Multilateral" }, { v: "tcr_brasil", nombre: "Brasil" }, { v: "tcr_eeuu", nombre: "EE.UU.", color: "celeste" }] });
}

function balance(main) {
  const intro = document.createElement("p"); intro.className = "seccion-intro";
  const fu = ult("bc_cuenta_corriente")[0];
  intro.textContent = `Datos mensuales del balance cambiario del BCRA${fu ? `, último mes publicado: ${mesCorto(fu)}` : ""}. Netos en millones de USD: positivo = ingreso de divisas, negativo = salida.`;
  main.appendChild(intro);
  const m = { mensual: true, dec: 0, resumen: "suma" };
  const h = (t) => { const x = document.createElement("h2"); x.className = "subtitulo"; x.textContent = t; main.appendChild(x); return grilla(main); };
  const barras = (lista) => lista.map(([v, nombre, color]) => ({ v, nombre, color, tipo: "bar", stack: "s" }));

  let g = h("Resultado global");
  tarjeta(g, { mide: "bc_global", ...m, ancha: true, titulo: () => `En ${mesCorto(fu)} las reservas variaron ${fmtS(ult("bc_var_reservas_transacciones")[1])} millones de USD por transacciones`,
    bajada: "Cuentas del balance cambiario y variación de reservas por transacciones · En millones de USD", fuente: F.bc, leyenda: true, cero: true,
    series: [...barras([["bc_cuenta_corriente", "Cuenta corriente", "azul"], ["bc_cuenta_capital", "Cuenta capital", "ocre"], ["bc_cuenta_financiera", "Cuenta financiera", "celeste"]]),
      { v: "bc_var_reservas_transacciones", nombre: "Variación de reservas", color: "naranja" }] });

  g = h("Cuenta corriente");
  tarjeta(g, { mide: "bc_cc", ...m, titulo: () => `La cuenta corriente cambiaria dio ${fmtS(ult("bc_cuenta_corriente")[1])} millones en ${mesCorto(fu)}`,
    bajada: "Componentes · En millones de USD", fuente: F.bc, leyenda: true, cero: true,
    series: barras([["bc_bienes", "Bienes", "azul"], ["bc_servicios", "Servicios", "celeste"], ["bc_ingreso_primario", "Ingreso primario", "naranja"], ["bc_ingreso_secundario", "Ingreso secundario", "gris"]]) });
  tarjeta(g, { mide: "bc_bienes", ...m, titulo: () => `El saldo de bienes fue de ${fmtS(ult("bc_bienes")[1])} millones`,
    bajada: "Cobros de exportaciones y pagos de importaciones (con signo negativo) · En millones de USD", fuente: F.bc, cero: true,
    series: [{ v: "bc_cobros_exportaciones", nombre: "Cobros expo" }, { v: "bc_pagos_importaciones", nombre: "Pagos impo", color: "naranja" }, { v: "bc_bienes", nombre: "Saldo", color: "gris", tipo: "bar" }] });
  tarjeta(g, { mide: "bc_expo_mod", ...m, titulo: "Cómo se cobran las exportaciones", bajada: "Cobros por modalidad · En millones de USD", fuente: F.bc + " Hoja MC por concepto.", leyenda: true,
    series: barras([["mcc_cobros_expo", "Cobros", "azul"], ["mcc_cobros_anticipados", "Anticipados", "celeste"], ["mcc_prefinanciaciones", "Prefinanciaciones del exterior", "verde"], ["mcc_financ_locales_expo", "Financiaciones locales", "ocre"]]) });
  tarjeta(g, { mide: "bc_impo_mod", ...m, titulo: "Cómo se pagan las importaciones", bajada: "Pagos por modalidad, con signo negativo · En millones de USD", fuente: F.bc + " Hoja MC por concepto.", leyenda: true,
    series: barras([["mcc_impo_diferidos", "Diferidos y otros", "azul"], ["mcc_impo_vista", "A la vista", "celeste"], ["mcc_impo_anticipados", "Anticipados", "naranja"]]) });
  tarjeta(g, { mide: "bc_viajes", ...m, titulo: () => `Viajes y pasajes restaron ${fmt(-ult("bc_viajes_pasajes_neto")[1])} millones en ${mesCorto(ult("bc_viajes_pasajes_neto")[0])}`,
    bajada: "Turismo: viajes y pasajes (estimación del BCRA) y consumos con tarjeta en el exterior · Netos en millones de USD", fuente: F.bc + " Anexo tarjetas y viajes.", cero: true,
    series: [{ v: "bc_viajes_pasajes_neto", nombre: "Viajes y pasajes" }, { v: "bc_tarjetas_neto", nombre: "Tarjetas", color: "celeste" }, { v: "bc_servicios", nombre: "Servicios totales", color: "gris" }] });
  tarjeta(g, { mide: "bc_intereses", ...m, titulo: "Intereses y utilidades", bajada: "Pagos de intereses por acreedor y giro de utilidades y dividendos · En millones de USD", fuente: F.bc, leyenda: true, cero: true,
    series: barras([["bc_intereses_fmi", "Intereses FMI", "naranja"], ["bc_intereses_otros_org", "Intereses otros organismos", "ocre"], ["bc_intereses_otros", "Otros intereses", "gris"],
      ["bc_utilidades_egresos", "Utilidades y dividendos", "celeste"]]) });

  g = h("Cuenta financiera");
  tarjeta(g, { mide: "bc_cf", ...m, ancha: true, titulo: () => `La cuenta financiera cambiaria dio ${fmtS(ult("bc_cuenta_financiera")[1])} millones en ${mesCorto(fu)}`,
    bajada: "Componentes por concepto · En millones de USD", fuente: F.bc, leyenda: true, cero: true, alto: 380, resumen: { modo: "suma", solo: ["Total"] },
    series: [...barras([["bc_billetes_divisas_spnf", "Billetes y divisas (SPNF)", "naranja"], ["bc_prestamos_titulos_deuda", "Préstamos y títulos de deuda", "azul"], ["bc_ied", "Inversión directa", "verde"],
      ["bc_portafolio", "Portafolio", "turquesa"], ["bc_fmi", "FMI", "rojo"], ["bc_otros_organismos", "Otros organismos", "ocre"], ["bc_fae_sector_financiero", "FAE sector financiero", "violeta"],
      ["bc_fae_sector_publico", "FAE sector público", "marron"], ["bc_canje", "Canje", "celeste"], ["bc_otros_movimientos", "Otros movimientos", "gris"]]),
    { v: "bc_cuenta_financiera", nombre: "Total", color: "tinta" }] });
  tarjeta(g, { mide: "bc_cf_sector", ...m, titulo: "Cuenta financiera por sector", bajada: "Sector privado no financiero, financiero y gobierno general y BCRA · En millones de USD", fuente: F.bc + " Hoja Cta. Financiera por sector.", leyenda: true, cero: true,
    series: barras([["bcs_spnf", "Privado no financiero", "azul"], ["bcs_financiero", "Financiero", "celeste"], ["bcs_gobierno_bcra", "Gobierno y BCRA", "naranja"], ["bcs_otros", "Otros", "gris"]]) });
  tarjeta(g, { mide: "bc_personas", ...m, titulo: () => `Las personas humanas demandaron USD ${fmt(-ult("mc_personas_humanas")[1])} millones netos en ${mesCorto(ult("mc_personas_humanas")[0])}`,
    bajada: "Operaciones de personas humanas en el mercado de cambios · En millones de USD", fuente: F.bc, cero: true,
    series: [{ v: "mc_personas_humanas", nombre: "Neto", tipo: "bar", color: "naranja" }] });
  tarjeta(g, { mide: "bc_fae", ...m, titulo: "Formación de activos externos: compras y ventas", bajada: "Billetes y divisas sin fines específicos del sector privado no financiero · En millones de USD", fuente: F.bc + " Detalle de compras: hoja MC por concepto.", leyenda: true, cero: true, resumen: { modo: "suma", solo: ["Neto"] },
    series: [...barras([["mcc_billetes_compras", "Compras de billetes", "naranja"], ["mcc_otras_inversiones", "Otras inversiones en el exterior", "ocre"], ["mcc_ide_residentes", "Inversión directa en el exterior", "marron"],
      ["mcc_billetes_ventas", "Ventas de billetes", "celeste"], ["mcc_divisas_ventas", "Ventas de divisas", "azul"]]), { v: "bc_billetes_divisas_spnf", nombre: "Neto", color: "tinta" }] });
  tarjeta(g, { mide: "bc_deuda", ...m, titulo: () => `La deuda financiera privada y pública dejó ${fmtS(ult("bc_prestamos_titulos_deuda")[1])} millones netos`,
    bajada: "Préstamos financieros, títulos de deuda y líneas de crédito: ingresos y cancelaciones · En millones de USD", fuente: F.bc, cero: true,
    series: [{ v: "bc_prestamos_ingresos", nombre: "Ingresos" }, { v: "bc_prestamos_egresos", nombre: "Cancelaciones", color: "naranja" }, { v: "bc_prestamos_titulos_deuda", nombre: "Neto", color: "gris", tipo: "bar" }] });
  tarjeta(g, { mide: "bc_deuda_instr", ...m, titulo: "Deuda por instrumento", bajada: "Financiaciones locales y deuda con el exterior, netas · En millones de USD", fuente: F.bc + " Hoja MC por concepto.", leyenda: true, cero: true,
    series: [{ datos: sumar(["mcc_financ_locales_ing", "mcc_financ_locales_egr"]), nombre: "Financiaciones locales", tipo: "bar", stack: "s", color: "celeste" },
      { datos: sumar(["mcc_deuda_ext_ing", "mcc_deuda_ext_egr"]), nombre: "Préstamos del exterior y títulos", tipo: "bar", stack: "s", color: "azul" }] });
  tarjeta(g, { mide: "bc_no_res", ...m, titulo: "Inversión de no residentes", bajada: "Inversión directa y de portafolio, netas · En millones de USD", fuente: F.bc, cero: true,
    series: [{ v: "bc_ied", nombre: "Directa", tipo: "bar", stack: "s", color: "verde" }, { v: "bc_portafolio", nombre: "Portafolio", tipo: "bar", stack: "s", color: "turquesa" }], leyenda: true });
  tarjeta(g, { mide: "bc_organismos", ...m, titulo: "Organismos internacionales", bajada: "FMI y otros organismos (desembolsos menos pagos de capital) · En millones de USD", fuente: F.bc, cero: true, leyenda: true,
    series: barras([["bc_fmi", "FMI", "rojo"], ["bc_otros_organismos", "Otros organismos", "ocre"]]) });

  g = h("Por sector de actividad");
  tmp("_mc_energia", sumar(["mc_petroleo", "mc_gas", "mc_electricidad"]));
  tarjeta(g, { mide: "bc_sec_expo", ...m, titulo: "Oferta neta de los sectores exportadores", bajada: "Agro, energía (petróleo, gas y electricidad) y minería · Netos en millones de USD", fuente: F.bc + " Hoja MC por sector.", cero: true,
    series: [{ v: "mc_oleaginosos_cerealeros", nombre: "Agro" }, { v: "_mc_energia", nombre: "Energía", color: "naranja" }, { v: "mc_mineria", nombre: "Minería", color: "celeste" }] });
  tarjeta(g, { mide: "bc_sec_ind", ...m, titulo: "Demanda neta de la industria", bajada: "Automotriz, maquinarias y equipos, metales comunes y química · Netos en millones de USD", fuente: F.bc + " Hoja MC por sector.", cero: true,
    series: [{ v: "mc_automotriz", nombre: "Automotriz" }, { v: "mc_maquinarias", nombre: "Maquinarias", color: "celeste" }, { v: "mc_metales_comunes", nombre: "Metales comunes", color: "naranja" }, { v: "mc_quimica", nombre: "Química", color: "gris" }] });
  tarjeta(g, { mide: "bc_sec_com", ...m, titulo: "Comercio, alimentos y sector público", bajada: "Netos en millones de USD", fuente: F.bc + " Hoja MC por sector.", cero: true,
    series: [{ v: "mc_alimentos", nombre: "Alimentos" }, { v: "mc_comercio", nombre: "Comercio", color: "celeste" }, { v: "mc_sector_publico", nombre: "Sector público", color: "naranja" }] });
  tarjeta(g, { mide: "bc_sec_energia", ...m, titulo: "Energía por rama", bajada: "Petróleo, gas y electricidad · Netos en millones de USD", fuente: F.bc + " Hoja MC por sector.", cero: true,
    series: [{ v: "mc_petroleo", nombre: "Petróleo" }, { v: "mc_gas", nombre: "Gas", color: "celeste" }, { v: "mc_electricidad", nombre: "Electricidad", color: "naranja" }] });
}

function internacional(main) {
  const g = grilla(main);
  const y = (cfg) => tarjeta(g, { fuente: F.yahoo, ...cfg });
  tarjeta(g, { mide: "ust", titulo: () => `El bono del Tesoro a 10 años rinde ${fmt(ult("ust_10y")[1], 2)}%`, bajada: "Rendimiento de bonos del Tesoro de EE.UU. · En %",
    fuente: "Fuente: elaboración propia en base a US Treasury.", dec: 2, decEje: 1,
    series: [{ v: "ust_10y", nombre: "10 años" }, { v: "ust_2y", nombre: "2 años", color: "celeste" }, { v: "ust_30y", nombre: "30 años", color: "gris" }] });
  y({ mide: "vix", titulo: () => `El VIX está en ${fmt(ult("vix")[1], 1)} puntos`, bajada: "Volatilidad implícita del S&P 500 · Índice", dec: 1, recortePicos: true, series: [{ v: "vix", nombre: "VIX" }] });
  y({ mide: "sp500", titulo: () => `El S&P 500 está en ${fmt(ult("sp500")[1], 0)} puntos`, bajada: "Índice bursátil de EE.UU.", dec: 0, series: [{ v: "sp500", nombre: "S&P 500" }] });
  y({ mide: "dxy", titulo: () => `El dólar global (DXY) está en ${fmt(ult("dxy")[1], 1)}`, bajada: "Índice del dólar frente a una canasta de monedas", dec: 1, series: [{ v: "dxy", nombre: "DXY" }] });
  y({ mide: "brl", titulo: () => `El real cotiza a R$ ${fmt(ult("brl_usd")[1], 2)} por dólar`, bajada: "Reales por dólar", dec: 2, decEje: 2, series: [{ v: "brl_usd", nombre: "BRL" }] });
  y({ mide: "brent", titulo: () => `El Brent cotiza a USD ${fmt(ult("brent")[1], 1)} por barril`, bajada: "Petróleo Brent, contrato más cercano · En USD por barril", dec: 1, series: [{ v: "brent", nombre: "Brent" }] });
  y({ mide: "gas", titulo: () => `El gas natural cotiza a USD ${fmt(ult("gas_natural_hh")[1], 2)} por MMBtu`, bajada: "Henry Hub, contrato más cercano · En USD por MMBtu", dec: 2, decEje: 1, recortePicos: true, series: [{ v: "gas_natural_hh", nombre: "Gas natural" }] });
  y({ mide: "soja", titulo: () => `La soja cotiza a USD ${fmt(ult("soja_cbot")[1] * 0.367437, 0)} por tonelada`, bajada: "Soja en Chicago, contrato más cercano · En USD por tonelada", dec: 0,
    series: [{ v: "soja_cbot", nombre: "Soja", escala: 0.367437 }] });
  y({ mide: "maiz", titulo: () => `El maíz cotiza a USD ${fmt(ult("maiz_cbot")[1] * 0.393679, 0)} por tonelada`, bajada: "Maíz en Chicago, contrato más cercano · En USD por tonelada", dec: 0,
    series: [{ v: "maiz_cbot", nombre: "Maíz", escala: 0.393679 }] });
  y({ mide: "trigo", titulo: () => `El trigo cotiza a USD ${fmt(ult("trigo_cbot")[1] * 0.367437, 0)} por tonelada`, bajada: "Trigo en Chicago, contrato más cercano · En USD por tonelada", dec: 0,
    series: [{ v: "trigo_cbot", nombre: "Trigo", escala: 0.367437 }] });
  y({ mide: "oro", titulo: () => `El oro cotiza a USD ${fmt(ult("oro")[1], 0)} por onza`, bajada: "Oro, contrato más cercano · En USD por onza troy", dec: 0, series: [{ v: "oro", nombre: "Oro" }] });
  y({ mide: "cobre", titulo: () => `El cobre cotiza a USD ${fmt(ult("cobre")[1] * 2204.62, 0)} por tonelada`, bajada: "Cobre en Nueva York (COMEX), contrato más cercano · En USD por tonelada", dec: 0,
    series: [{ v: "cobre", nombre: "Cobre", escala: 2204.62 }] });
}

// ------------------------------------------------------------------ acciones
const ADRS = [["GGAL", "Galicia"], ["BMA", "Macro"], ["BBAR", "BBVA"], ["SUPV", "Supervielle"], ["YPF", "YPF"], ["PAM", "Pampa"], ["VIST", "Vista"],
  ["TGS", "TGS"], ["CEPU", "Central Puerto"], ["EDN", "Edenor"], ["LOMA", "Loma Negra"], ["TEO", "Telecom"], ["CRESY", "Cresud"], ["IRS", "IRSA"]];
const adrV = (t) => "adr_" + t.toLowerCase();
const F_MERVAL = "Fuente: elaboración propia en base a Yahoo Finance (S&P Merval hasta el 16/10/26) y BYMA (MSCI MERVAL desde el 19/10/26). CCL propio con AL30.";

function tablaAdrs(el) {
  el.style.height = "auto";
  const filas = ADRS.map(([t, n]) => {
    const v = adrV(t), s = S(v);
    if (!s.length) return `<tr><td>${t}</td><td class="izq">${n}</td><td colspan="5">s/d</td></tr>`;
    const [f, x] = s.at(-1);
    const desde = (fd) => { const b = valEn(v, fd); return b ? (x / b - 1) * 100 : null; };
    const cel = (d) => (d == null ? "<td></td>" : `<td class="${Math.abs(d) < 0.005 ? "" : d > 0 ? "dif-pos" : "dif-neg"}">${fmtS(d, 1)}%</td>`);
    return `<tr><td>${t}</td><td class="izq">${n}</td><td>${fmt(x, 2)}</td>${cel(desde(prev(v)[0]))}${cel(desde(iso(Date.parse(f) - 30 * 864e5)))}` +
      `${cel(desde(f.slice(0, 4) + "-00"))}${cel(desde(iso(Date.parse(f) - 365 * 864e5)))}<td>${fechaCorta(f)}</td></tr>`;
  }).join("");
  const tw = document.createElement("div"); tw.className = "tw";
  tw.innerHTML = `<table class="tabla"><tr><th>ADR</th><th class="izq">Empresa</th><th>USD</th><th>Día</th><th>30 días</th><th>En el año</th><th>12 meses</th><th>Dato</th></tr>${filas}</table>`;
  el.appendChild(tw);
}

function acciones(main) {
  const g = grilla(main);
  tarjeta(g, { mide: "merval_usd", ancha: true, titulo: () => `El Merval vale USD ${fmt(ult("merval_usd")[1], 0)} al contado con liqui`,
    bajada: "Merval dividido por el dólar CCL · En dólares", fuente: F_MERVAL + " Antes del primer dato propio del CCL, CCL de ArgentinaDatos.", logAuto: true, dec: 0,
    lineas: [{ x: "2026-10-19", txt: "pasa a MSCI" }], series: [{ v: "merval_usd", nombre: "Merval USD" }] });
  tarjeta(g, { mide: "merval", titulo: () => `El Merval está en ${fmt(ult("merval")[1], 0)} puntos`,
    bajada: "Índice en pesos, en la escala del S&P Merval · En puntos", fuente: F_MERVAL, logAuto: true, dec: 0,
    series: [{ v: "merval", nombre: "Merval" }] });
  tarjeta(g, { mide: "adr_base100", titulo: "Los ADR más operados", leyenda: true, base100: true, cero: true, dec: 1,
    bajada: "Cotización en Nueva York, base 100 al inicio del período · En dólares", fuente: F.yahoo,
    series: [{ v: "adr_ggal", nombre: "Galicia" }, { v: "adr_ypf", nombre: "YPF", color: "celeste" }, { v: "adr_pam", nombre: "Pampa", color: "naranja" },
      { v: "adr_bma", nombre: "Macro", color: "gris" }, { v: "adr_vist", nombre: "Vista", color: "verde" }] });
  tarjeta(g, { mide: "tabla_adrs", ancha: true, titulo: "ADR argentinos en Nueva York", bajada: "Último precio y variaciones · En USD por ADR",
    fuente: F.yahoo, render: tablaAdrs });
}

// ------------------------------------------------------------------ fiscal y licitaciones del Tesoro
function licEtiqueta(i) {         // ticker, o tipo y vencimiento cuando la letra es nueva y el comunicado no da el ticker
  if (i.t) return i.t;
  const m = i.d.match(/VENCIMIENTO (\d{1,2}) DE (\w+) DE (\d{4})/i);
  const MES = { ENERO: 0, FEBRERO: 1, MARZO: 2, ABRIL: 3, MAYO: 4, JUNIO: 5, JULIO: 6, AGOSTO: 7, SEPTIEMBRE: 8, OCTUBRE: 9, NOVIEMBRE: 10, DICIEMBRE: 11 };
  return m && MES[m[2].toUpperCase()] != null ? `Nueva (vto. ${m[1]}-${MESES[MES[m[2].toUpperCase()]]}-${m[3].slice(2)})` : "Nueva";
}

function licTipo(t) {             // encabezado de la tabla del comunicado -> tipo corto
  const x = t.toLowerCase();
  return x.includes("dual") ? "Dual" : x.includes("cer") ? "CER" : x.includes("linked") ? "Dólar linked" : x.includes("variable") || x.includes("tamar") ? "TAMAR"
    : x.includes("fija") ? "Tasa fija" : x.includes("dólar") || x.includes("dolar") ? "En dólares" : t.replace(/^(a|en)\s+/i, "");
}

function licitacionesGrafico(el, card) {
  const c = COL(); const ch = echarts.init(el); charts.push(ch);
  const [a, b] = rango(card._r);
  const L = (D.licitaciones || []).filter((x) => x.f >= a && x.f <= b);
  const tot = (k) => L.reduce((s, x) => s + (x[k] || 0), 0) / 1e6;
  el._resumen = L.length ? `Acumulado del ${fechaCorta(a)} a ${fechaCorta(b)}: ${L.length} licitaciones, adjudicado <b>$${fmt(tot("adjudicado"), 2)} billones</b> sobre ofertas por $${fmt(tot("ofertado"), 2)} billones` : "";
  ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" },
    legend: { top: 0, left: 0, itemWidth: 12, itemHeight: 8, textStyle: { color: c.texto2, fontSize: 11 } },
    grid: { left: 8, right: 16, top: 34, bottom: 28, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => { const x = L[ps[0].dataIndex];
        return `<div style="font-size:11px;color:${c.texto2}">${fechaCorta(x.f)}</div>Ofertado: <b>${fmt(x.ofertado / 1e6, 2)}</b> billones<br>Adjudicado: <b>${fmt(x.adjudicado / 1e6, 2)}</b> billones` +
          (x.ofertado ? `<br>Adjudicado / ofertado: ${fmt(x.adjudicado / x.ofertado * 100)}%` : "") + (x.suma_instrumentos ? "<br><i>Suma de los instrumentos del comunicado</i>" : ""); } },
    xAxis: { type: "category", data: L.map((x) => fechaCorta(x.f)), axisLabel: { color: c.texto2, fontSize: 10, hideOverlap: true }, axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v, 0) } },
    series: [{ name: "Ofertado", type: "bar", barGap: "-100%", barMaxWidth: 18, itemStyle: { color: c.gris, opacity: 0.35 }, data: L.map((x) => (x.ofertado ? x.ofertado / 1e6 : null)) },
      { name: "Adjudicado", type: "bar", barMaxWidth: 18, itemStyle: { color: c.azul }, data: L.map((x) => x.adjudicado / 1e6) }] });
}

function licMercado(i, f) {       // TEA de mercado de la letra el día hábil anterior a la licitación, y diferencia con el corte
  const v = i.t && "lecap_tem_" + i.t; const s = v ? S(v) : [];
  const p = s.filter((q) => q[0] < f).at(-1);
  if (!p || i.tirea == null || (Date.parse(f) - Date.parse(p[0])) / 864e5 > 5) return "<td></td><td></td>";
  const tea = ((1 + p[1] / 100) ** (365 / 30) - 1) * 100, d = (i.tirea - tea) * 100;
  return `<td>${fmt(tea, 2)}%</td><td class="${Math.abs(d) < 0.5 ? "" : d > 0 ? "dif-neg" : "dif-pos"}">${fmtS(d, 0)} pb</td>`;
}

function tablaLicitaciones(el) {
  el.style.height = "auto";
  const L = (D.licitaciones || []).slice(-6).reverse();
  const filas = L.map((x) => {
    const ins = x.inst.filter((i) => i.ve);
    return ins.map((i, k) => `<tr>${k === 0 ? `<td rowspan="${ins.length}">${fechaCorta(x.f)}<br><span class="est">${fmt(x.adjudicado / 1e6, 2)} bill.</span></td>` : ""}` +
      `<td class="izq">${licEtiqueta(i)}</td><td class="izq">${licTipo(i.tipo)}</td><td>${fmt(i.ve / 1e6, 2)}</td><td>${i.tirea == null ? "" : fmt(i.tirea, 2) + "%"}</td>${licMercado(i, x.f)}</tr>`).join("");
  }).join("");
  const tw = document.createElement("div"); tw.className = "tw";
  tw.innerHTML = `<table class="tabla"><tr><th>Licitación</th><th class="izq">Instrumento</th><th class="izq">Tipo</th><th>Adjudicado (billones $)</th><th>TIREA de corte</th><th>TEA de mercado el día anterior</th><th>Corte - mercado</th></tr>${filas}</table>` +
    '<p class="fuente">Mercado: TEM de la letra en BYMA el día hábil anterior a la licitación, llevada a tasa efectiva anual. Positivo: el Tesoro convalidó una tasa mayor que la del mercado. Solo para LECAP y BONCAP que ya cotizaban.</p>';
  el.appendChild(tw);
}

function fiscal(main) {
  const g = grilla(main);
  const ultIpc = ult("ipc_nivel_general")[0];
  const aPrecios = ultIpc ? mesCorto(ultIpc) : "";
  tmp("_rpr", deflactar("resultado_primario_spn").map(([f, x]) => [f, x / 1e3]));
  tmp("_int", deflactar("intereses_netos_spn").map(([f, x]) => [f, -x / 1e3]));
  const intereses = new Map(S("_int"));   // financiero = primario - intereses netos (los intereses ya van con signo negativo)
  tmp("_rfr", S("_rpr").filter(([f]) => intereses.has(f)).map(([f, x]) => [f, x + intereses.get(f)]));
  tarjeta(g, { mide: "resultado_primario", titulo: () => { const v = ult("_rpr")[1], w = ult("_rfr")[1];
      return `En ${mesCorto(ult("_rpr")[0])} hubo un ${v >= 0 ? "superávit" : "déficit"} primario de $${fmt(Math.abs(v))} y un ${w >= 0 ? "superávit" : "déficit"} financiero de $${fmt(Math.abs(w))} miles de millones`; },
    bajada: `Sector público nacional, base caja · En miles de millones de pesos a precios de ${aPrecios}`, leyenda: true,
    fuente: "Fuente: elaboración propia en base a Ministerio de Economía (Secretaría de Hacienda). Deflactado por IPC del INDEC.", mensual: true, cero: true, resumen: "suma",
    series: [{ v: "_rpr", nombre: "Resultado primario", tipo: "bar" }, { v: "_int", nombre: "Intereses (con signo negativo)", tipo: "bar", color: "naranja" },
      { v: "_rfr", nombre: "Resultado financiero", color: "gris" }] });
  tmp("_rec_t", varIA("recaudacion_total", true)); tmp("_rec_dgi", varIA("recaudacion_dgi", true));
  tmp("_rec_dga", varIA("recaudacion_dga", true));
  tarjeta(g, { mide: "recaudacion", titulo: () => { const v = ult("_rec_t")[1]; return `En ${mesCorto(ult("_rec_t")[0])} la recaudación ${v >= 0 ? "creció" : "cayó"} ${fmt(Math.abs(v), 1)}% interanual en términos reales`; },
    bajada: "Recaudación tributaria nacional deflactada por IPC · Variación % interanual", leyenda: true, mensual: true, cero: true, dec: 1,
    fuente: "Fuente: elaboración propia en base a ARCA (vía datos.gob.ar) e IPC del INDEC.",
    series: [{ v: "_rec_t", nombre: "Total" }, { v: "_rec_dgi", nombre: "Impositiva (DGI)", color: "celeste" }, { v: "_rec_dga", nombre: "Aduana (DGA)", color: "naranja" }] });
  const ultLic = () => (D.licitaciones || []).at(-1) || { f: "2000-01-01", adjudicado: 0 };
  tarjeta(g, { mide: "licitaciones", ancha: true, conRango: true, alto: 320,
    titulo: () => `En la última licitación (${fechaCorta(ultLic().f)}) el Tesoro adjudicó $${fmt(ultLic().adjudicado / 1e6, 2)} billones`,
    bajada: "Licitaciones por efectivo del Tesoro: valor efectivo ofertado y adjudicado · En billones de pesos corrientes",
    fuente: "Fuente: elaboración propia en base a los comunicados de resultados de la Secretaría de Finanzas. No incluye canjes, conversiones ni emisiones en dólares.",
    render: licitacionesGrafico });
  tarjeta(g, { mide: "tabla_licitaciones", ancha: true, titulo: "Qué colocó el Tesoro en las últimas licitaciones",
    bajada: "Valor efectivo adjudicado y tasa de corte por instrumento · TIREA: tasa interna de retorno efectiva anual; en los bonos CER es tasa real",
    fuente: "Fuente: elaboración propia en base a los comunicados de resultados de la Secretaría de Finanzas.", render: tablaLicitaciones });
}

// ------------------------------------------------------------------ industria
function industria(main) {
  const g = grilla(main);
  tmp("_ipi_m", varMensual("ipi_desest")); tmp("_isac_m", varMensual("isac_desest"));
  const fI = ult("ipi_desest")[0];
  tarjeta(g, { mide: "ipi", ancha: true, titulo: () => `En ${mesCorto(fI)} la industria ${ult("_ipi_m")[1] >= 0 ? "creció" : "cayó"} ${fmt(Math.abs(ult("_ipi_m")[1]), 1)}% y la construcción ${ult("_isac_m")[1] >= 0 ? "creció" : "cayó"} ${fmt(Math.abs(ult("_isac_m")[1]), 1)}% contra el mes anterior`,
    bajada: "IPI manufacturero e ISAC, series desestacionalizadas · Índice 2004 = 100", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: "ipi_desest", nombre: "Industria (IPI)" }, { v: "isac_desest", nombre: "Construcción (ISAC)", color: "naranja" }] });
  tarjeta(g, { mide: "ipi_metalmecanica", titulo: "Ramas metalmecánicas", leyenda: true,
    bajada: "IPI manufacturero por división, desestacionalizado · Índice 2004 = 100", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: "ipi_div_metalicas_basicas_desest", nombre: "Metálicas básicas" }, { v: "ipi_div_productos_metal_desest", nombre: "Productos de metal", color: "celeste" },
      { v: "ipi_div_maquinaria_desest", nombre: "Maquinaria y equipo", color: "naranja" }, { v: "ipi_div_automotriz_desest", nombre: "Automotriz", color: "gris" },
      { v: "ipi_div_otros_equipos_desest", nombre: "Otros equipos", color: "verde" }] });
  const ia = (v) => tmp("_ia_" + v, varIA(v));
  tarjeta(g, { mide: "ipi_subclases", titulo: () => `La siderurgia ${ult(ia("ipi_siderurgia"))[1] >= 0 ? "creció" : "cayó"} ${fmt(Math.abs(ult("_ia_ipi_siderurgia")[1]), 1)}% interanual en ${mesCorto(fI)}`, leyenda: true, cero: true,
    bajada: "Subclases del IPI manufacturero, serie original · Variación % interanual", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: ia("ipi_siderurgia"), nombre: "Siderurgia" }, { v: ia("ipi_vehiculos"), nombre: "Vehículos", color: "celeste" },
      { v: ia("ipi_autopartes"), nombre: "Autopartes", color: "naranja" }, { v: ia("ipi_maq_agricola"), nombre: "Maquinaria agrícola", color: "verde" }] });
  tarjeta(g, { mide: "ipi_bienes_metal", leyenda: true, cero: true, titulo: "Maquinaria, línea blanca y estructuras metálicas",
    bajada: "Subclases del IPI manufacturero, serie original · Variación % interanual", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: ia("ipi_maq_uso_general"), nombre: "Maquinaria de uso general" }, { v: ia("ipi_aparatos_domesticos"), nombre: "Aparatos de uso doméstico", color: "celeste" },
      { v: ia("ipi_metalicos_estructurales"), nombre: "Metálicos estructurales", color: "naranja" }] });
  tarjeta(g, { mide: "isac_insumos", leyenda: true, cero: true, titulo: () => `El cemento portland ${ult(ia("isac_cemento"))[1] >= 0 ? "creció" : "cayó"} ${fmt(Math.abs(ult("_ia_isac_cemento")[1]), 1)}% interanual`,
    bajada: "Insumos de la construcción del ISAC, serie original · Variación % interanual", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: ia("isac_cemento"), nombre: "Cemento portland" }, { v: ia("isac_hierro_redondo"), nombre: "Hierro redondo y aceros", color: "naranja" }, { v: ia("isac_original"), nombre: "ISAC total", color: "gris" }] });
}

// ------------------------------------------------------------------ armado general
function decodificar(j) {          // {t:[día inicial, saltos...], v:[...]} -> d:[[fecha, valor]]
  const memo = new Map();
  const iso = (n) => { let s = memo.get(n); if (!s) { s = new Date(n * 864e5).toISOString().slice(0, 10); memo.set(n, s); } return s; };
  Object.values(j.series).forEach((s) => {
    if (s.d || !s.t) return;
    let n = 0; s.d = s.t.map((x, i) => { n += x; return [iso(n), s.v[i]]; });
    delete s.t; delete s.v;
  });
  return j;
}

function render() {
  const [pa, pb] = rango();
  document.getElementById("periodoTxt").textContent = R.desde ? `Período elegido: ${fechaCorta(pa)} a ${fechaCorta(pb)}` : "";
  charts.splice(0).forEach((c) => c.dispose());
  const main = document.getElementById("main"); main.innerHTML = "";
  SECCIONES.find((s) => s.id === TAB).armar(main);
}

// ------------------------------------------------------------------ selector de período (navegador con asas)
let NAV = null, navSilencio = false;
function dibujarNav() {
  if (NAV) NAV.dispose();
  const c = COL(); const el = document.getElementById("nav");
  const fondo = S("reservas_brutas");
  const t0 = Date.parse(fondo[0][0]), t1 = Date.now();
  NAV = echarts.init(el);
  NAV.setOption({
    animation: false, grid: { left: 0, right: 0, top: 0, height: 0 },
    xAxis: { type: "time", min: t0, max: t1, show: false }, yAxis: { type: "value", show: false, scale: true },
    series: [{ type: "line", data: fondo.map((p) => [p[0], p[1]]), showSymbol: false, lineStyle: { opacity: 0 }, sampling: "lttb" }],
    dataZoom: [{ type: "slider", xAxisIndex: 0, realtime: false, top: 4, bottom: 4, left: 46, right: 46, filterMode: "none",
      borderColor: c.borde || c.eje, backgroundColor: "transparent", fillerColor: c.azul + "22",
      dataBackground: { lineStyle: { color: c.gris, width: 1 }, areaStyle: { color: c.gris, opacity: 0.12 } },
      selectedDataBackground: { lineStyle: { color: c.azul, width: 1 }, areaStyle: { color: c.azul, opacity: 0.15 } },
      handleStyle: { color: c.card, borderColor: c.azul }, moveHandleStyle: { color: c.azul, opacity: 0.5 }, moveHandleSize: 5,
      textStyle: { color: c.texto2, fontSize: 10, fontFamily: "Poppins" }, labelFormatter: (v) => (v ? mesCorto(iso(v)) : ""),
      brushSelect: false, ...navVentana() }],
  });
  NAV.on("datazoom", () => {
    if (navSilencio) return;
    const z = NAV.getOption().dataZoom[0];
    const a = iso(z.startValue), b = iso(z.endValue);
    R.desde = a; R.hasta = b >= iso(Date.now() - 3 * 864e5) ? null : b;
    document.querySelectorAll("#rangos button").forEach((x) => x.classList.remove("on"));
    render();
  });
}
function navVentana() { const [a, b] = rango(); return { startValue: Math.max(Date.parse(a), Date.parse(S("reservas_brutas")[0][0])), endValue: Date.parse(b) }; }
function moverNav() {
  if (!NAV) return;
  navSilencio = true; NAV.dispatchAction({ type: "dataZoom", ...navVentana() }); navSilencio = false;
}

function estado() {
  const e = D.estado; const gen = new Date(D.generado);
  document.getElementById("actualizado").textContent =
    `Última actualización del tablero: ${gen.toLocaleDateString("es-AR", { day: "numeric", month: "long", timeZone: "America/Argentina/Buenos_Aires" })}, ${gen.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Argentina/Buenos_Aires" })} h`;
  const problemas = Object.entries(e.fuentes).filter(([, v]) => v.estado === "ERROR" || v.estado === "PARCIAL" || v.error);
  const atrasadas = e.atrasadas || [];
  const aviso = document.getElementById("avisoDatos");
  aviso.replaceChildren(); aviso.hidden = !problemas.length && !atrasadas.length;
  if (!aviso.hidden) {
    const detalle = [];
    if (problemas.length) detalle.push(`Fuentes con problemas: ${problemas.map(([k]) => k).join(", ")}`);
    if (atrasadas.length) detalle.push(`${atrasadas.length} series con demora mayor a la esperada`);
    aviso.append(document.createTextNode(detalle.join(". ") + ". "));
    const enlace = document.createElement("a"); enlace.href = "#estado"; enlace.textContent = "Ver estado y fechas";
    enlace.onclick = () => { document.getElementById("estado").closest("details").open = true; };
    aviso.append(enlace);
  }
  const panel = document.getElementById("estado"); panel.replaceChildren();
  const tabla = document.createElement("table"); tabla.className = "tabla";
  const encabezado = document.createElement("tr");
  ["Fuente", "Estado", "Filas", "Detalle"].forEach((t) => { const th = document.createElement("th"); th.textContent = t; encabezado.append(th); });
  tabla.append(encabezado);
  Object.entries(e.fuentes).forEach(([k, v]) => {
    const tr = document.createElement("tr");
    const status = v.estado === "ok" && v.error ? (v.filas === 0 ? "ERROR" : "PARCIAL") : v.estado;
    [k, status, v.filas ?? "", v.error || ""].forEach((t) => { const td = document.createElement("td"); td.textContent = String(t); tr.append(td); });
    tabla.append(tr);
  });
  panel.append(tabla);
  if (typeof ipomEstado === 'function') ipomEstado();
  if (atrasadas.length) {
    const p = document.createElement("p"); p.textContent = "Series atrasadas: " + atrasadas.join(", "); panel.append(p);
  }
}

function iniciar() {
  const tabs = document.getElementById("tabs");
  SECCIONES.forEach((s) => { const b = document.createElement("button"); b.textContent = s.nombre; b.dataset.id = s.id;
    b.setAttribute("aria-pressed", String(s.id === TAB));
    if (s.id === TAB) b.className = "on"; b.onclick = () => { TAB = s.id; tabs.querySelectorAll("button").forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-pressed", String(x === b)); });
      try { history.replaceState(null, "", "#" + TAB); } catch (e) {} render(); window.scrollTo(0, 0); }; tabs.appendChild(b); });
  document.querySelectorAll("#rangos button").forEach((b) => b.classList.toggle("on", !R.desde && +b.dataset.r === R.dias));
  document.querySelectorAll("#rangos button").forEach((b) => b.onclick = () => {
    R.dias = +b.dataset.r; R.desde = R.hasta = null;
    document.querySelectorAll("#rangos button").forEach((x) => x.classList.toggle("on", x === b)); moverNav(); render(); });
  document.getElementById("tema").onclick = () => {
    const oscuro = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = oscuro ? "light" : "dark";
    try { localStorage.setItem("tema", document.documentElement.dataset.theme); } catch (e) {}
    dibujarNav(); render();
  };
  let tr = null;   // al cambiar el ancho se redibuja (márgenes y etiquetas dependen del ancho)
  let anchoPrevio = window.innerWidth;   // en el celular el scroll cambia el alto: solo cuenta el ancho
  window.addEventListener("resize", () => { if (window.innerWidth === anchoPrevio) return; anchoPrevio = window.innerWidth;
    if (NAV) NAV.resize(); clearTimeout(tr); tr = setTimeout(render, 250); });
}

instalarAmpliacion();
instalarIPOM();
const h = location.hash.slice(1); if (h) TAB = h;
try {   // ?r=días (0 = todo) o ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD
  const q = new URLSearchParams(location.search);
  if (q.has("r")) R.dias = +q.get("r");
  if (q.get("desde")) { R.desde = q.get("desde"); R.hasta = q.get("hasta"); }
} catch (e) {}
// Carga en dos pasos: data_resumen.json (lo que usa el Resumen, últimos dos años, unos 100 KB) dibuja la página enseguida
// y data.json (todo, varios MB) baja en segundo plano. Las demás pestañas esperan al completo.
let COMPLETO = false;
let errorCarga = null, cargandoCompleto = false;
async function pedir(archivo) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  try {
    const r = await fetch(archivo, { cache: "no-cache", signal: controller.signal });
    if (!r.ok) throw new Error(archivo + " " + r.status);
    return await r.json();
  } finally { clearTimeout(timeout); }
}
function mostrarErrorCarga() {
  const aviso = document.getElementById("avisoCarga"); aviso.hidden = !errorCarga; aviso.replaceChildren();
  if (!errorCarga) return;
  aviso.append(document.createTextNode(D ? "No se pudo descargar la base completa. El resumen disponible sigue visible. " : "No se pudieron cargar los datos. "));
  const boton = document.createElement("button"); boton.textContent = "Reintentar carga"; boton.onclick = cargarCompleto; aviso.append(boton);
}
const renderBase = render;
render = function () {   // eslint-disable-line no-func-assign
  if (COMPLETO || TAB === "resumen") return renderBase();
  charts.splice(0).forEach((c) => c.dispose());
  document.getElementById("main").innerHTML = `<p class="seccion-intro" style="margin:32px 0">${errorCarga ? "Esta sección necesita la base completa. Usá Reintentar carga para volver a descargarla." : "Cargando datos…"}</p>`;
};
function arrancar(j) {
  D = decodificar(j); if (!SECCIONES.some((s) => s.id === TAB)) TAB = "resumen";
  iniciar(); estado(); dibujarNav(); render(); mostrarErrorCarga();
}
async function cargarCompleto() {
  if (cargandoCompleto) return;
  cargandoCompleto = true; errorCarga = null; mostrarErrorCarga();
  if (D) render();
  try {
    const j = await pedir("data.json");
    const yaArranco = !!D;
    D = decodificar(j); COMPLETO = true;
    if (!yaArranco) { arrancar(j); return; }
    estado(); dibujarNav();
    // Con la base completa se reemplaza también un resumen de una publicación anterior.
    render();
  } catch (e) {
    errorCarga = e; mostrarErrorCarga();
    if (D) render(); else document.getElementById("main").textContent = "La carga no se completó. Podés reintentar con el botón de arriba.";
  } finally { cargandoCompleto = false; }
}
// Dar tiempo a la tipografía sin bloquear los datos si su servidor no responde.
Promise.race([document.fonts?.ready || Promise.resolve(), new Promise(resolve => setTimeout(resolve, 1500))]).then(() => {
cargarCompleto();
if (!location.hash || location.hash === "#resumen") {
  pedir("data_resumen.json").then((j) => { if (!D) arrancar(j); }).catch(() => {});   // si falla, arranca con el completo
}
});
