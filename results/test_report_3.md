## assets/boletin-diario-service-B5YzYwVE.js
mercado/extractooperaciones
mercado/titulo/boletindiario/volumennegociado
--- ctx ---
import{af as o}from"./index-DseC26QM.js";class e{static GetBoletinDiario=e=>o.get(""==e.fechaDesde?"mercado/extractooperaciones":`mercado/extractooperaciones?oTitulo=${JSON.stringify(e)}`);static GetVentas=(e,t)=>o.get(""==t.fechaDesde?"merca
...
do/extractooperaciones?oTitulo=${JSON.stringify(e)}`);static GetVentas=(e,t)=>o.get(""==t.fechaDesde?"mercado/titulo/boletindiario/volumennegociado":`mercado/titulo/boletindiario/volumennegociado${e}?oTitulo=${JSON.stringify(t)}`);static GetDet
...
/volumennegociado${e}?oTitulo=${JSON.stringify(t)}`);static GetDetails=(e,t)=>o.get(`mercado/titulo/boletindiario/volumennegociadodetalle${e}?oTitulo=${JSON.stringify(t)}`)}export{e as B};


## assets/cauciones-DXQgoFr0.js

--- ctx ---


## assets/cauciones-az370nHs.js
/cauciones/historico
--- ctx ---


