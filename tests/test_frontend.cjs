const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../site/app.js'), 'utf8');
const ipomSource = fs.readFileSync(path.join(__dirname, '../site/ipom.js'), 'utf8');

test('las fechas de fuentes con distintos rezagos se muestran por separado', () => {
  const dates={ibc:'2026-09-01',manufactura:'2026-08-01'};
  const c=vm.createContext({ult:k=>[dates[k],100],mesCorto:f=>f.slice(0,7),fechaCorta:f=>f});
  vm.runInContext(ipomSource.slice(ipomSource.indexOf('function icorte'),ipomSource.indexOf('function icard')),c);
  const expr="icorte([{v:'ibc',nombre:'Actividad'},{v:'manufactura',nombre:'Manufactura'}],true)";
  assert.equal(vm.runInContext(expr,c),'Actividad: 2026-09 · Manufactura: 2026-08');
  dates.manufactura=dates.ibc;
  assert.equal(vm.runInContext(expr,c),'Hasta 2026-09');
});

function entorno(fetch, hash = '') {
  const elements = new Map();
  function element() { return { hidden: true, children: [], textContent: '', innerHTML: '',
    append(x) { this.children.push(x); }, replaceChildren() { this.children = []; } }; }
  const context = vm.createContext({ fetch, location: { hash, search: '' }, URLSearchParams, AbortController,
    setTimeout, clearTimeout, Date, console, document: {
      getElementById(id) { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); },
      createElement: element, createTextNode: (s) => s,
    } });
  vm.runInContext(`let D=null, TAB='resumen'; const R={dias:365}; const charts=[];
    const SECCIONES=[{id:'resumen'},{id:'bonos'}];
    function render(){document.getElementById('main').textContent=TAB;}
    function decodificar(j){return j;} function iniciar(){} function estado(){} function dibujarNav(){}`, context);
  vm.runInContext(source.slice(source.indexOf('const h = location.hash')), context);
  return { context, elements, get: (expr) => vm.runInContext(expr, context) };
}
const flush = () => new Promise((resolve) => setImmediate(resolve));
const ok = (j) => Promise.resolve({ ok: true, json: async () => j });

test('resumen disponible + base completa fallida muestra error y permite reintentar', async () => {
  let intentos = 0;
  const e = entorno((url) => url.includes('resumen') ? ok({ parcial: true }) : ++intentos === 1 ? Promise.reject(Error('red')) : ok({ series: {} }));
  await flush();
  assert.equal(e.get('COMPLETO'), false);
  assert.equal(e.elements.get('avisoCarga').hidden, false);
  e.get("TAB='bonos';render()");
  assert.match(e.elements.get('main').innerHTML, /Reintentar/);
  await e.get('cargarCompleto()');
  assert.equal(e.get('COMPLETO'), true);
  assert.equal(e.elements.get('avisoCarga').hidden, true);
});

test('falla de ambas descargas permite recuperarse', async () => {
  let falla = true;
  const e = entorno(() => falla ? Promise.reject(Error('offline')) : ok({ series: {} }));
  await flush();
  assert.equal(e.elements.get('avisoCarga').hidden, false);
  assert.match(e.elements.get('main').textContent, /reintentar/);
  falla = false; await e.get('cargarCompleto()');
  assert.equal(e.get('COMPLETO'), true);
});

test('enlace directo a Bonos también permite recuperarse', async () => {
  const e = entorno(() => Promise.reject(Error('HTTP 500')), '#bonos');
  await flush();
  assert.equal(e.elements.get('avisoCarga').hidden, false);
});

test('la distancia describe suba requerida, igualdad y exceso sin cambiar fórmula', () => {
  const c = vm.createContext({ Intl });
  vm.runInContext(source.slice(source.indexOf('const nf ='), source.indexOf('const fechaCorta')), c);
  assert.match(vm.runInContext('textoDistanciaTecho(27.25)', c), /subir 27,3% para alcanzar/);
  assert.match(vm.runInContext('textoDistanciaTecho(-5)', c), /bajar 5,0%/);
  assert.match(vm.runInContext('textoDistanciaTecho(null)', c), /No hay/);
  assert.match(vm.runInContext('textoDistanciaTecho(0)', c), /está en el techo/);
});
