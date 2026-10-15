# Test de fuentes — 2026-10-15T00:28:31.222646Z

## 00. BCRA v4 lista de variables
- estado: 200 | bytes: 347904 | tipo: application/json; charset=utf-8
- muestra: `{"status":200,"metadata":{"resultset":{"count":1610,"offset":0,"limit":1000}},"results":[{"idVariable":1,"descripcion":"Reservas internacionales","categoria":"Principales Variables","tipoSerie":"Saldos","periodicidad":"D","unidadExpresion":"En millones de USD","moneda":"ME","primerFechaInformada":"1996-01-03","ultFechaInformada":"2026-10-09","ultValorInformado":49709.00000000000},{"idVariable":4,"descripcion":"Tipo de cambio minorista (promedio vendedor)","categoria":"Principales Variables","tipoSerie":"Tipo de cambio","periodicidad":"D","unidadExpresion":"Pesos argentinos por dólar estadounid`

## 01. BCRA v4 reservas (id 1)
- estado: 200 | bytes: 656 | tipo: application/json; charset=utf-8
- muestra: `{"status":200,"metadata":{"resultset":{"count":11,"offset":0,"limit":1000}},"results":[{"idVariable":1,"detalle":[{"fecha":"2026-10-09","valor":49709.00000000000},{"fecha":"2026-10-08","valor":49323.00000000000},{"fecha":"2026-10-07","valor":49133.00000000000},{"fecha":"2026-10-06","valor":49125.00000000000},{"fecha":"2026-10-05","valor":48798.00000000000},{"fecha":"2026-10-02","valor":48657.00000000000},{"fecha":"2026-10-01","valor":48288.00000000000},{"fecha":"2026-09-30","valor":46092.00000000000},{"fecha":"2026-09-29","valor":47482.00000000000},{"fecha":"2026-09-28","valor":47960.000000000`

## 02. BCRA cambiarias cotizaciones
- estado: 200 | bytes: 4156 | tipo: application/json; charset=utf-8
- muestra: `{"status":200,"results":{"fecha":"2026-10-14","detalle":[{"codigoMoneda":"ARS","descripcion":"PESO","tipoPase":0.00066100,"tipoCotizacion":0.00000000},{"codigoMoneda":"AUD","descripcion":"DOLAR AUSTRALIA","tipoPase":0.69620000,"tipoCotizacion":1053.35060000},{"codigoMoneda":"AWG","descripcion":"FLORIN (ANTILLAS HOLANDESAS)","tipoPase":0.55865900,"tipoCotizacion":845.25139700},{"codigoMoneda":"BOB","descripcion":"BOLIVIANOS","tipoPase":0.08547000,"tipoCotizacion":129.31623900},{"codigoMoneda":"BRL","descripcion":"REAL","tipoPase":0.19872400,"tipoCotizacion":300.66970100},{"codigoMoneda":"CAD","`

## 03. BCRA series.xlsm
- estado: 200 | bytes: 8005110 | tipo: application/octet-stream
- muestra: `[binario 8005110 bytes]`

## 04. BCRD EMBI xlsx
- estado: 200 | bytes: 972894 | tipo: application/octet-stream
- muestra: `[binario 972894 bytes]`

## 05. BCRP EMBIG Arg/LatAm
- estado: 200 | bytes: 1061 | tipo: text/html; charset=UTF-8
- muestra: `{ "config": { "title":"Tasas de interés: EMBIG (variación en pbs)", "series": [ { "name":"Tasas de interés: EMBIG (variación en pbs) - Spread - EMBIG America Latina (pbs)", "dec":"0" }, { "name":"Tasas de interés: EMBIG (variación en pbs) - Spread - EMBIG Argentina (pbs)", "dec":"0" }] }, "periods": [ { "name":"25.Set.26", "values":["n.d.","n.d."] }, { "name":"28.Set.26", "values":["n.d.","n.d."] }, { "name":"29.Set.26", "values":["n.d.","n.d."] }, { "name":"30.Set.26", "values":["n.d.","n.d."] }, { "name":"01.Oct.26", "values":["n.d.","n.d."] }, { "name":"02.Oct.26", "values":["n.d.","n.d."] `

