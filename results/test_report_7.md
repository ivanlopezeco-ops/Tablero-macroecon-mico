# Test 7 — 2026-10-30 20:27 UTC


## INDEC IPC
https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls -> 200 1256960 Tue, 13 Oct 2026 19:02:57 GMT
https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_06_26.xls -> 200 2356736 Thu, 11 Jun 2026 19:06:07 GMT
https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv -> 200 1242105 Tue, 13 Oct 2026 19:02:43 GMT
Codigo;Descripcion;Clasificador;Periodo;Indice_IPC;v_m_IPC;v_i_a_IPC;Region
0;NIVEL GENERAL;Nivel general y divisiones COICOP;201612;100;NA;NA;GBA
0;NIVEL GENERAL;Nivel general y divisiones COICOP;201612;100;NA;NA;Pampeana
Regulados;;Categorias;202609;13238,1788;2,3;43,3;Nacional
B;;Bienes y servicios;202609;12233,3055;1,7;29,2;Nacional
S;;Bienes y servicios;202609;13139,2715;2,4;41,9;Nacional
https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv -> 200 2505225 Tue, 13 Oct 2026 19:02:39 GMT
Codigo;Descripcion_aperturas;Clasificador;Periodo;Indice_IPC;v_m_IPC;v_i_a_IPC;Region
0;Nivel general;Nivel general y divisiones COICOP;201612;100;NA;NA;Pampeana
0;Nivel general;Nivel general y divisiones COICOP;201612;100;NA;NA;Noreste
0;Nivel general;Nivel general y divisiones COICOP;202609;12591,9359;1,9;33;Cuyo
0;Nivel general;Nivel general y divisiones COICOP;202609;12434,4545;1,4;30,3;Patagonia
0;Nivel general;Nivel general y divisiones COICOP;202609;12523,1733;2;33,5;GBA

## FRED CPIAUCSL
ERROR ^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/requests/sessions.py", line 651, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/requests/sessions.py", line 784, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.15/x64/lib/python3.12/site-packages/requests/adapters.py", line 742, in send
    raise ReadTimeout(e, request=request)
requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='fred.stlouisfed.org', port=443): Read timed out. (read timeout=60)


## BLS CPI
{"status":"REQUEST_SUCCEEDED","responseTime":28,"message":[],"Results":{
"series":
[{"seriesID":"CUSR0000SA0","data":[{"year":"2026","period":"M09","periodName":"September","latest":"true","value":"336.298","footnotes":[{}]},{"year":"2026","period":"M08","periodName":"August","value":"334.131","footnotes":[{}]},{"year":"2026","period":"M07","periodName":"July","value":"332.813","footnotes":[{}]},{"year":"2026","period":"M06","periodName":"June","value":"332.568","footnotes":[{}]},{"year":"2026","period":"M05","periodName":"May","value":"333.979","footnotes":[{}]},{"year":"2026","period":"M04",

## BCRA series.xlsm filas diarias
=== BASE MONETARIA (6445, 33)
0 C60 | nan | nan | Gerencia de Estadísticas Mon | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
1 nan | nan | BASE MONETARIA | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
2 nan | nan | NOTAS METODOLOGICAS | nan | nan | nan | 30/10/2026 | nan | nan | nan | nan | nan | nan | nan | nan | nan
3 Fecha | nan | Variaciones Diarias | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
4 nan | nan | Factores de Explicación de l | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
5 nan | nan | Total | Compras Netas de Divisas | nan | Otras Operaciones con el Tes | nan | nan | Pases, LELIQ, NOTALIQ y Rede | nan | nan | nan | LEBAC y NOBAC | Rescate de Cuasimonedas | Operaciones con LEFI | Otros
6 nan | nan | nan | Al Sector
 Privado y Otros | Al Tesoro Nacional | Adelantos Transitorios | Transferencia de Utilidades  | Resto | Pases | LELIQ y NOTALIQ | Redescuentos y Adelantos | Intereses, Primas y Remun. C | nan | nan | nan | nan
7 nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
8 Fecha | nan | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor | Variaciones Diarias - Factor
9 2003-01-02 00:00:00 | nan | 151.1909999999995 | 98.77131 | 0 | 0 | 0 | -6.2491211384 | 30.00999999999999 | 0 | -27.51900000000023 | -49.68171621000002 | 83.67096 | 0 | 0 | 22.18856734839972
10 2003-01-03 00:00:00 | nan | 57.63999999999944 | 206.65925 | 0 | 0 | 0 | -1.640000000000001 | -0.1500000000000057 | 0 | 0 | -0.06766472 | -148.304377346458 | 0 | 0 | 1.142792066457468
11 2003-01-06 00:00:00 | nan | 163.7400000000016 | 172.239104 | 0 | 0 | 0 | -7.890000000000008 | 0.03000000000000114 | 0 | 0 | 0.798643592 | 0 | 0 | 0 | -1.437747591998396
--- últimas filas diarias
2026-10-26 00: | nan | -8381 | 0 | 0 | 0 | 0 | -144621.146899 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 136240.1468993
2026-10-27 00: | nan | -1234595 | 0 | 0 | 0 | 0 | 67776.37107724 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -1302371.37107
2026-09-01 00: | nan | -542118 | 717482.75 | 0 | 0 | 0 | -270815.711338 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -988785.038661
2026-10-01 00: | nan | -1339496 | 1902534 | 0 | 0 | 0 | -1002742.21141 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | -2239287.78858
2026-09-01 00: | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
2026-10-01 00: | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
=== RESERVAS (6159, 17)
0 C76 | nan | nan | Gerencia de Estadísticas Mon | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
1 nan | nan | RESERVAS INTERNACIONALES | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
2 nan | nan | NOTAS METODOLOGICAS | nan | nan | nan | 30/10/2026 | nan | nan | nan | nan | nan | nan | nan | nan | nan
3 Fecha | nan | Stock de Reservas Internacio | nan | nan | nan | Variaciones Diarias | nan | nan | nan | nan | nan | nan | Asignaciones DEGs 2009 (Stoc | nan | Tipo de cambio
(1 u$s = … $)
4 nan | nan | nan | nan | nan | nan | Reservas Internacionales | Factores de explicación de l | nan | nan | nan | nan | nan | nan | nan | nan
5 nan | nan | Total | Oro, Divisas, Colocaciones a | Divisas - Pase Pasivo en USD | nan | nan | Compra de Divisas | Organismos Internacionales | Otras Operaciones del Sector | Efectivo Mínimo | Otros 
(incl. pases pasivos  | nan | nan | nan | nan
6 nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan
7 nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan

## BCRA catálogo: compras/reservas
1: Reservas internacionales | 2026-10-28
47: Efecto monetario de las compras netas de divisas al sector privado y otros  | 2026-10-27
48: Efecto monetario de las compras netas de divisas al tesoro nacional  | 2026-10-27
74: Reservas internacionales (excluidas asignaciones deg 2009) | 2026-10-27
75: Oro, divisas, colocaciones a plazo y otros activos de reserva | 2026-10-27
76: Divisas-pase pasivo en dólares con el exterior | 2026-10-27
77: Reservas internacionales  | 2026-10-27
78: Variación de reservas internacionales por compra de divisas  | 2026-10-27
79: Variación de reservas internacionales por operaciones con organismos internacionales | 2026-10-27
80: Variación de reservas internacionales por otras operaciones del sector público  | 2026-10-27
81: Variación de reservas internacionales por efectivo mínimo  | 2026-10-27
82: Variación de reservas internacionales por otras operaciones no incluidas en otros rubros  | 2026-10-27