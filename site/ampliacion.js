/* Flujos de reservas, liquidez y empleo/ingresos. Actualización mediante pipeline/ampliacion.py. */
'use strict';

const AMP_BCRA = 'Fuente: <a href="https://www.bcra.gob.ar/estadisticas-e-indicadores/" target="_blank" rel="noopener">BCRA</a>, series monetarias diarias. Fechas de observación indicadas en cada gráfico.';
const A = (k) => 'amp_' + k;
const as = (k,nombre,color='azul',tipo='line') => ({v:A(k),nombre,color,tipo});
function ampHasta(nombre) {return D.ampliacion?.cobertura?.[nombre]?.hasta || ult(A(nombre==='reservas'?'b77':'b46'))[0];}
function ampCorte(nombre) {const f=ampHasta(nombre);return f?'Último acumulado: '+mesCorto(f)+' (datos hasta '+fechaCorta(f)+')':'Sin datos publicados.';}
function ampDisponible(main,variables) {
  if(variables.every(v=>S(A(v)).length))return true;
  ampIntro(main,'Datos adicionales no disponibles','La última actualización no pudo completar las fuentes necesarias para este bloque. Revisá el estado de las fuentes al pie.');
  return false;
}

function ampIntro(main,titulo,texto) {
  const el=document.createElement('div'); el.className='amp-intro';
  el.innerHTML=`<h2>${titulo}</h2><p>${texto}</p>`; main.append(el);
}
function ampNota(main,texto) {const el=document.createElement('p'); el.className='amp-nota'; el.innerHTML=texto; main.append(el);}
function ampTabla(el,heads,rows) {
  el.style.height='auto'; el.classList.add('amp-scroll');
  el.innerHTML=`<table class="tabla"><thead><tr>${heads.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map((c,i)=>i?`<td>${c}</td>`:`<th scope="row">${c}</th>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function ampMeses(el,series,total) {
  el.style.height='auto';
  const fechas=S(A(total)).map(p=>p[0]); const label=document.createElement('label');label.className='amp-selector';label.textContent='Mes: ';
  const select=document.createElement('select'); select.setAttribute('aria-label','Mes del detalle');
  fechas.slice().reverse().forEach(f=>{const o=document.createElement('option');o.value=f;o.textContent=mesCorto(f)+(f===fechas.at(-1)?' · hasta '+fechaCorta(ampHasta(total==='m77'?'reservas':'base')):'');select.append(o);});
  select.value=fechas.filter(f=>f<hoy().slice(0,7)+'-01').at(-1)||fechas.at(-1); label.append(select);el.append(label);
  const lectura=document.createElement('p');lectura.className='amp-nota';if(total==='m77')el.append(lectura);
  const wrap=document.createElement('div');el.append(wrap);
  const draw=()=>{
    if(total==='m77'){
      const compras=new Map(S(A('m78'))).get(select.value), cambio=new Map(S(A(total))).get(select.value);
      lectura.textContent=`En ${mesCorto(select.value)}${select.value===fechas.at(-1)?' (hasta '+fechaCorta(ampHasta('reservas'))+')':''}, las compras netas de divisas fueron USD ${fmt(compras)} millones y las reservas brutas ${cambio<0?'bajaron':'aumentaron'} USD ${fmt(Math.abs(cambio))} millones. La tabla muestra todos los movimientos que forman ese cambio total.`;
    }
    ampTabla(wrap,['Movimiento',total==='m77'?'Millones de USD':'Millones de pesos'],[...series,[total,'Cambio total de las reservas brutas']].map(([k,n])=>{
      const v=new Map(S(A(k))).get(select.value);
      return [k===total&&total!=='m77'?'Variación total publicada':n,fmtS(Math.abs(v)<0.005?0:v,2)];
    }));
  };
  select.onchange=draw;draw();
}
function ampReservas(main) {
  if(!ampDisponible(main,['m77','m78','m79','m80','m81','m82']))return;
  ampIntro(main,'Por qué cambian las reservas brutas','Comprar dólares aumenta las reservas, pero al mismo tiempo hay otros movimientos que pueden aumentarlas o reducirlas: operaciones con organismos internacionales, del sector público y cambios en los encajes de los bancos. Este bloque suma esos movimientos para explicar cuánto cambiaron las reservas en cada mes.');
  ampNota(main,'La presentación de Werning del BCRA del 5 de octubre de 2026 (página 5) sirve como referencia conceptual. Los valores se calculan con las series diarias oficiales del BCRA, sumadas por mes; no se transcribieron del gráfico de la presentación. '+ampCorte('reservas'));
  const g=grilla(main);
  tarjeta(g,{titulo:'Compras de divisas y variación de reservas',bajada:'Sumas mensuales · Millones de USD · '+ampCorte('reservas'),mide:'amp_reservas',fuente:AMP_BCRA,mensual:true,leyenda:true,cero:true,ancha:true,series:[as('m77','Variación de reservas'),as('m78','Compras de divisas','naranja','bar')]});
  tarjeta(g,{titulo:'Qué hizo subir o bajar las reservas en el mes',bajada:'Elegí un mes. Los valores positivos suman reservas y los negativos las reducen; la última fila muestra el resultado de todos los movimientos.',fuente:AMP_BCRA,sinRango:true,mide:'amp_reservas',render:el=>ampMeses(el,[['m78','Compras netas de divisas'],['m79','Operaciones con organismos internacionales'],['m80','Otras operaciones del sector público'],['m81','Efectivo mínimo (encajes de los bancos)'],['m82','Otros factores publicados por el BCRA'],['reservas_diferencia','Diferencia por redondeo']],'m77')});
  tarjeta(g,{titulo:'Organismos, sector público y efectivo mínimo',bajada:'Sumas mensuales · Millones de USD · '+ampCorte('reservas'),fuente:AMP_BCRA,mensual:true,leyenda:true,cero:true,series:[as('m79','Organismos'),as('m80','Sector público','naranja'),as('m81','Efectivo mínimo','verde')]});
  ampNota(main,'La suma de estos movimientos reproduce el cambio de las reservas brutas, salvo diferencias pequeñas de redondeo. “Otros factores” conserva la categoría del BCRA: no se supone que todo sea efecto de la valuación del oro o de las monedas. Las reservas netas y las súper netas siguen calculándose con la metodología que ya tenía el tablero.');
}
function ampLiquidez(main) {
  if(!ampDisponible(main,['liquidez','b44','b7','m46']))return;
  ampIntro(main,'Liquidez bancaria y movimientos de pesos','La cuenta corriente de los bancos en el BCRA, las tasas de depósitos y los factores de la base monetaria se muestran por separado. Su evolución conjunta permite seguir el mercado sin atribuir causalidad a una coincidencia.');
  const g=grilla(main);
  tarjeta(g,{titulo:'Cuenta corriente bancaria respecto de los depósitos',bajada:'Cuenta corriente en el BCRA / depósitos en pesos × 100 · Fechas comunes',fuente:AMP_BCRA,mide:'amp_liquidez',leyenda:true,dec:1,series:[as('liquidez','Ratio observado')]});
  tarjeta(g,{titulo:'Tasas de depósitos mayoristas',bajada:'Tasa nominal anual (%) · TAMAR: '+fechaCorta(ult(A('b44'))[0])+' · BADLAR: '+fechaCorta(ult(A('b7'))[0]),fuente:AMP_BCRA,leyenda:true,dec:1,series:[as('b44','TAMAR'),as('b7','BADLAR','naranja')]});
  tarjeta(g,{titulo:'Factores de variación de la base monetaria',bajada:'Sumas mensuales · Billones de pesos corrientes · '+ampCorte('base'),mide:'amp_base',fuente:AMP_BCRA,mensual:true,leyenda:true,cero:true,ancha:true,dec:2,series:[{...as('m47','Divisas privadas','azul','bar'),escala:1e-6,stack:'base'},{...as('base_tesoro','Tesoro','naranja','bar'),escala:1e-6,stack:'base'},{...as('base_instrumentos','Instrumentos','gris','bar'),escala:1e-6,stack:'base'},{...as('m59','Otros','verde','bar'),escala:1e-6,stack:'base'},{...as('m46','Total','violeta'),escala:1e-6}]});
  tarjeta(g,{titulo:'Detalle de los movimientos de pesos',bajada:'Millones de pesos corrientes. Un valor negativo indica absorción.',fuente:AMP_BCRA,mide:'amp_base',sinRango:true,ancha:true,render:el=>ampMeses(el,[['m47','Compra de divisas al sector privado y otros'],['base_tesoro','Operaciones con el Tesoro'],['base_instrumentos','Instrumentos y operaciones del BCRA'],['m59','Otras operaciones'],['base_diferencia','Diferencia de conciliación (redondeo)']],'m46')});
}
function ampEmpleo(main) {
  if(!ampDisponible(main,['empleo_privado_desest','salario_privado','salario_publico','credito_real_117']))return;
  ampIntro(main,'Empleo, salarios y crédito','Cada serie conserva su fecha y su universo. Empleo registrado: '+mesCorto(ult(A('empleo_privado_desest'))[0])+'; salarios registrados: '+mesCorto(ult(A('salario_privado'))[0])+'; crédito real: '+mesCorto(ult(A('credito_real_117'))[0])+'. No se estiman meses sin publicación.');
  const g=grilla(main);
  tarjeta(g,{titulo:'Empleo asalariado privado registrado',bajada:'Miles de personas · Serie desestacionalizada oficial · Datos recientes provisorios',fuente:'Fuente: <a href="https://www.argentina.gob.ar/trabajo/estadisticas/situacion-y-evolucion-del-trabajo-registrado">Secretaría de Trabajo, SIPA</a>, cuadro T.2.2.',mide:'amp_empleo',mensual:true,leyenda:true,series:[as('empleo_privado_desest','Asalariados privados')]});
  tarjeta(g,{titulo:'Salarios registrados en términos reales',bajada:'Índice dic-2023 = 100 · Deflactado por el IPC nacional del mismo mes',fuente:'Fuente: <a href="https://www.indec.gob.ar/Nivel4/Tema/4/31/61">INDEC, índice de salarios e IPC</a>.',mide:'amp_salarios',mensual:true,leyenda:true,dec:1,series:[as('salario_privado','Privado registrado'),as('salario_publico','Público','naranja')]});
  const lineas=[[110,'Adelantos'],[111,'Documentos'],[112,'Hipotecarios'],[113,'Prendarios'],[114,'Personales'],[115,'Tarjetas'],[116,'Otros']];
  const card=tarjeta(g,{titulo:'Crédito en pesos por línea',bajada:'Índice real dic-2023 = 100 · Promedio mensual de saldos / IPC',fuente:AMP_BCRA+' IPC nacional: INDEC.',mide:'amp_credito',mensual:true,conRango:true,ancha:true,render:(el,card)=>{const id=card.dataset.linea||'114';grafico(el,{mensual:true,leyenda:true,dec:1,series:[as('credito_real_'+id,lineas.find(x=>String(x[0])===id)[1]),as('credito_real_117','Total privado en pesos','gris')]});}});
  const label=document.createElement('label');label.className='amp-selector';label.textContent='Línea de crédito: ';
  const sel=document.createElement('select');sel.setAttribute('aria-label','Línea de crédito');lineas.forEach(([id,n])=>{const o=document.createElement('option');o.value=id;o.textContent=n;sel.append(o);});sel.value='114';sel.onchange=()=>{card.dataset.linea=sel.value;card._redibujar();};label.append(sel);card.querySelector('.bajada').after(label);
  ampNota(main,'La línea crediticia describe el producto financiero; no identifica por sí sola el destino final del préstamo. Los salarios reales comparan índices, no niveles de remuneración entre sectores. No se estiman los meses todavía no publicados.');
}
function instalarAmpliacion() {
  Object.assign(MIDE,{
    amp_reservas:'BCRA, variables 77 a 82: variación diaria de saldos, compras de divisas, organismos internacionales, otras operaciones del sector público, efectivo mínimo y otros factores. Se usan exclusivamente fechas comunes y se suman los flujos por mes. El último mes se muestra hasta la fecha publicada. El residuo se muestra como diferencia de conciliación, sin asignarle una causa económica.',
    amp_liquidez:'Ratio descriptivo: depósitos de entidades en cuenta corriente en el BCRA (serie 19) / depósitos en pesos de los sectores público y privado no financieros (serie 91) × 100. Se cruzan fechas exactas. No es la liquidez total del sistema ni el excedente sobre la exigencia de encajes; no mide fondos de libre disponibilidad.',
    amp_base:'Flujos nominales de la base monetaria. Divisas privadas: serie 47. Tesoro: series 48 a 51 (divisas, adelantos transitorios, utilidades y otras operaciones). Instrumentos: series 52 a 58 (pases, letras, redescuentos, intereses, cuasimonedas y LEFI). Otros: serie 59. Total: serie 46. Positivo: expansión; negativo: absorción. Son movimientos contables, sin estimar una regla de reacción del BCRA.',
    amp_empleo:'Personas con empleo asalariado privado registrado, según modalidad ocupacional principal del SIPA. Se emplea el ajuste estacional oficial del cuadro T.2.2. No se extrapolan meses faltantes. Datos recientes provisorios.',
    amp_salarios:'Índices de salarios del sector privado registrado y público divididos por el IPC nacional del mismo mes. Se normaliza el cociente a diciembre de 2023 = 100. Solo se incluyen meses observados en ambas fuentes. No se utiliza el salario no registrado para evitar mezclar sus rezagos.',
    amp_credito:'Préstamos en pesos al sector privado, BCRA series 110 a 117. Se promedian saldos diarios observados en cada mes completo, se divide por el IPC nacional mensual y se normaliza a diciembre de 2023 = 100. No son nuevas originaciones. No se imputa inflación al mes en curso.'
  });
  SECCIONES.splice(SECCIONES.findIndex(s=>s.id==='dinero')+1,0,{id:'liquidez',nombre:'Liquidez',armar:ampLiquidez});
  SECCIONES.splice(SECCIONES.findIndex(s=>s.id==='actividad')+1,0,{id:'empleo-ingresos',nombre:'Empleo e ingresos',armar:ampEmpleo});
}