## 06. ArgentinaDatos riesgo país último
- estado: 200 | bytes: 43 | tipo: application/json; charset=utf-8
- muestra: `{   "valor": 597,   "fecha": "2026-10-13" }`

## 07. ArgentinaDatos dólar MEP
- estado: 200 | bytes: 285991 | tipo: application/json; charset=utf-8
- muestra: `[   {     "casa": "bolsa",     "compra": 36.97,     "venta": 36.97,     "fecha": "2018-10-29"   },   {     "casa": "bolsa",     "compra": 36.63,     "venta": 36.63,     "fecha": "2018-10-30"   },   {     "casa": "bolsa",     "compra": 35.93,     "venta": 35.93,     "fecha": "2018-10-31"   },   {     "casa": "bolsa",     "compra": 35.89,     "venta": 35.89,     "fecha": "2018-11-01"   },   {     "casa": "bolsa",     "compra": 35.66,     "venta": 35.66,     "fecha": "2018-11-02"   },   {     "casa": "bolsa",     "compra": 35.66,     "venta": 35.66,     "fecha": "2018-11-03"   },   {     "casa": `

## 08. ArgentinaDatos dólar CCL
- estado: 200 | bytes: 540857 | tipo: application/json; charset=utf-8
- muestra: `[   {     "casa": "contadoconliqui",     "compra": 6.67,     "venta": 6.67,     "fecha": "2013-01-02"   },   {     "casa": "contadoconliqui",     "compra": 6.68,     "venta": 6.68,     "fecha": "2013-01-03"   },   {     "casa": "contadoconliqui",     "compra": 6.82,     "venta": 6.82,     "fecha": "2013-01-04"   },   {     "casa": "contadoconliqui",     "compra": 6.82,     "venta": 6.82,     "fecha": "2013-01-05"   },   {     "casa": "contadoconliqui",     "compra": 6.82,     "venta": 6.82,     "fecha": "2013-01-06"   },   {     "casa": "contadoconliqui",     "compra": 6.83,     "venta": 6.83,`

## 09. BYMA public-bonds
- estado: 200 | bytes: 124 | tipo: application/json
- muestra: `{"content":{"page_number":1,"page_count":0,"page_size":189,"total_elements_count":0},"data":[],"empty":true,"upgrade":false}`

## 10. BYMA lebacs
- estado: 200 | bytes: 124 | tipo: application/json
- muestra: `{"content":{"page_number":1,"page_count":0,"page_size":189,"total_elements_count":0},"data":[],"empty":true,"upgrade":false}`

## 11. BYMA short-term-government-bonds
- estado: 401 | bytes: 0 | tipo: 
- muestra: `[binario 0 bytes]`

## 12. BYMA cauciones
- estado: 200 | bytes: 49891 | tipo: application/json
- muestra: `[{"tradeVolume":27672422,"symbol":"CABLE-1510-U-CT-EXT","imbalance":0.0,"previousSettlementPrice":0.0,"offerPrice":0.0,"openInterest":0.0,"vwap":0.018123473,"description":"","numberOfOrders":117,"openingPrice":0.025,"tickDirection":-1,"underlyingSymbol":"CABLE","securityDesc":"","securitySubType":"","maturityDate":"2026-10-15","previousClosingPrice":0.0,"settlementType":"1","quantityOffer":0.0,"tradingHighPrice":0.0275,"denominationCcy":"EXT","bidPrice":0.0,"tradingLowPrice":0.005,"market":"BYMA","volumeAmount":27673796.07,"volume":27672422,"trade":0.01,"daysToMaturity":1,"tradeHour":"16:39:57`

## 13. BYMA negociable-obligations
- estado: 200 | bytes: 10404 | tipo: application/json
- muestra: `[{"tradeVolume":0.0,"symbol":"AEC3X","imbalance":0.0,"previousSettlementPrice":156652.0,"offerPrice":0.0,"openInterest":0.0,"vwap":0.0,"description":"","numberOfOrders":0,"openingPrice":0.0,"tickDirection":-1,"securityDesc":"","securitySubType":"","maturityDate":"2028-08-06","previousClosingPrice":156652.0,"settlementType":"2","quantityOffer":0.0,"tradingHighPrice":0.0,"denominationCcy":"ARS","bidPrice":0.0,"tradingLowPrice":0.0,"market":"BYMA","volumeAmount":0.0,"volume":0.0,"trade":0.0,"daysToMaturity":662,"securityType":"CORP","closingPrice":156652.0,"settlementPrice":0,"quantityBid":0.0},{`

