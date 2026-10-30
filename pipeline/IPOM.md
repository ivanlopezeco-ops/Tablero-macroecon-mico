# Fuentes incorporadas a partir de la revisión del IPOM

El usuario aprobó Brasil, Fed/PCE, cantidades y términos del intercambio, tasas activas, morosidad y financiamiento CNV. Se conserva la metodología de la versión local revisada el 30/10/2026. No se agregan PIB/demanda interna ni cuenta corriente de balanza de pagos. Reservas netas y ponderaciones existentes permanecen sin cambios.

## Actualización

`run.py` llama a `ipom.actualizar` y `exportar.py` incorpora `data/ipom.json`. Los datos se conservan en la rama `datos`, junto con el resto de la base. Se usa el cron ya existente; Fed y tasas activas diarias se vuelven a consultar cada 3 horas, y las fuentes mensuales cada 12 horas. La corrida histórica fuerza todas las consultas. Una falla se reintenta en la siguiente corrida, aunque no haya vencido el intervalo.

Las fechas finales de consulta se calculan con la fecha argentina del proceso. No se limitan a octubre de 2026. La CNV se descubre desde sus páginas oficiales: identificador del listado de informes y enlace vigente de la planilla PyME. Se refresca el listado en cada consulta CNV; se descargan los informes de los últimos tres meses y los anteriores al menos semanalmente, o antes si cambia su URL. Se vuelven a leer las historias oficiales completas para incorporar revisiones.

Las descargas y el JSON final se reemplazan de forma atómica. En `data/raw/ipom` se conservan los originales y metadatos con URL, fecha de descarga y SHA256. Se validan fechas, duplicados, valores finitos, continuidad mensual, cantidad de series y conservación de la cobertura previa. Una respuesta truncada no borra historia. Si falla un bloque, se conserva su versión válida y su fecha de última consulta exitosa; se marca PARCIAL o ERROR en el sistema de alertas existente. La fuente nueva no se considera correcta por utilizar datos en caché después de una falla.

Antes del despliegue, `ipom.py --verificar site/data.json` exige las 40 series completas. Una primera carga incompleta bloquea la publicación. Las ramas de trabajo ejecutan las pruebas y el proceso completo, pero solo `main` guarda la rama `datos`, gestiona alertas y publica Pages. Se conserva un artefacto de validación de cada corrida durante siete días.

## Definiciones

| Bloque | Fuente y tratamiento |
|---|---|
| Brasil | BCB SGS 24364 (IBC-Br) y 28505 (manufactura IBGE). Índices 2022=100 desestacionalizados oficiales, desde 2015. No se desestacionaliza ni empalma por cuenta propia. IBC-Br no es PIB. |
| Fed | Federal Reserve Board vía FRED, DFEDTARL/DFEDTARU. Rango objetivo diario, incluidos ceros; se valida piso ≤ techo. |
| PCE | BEA vía FRED, PCEPI/PCEPILFE. Índices oficiales desestacionalizados, base 2017=100. Mensual e interanual = (índice t / índice t−n − 1) × 100, n=1 o 12. Fechas exactas, sin imputar ni anualizar. |
| Comercio | INDEC, `serie_mensual_indices_comex.xls`, base 2004=100. Cantidades y precios originales. Términos del intercambio = Px/Pm × 100, mismos meses y base. Interanuales de cantidades con t−12 exacto. No se comparan toneladas ni se interpreta distancia de índices como saldo. |
| Tasas | BCRA `preser_tas.xls`, hoja Tasas_sector_privado, columnas D/R/AX, con validación de encabezados. TNA ponderadas oficiales de adelantos, documentos descontados y personales. Diarias: API monetarias 13/14, con paginación completa. Adelantos diarios: empresas con acuerdo, 1–7 días y $10 millones o más; no se empalman con el total mensual. Se omiten ceros de tasas aún sin cerrar, siguiendo el tratamiento existente de tasas BCRA. |
| Morosidad | Anexo del Informe sobre Bancos. Ratios oficiales de cartera irregular sobre financiaciones: familias, empresas y total. Se contrasta el total en dos hojas y se preservan las clasificaciones del BCRA. No se reconstruye el ratio con ponderaciones de saldos ni se incorpora un dato preliminar de otra publicación. |
| CNV | Total mensual del informe: resumen ejecutivo contrastado con cuerpo. Enero 2025 en adelante. Se usa el valor del mes en pesos de ese mismo mes, no el acumulado reexpresado. PyME e instrumentos desde febrero 2015: planilla oficial, seis componentes que concilian con el total. Millones de pesos corrientes; presentación en billones = valor/1.000.000. PyME forma parte del total; no sumarlos. Sin deflactar ni convertir monedas con cotizaciones propias. |

La apertura de cinco instrumentos del mercado total, conservada como auxiliar, no incluye acciones/FCI cerrados y no se presenta como suma exhaustiva. Se mantuvo el comienzo del total en 2025 porque el informe de julio de 2024 contiene una discrepancia entre resumen y cuerpo. No se utiliza la planilla FCE separada que mostró una inconsistencia en agosto de 2026.

## Verificación

Pruebas sin red: `python -m unittest discover -s tests -p "test_ipom.py"`, además de regresiones, ampliación y frontend existentes. Incluyen revisión de valores, truncamiento, meses ausentes, fechas futuras, ceros de la Fed, paginación, caché, falla/recuperación y bloqueo de una primera carga incompleta.

Actualización de todas las fuentes nuevas: `python pipeline/ipom.py --force`. Actualización completa del tablero: `python pipeline/run.py`. Las fuentes reportan su estado por separado; `data/ipom.json` conserva cobertura y fecha de consulta. El selector de período y las descargas usan los mismos componentes del tablero existente.
