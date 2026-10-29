# Tablero macroeconómico

Tablero de seguimiento de la macro argentina con actualización automática diaria.

## Dónde están los datos (desde oct-26)

La base acumulada (`data/series.csv`, `estado.json`, `validacion.md`, crudos) vive en la rama `datos`, que tiene un único commit y se reemplaza en cada corrida. Así el repositorio no crece con las corridas horarias. Para verla: rama `datos` en GitHub.

## Instalación y comprobaciones

Python 3.12 y Node.js 20 o posterior:

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_regresiones.py"
python -m unittest discover -s tests -p "test_ampliacion.py"
node --test tests/test_frontend.cjs
```

Estas pruebas no descargan fuentes ni modifican la base. Los scripts `test_fuentes*.py` son exploraciones de proveedores y sí realizan descargas.

`python pipeline/run.py` actualiza los datos y exporta la web; requiere la base de la rama `datos` para conservar la historia acumulada. Para ver una copia local ya exportada: `python -m http.server 8000 --directory site`.

Las fuentes pueden quedar en `ok`, `PARCIAL` o `ERROR`. Las fallas completas y parciales persistentes conservan su fecha de inicio y activan la alerta después de tres horas. La web señala fuentes con problemas y series que superan su rezago esperado. Si BYMA no informa la fecha de una cotización del Merval, se mantiene el último dato fechado: no se usa la fecha de consulta como fecha del precio.

Las descargas GET hacen hasta tres intentos ante cortes de conexión, transferencias incompletas y errores HTTP 5xx, con pausas de 4 y 8 segundos. En los históricos de BYMA para MEP/CCL y bonos se reintenta también el HTTP 400: se comprobó que consultas válidas rechazadas en una corrida responden correctamente al repetirlas. Cada intento conserva URL, especie, plazo de liquidación, período y parámetros; no utiliza una fuente alternativa. Si un símbolo sigue fallando, se informa el error y se guardan los demás símbolos descargados. La base acumulada conserva los datos previos de la serie fallida. El balance cambiario sigue usando el mismo Excel del BCRA, las mismas hojas, unidades y signos.

## Bloques incorporados el 29 de octubre de 2026

### Revisión de los avisos de atraso (29/10/2026)

Las tres series de recaudación tenían septiembre de 2026, el último período publicado tanto en datos.gob.ar como en la página de la DNIAF. El umbral anterior esperaba octubre antes de que terminara ese mes. El criterio aprobado es esperar **cinco días hábiles desde el cierre del mes siguiente al último disponible**, excluyendo fines de semana y feriados nacionales argentinos mediante `holidays` (calendario AR, categoría pública). Se mantiene el plazo durante todo el quinto día; se alerta al día siguiente. Ejemplo: con septiembre como último dato, octubre cierra el 31/10 y el plazo termina el 6/11/2026. Los otros criterios de rezago no cambian.

El enlace antiguo del BCRA, `ITCRMSerie.xlsx`, seguía respondiendo correctamente pero terminaba el 16/10/2026. La [página oficial del ITCRM](https://www.bcra.gob.ar/indices-de-tipo-de-cambio-multilateral/) enlaza ahora `itcrm-serie.xlsx`, que al revisar llegaba al 28/10/2026. Se descarga la serie oficial completa y se registra su URL en el estado de fuentes; un cambio de URL obliga a descargar aunque la consulta anterior sea reciente.

La incorporación de la nueva versión histórica fue aprobada expresamente: mantiene base 17/12/2015=100 y las mismas columnas, pero revisa valores desde el 2/12/2022 en ITCRM y Brasil, y desde el 9/8/2026 en Estados Unidos. Por ejemplo, ITCRM del 16/10/2026 pasa de 85,4217 a 82,8770. No se mezclan versiones ni se reconstruyen valores; no se atribuye una causa a la revisión. El piso y techo del TCRM se recalculan con la fórmula existente `ITCRM × banda / A3500`. Las dos versiones descargadas y su comparación se conservaron en los artefactos locales de validación.

### Ampliación aprobada

Se incorporan los flujos de reservas dentro de Reservas, y las secciones Liquidez y Empleo e ingresos. No se incorporan los bloques experimentales de comercio, colocaciones de deuda ni el duplicado de pagos y recursos. La copia `version-local-ampliada` es un borrador anterior, no la fuente de publicación. La versión vigente se genera desde `site/` y `pipeline/` en `main`.

`pipeline/ampliacion.py` se ejecuta dentro de la corrida existente. Descarga las series diarias del BCRA cada tres horas y salarios/SIPA cada doce horas; reintenta después de fallas. Guarda observaciones y fuentes en `data/raw/ampliacion-cache.json`, y exporta `data/ampliacion.json`. Ambos archivos se conservan en la rama `datos`. `exportar.py` integra las series con prefijo `amp_` y sus metadatos al JSON completo. No depende de los datos congelados de la copia local ni de PDFs de Drive.

- **Reservas brutas:** series BCRA 77 a 82. Sumas mensuales de variación total y cinco factores sobre fechas diarias comunes. No se rellenan faltantes. Se controla que componentes y total coincidan dentro del redondeo de la fuente. No cambia el método de reservas netas ni súper netas. La presentación de V. Werning del 5/10/2026, página 5, es referencia conceptual; las cifras provienen de la API.
- **Liquidez:** cuenta corriente de entidades en BCRA (19) / depósitos en pesos de los sectores público y privado no financieros (91) × 100, en fechas exactas. Ratio descriptivo tomado del informe de Balanz del 6/10/2026; no estima encajes excedentes ni replica su modelo econométrico. TAMAR (44) y BADLAR (7) aportan contexto.
- **Base monetaria:** total 46; divisas privadas 47; Tesoro 48 a 51; instrumentos 52 a 58; otras operaciones 59. Se suman flujos mensuales nominales sobre fechas comunes. No se estima esterilización ni causalidad. El último mes informa la fecha hasta la que se acumulan movimientos.
- **Empleo:** SIPA, cuadro T.2.2, asalariados privados registrados, miles de personas, ajuste estacional oficial. El enlace del archivo se descubre en la página oficial, sin fijar un mes. Conserva datos provisorios y no extrapola meses faltantes.
- **Salarios reales:** índices INDEC de privados registrados y públicos / IPC nacional del mismo mes, reescalados a diciembre de 2023 = 100. Solo meses comunes observados.
- **Crédito por línea:** series BCRA 110 a 117, promedio de saldos diarios por mes cerrado / IPC del mismo mes; diciembre de 2023 = 100. No son desembolsos ni una clasificación por destino efectivo.

Ante una descarga fallida, se conservan los datos previos y se informa la falla en el estado de fuentes. Si falla el cálculo o una conciliación, no se reemplaza la última ampliación válida. Si nunca se generó, las secciones muestran un mensaje de falta de datos. La publicación y la actualización de datos se comprueban en GitHub Actions, no se deducen de las pruebas locales.