## 14. BYMA histórico AL30
- estado: 200 | bytes: 1394 | tipo: application/json
- muestra: `{"s":"ok","t":[1788231600,1788318000,1788404400,1788490800,1788750000,1788836400,1788922800,1789009200,1789095600,1789354800,1789441200,1789527600,1789614000,1789700400,1789959600,1790046000,1790132400,1790218800,1790305200,1790564400,1790650800,1790737200,1790823600,1790910000,1791169200,1791255600,1791342000,1791428400,1791514800,1791860400],"c":[85280,85430,85300,85300,85580,85420,85930,85700,85660,85250,85250,85350,85250,85300,85100,84800,84110,84090,84130,83940,84440,84440,84220,84450,85350,85840,85800,86220,86600,86360],"o":[85000,85500,85590,85300,85100,85650,85500,85810,85950,85600,851`

## 15. Matba Rofex API CEM
- estado: 200 | bytes: 49502 | tipo: application/json; charset=utf-8
- muestra: `{"data":[{"dateTime":"2026-09-25T00:00:00.000Z","symbol":"DLR092026","settlement":1531.000000,"high":1532.000000,"low":1525.000000,"open":1526.000000,"close":1531.000000,"openInterest":1258031.000000,"openInterestChange":-131413.000000,"change":6.500000,"changePercent":0.426369,"volume":1149748,"tradeCount":1683,"impliedRate":33.6928,"previousClose":1524.500000,"unitsOpenInterest":null,"unitsOpenInterestChange":null,"unitsVolume":null,"optionType":null,"strikePrice":null,"underlying":null,"product":"DLR"},{"dateTime":"2026-09-25T00:00:00.000Z","symbol":"DLR102026","settlement":1556.000000,"hig`

## 16. A3 MAE marketdata home
- estado: 200 | bytes: 1785 | tipo: text/html
- muestra: `<!doctype html> <html lang="en"> <head>   <meta charset="UTF-8" />   <link rel="icon" type="image/svg+xml" href="/faviconA3.png" />   <link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/roboto-latin-400-normal.woff2" />   <link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/inter-latin-600-normal.woff2" />     <script>       window.ENV = {};       window.ENV.VIEW = "";       if(window.ENV.VIEW === "__VIEW__"){         window.ENV.VIEW = "";       }        window.ENV.GA_ID = "__GA_ID__";              if(window.ENV.GA_ID === "__GA_ID__"){ `

## 17. CAMMESA demanda región
- estado: 200 | bytes: 31777 | tipo: application/json
- muestra: `[{"fecha":"2026-10-14T00:00:00.000-0300","demHoy":16317,"demAyer":15935,"demSemanaAnt":15860,"demPrevista":16674,"tempHoy":14.1,"tempAyer":13.3,"tempSemanaAnt":18.8},{"fecha":"2026-10-14T00:05:00.000-0300","demHoy":16188,"demAyer":15755,"demSemanaAnt":15724},{"fecha":"2026-10-14T00:10:00.000-0300","demHoy":16068,"demAyer":15755,"demSemanaAnt":15552},{"fecha":"2026-10-14T00:15:00.000-0300","demHoy":15907,"demAyer":15548,"demSemanaAnt":15385,"tempHoy":14.2,"tempAyer":13.3,"tempSemanaAnt":18.9},{"fecha":"2026-10-14T00:20:00.000-0300","demHoy":15649,"demAyer":15423,"demSemanaAnt":15199},{"fecha":"`

