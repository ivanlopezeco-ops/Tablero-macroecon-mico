'use strict';
const I=k=>'ipom_'+k;
const iser=(k,nombre,color='azul',extra={})=>({v:I(k),nombre,color,...extra});
function icorte(series,mensual) {
  const fecha=mensual?mesCorto:fechaCorta;
  const fechas=series.map(s=>ult(s.v)[0]);
  return new Set(fechas).size===1?'Hasta '+fecha(fechas[0]):series.map((s,i)=>s.nombre+': '+fecha(fechas[i])).join(' · ');
}
function icard(g,titulo,bajada,series,opts={}) {
  if(series.some(s=>!S(s.v).length)){ampNota(g,'No hay datos disponibles para '+titulo+'. Revisá el estado de las fuentes al pie.');return null;}
  const key=series[0].v, m=meta(key), mensual=opts.mensual!==false;
  MIDE[key]=opts.explicacion||m.metodologia;
  const fuentes=[...new Map(series.map(s=>[meta(s.v).url,meta(s.v)])).values()];
  const card=tarjeta(g,{titulo,bajada:()=>bajada+' · '+icorte(series,mensual),series,mensual,leyenda:true,dec:1,decEje:opts.dec===2?2:1,mide:key,
    fuente:'Fuente: '+fuentes.map(s=>`<a href="${s.url}" target="_blank" rel="noopener">${s.f}</a>`).join(' · ')+'.',...opts});
  card.classList.add('ipom-card');return card;
}
function ipomInternacional(main) {
  ampIntro(main,'Brasil y política monetaria de EE.UU.','Actividad y manufactura de Brasil con ajuste estacional oficial. La inflación estadounidense se sigue con el PCE general y núcleo, junto con el rango objetivo de la Fed.');
  const g=grilla(main);
  icard(g,'Brasil: actividad económica y manufactura','Índices 2022 = 100 · Desestacionalizados',[iser('br_ibc','Actividad IBC-Br'),iser('br_industria','Manufactura','naranja')],{explicacion:'IBC-Br del Banco Central do Brasil (SGS 24364) y producción física manufacturera del IBGE, distribuida por BCB (SGS 28505). Ambas series son índices 2022=100 con ajuste estacional oficial. El IBC-Br es un indicador mensual de actividad, no el PIB. La manufactura excluye las industrias extractivas. La base común permite comparar su trayectoria; la distancia entre índices no mide una participación sectorial.'});
  icard(g,'Fed: rango objetivo de la tasa','Porcentaje anual · Límites inferior y superior · Días hábiles',[iser('fed_piso','Límite inferior','azul',{step:'end'}),iser('fed_techo','Límite superior','naranja',{step:'end'})],{mensual:false,dec:2,explicacion:'Rango objetivo para la tasa de fondos federales establecido por el FOMC. Se muestran targetRateFrom y targetRateTo del registro EFFR de la Fed de Nueva York, por fecha efectiva y días hábiles. No se utiliza la tasa efectiva percentRate ni se completan días sin publicación. Las fechas de los cambios de diciembre de 2015 y 2016 siguen la publicación de la Fed de Nueva York. No es la tasa efectiva observada ni una tasa proyectada. Se conservan los valores de cero y las fechas de vigencia.'});
  icard(g,'EE.UU.: inflación PCE interanual','Variación respecto del mismo mes del año anterior (%)',[iser('pce_general_ia','General'),iser('pce_nucleo_ia','Núcleo','naranja')],{cero:true,explicacion:'Índice de precios del gasto de consumo personal (PCE), BEA, obtenido directamente de su tabla mensual 2.3.4U. Núcleo excluye alimentos y energía. Variación calculada como (índice del mes / índice del mismo mes del año anterior − 1) × 100. Se utilizan las series oficiales desestacionalizadas DPCERG y DPCCRG; no se imputan meses.'});
  icard(g,'EE.UU.: inflación PCE mensual','Variación mensual (%) · Desestacionalizada · Sin anualizar',[iser('pce_general_mensual','General'),iser('pce_nucleo_mensual','Núcleo','naranja')],{dec:2,cero:true});
}
function ipomComercio(main) {
  ampIntro(main,'Comercio exterior: cantidades y precios','Índices mensuales del INDEC. Las cantidades permiten seguir el volumen comerciado; los términos del intercambio relacionan los precios de exportación con los de importación. Los datos recientes son provisorios y están sujetos a revisión.');
  const g=grilla(main);
  icard(g,'Cantidades exportadas e importadas','Índices 2004 = 100 · Series originales, sin desestacionalizar',[iser('expo_cantidad','Exportaciones'),iser('impo_cantidad','Importaciones','naranja')],{explicacion:'Índices oficiales de cantidades del comercio exterior de bienes, base 2004=100. Cada flujo tiene su propia canasta: el nivel de los índices no permite comparar toneladas ni afirmar que se exporta más volumen que el importado. Se conserva la estacionalidad de la publicación.'});
  icard(g,'Variación interanual de las cantidades','Variación respecto del mismo mes del año anterior (%)',[iser('expo_cantidad_ia','Exportaciones'),iser('impo_cantidad_ia','Importaciones','naranja')],{cero:true});
  icard(g,'Términos del intercambio','Índice 2004 = 100 · Precio exportado / precio importado × 100',[iser('terminos_intercambio','Términos del intercambio')],{explicacion:'Cálculo con los índices mensuales de precios de exportación e importación del INDEC: Px / Pm × 100. Se cruzan meses exactos y la misma base 2004=100. Una suba significa que los precios exportados aumentan respecto de los importados. No mide por sí sola el saldo comercial, el poder de compra efectivo de exportaciones ni una ganancia de ingreso.'});
  icard(g,'Precios de exportación e importación','Índices 2004 = 100 · Precios en dólares',[iser('expo_precio','Exportaciones'),iser('impo_precio','Importaciones','naranja')]);
}
function ipomTasas(main) {
  ampIntro(main,'Tasas de préstamos','Tasas nominales anuales publicadas por el BCRA. El panel mensual permite comparar líneas; las referencias diarias tienen coberturas específicas.');
  const g=grilla(main);
  icard(g,'Tasas activas por línea de crédito','Promedio mensual · TNA (%)',[iser('tasa_adelantos_mensual','Adelantos'),iser('tasa_documentos_mensual','Documentos','naranja'),iser('tasa_personales_mensual','Personales','verde')]);
  icard(g,'Referencias diarias de préstamos','TNA (%) · Adelantos a empresas con acuerdo, 1–7 días, $10 M o más',[iser('tasa_adelantos_diaria','Adelantos'),iser('tasa_personales_diaria','Personales','verde')],{mensual:false,explicacion:'BCRA, referencias diarias: adelantos en cuenta corriente a empresas con acuerdo, plazo de 1 a 7 días y monto de $10 millones o más, y préstamos personales. Los adelantos diarios corresponden a un universo más acotado que el total mensual; no se empalman ambas series. Son tasas nominales anuales, no el costo financiero total.'});
}
function ipomMora(main) {
  if(!S(I('mora_total')).length){ampNota(main,'No hay datos de morosidad disponibles. Revisá el estado de las fuentes al pie.');return;}
  ampIntro(main,'Morosidad del crédito bancario','Cartera irregular como porcentaje de las financiaciones. Último dato: '+mesCorto(ult(I('mora_total'))[0])+', sujeto a revisión.');
  const g=grilla(main);
  icard(g,'Cartera irregular: familias, empresas y total','Porcentaje del saldo de financiaciones · Sistema financiero',[iser('mora_familias','Familias'),iser('mora_empresas','Empresas','naranja'),iser('mora_total','Total','gris')],{ancha:true,dec:2});
}
function ipomFinanciamiento(main) {
  ampIntro(main,'Financiamiento en el mercado de capitales','Montos financiados durante cada mes según la CNV. Son flujos en pesos corrientes; no representan saldos de deuda ni crecimiento en términos reales. PyME está incluido en el total del mercado.');
  const g=grilla(main);
  icard(g,'Financiamiento total y PyME','Billones de pesos corrientes por mes · No sumar ambas series',[iser('cnv_total','Total del mercado','azul',{escala:1e-6}),iser('cnv_pyme_total','PyME','naranja',{escala:1e-6})],{dec:2,explicacion:'Montos mensuales publicados por CNV en millones de pesos corrientes, convertidos a billones para el gráfico (división por 1.000.000). El financiamiento PyME es parte del total. No se suman ni se apilan. Total desde enero de 2025; PyME desde febrero de 2015. No se deflactan montos ni se convierten monedas con un tipo de cambio propio.'});
  const card=icard(g,'Financiamiento PyME por instrumento','Billones de pesos corrientes por mes',[iser('cnv_pyme_on','Obligaciones negociables','azul',{escala:1e-6})],{dec:2,explicacion:'Apertura oficial del financiamiento PyME: obligaciones negociables, fideicomisos financieros, cheques de pago diferido avalados y directos, pagarés y facturas de crédito electrónicas. Los seis componentes concilian con el total mensual. Se muestra un instrumento por vez para facilitar la lectura y la descarga.'});
  if(!card)return;
  const label=document.createElement('label');label.className='amp-selector';label.textContent='Instrumento: ';
  const select=document.createElement('select');select.setAttribute('aria-label','Instrumento de financiamiento PyME');
  const opciones=[['on','Obligaciones negociables'],['ff','Fideicomisos financieros'],['cpd_avalados','Cheques avalados'],['cpd_directos','Cheques directos'],['pagares','Pagarés'],['fce','Facturas de crédito electrónicas']];
  opciones.forEach(([k,n])=>{const o=document.createElement('option');o.value=k;o.textContent=n;select.append(o);});
  const original=card._redibujar;
  select.onchange=()=>{const s=card.querySelector('.chart')._cfg.series[0];s.v=I('cnv_pyme_'+select.value);s.nombre=opciones.find(p=>p[0]===select.value)[1];original();};
  label.append(select);card.querySelector('.bajada').after(label);
  ampNota(main,'Los montos conservan el tratamiento de la CNV. La historia del total comienza en 2025; la de PyME, en 2015. El selector del gráfico permite consultar cada instrumento sin confundirlo con un saldo bancario.');
}
function instalarIPOM() {
  for (const [id,fn] of [['internacional',ipomInternacional],['tasas',ipomTasas],['dinero',ipomMora]]) {
    const s=SECCIONES.find(s=>s.id===id), previo=s.armar;
    s.armar=main=>{fn(main);previo(main);};
  }
  SECCIONES.splice(SECCIONES.findIndex(s=>s.id==='internacional'),0,{id:'comercio',nombre:'Comercio exterior',armar:ipomComercio});
  SECCIONES.splice(SECCIONES.findIndex(s=>s.id==='dinero')+1,0,{id:'financiamiento',nombre:'Financiamiento CNV',armar:ipomFinanciamiento});
}
function ipomEstado() {
  if(!D.ipom)return;
  const panel=document.getElementById('estado');
  const h=document.createElement('h3');h.textContent='Brasil, EE.UU., comercio y financiamiento: cobertura';panel.append(h);
  const wrap=document.createElement('div');wrap.className='amp-scroll';panel.append(wrap);
  const keys=['br_ibc','br_industria','fed_piso','pce_general_ia','expo_cantidad','impo_cantidad','terminos_intercambio','tasa_adelantos_mensual','tasa_personales_diaria','mora_total','cnv_total','cnv_pyme_total'];
  ampTabla(wrap,['Serie','Desde','Hasta','Observaciones'],keys.filter(k=>S(I(k)).length).map(k=>[meta(I(k)).n,S(I(k))[0][0],ult(I(k))[0],String(S(I(k)).length)]));
}