## assets/caucionesWidgets-ClADJlb0.js
mercado/titulo/forexofertas
--- ctx ---
BRMP4yJl.js";import"./recharts-C_K9jEUK.js";class c{static GetOffersForex=()=>o.get("mercado/titulo/forexofertas");static GetEspeciePlazos=e=>o.get(`mercado/especieplazos?oTitulo=${JSON.stringify({codTitulo:e})}`)}const n=[{field:"cantidadCompr
...
fersForex=()=>o.get("mercado/titulo/forexofertas");static GetEspeciePlazos=e=>o.get(`mercado/especieplazos?oTitulo=${JSON.stringify({codTitulo:e})}`)}const n=[{field:"cantidadCompra",headerName:"Cantidad Tom.",cell:t,align:"right"},{field:"prec

## assets/forex-Da8JMbkm.js

--- ctx ---


## assets/forex-wSJsBhYg.js
/forex/historico
--- ctx ---


## assets/forexWidgets-DaqcBe6J.js

--- ctx ---


## assets/historicARS-gvaZ2bl9.js

--- ctx ---
ate(u);return t.useEffect(()=>{(async()=>{l(""),i(!0),r([]);try{const t=await d.get(`mercado/titulo/indicearsmae/historico?oTitulo=${JSON.stringify(f)}`);r(t)}catch(t){if(t instanceof m)return void l(t.message);l("No hay Datos Históricos")}fina

## assets/history-service-CA9Ln2Wy.js
mercado/equivalenciascontrato
--- ctx ---
t{t as a}from"./download-CXfJiEGB.js";class o{static GetHistoricData=(e,a,o)=>t.get(`mercado/titulo/historico${i[e].slice(1)}?oTitulo=${JSON.stringify({fechaDesde:a,fechaHasta:o})}`);static GetHistoricDataWithFilters=(e,a)=>t.get(`mercado/titul
...
gify({fechaDesde:a,fechaHasta:o})}`);static GetHistoricDataWithFilters=(e,a)=>t.get(`mercado/titulo/historico${i[e].slice(1)}?oTitulo=${JSON.stringify(a)}`);static GetHistoricDataPaged=(e,a,o=0,s=10,r)=>{const c={...a,skip:o,take:s};return t.ge
...
c GetHistoricDataPaged=(e,a,o=0,s=10,r)=>{const c={...a,skip:o,take:s};return t.get(`mercado/titulo/historico${i[e].slice(1)}?oTitulo=${JSON.stringify(c)}`,{signal:r})};static GetHistoricChart=(e,a)=>t.get(`mercado/titulo/historico${i[e].slice(
...
1)}?oTitulo=${JSON.stringify(c)}`,{signal:r})};static GetHistoricChart=(e,a)=>t.get(`mercado/titulo/historico${i[e].slice(1)}/grafico?oTitulo=${JSON.stringify(a)}`);static GetHistoricDataDetails=(i,e,a=0,o=10,s)=>{const r={fecha:i,...e,skip:a,t
...
ricDataDetails=(i,e,a=0,o=10,s)=>{const r={fecha:i,...e,skip:a,take:o};return t.get(`mercado/titulo/historicorentafija/detalle?oTitulo=${JSON.stringify(r)}`,{signal:s})};static GetHistoricForexVolumenOperadoWithFilters=(e,a)=>t.get(`mercado/tit
...
ify(r)}`,{signal:s})};static GetHistoricForexVolumenOperadoWithFilters=(e,a)=>t.get(`mercado/titulo/historico${i[e].slice(1)}/volumenoperado?oTitulo=${JSON.stringify(a)}`);static GetLastOpenDate=()=>t.get(`mercado/fechahabilanterior?fecha=${e()
...
(1)}/volumenoperado?oTitulo=${JSON.stringify(a)}`);static GetLastOpenDate=()=>t.get(`mercado/fechahabilanterior?fecha=${e()}`);static GetTasaImplicitaChartPoints=i=>t.get(`mercado/tasaimplicita?oTitulo=${JSON.stringify({tipoNegociacion:"F",fech
...
rcado/fechahabilanterior?fecha=${e()}`);static GetTasaImplicitaChartPoints=i=>t.get(`mercado/tasaimplicita?oTitulo=${JSON.stringify({tipoNegociacion:"F",fecha:i})}`);static GetOffersData=(e,a)=>t.get(`mercado${i[e]}/ofertasgrafico?oTitulo=${JSO

## assets/index-B69H88mC.js
usuario/registrar
usuarios/${e}
--- ctx ---
a:o.getUsuarioAuditoria};class P{static async getUsuarios(){try{const e=await g.get("usuarios");if(Array.isArray(e))return e;throw new Error("La respuesta no es un array de usuarios")}catch(e){throw e}}static CreateUsuario=e=>g.post("usuario/re

## assets/index-B87Kz1hY.js

--- ctx ---


## assets/index-BU5MzBZ9.js
/administrador/banners
/comunicados/todos
text/css
--- ctx ---


## assets/index-BZRTA_bo.js
mercado/resoluciones
--- ctx ---
alue:a.origen,onChange:o,options:g})]})}class x{static GetResoluciones=(e,a)=>i.get(""==e.fechaDesde?"mercado/resoluciones":`mercado/resoluciones?oTitulo=${JSON.stringify(e)}&origen=${a}`)}function C(){const{items:o,dataState:r,dateFilters:i,lo

## assets/index-Ba5El3gv.js

--- ctx ---


## assets/index-C0XQFMeX.js

--- ctx ---


## assets/index-C0ex5s_0.js

--- ctx ---
=>"string"==typeof e.field).map(e=>[e.field,e.width]));r(e=>e.map(e=>{const s=a.get(e.field);return"number"==typeof s?{...e,width:s}:e}))},[]),{tipo:f}=A(),{fci:g,fciAll:b,dataState:y,filters:v,options:C,loading:N,error:w,fecha:M,handleDataStat

## assets/index-C1azI-0Z.js

--- ctx ---


## assets/index-C4pjiw2q.js

--- ctx ---


## assets/index-C5uR3ljw.js

--- ctx ---
sta",e)})]})}const E=e=>{const a=encodeURIComponent(JSON.stringify(e));return h.get(`mercado/operaciones-totales-terceros-titulo-detalle?oData=${a}`)},O=e=>{const a=(...a)=>{for(const t of a){const a=e[t];if(null!=a)return Number(a)}return 0},t
...
}),d=a.useCallback(async(a,t)=>{const n=`${e}|${a}|${t}`;if(M.has(n)){const e=M.get(n);return o(e.data),void r(e.total)}s(!0),o([]);try{const l=await E({fechaDesde:e,fechaHasta:e,soloTotales:!0,skip:a,take:t}),s=l.data.map(O);M.set(n,{data:s,to
...
]);try{const e=await(e=>{const a=encodeURIComponent(JSON.stringify(e));return h.get(`mercado/operaciones-totales-terceros-titulo-fechas?oData=${a}`)})({fechaDesde:y.fechaDesde,fechaHasta:y.fechaHasta});r(e)}catch(e){if(e instanceof m)return voi
...
ck(async(e,a,o,n,r)=>{const l=`${e}|${a}|${o}|${n}|${r}`;if(F.has(l)){const e=F.get(l);return s(e.data),void t(e.total)}p(!0),s([]);try{const i=await E({fechaDesde:e,fechaHasta:e,codNegociacion:a,titulo:o,skip:n,take:r}),c=i.data.map(O);F.set(l

## assets/index-C80N3f95.js
mercado/precioreferenciaoct
--- ctx ---
",onChange:e=>o("fechaHasta",e)})]})}class D{static GetPrecioReferenciaOCT=e=>i.get(""==e.fechaDesde?"mercado/precioreferenciaoct":`mercado/precioreferenciaoct?oTitulo=${JSON.stringify(e)}`)}function C(){const[s,o]=a.useState(y),i=a.useCallback
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));o(e=>e.map(e=>{const t=a.get(e.field);return"number"==typeof t?{...e,width:t}:e}))},[]),{items:l,dataState:f,dateFilters:m,loading:h,error:p,handleDataStateChange:C,handleDateChange:S}=(()=

## assets/index-CBBygn_N.js
dd/MM/y
w-1/3
--- ctx ---


## assets/index-CH5yj6Ne.js

--- ctx ---
(!Y)return e.width;const t=fe?.[String(e.field)];return void 0!==t?t:Me?.widths.get(String(e.field))??e.width},_e=(()=>{if(!Y||null===ce)return"";const e=[];let t=0,r=0;for(let n=ie.length-1;n>=0;n--){const l=ie[n];if(!l.sticky)break;r++;const 

## assets/index-CHlL-qZW.js

--- ctx ---
ait((e,a,t)=>{const i=R(e,a,t),n=encodeURIComponent(JSON.stringify(i));return g.get(`mercado/resumen-operaciones-oct?oData=${n}`)})(C.fechaDesde,C.fechaHasta,S||void 0)).map(q);i(e)}catch(e){if(e instanceof j)return void h(e.message);h("Error a
...
((e,a)=>{const t=R(e,a,void 0),i=encodeURIComponent(JSON.stringify(t));return g.get(`mercado/resumen-operaciones-oct-detalle?oData=${i}`)})(e,e)).map(V);l(a),k(!0)}catch{h("Error al obtener el detalle de operaciones OCT")}finally{s(!1),setTimeo

## assets/index-CJReWJHx.js

--- ctx ---


## assets/index-CNcfcZFl.js
dd/MM/y
--- ctx ---
dren:a.jsx(v,{className:"h-5 w-5"})})})]})}class F{static GetPreciosCierre=e=>h.get(`mercado/historico/preciocierre?oTitulo=${JSON.stringify(e)}`)}function H(){const[r,i]=e.useState(N),o=e.useCallback(e=>{const a=new Map(e.columns.filter(e=>"st
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));i(e=>e.map(e=>{const t=a.get(e.field);return"number"==typeof t?{...e,width:t}:e}))},[]),{preciosCierre:n,dataState:d,filters:p,statusFilters:m,loading:u,error:f,handleDataStateChange:h,hand

## assets/index-CcQzftQK.js
agro/totales/${e}
agro/volumen-categoria/${e}
agro/volumen-producto/${e}
agro/volumenpormes
--- ctx ---
peed:1.5,disableNavigation:!1,size:"lg"})}class B{static GetVolumenPorMes=()=>r.get("agro/volumenpormes");static GetTotalesPorPeriodo=e=>r.get(`agro/totales/${e}`);static GetTotalsCategoria=e=>r.get(`agro/volumen-categoria/${e}`);static GetTota
...
tVolumenPorMes=()=>r.get("agro/volumenpormes");static GetTotalesPorPeriodo=e=>r.get(`agro/totales/${e}`);static GetTotalsCategoria=e=>r.get(`agro/volumen-categoria/${e}`);static GetTotalsCategoriaPorProducto=e=>r.get(`agro/volumen-producto/${e}
...
tTotalesPorPeriodo=e=>r.get(`agro/totales/${e}`);static GetTotalsCategoria=e=>r.get(`agro/volumen-categoria/${e}`);static GetTotalsCategoriaPorProducto=e=>r.get(`agro/volumen-producto/${e}`)}function z({className:a,titulo:t="Totales por product
...
>r.get(`agro/volumen-categoria/${e}`);static GetTotalsCategoriaPorProducto=e=>r.get(`agro/volumen-producto/${e}`)}function z({className:a,titulo:t="Totales por producto",periodo:r="Month"}){const{agroPeriodTotal:o,loading:i}=(s=>{const[a,t]=e.u

## assets/index-CgsIfrUd.js
/comunicados/todos
/licitaciones/Todos
basis-1/2
dd/MM/y
w-1/3
--- ctx ---
s","Contado"],c=Array.from(i.reduce((e,s)=>(e.has(s.grupo)||e.set(s.grupo,[]),e.get(s.grupo).push(s),e),new Map)).sort(([e],[s])=>o.indexOf(e)-o.indexOf(s)).map(([e,s])=>[e,[...s].sort((e,s)=>(e.orden??0)-(s.orden??0))]);return e.jsxs(y,{classN

## assets/index-ClVicGIH.js

--- ctx ---


## assets/index-Clvr2R35.js
administrador/banners
administrador/banners${t}
administrador/banners/${e}
dd/MM/yyyy
--- ctx ---
eys(e).length>0?`?oTitulo=${encodeURIComponent(JSON.stringify(e))}`:"";return r.get(`administrador/banners${t}`)};static CreateBanner=e=>r.post("administrador/banners",e);static UpdateBanner=(e,t)=>r.patch(`administrador/banners/${e}`,t);static

## assets/index-Cox2sCLF.js

--- ctx ---


## assets/index-Cw3U_dpm.js

--- ctx ---


## assets/index-CwgGD0e6.js

--- ctx ---
);try{const e=(await(e=>{const a=encodeURIComponent(JSON.stringify(e));return m.get(`mercado/operaciones-totales-titulo?oData=${a}`)})({fechaDesde:N.fechaDesde,fechaHasta:N.fechaHasta,titulo:y})).map(_);o(e)}catch(e){if(e instanceof f)return vo
...
);try{const a=(await(e=>{const a=encodeURIComponent(JSON.stringify(e));return m.get(`mercado/operaciones-totales-titulo-detalle?oData=${a}`)})({fechaDesde:e,fechaHasta:e,titulo:""})).map(b);i(a),A(!0)}catch{p("Error al obtener el detalle de ope

## assets/index-Cy40cC6D.js

--- ctx ---


## assets/index-DCGmrtMC.js
mercado/circulares-oct
--- ctx ---
"Hasta",onChange:e=>o("fechaHasta",e)})]})}class g{static GetCircularesOCT=e=>i.get(""==e.fechaDesde?"mercado/circulares-oct":`mercado/circulares-oct?oTitulo=${JSON.stringify(e)}`)}function C(){const{items:r,dataState:o,dateFilters:i,loading:l,

## assets/index-DE73Fx7S.js
/comunicados/garantizados
/comunicados/mae
/comunicados/todos
--- ctx ---
xact:!0}},N={fechaDesde:i(0,-1),fechaHasta:i()};class b{static GetReleases=e=>n.get(`institucional/comunicados?oTitulo=${JSON.stringify(e)}`)}function w({dateFilters:e,filters:t,options:o,loading:s,filterTipo:r,onChange:i,onDateChange:n}){const

## assets/index-DIMLjeZU.js

--- ctx ---
e?.point?.y<0?s.dataByIndex(Number.MAX_SAFE_INTEGER,i.NearestLeft):e.seriesData.get(s);_(t?e=>({...e,element:t,variation:t.close-t.open?t.close-t.open:0,variationPctg:t.close-t.open?(t.close-t.open)/t.open*100:0}):void 0)},a=(e,s)=>{if(!e||!s)r
...
oint?.x<0||e?.point?.y<0?s.dataByIndex(Number.MAX_SAFE_INTEGER,-1):e.seriesData.get(s);_(t?e=>({...e,volume:t}):void 0)};e.timeScale().fitContent(),n.filter(e=>e.points?.length>0&&!B[e.name]).forEach(t=>{f(t.points,t.type).forEach(r=>{let i;swi

## assets/index-DIvTquFE.js

--- ctx ---


## assets/index-DPcCCJJl.js

--- ctx ---


## assets/index-DQym66lx.js

--- ctx ---
lYear(),s.getMonth()+1,0);a.fechaHasta=u(e,"yyyy-MM-dd")}return a})(e);return l.get(`mercado/estadisticas?data=${encodeURIComponent(JSON.stringify(a))}`).then(e=>e?(Array.isArray(e)?e:e.data&&Array.isArray(e.data)?e.data:[]).map(e=>{const a=e.I

## assets/index-DR6tSTbE.js
usuario/reenviarAPIKey
usuario/registrarAPI
--- ctx ---


## assets/index-DWnDpIvj.js
dd/MM/yyyy
--- ctx ---


## assets/index-DdgLO_yg.js
mercado/pagoamortizrenta
--- ctx ---
sta",onChange:e=>o("fechaHasta",e)})]})}class D{static GetPagoAmortizRenta=e=>i.get(""==e.fechaDesde?"mercado/pagoamortizrenta":`mercado/pagoamortizrenta?oTitulo=${JSON.stringify(e)}`)}function S(){const[r,o]=a.useState(u),i=a.useCallback(e=>{c
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));o(e=>e.map(e=>{const t=a.get(e.field);return"number"==typeof t?{...e,width:t}:e}))},[]),{items:l,dataState:c,dateFilters:f,loading:h,error:p,handleDataStateChange:S,handleDateChange:M}=(()=

## assets/index-DmuDj1Wt.js
/boletindiario/extracto-operaciones
/boletindiario/ventas-terceros
/boletindiario/ventas-totales
/comunicados/todos
--- ctx ---


## assets/index-DpK5IWEa.js
mercado/circulares
--- ctx ---
el:"Hasta",onChange:e=>o("fechaHasta",e)})]})}class g{static GetCirculares=e=>i.get(""==e.fechaDesde?"mercado/circulares":`mercado/circulares?oTitulo=${JSON.stringify(e)}`)}function S(){const{items:r,dataState:o,dateFilters:i,loading:l,error:m,

## assets/index-DvZuea1J.js

--- ctx ---


## assets/index-WOEoYlUe.js
/api/
--- ctx ---
,align:"right",grupo:"Acumulado Previo",cell:D}];class Q{static GetRanking=e=>u.get(`mercado/ranking/getranking?data=${encodeURIComponent(JSON.stringify(e))}`);static GetTiposRanking=e=>u.get(`mercado/ranking/gettiporanking?data=${encodeURIComp
...
ing?data=${encodeURIComponent(JSON.stringify(e))}`);static GetTiposRanking=e=>u.get(`mercado/ranking/gettiporanking?data=${encodeURIComponent(JSON.stringify(e))}`);static DownloadRanking=async e=>{try{const a=m.BASE_URL||"/api/",i=`${a.endsWith
...
rcado/ranking/getranking?data=${encodeURIComponent(JSON.stringify(e))}`,t=await fetch(i,{method:"GET",credentials:"include"});if(!t.ok)throw new Error(`Error descargando ranking: ${t.status}`);const n=await t.blob(),o=`Ranking_Tipo${e.idRanking}_
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));x(e=>e.map(e=>{const i=a.get(e.field);return"number"==typeof i?{...e,width:i}:e})),j(e=>e.map(e=>{const i=a.get(e.field);return"number"==typeof i?{...e,width:i}:e}))},[]);return e.jsxs(M,{t
...
(e.field);return"number"==typeof i?{...e,width:i}:e})),j(e=>e.map(e=>{const i=a.get(e.field);return"number"==typeof i?{...e,width:i}:e}))},[]);return e.jsxs(M,{title:"Ranking",className:"h-full",children:["2xl"!==b&&"xl"!==b||N?e.jsx(L,{pageabl

## assets/index-WXSPk_Sc.js
mercado/boletin-mpmae
--- ctx ---
:"Hasta",onChange:e=>o("fechaHasta",e)})]})}class D{static GetBoletinMPMAE=e=>n.get(""==e.fechaDesde?"mercado/boletin-mpmae":`mercado/boletin-mpmae?oTitulo=${JSON.stringify(e)}`)}function g(){const{boletinMPMAE:r,dataState:o,dateFilters:n,loadi

## assets/index-ZomMR07u.js
mercado/precioreferenciarepo
--- ctx ---
{fechaDesde:o(0,-1),fechaHasta:o()};class g{static GetPrecioReferenciaRepo=e=>i.get(""==e.fechaDesde?"mercado/precioreferenciarepo":`mercado/precioreferenciarepo?oTitulo=${JSON.stringify(e)}`)}function D({dateFilters:e,loading:t,onDateChange:r,
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));o(e=>e.map(e=>{const t=a.get(e.field);return"number"==typeof t?{...e,width:t}:e}))},[]),{items:l,dataState:f,dateFilters:h,loading:p,error:u,handleDataStateChange:S,handleDateChange:M}=(()=

## assets/index-exp-det-vt-03lX8n1k.js

--- ctx ---


## assets/index-gihrmiEJ.js

--- ctx ---
cio",cell:x,align:"right",width:200}];class R{static GetOperacionesTermino=e=>S.get(`mercado/operaciones-concertadas-termino?oData=${JSON.stringify(e)}`)}const z=e=>{if(e)return`${e.getFullYear()}-${String(e.getMonth()+1).padStart(2,"0")}-${Str

## assets/index-i9Qb_g_h.js

--- ctx ---


## assets/index-wUtgCuzN.js
mercado/inforelevante
--- ctx ---
"Hasta",onChange:e=>n("fechaHasta",e)})]})}class D{static GetInfoRelevante=e=>o.get(""==e.fechaDesde?"mercado/inforelevante":`mercado/inforelevante?oTitulo=${JSON.stringify(e)}`)}function S(){const[r,n]=a.useState(y),o=a.useCallback(e=>{const a
...
=>"string"==typeof e.field).map(e=>[e.field,e.width]));n(e=>e.map(e=>{const t=a.get(e.field);return"number"==typeof t?{...e,width:t}:e}))},[]),{items:c,dataState:f,dateFilters:m,loading:h,error:p,handleDataStateChange:S,handleDateChange:v}=(()=

## assets/index-xUXMyIYU.js

--- ctx ---


## assets/index-yq90uGyC.js

--- ctx ---


## assets/indexARS-BVRbppu7.js
mercado/indiceARS
--- ctx ---
c"}]});return t.useEffect(()=>{(async()=>{m(""),d(!0),s([]);try{const t=await n.get("mercado/indiceARS");s(t)}catch(t){if(t instanceof l)return void m(t.message);m("No se encontraron registros")}finally{d(!1)}})()},[]),t.useEffect(()=>{u(t=>({.