## 18. Tesoro EE.UU. curva CSV
- estado: 200 | bytes: 16067 | tipo: text/csv; charset=UTF-8
- muestra: `Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr" 10/14/2026,4.11,4.15,4.15,4.28,4.36,4.37,4.53,4.82,4.92,5.00,5.09,5.19,5.57,5.52 10/13/2026,4.10,4.15,4.15,4.26,4.32,4.34,4.48,4.79,4.90,5.00,5.11,5.21,5.60,5.56 10/09/2026,4.13,4.13,4.13,4.25,4.29,4.32,4.47,4.80,4.89,5.02,5.13,5.24,5.65,5.60 10/08/2026,4.14,4.14,4.13,4.23,4.29,4.30,4.44,4.75,4.85,4.99,5.11,5.22,5.64,5.60 10/07/2026,4.07,4.13,4.14,4.22,4.28,4.28,4.42,4.77,4.87,5.03,5.15,5.28,5.71,5.67 10/06/2026,4.06,4.12,4.13,4.21,4.26,4.28,4.46,4.79,4.88,5.03,5.15,5.27,5.68,5.64 10/`

## 19. FRED VIX/Brent/DXY/BRL
- estado: ERROR | bytes: 0 | tipo: 
- muestra: `ReadTimeout: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=40)`

## 20. Stooq oro
- estado: 200 | bytes: 796 | tipo: text/html; charset=utf-8
- muestra: `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"></head><body><noscript>This site requires JavaScript to verify your browser. Please enable JavaScript and reload.</noscript><script nonce="IhAYg1hmoXIfbjUSbAI1wg"> (async()=>{const c="AAAAAGrQHiwfhaYgfZe1ACSoS-vs4MG0rMvEuQZsjy0g5haoygl6nu1yH2Q",d=4,t="0".repeat(d),e=new TextEncoder;let n=0;while(1){const h=await crypto.subtle.digest("SHA-256",e.encode(c+n)),x=Array.from(new Uint8Array(h)).map(b=>b.toString(16).padStart(2,"0")).join("");if(x.startsWith(t))break;n++}const r=await fetch("/__verify",{me`

## 21. Stooq soja
- estado: 200 | bytes: 796 | tipo: text/html; charset=utf-8
- muestra: `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"></head><body><noscript>This site requires JavaScript to verify your browser. Please enable JavaScript and reload.</noscript><script nonce="jKgMyZekd2BSa_oAtWpkvw"> (async()=>{const c="AAAAAGrQHiznfyMsr180HeRX96jKru9IrMvEuZ6xNqnMpg6a0dlMQBJdBXA",d=4,t="0".repeat(d),e=new TextEncoder;let n=0;while(1){const h=await crypto.subtle.digest("SHA-256",e.encode(c+n)),x=Array.from(new Uint8Array(h)).map(b=>b.toString(16).padStart(2,"0")).join("");if(x.startsWith(t))break;n++}const r=await fetch("/__verify",{me`

## 22. datos.gob.ar IPC
- estado: 200 | bytes: 1244 | tipo: application/json
- muestra: `{"data": [["2026-06-01", 11826.4103], ["2026-07-01", 12076.3937], ["2026-08-01", 12276.766]], "count": 117, "meta": [{"frequency": "month", "start_date": "2026-06-01", "end_date": "2026-08-01"}, {"catalog": {"title": "Datos Programaci\u00f3n Macroecon\u00f3mica"}, "dataset": {"title": "\u00cdndice de Precios al Consumidor Nacional (IPC). Base diciembre 2016.", "description": "\u00cdndice de Precios al Consumidor Nacional. Base diciembre 2016.", "issued": "2017-09-28", "source": "Instituto Nacional de Estad\u00edstica y Censos (INDEC)"}, "distribution": {"title": "\u00cdndice de Precios al Cons`

## 23. Mecon licitaciones
- estado: 404 | bytes: 18805 | tipo: text/html
- muestra: `<!DOCTYPE html> <html lang="es">  <head>     <meta charset="utf-8" />     <meta http-equiv="X-UA-Compatible" content="IE=edge" />     <meta name="viewport" content="width=device-width, initial-scale=1" />     <title>404 - Error | Argentina.gob.ar</title>     <meta name="description"         content="Portal oficial del Gobierno argentino. ConocÃ© cÃ³mo hacer trÃ¡mites en organismos pÃºblicos, tramitalos en lÃ­nea y recibÃ­ servicios digitales y beneficios." />     <meta name="keywords"         content="gobierno, argentino, nacional, gobierno argentino, gobierno nacional, RepÃºblica Argentina, a`

## URLs de API encontradas en la web de A3
```
https://api.marketdata.mae.com.ar/api/
https://api.marketdata.mae.com.ar/api/upload
```
