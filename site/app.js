/* Tablero macro · Argentina. Lee data.json (generado por el pipeline) y arma secciones y gráficos. */
"use strict";

let D = null;              // series
const R = { dias: 365, desde: null, hasta: null };   // período visible: botones (dias, 0 = todo) o selector (desde/hasta)
let TAB = "resumen";
const charts = [];         // instancias ECharts vivas

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const COL = () => ({ azul: css("--azul"), celeste: css("--celeste"), gris: css("--gris"), naranja: css("--naranja"),
  tinta: css("--tinta"), texto2: css("--texto2"), nota: css("--nota"), grilla: css("--grilla"), eje: css("--eje"), card: css("--card") });

// ------------------------------------------------------------------ formato
const nf = (dec) => new Intl.NumberFormat("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const fmt = (v, dec = 0) => (v == null || isNaN(v) ? "s/d" : nf(dec).format(v));
const fechaCorta = (s) => { const [y, m, d] = s.split("-"); return `${+d}-${MESES[+m - 1]}-${y.slice(2)}`; };
const mesCorto = (s) => { const [y, m] = s.split("-"); return `${MESES[+m - 1]}-${y.slice(2)}`; };

// ------------------------------------------------------------------ datos
const S = (v) => (D.series[v] ? D.series[v].d : []);
const meta = (v) => D.series[v] || { u: "", f: "" };
const ult = (v) => { const s = S(v); return s.length ? s[s.length - 1] : [null, null]; };
const prev = (v) => { const s = S(v); return s.length > 1 ? s[s.length - 2] : [null, null]; };
const iso = (t) => new Date(t).toISOString().slice(0, 10);
const hoy = () => iso(Date.now());
function rango() {                 // [desde, hasta] en ISO
  if (R.desde) return [R.desde, R.hasta || hoy()];
  return [R.dias ? iso(Date.now() - R.dias * 864e5) : "1900-01-01", hoy()];
}
function recortar(serie, mensual) {
  let [a, b] = rango();
  if (mensual && (Date.parse(b) - Date.parse(a)) / 864e5 < 730) a = iso(Date.parse(b) - 730 * 864e5);  // mensuales: al menos dos años
  return serie.filter((p) => p[0] >= a && p[0] <= b);
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
function deflactar(v) {            // serie diaria nominal -> a precios del último IPC (solo desde el inicio del IPC, dic-16)
  const ipc = S("ipc_nivel_general"); if (!ipc.length) return [];
  const base = ipc[ipc.length - 1][1]; let j = 0;
  return S(v).filter(([f]) => f.slice(0, 7) >= ipc[0][0].slice(0, 7)).map(([f, x]) => {
    while (j + 1 < ipc.length && ipc[j + 1][0].slice(0, 7) <= f.slice(0, 7)) j++;
    return [f, x * base / ipc[j][1]];
  });
}

// ------------------------------------------------------------------ gráfico de líneas / barras
// cfg.series: [{v | datos, nombre, color, escala, estimadoAntes}] · cfg.agregar: "suma" | "prom" pasa barras diarias
// a mensuales cuando el período supera dos años · cfg.desdeEmpalme: v cuyo primer dato marca el fin del tramo de otra fuente
function grafico(el, cfg) {
  const c = COL();
  const ch = echarts.init(el, null, { renderer: "canvas" });
  charts.push(ch);
  const paleta = [c.azul, c.gris, c.celeste, c.naranja];
  const series = [];
  const [ra, rb] = rango();
  const agregado = cfg.agregar && !cfg.mensual && (Date.parse(rb) - Date.parse(ra)) / 864e5 > 730;
  const mensual = cfg.mensual || agregado;
  const muestra = Math.abs(((cfg.series[0].datos || S(cfg.series[0].v)).slice(-1)[0] || [0, 0])[1] * (cfg.series[0].escala || 1));
  const dec = cfg.dec ?? (muestra >= 1000 ? 0 : 1);
  const ancho = el.clientWidth || 600;
  const margen = cfg.sinEtiquetas ? 16 : Math.round(Math.min(cfg.margenDer || 150, Math.max(84, ancho * 0.3)));
  const chica = ancho < 420;
  let fMin = null, fMax = null; const visibles = [];
  cfg.series.forEach((s, i) => {
    let datos = s.datos || S(s.v);
    if (s.escala) datos = datos.map(([f, x]) => [f, x * s.escala]);
    datos = recortar(datos, cfg.mensual);
    if (agregado) datos = aMensual(datos, cfg.agregar);
    datos.forEach((p) => { if (p[1] != null) visibles.push(p[1]); });
    if (datos.length) { fMin = fMin && fMin < datos[0][0] ? fMin : datos[0][0]; fMax = fMax && fMax > datos.at(-1)[0] ? fMax : datos.at(-1)[0]; }
    const color = s.color ? c[s.color] : paleta[i];
    const grosor = i === 0 ? 2.4 : 1.6;
    const etiqueta = {
      show: !cfg.sinEtiquetas, formatter: (p) => `${s.nombre} ${fmt(p.value[1], dec)}`,
      color, fontWeight: 600, fontSize: chica ? 10 : 11, fontFamily: "Poppins", distance: 6,
    };
    const base = {
      name: s.nombre, type: s.tipo || cfg.tipo || "line", showSymbol: !!cfg.mensual && (s.tipo || cfg.tipo) !== "bar" && datos.length < 80,
      symbol: "emptyCircle", symbolSize: 5, itemStyle: { color, borderColor: color }, lineStyle: { width: grosor, color },
      emphasis: { disabled: true }, z: 10 - i, barMaxWidth: 14, labelLayout: { moveOverlap: "shiftY" },
      sampling: datos.length > 1500 ? "lttb" : undefined, large: datos.length > 1500,
    };
    if (base.type === "bar") base.itemStyle = { color: (p) => (p.value[1] < 0 && cfg.negGris ? c.gris : color) };
    if (s.estimadoAntes) {     // tramo estimado u otra fuente, punteado
      const a = datos.filter((p) => p[0] < s.estimadoAntes), b = datos.filter((p) => p[0] >= s.estimadoAntes);
      if (a.length && b.length) a.push(b[0]);
      series.push({ ...base, name: s.nombre + " (estimado)", data: a, lineStyle: { ...base.lineStyle, type: [5, 4] }, endLabel: { ...etiqueta, show: !b.length && !cfg.sinEtiquetas } });
      series.push({ ...base, data: b, endLabel: etiqueta });
    } else {
      series.push({ ...base, data: datos, endLabel: base.type === "line" ? etiqueta : undefined });
    }
  });
  if (cfg.cero || cfg.lineas) {
    const ml = [];
    if (cfg.cero) ml.push({ yAxis: 0, lineStyle: { color: c.eje, type: "solid", width: 1 }, label: { show: false } });
    (cfg.lineas || []).filter((l) => l.x >= (fMin || "") && l.x <= (fMax || "9")).forEach((l) => ml.push({ xAxis: l.x, lineStyle: { color: c.nota, type: [3, 3] },
      label: { formatter: l.txt, color: c.nota, fontSize: 10, position: "insideEndTop" } }));
    series[0].markLine = { symbol: "none", silent: true, data: ml, animation: false };
  }
  const anios = fMin ? (Date.parse(fMax) - Date.parse(fMin)) / 864e5 / 365 : 0;
  el.dataset.agregado = agregado ? cfg.agregar : "";
  let techo;   // recorte de picos: si unos pocos días aplastan la escala, el eje se corta en el percentil 97
  if (cfg.recortePicos && visibles.length > 20) {
    const o = [...visibles].sort((a, b) => a - b); const p97 = o[Math.floor(o.length * 0.97)];
    if (p97 > 0 && o.at(-1) > p97 * 1.5) techo = Math.ceil((p97 * 1.25) / 10) * 10;
  }
  el.dataset.recorte = techo ?? "";
  // niveles de precios en pesos: si en el período el valor se multiplica más de 10 veces, escala logarítmica
  const log = cfg.logAuto && visibles.length && Math.min(...visibles) > 0 && Math.max(...visibles) / Math.min(...visibles) > 10;
  el.dataset.log = log ? "1" : "";
  ch.setOption({
    animation: false, textStyle: { fontFamily: "Poppins" },
    grid: { left: 8, right: margen, top: 14, bottom: 22, containLabel: true },
    tooltip: {
      trigger: "axis", backgroundColor: c.card, borderColor: c.eje, textStyle: { color: c.tinta, fontSize: 12 }, confine: true,
      formatter: (ps) => {
        const f = ps[0].value[0];
        const filas = ps.filter((p) => !p.seriesName.endsWith("(estimado)") || !ps.some((q) => q.seriesName === p.seriesName.replace(" (estimado)", "") && q.value[0] === f))
          .map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName.replace(" (estimado)", "*")}: <b>${fmt(p.value[1], dec)}</b>`);
        return `<div style="font-size:11px;color:${c.texto2}">${mensual ? mesCorto(f) : fechaCorta(f)}</div>${filas.join("<br>")}`;
      },
    },
    xAxis: {
      type: "time", axisLine: { lineStyle: { color: c.eje } }, axisTick: { show: false }, splitLine: { show: false },
      splitNumber: Math.max(3, Math.floor((ancho - margen) / 95)),
      axisLabel: { color: c.texto2, fontSize: 11, hideOverlap: true, formatter: (v) => { const d = new Date(v);
        return anios > 4 ? String(d.getFullYear()) : `${MESES[d.getMonth()]}-${String(d.getFullYear()).slice(2)}`; } },
    },
    yAxis: {
      type: log ? "log" : "value", logBase: 10, scale: !cfg.desdeCero, max: techo, axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: c.grilla } }, axisLabel: { color: c.texto2, fontSize: 11, formatter: (v) => fmt(v, cfg.decEje ?? 0) },
    },
    series,
  });
  return ch;
}

// ------------------------------------------------------------------ tarjetas
function tarjeta(cont, cfg) {
  const card = document.createElement("section");
  card.className = "card" + (cfg.ancha ? " ancha" : "");
  const titulo = typeof cfg.titulo === "function" ? cfg.titulo() : cfg.titulo;
  const bajada = typeof cfg.bajada === "function" ? cfg.bajada() : (cfg.bajada || "");
  card.innerHTML = `<h3>${titulo}${cfg.badge ? `<span class="badge">${cfg.badge}</span>` : ""}</h3>
    <p class="bajada">${bajada}</p><div class="chips"></div><div class="chart"></div><p class="fuente">${cfg.fuente}</p>`;
  cont.appendChild(card);
  if (!cfg.chips) card.querySelector(".chips").remove();
  const el = card.querySelector(".chart");
  if (cfg.alto) el.style.height = cfg.alto + "px";
  if (cfg.render) cfg.render(el, card); else grafico(el, cfg);
  const baj = card.querySelector(".bajada");
  if (el.dataset.log) baj.textContent += " · Escala logarítmica";
  if (el.dataset.recorte) baj.textContent += ` · Eje cortado en ${el.dataset.recorte}: hay picos fuera de escala`;
  if (el.dataset.agregado) baj.textContent += el.dataset.agregado === "suma" ? " · Sumas mensuales" : " · Promedios mensuales";
  if (cfg.series && cfg.series[0].v) {   // aviso si la serie principal dejó de actualizarse
    const f = ult(cfg.series[0].v)[0]; const dias = f ? (Date.now() - Date.parse(f)) / 864e5 : 0;
    if (f && dias > (cfg.mensual ? 110 : 10)) baj.insertAdjacentHTML("beforeend", ` · <span class="viejo">último dato: ${cfg.mensual ? mesCorto(f) : fechaCorta(f)}</span>`);
  }
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
  const viejo = f && atraso > (k.mensual ? 110 : 9);
  el.innerHTML = `<div class="lbl">${k.lbl}</div><div class="val">${val}<small>${k.u || ""}</small></div>
    <div class="meta"><span>${dt}</span><span class="${viejo ? "viejo" : ""}" title="${viejo ? `Último dato hace ${atraso} días` : ""}">${f ? (k.mensual ? mesCorto(f) : fechaCorta(f)) : ""}</span></div><div class="spark"></div>`;
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
    </div><div class="tw"></div>`;
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
    el.querySelector(".tw").innerHTML = `<table class="tabla"><tr><th>Millones de USD</th><th>${fechaCorta(b)}</th><th>${fechaCorta(a)}</th><th>Dif.</th></tr>${celdas}</table>` +
      (hayEst ? '<p class="fuente">*Estimado por calibración contra el gráfico de F. Machado.</p>' : "");
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
  bcrd: "Fuente: elaboración propia en base a JP Morgan (EMBI Global Diversified) publicado por el BCRD.",
  indec: "Fuente: elaboración propia en base a INDEC.",
};

const CARD_TABLA_RES = { titulo: "De reservas brutas a súper netas", bajada: "Composición por fecha, método Machado · En millones de USD",
  fuente: F.bcra + " Swap, encajes y depósitos del Tesoro valuados al día.", render: tablaReservas };

const SECCIONES = [
  { id: "resumen", nombre: "Resumen", armar: resumen },
  { id: "cambiario", nombre: "Cambiario", armar: cambiario },
  { id: "reservas", nombre: "Reservas", armar: reservas },
  { id: "tasas", nombre: "Tasas", armar: tasas },
  { id: "riesgo", nombre: "Riesgo país", armar: riesgo },
  { id: "dinero", nombre: "Dinero y crédito", armar: dinero },
  { id: "actividad", nombre: "Precios y actividad", armar: actividad },
  { id: "bc", nombre: "Balance cambiario", armar: balance },
  { id: "internacional", nombre: "Internacional", armar: internacional },
];

function grilla(main) { const g = document.createElement("div"); g.className = "grilla"; main.appendChild(g); return g; }

function resumen(main) {
  const k = document.createElement("div"); k.className = "kpis"; main.appendChild(k);
  const ipcM = varMensual("ipc_nivel_general"); if (ipcM.length) D.series._ipc_m = { u: "%", f: "", d: ipcM };
  [
    { lbl: "Dólar mayorista (A3500)", v: "tc_mayorista_a3500", dec: 1, u: " $" },
    { lbl: "Contado con liqui", v: "ccl", dec: 1, u: " $" },
    { lbl: "Brecha CCL / A3500", v: "brecha_ccl", dec: 1, u: " %" },
    { lbl: "Distancia al techo de la banda", v: "distancia_techo_banda", dec: 1, u: " %" },
    { lbl: "Riesgo país", v: "riesgo_pais_argentina", u: " pb" },
    { lbl: "Reservas brutas", v: "reservas_brutas", u: " M USD" },
    { lbl: "Reservas netas (Machado)", v: "reservas_netas", u: " M USD" },
    { lbl: "Compras BCRA en el año", v: "compras_bcra_acum_anio", u: " M USD" },
    { lbl: "TAMAR", v: "tamar", dec: 2, u: " % TNA" },
    { lbl: "Caución 1 día", v: "caucion_a3_pesos_1d", dec: 2, u: " % TNA" },
    { lbl: "Tasa real ex ante", v: "tasa_real_ex_ante_tamar", dec: 2, u: " % mens." },
    { lbl: "Inflación mensual (IPC)", v: "_ipc_m", dec: 1, u: " %", n: 24, mensual: true },
  ].forEach((x) => kpi(k, x));
  const g = grilla(main);
  tarjeta(g, { titulo: () => `Las reservas netas suman USD ${fmt(ult("reservas_netas")[1])} millones`,
    bajada: "Netas y súper netas, método Machado · En millones de USD", fuente: F.bcra + " *Tramo estimado por calibración.",
    cero: true, series: [{ v: "reservas_netas", nombre: "Netas", estimadoAntes: "2026-07-01" },
      { v: "reservas_super_netas", nombre: "Súper netas", estimadoAntes: "2026-09-30", color: "celeste" }] });
  tarjeta(g, CARD_TABLA_RES);
  tarjeta(g, { titulo: () => `La brecha con el contado con liqui es de ${fmt(ult("brecha_ccl")[1], 1)}%`,
    bajada: "Tipo de cambio mayorista, MEP y CCL · En pesos por dólar", fuente: F.byma + " A3500 del BCRA. " + NOTA_AD, logAuto: true,
    series: [{ v: "ccl_largo", nombre: "CCL", estimadoAntes: inicio("ccl") }, { v: "tc_mayorista_a3500", nombre: "A3500" }, { v: "mep_largo", nombre: "MEP", color: "celeste", estimadoAntes: inicio("mep") }] });
  tarjeta(g, { titulo: () => `El riesgo país está en ${fmt(ult("riesgo_pais_argentina")[1])} puntos`,
    bajada: "EMBI Global Diversified · Argentina y América Latina · En puntos básicos", fuente: F.bcrd + " *Antes de oct-07, ArgentinaDatos.",
    lineas: [{ x: "2026-09-04", txt: "cambio metodológico" }],
    dec: 0, series: [{ v: "riesgo_pais_argentina_largo", nombre: "Argentina", estimadoAntes: inicio("riesgo_pais_argentina") }, { v: "riesgo_pais_latam", nombre: "América Latina" }] });
}

function cambiario(main) {
  const g = grilla(main);
  tarjeta(g, { titulo: () => `El mayorista está ${fmt(ult("distancia_techo_banda")[1], 1)}% por debajo del techo de la banda`,
    bajada: "A3500 y límites de la banda cambiaria · En pesos por dólar", fuente: F.bcra, logAuto: true,
    series: [{ v: "tc_mayorista_a3500", nombre: "A3500" }, { v: "banda_techo", nombre: "Techo" }, { v: "banda_piso", nombre: "Piso", color: "gris" }] });
  tarjeta(g, { titulo: () => `El CCL cotiza a $${fmt(ult("ccl")[1], 0)} y el MEP a $${fmt(ult("mep")[1], 0)}`,
    bajada: "Dólares financieros calculados con el AL30 · En pesos por dólar", fuente: F.byma + " " + NOTA_AD, logAuto: true,
    series: [{ v: "ccl_largo", nombre: "CCL", estimadoAntes: inicio("ccl") }, { v: "mep_largo", nombre: "MEP", color: "celeste", estimadoAntes: inicio("mep") }, { v: "tc_mayorista_a3500", nombre: "A3500", color: "gris" }] });
  tarjeta(g, { titulo: () => `La brecha es de ${fmt(ult("brecha_ccl")[1], 1)}% y el canje de ${fmt(ult("canje_ccl_mep")[1], 1)}%`,
    bajada: "Brecha CCL / A3500 y canje CCL / MEP · En %", fuente: F.byma + ` Antes de ${mesCorto(inicio("ccl") || "2024-10")}, CCL y MEP de ArgentinaDatos.`, cero: true,
    series: [{ v: "brecha_ccl", nombre: "Brecha" }, { v: "canje_ccl_mep", nombre: "Canje", color: "celeste" }] });
  tarjeta(g, { titulo: () => `El mercado paga $${fmt(ult("futuro_diciembre")[1], 0)} por el dólar de diciembre`,
    bajada: "Dólar futuro: contrato más corto y diciembre, contra el A3500 · En pesos por dólar", fuente: F.a3, logAuto: true,
    series: [{ v: "futuro_diciembre", nombre: "Diciembre" }, { v: "futuro_fin_mes", nombre: "Fin de mes", color: "celeste" }, { v: "tc_mayorista_a3500", nombre: "A3500", color: "gris" }] });
  tarjeta(g, { ancha: true, titulo: () => `En el MLC se operaron USD ${fmt(ult("volumen_mlc")[1])} millones en la última rueda`,
    bajada: "Volumen diario operado en el mercado de cambios · En millones de USD", fuente: F.a3, tipo: "bar", sinEtiquetas: true, desdeCero: true, agregar: "prom",
    series: [{ v: "volumen_mlc", nombre: "Volumen" }] });
}

function reservas(main) {
  const g = grilla(main);
  tarjeta(g, { ancha: true, titulo: () => `Las reservas netas suman USD ${fmt(ult("reservas_netas")[1])} millones y las súper netas USD ${fmt(ult("reservas_super_netas")[1])} millones`,
    bajada: "Método Machado · En millones de USD", fuente: F.bcra + " *Tramo discontinuo: BIS, repos y Bopreal estimados por calibración contra el gráfico de F. Machado.",
    cero: true, series: [{ v: "reservas_netas", nombre: "Netas", estimadoAntes: "2026-07-01" },
      { v: "reservas_super_netas", nombre: "Súper netas", estimadoAntes: "2026-09-30", color: "celeste" }] });
  tarjeta(g, CARD_TABLA_RES);
  tarjeta(g, { titulo: () => `Las reservas brutas suman USD ${fmt(ult("reservas_brutas")[1])} millones`,
    bajada: "Stock diario · En millones de USD", fuente: F.bcra, series: [{ v: "reservas_brutas", nombre: "Brutas" }] });
  tarjeta(g, { titulo: () => `El BCRA compró USD ${fmt(ult("compras_bcra_acum_anio")[1])} millones en el año`,
    bajada: "Compras diarias en el mercado de cambios · En millones de USD", fuente: F.bcra, tipo: "bar", sinEtiquetas: true, cero: true, agregar: "suma", negGris: true,
    series: [{ v: "compras_bcra_mlc", nombre: "Compras" }] });
  tarjeta(g, { titulo: () => `Las compras equivalen al ${fmt(ult("compras_bcra_pct_volumen")[1], 1)}% del volumen del MLC`,
    bajada: "Compras del BCRA sobre volumen operado · En %", fuente: F.bcra + " Volumen de A3 Mercados.", tipo: "bar", sinEtiquetas: true, cero: true, agregar: "prom",
    series: [{ v: "compras_bcra_pct_volumen", nombre: "Compras / volumen" }] });
  tarjeta(g, { ancha: true, titulo: () => `El Tesoro tiene USD ${fmt(ult("res_dep_tesoro")[1])} millones depositados en el BCRA`,
    bajada: "Depósitos del gobierno en moneda extranjera · En millones de USD", fuente: F.bcra,
    series: [{ v: "res_dep_tesoro", nombre: "Depósitos" }] });
}

function tasas(main) {
  const g = grilla(main);
  tarjeta(g, { titulo: () => `La TAMAR se ubica en ${fmt(ult("tamar")[1], 1)}% anual`,
    bajada: "Tasas de bancos privados · En % TNA", fuente: F.bcra, dec: 1, recortePicos: true,
    series: [{ v: "tamar", nombre: "TAMAR" }, { v: "badlar", nombre: "BADLAR" }, { v: "tasa_plazo_fijo_30d", nombre: "Plazo fijo", color: "celeste" }, { v: "baibar", nombre: "BAIBAR", color: "naranja" }] });
  tarjeta(g, { titulo: () => `La caución a un día rinde ${fmt(ult("caucion_a3_pesos_1d")[1], 1)}% anual`,
    bajada: "Tasas de corto plazo en pesos · En % TNA", fuente: F.a3 + " Pases entre terceros del BCRA.", dec: 1, recortePicos: true,
    series: [{ v: "caucion_a3_pesos_1d", nombre: "Caución" }, { v: "tasa_pases_terceros_1d", nombre: "Pases" }, { v: "repo_a3_pesos_1d", nombre: "Repo", color: "celeste" }] });
  tarjeta(g, { titulo: () => `La tasa real esperada es de ${fmt(ult("tasa_real_ex_ante_tamar")[1], 2)}% mensual`,
    bajada: "TAMAR y BADLAR efectivas mensuales contra inflación esperada del mes siguiente (REM) · En %", fuente: F.bcra, dec: 2, decEje: 1, cero: true,
    series: [{ v: "tasa_real_ex_ante_tamar", nombre: "TAMAR" }, { v: "tasa_real_ex_ante_badlar", nombre: "BADLAR" }] });
  tarjeta(g, { titulo: "Curva de tasa fija", badge: "en validación",
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
}

function riesgo(main) {
  const g = grilla(main);
  tarjeta(g, { titulo: () => `El riesgo país de Argentina está en ${fmt(ult("riesgo_pais_argentina")[1])} puntos`,
    bajada: "EMBI Global Diversified · Argentina y América Latina · En puntos básicos", fuente: F.bcrd + " Desde el 4/9/26 cambió la metodología de JP Morgan. *Tramo punteado (antes de oct-07): ArgentinaDatos (Ámbito), que coincide con el BCRD en el período común.",
    lineas: [{ x: "2026-09-04", txt: "cambio metodológico" }],
    dec: 0, series: [{ v: "riesgo_pais_argentina_largo", nombre: "Argentina", estimadoAntes: inicio("riesgo_pais_argentina") }, { v: "riesgo_pais_latam", nombre: "América Latina" }] });
  const paises = { brasil: "Brasil", chile: "Chile", colombia: "Colombia", ecuador: "Ecuador", mexico: "México", peru: "Perú",
    uruguay: "Uruguay", paraguay: "Paraguay", bolivia: "Bolivia", el_salvador: "El Salvador", panama: "Panamá",
    costa_rica: "Costa Rica", guatemala: "Guatemala", honduras: "Honduras", rep_dominicana: "Rep. Dominicana", venezuela: "Venezuela" };
  let sel = ["brasil", "ecuador", "colombia"];
  tarjeta(g, { titulo: "Argentina frente a otros países de la región", chips: true,
    bajada: "Elegí hasta tres países · En puntos básicos", fuente: F.bcrd,
    render: (el, card) => {
      const chips = card.querySelector(".chips");
      const dibujar = () => {
        const viejo = echarts.getInstanceByDom(el); if (viejo) viejo.dispose();
        grafico(el, { dec: 0, series: [{ v: "riesgo_pais_argentina", nombre: "Argentina" },
          ...sel.map((p, i) => ({ v: "riesgo_pais_" + p, nombre: paises[p], color: ["gris", "celeste", "naranja"][i] }))] });
      };
      Object.entries(paises).forEach(([k, n]) => {
        const b = document.createElement("button"); b.textContent = n; if (sel.includes(k)) b.className = "on";
        b.onclick = () => { if (sel.includes(k)) sel = sel.filter((x) => x !== k); else { sel.push(k); if (sel.length > 3) sel.shift(); }
          chips.querySelectorAll("button").forEach((x, i) => x.classList.toggle("on", sel.includes(Object.keys(paises)[i]))); dibujar(); };
        chips.appendChild(b);
      });
      dibujar();
    } });
  tarjeta(g, { ancha: true, titulo: "Ranking regional de riesgo país", alto: 380,
    bajada: () => "", fuente: F.bcrd + " Venezuela fuera de escala, excluida del gráfico.",
    render: (el) => {
      const ks = Object.keys(D.series).filter((k) => k.startsWith("riesgo_pais_") && !["riesgo_pais_venezuela", "riesgo_pais_global"].includes(k) && !/_(ad|bcrp|largo)$/.test(k));
      const pts = ks.map((k) => [k === "riesgo_pais_latam" ? "América Latina" : (paises[k.slice(12)] || "Argentina"), ult(k)[1]]).sort((a, b) => a[1] - b[1]);
      const c = COL(); const ch = echarts.init(el); charts.push(ch);
      ch.setOption({ animation: false, textStyle: { fontFamily: "Poppins" }, grid: { left: 16, right: 50, top: 6, bottom: 6, containLabel: true },
        xAxis: { type: "value", show: false }, yAxis: { type: "category", data: pts.map((p) => p[0]), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: c.texto2, width: 120, overflow: "none" } },
        series: [{ type: "bar", data: pts.map((p) => ({ value: p[1], itemStyle: { color: p[0] === "Argentina" ? c.azul : p[0] === "América Latina" ? c.celeste : c.gris } })),
          barMaxWidth: 16, label: { show: true, position: "right", color: c.texto2, fontSize: 11, formatter: (p) => fmt(p.value) } }] });
    } });
}

function dinero(main) {
  const g = grilla(main);
  const ultIpc = ult("ipc_nivel_general")[0];
  const aPrecios = ultIpc ? `a precios de ${mesCorto(ultIpc)} · Desde dic-16 (inicio del IPC nacional)` : "";
  D.series._m2r = { u: "", f: "", d: deflactar("m2_transaccional_privado").map(([f, x]) => [f, x / 1e6]) };
  D.series._bmr = { u: "", f: "", d: deflactar("base_monetaria").map(([f, x]) => [f, x / 1e6]) };
  D.series._prr = { u: "", f: "", d: deflactar("prestamos_privados_pesos").map(([f, x]) => [f, x / 1e6]) };
  tarjeta(g, { titulo: "Demanda de dinero: M2 privado transaccional en términos reales",
    bajada: `En billones de pesos ${aPrecios}`, fuente: F.bcra + " Deflactado por IPC del INDEC.", dec: 1, decEje: 0,
    series: [{ v: "_m2r", nombre: "M2 transaccional" }, { v: "_bmr", nombre: "Base monetaria" }] });
  tarjeta(g, { titulo: "Préstamos en pesos al sector privado en términos reales",
    bajada: `En billones de pesos ${aPrecios}`, fuente: F.bcra + " Deflactado por IPC del INDEC.", dec: 1,
    series: [{ v: "_prr", nombre: "Préstamos" }] });
  tarjeta(g, { titulo: () => `Los depósitos privados en dólares suman USD ${fmt(ult("depositos_privados_usd")[1])} millones`,
    bajada: "Depósitos y préstamos en dólares del sector privado · En millones de USD", fuente: F.bcra,
    series: [{ v: "depositos_privados_usd", nombre: "Depósitos" }, { v: "prestamos_privados_usd", nombre: "Préstamos", color: "celeste" }] });
}

function actividad(main) {
  const g = grilla(main);
  D.series._ipc_m = { u: "%", f: "", d: varMensual("ipc_nivel_general") };
  D.series._nuc_m = { u: "%", f: "", d: varMensual("ipc_nucleo") };
  tarjeta(g, { titulo: () => `La inflación de ${mesCorto(ult("_ipc_m")[0])} fue de ${fmt(ult("_ipc_m")[1], 1)}%`,
    bajada: "IPC nivel general y núcleo · Variación % mensual", fuente: F.indec, mensual: true, dec: 1, decEje: 1,
    series: [{ v: "_ipc_m", nombre: "General" }, { v: "_nuc_m", nombre: "Núcleo", color: "celeste" }] });
  tarjeta(g, { titulo: () => `El mercado espera ${fmt(ult("rem_inflacion_12m")[1], 1)}% de inflación a 12 meses`,
    bajada: "Relevamiento de Expectativas de Mercado (REM), mediana · En % interanual", fuente: F.bcra, mensual: true, dec: 1,
    series: [{ v: "rem_inflacion_12m", nombre: "Próximos 12 meses" }] });
  tarjeta(g, { titulo: "Actividad económica (EMAE)", bajada: "Serie desestacionalizada · Índice 2004 = 100", fuente: F.indec, mensual: true, dec: 1,
    series: [{ v: "emae_desest", nombre: "EMAE" }] });
  const nDem = S("demanda_electrica_diaria").length;
  tarjeta(g, { titulo: "Demanda eléctrica diaria", badge: nDem < 30 ? "acumulando historia" : "",
    bajada: "Energía demandada en el sistema · En MWh por día", fuente: "Fuente: elaboración propia en base a CAMMESA. CAMMESA publica solo el día anterior: la serie se acumula desde oct-26.",
    series: [{ v: "demanda_electrica_diaria", nombre: "Demanda" }],
    render: nDem < 10 ? (el) => { el.style.height = "auto"; el.innerHTML = `<p class="seccion-intro" style="margin:24px 0">${nDem === 1 ? "Hay un día registrado" : `Hay ${nDem} días registrados`} (último: ${fmt(ult("demanda_electrica_diaria")[1])} MWh). El gráfico aparece con diez días de historia.</p>`; } : undefined });
  tarjeta(g, { titulo: () => `En ${mesCorto(ult("exportaciones")[0])} se exportaron USD ${fmt(ult("exportaciones")[1])} millones`,
    bajada: "Intercambio comercial de bienes · En millones de USD", fuente: F.indec, mensual: true,
    series: [{ v: "exportaciones", nombre: "Expo" }, { v: "importaciones", nombre: "Impo" }] });
  const ultIpc = ult("ipc_nivel_general")[0];
  D.series._rpr = { u: "", f: "", d: deflactar("resultado_primario_spn").map(([f, x]) => [f, x / 1e3]) };
  tarjeta(g, { titulo: () => { const v = ult("_rpr")[1]; return `En ${mesCorto(ult("_rpr")[0])} hubo un ${v >= 0 ? "superávit" : "déficit"} primario de $${fmt(Math.abs(v))} miles de millones`; },
    bajada: `Sector público nacional, base caja · En miles de millones de pesos a precios de ${ultIpc ? mesCorto(ultIpc) : ""}`,
    fuente: "Fuente: elaboración propia en base a Ministerio de Economía. Deflactado por IPC del INDEC.", mensual: true, tipo: "bar", sinEtiquetas: true, cero: true, negGris: true,
    series: [{ v: "_rpr", nombre: "Resultado primario" }] });
  tarjeta(g, { ancha: true, titulo: () => `El tipo de cambio real multilateral está en ${fmt(ult("tcrm")[1], 1)}`,
    bajada: "Índice de tipo de cambio real multilateral y bilaterales · Base 17-12-15 = 100", fuente: F.bcra, dec: 1,
    series: [{ v: "tcrm", nombre: "Multilateral" }, { v: "tcr_brasil", nombre: "Brasil" }, { v: "tcr_eeuu", nombre: "EE.UU.", color: "celeste" }] });
}

function balance(main) {
  const g = grilla(main);
  const m = { mensual: true, dec: 0 };
  tarjeta(g, { ...m, titulo: () => `Las personas humanas demandaron USD ${fmt(-ult("mc_personas_humanas")[1])} millones netos en ${mesCorto(ult("mc_personas_humanas")[0])}`,
    bajada: "Operaciones netas de personas humanas en el mercado de cambios · En millones de USD", fuente: F.bcra, tipo: "bar", sinEtiquetas: true, cero: true,
    series: [{ v: "mc_personas_humanas", nombre: "Personas humanas" }] });
  tarjeta(g, { ...m, titulo: "Oferta neta de los sectores exportadores", bajada: "Agro, petróleo y minería · En millones de USD", fuente: F.bcra,
    series: [{ v: "mc_oleaginosos_cerealeros", nombre: "Agro" }, { v: "mc_petroleo", nombre: "Petróleo" }, { v: "mc_mineria", nombre: "Minería", color: "celeste" }] });
  tarjeta(g, { ...m, titulo: "Giro de utilidades y financiamiento con deuda", bajada: "Netos del balance cambiario · En millones de USD", fuente: F.bcra, cero: true,
    series: [{ v: "bc_prestamos_titulos_deuda", nombre: "Deuda" }, { v: "bc_utilidades_dividendos", nombre: "Utilidades" }] });
  tarjeta(g, { ...m, titulo: "Cuenta corriente y cuenta financiera cambiarias", bajada: "En millones de USD", fuente: F.bcra, cero: true,
    series: [{ v: "bc_cuenta_corriente", nombre: "Corriente" }, { v: "bc_cuenta_financiera", nombre: "Financiera" }] });
}

function internacional(main) {
  const g = grilla(main);
  tarjeta(g, { titulo: () => `El bono del Tesoro a 10 años rinde ${fmt(ult("ust_10y")[1], 2)}%`, bajada: "Rendimiento de bonos del Tesoro de EE.UU. · En %",
    fuente: "Fuente: elaboración propia en base a US Treasury.", dec: 2, decEje: 1,
    series: [{ v: "ust_10y", nombre: "10 años" }, { v: "ust_2y", nombre: "2 años" }] });
  tarjeta(g, { titulo: () => `El VIX está en ${fmt(ult("vix")[1], 1)} puntos`, bajada: "Volatilidad implícita del S&P 500 · Índice",
    fuente: "Fuente: elaboración propia en base a Yahoo Finance.", dec: 1, series: [{ v: "vix", nombre: "VIX" }] });
  tarjeta(g, { titulo: "Dólar global y real brasileño", bajada: "Índice DXY y reales por dólar", fuente: "Fuente: elaboración propia en base a Yahoo Finance.", dec: 2,
    render: (el) => { el.style.display = "grid"; el.style.gridTemplateColumns = "1fr 1fr"; el.style.gap = "8px";
      const a = document.createElement("div"), b = document.createElement("div"); el.append(a, b);
      grafico(a, { dec: 1, margenDer: 70, series: [{ v: "dxy", nombre: "DXY" }] });
      grafico(b, { dec: 2, decEje: 2, margenDer: 70, series: [{ v: "brl_usd", nombre: "BRL" }] }); } });
  tarjeta(g, { titulo: "Materias primas", bajada: "Brent (USD/barril), oro (USD/onza) y soja (centavos de USD/bushel)", fuente: "Fuente: elaboración propia en base a Yahoo Finance.",
    render: (el) => { el.style.display = "grid"; el.style.gridTemplateColumns = "1fr 1fr 1fr"; el.style.gap = "6px";
      ["brent", "oro", "soja_cbot"].forEach((v, i) => { const d = document.createElement("div"); el.appendChild(d);
        grafico(d, { dec: v === "brent" ? 1 : 0, margenDer: 64, series: [{ v, nombre: ["Brent", "Oro", "Soja"][i] }] }); }); } });
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
    `Datos al ${gen.toLocaleDateString("es-AR", { day: "numeric", month: "long" })}, ${gen.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false })} h`;
  const filas = Object.entries(e.fuentes).map(([k, v]) => `<tr><td>${k}</td><td>${v.estado}</td><td>${v.filas ?? ""}</td><td>${(v.error || "").slice(0, 120)}</td></tr>`);
  document.getElementById("estado").innerHTML = `<table class="tabla"><tr><th>Fuente</th><th>Estado</th><th>Filas</th><th>Detalle</th></tr>${filas.join("")}</table>`;
}

function iniciar() {
  const tabs = document.getElementById("tabs");
  SECCIONES.forEach((s) => { const b = document.createElement("button"); b.textContent = s.nombre; b.dataset.id = s.id;
    if (s.id === TAB) b.className = "on"; b.onclick = () => { TAB = s.id; tabs.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
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

const h = location.hash.slice(1); if (h) TAB = h;
try {   // ?r=días (0 = todo) o ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD
  const q = new URLSearchParams(location.search);
  if (q.has("r")) R.dias = +q.get("r");
  if (q.get("desde")) { R.desde = q.get("desde"); R.hasta = q.get("hasta"); }
} catch (e) {}
fetch("data.json", { cache: "no-cache" }).then((r) => r.json()).then((j) => {
  D = decodificar(j); if (!SECCIONES.some((s) => s.id === TAB)) TAB = "resumen";
  iniciar(); estado(); dibujarNav(); render();
}).catch((e) => { document.getElementById("main").textContent = "No se pudieron cargar los datos: " + e; });
