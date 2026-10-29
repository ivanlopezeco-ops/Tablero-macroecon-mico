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

## Bloques incorporados el 29 de octubre de 2026

Se incorporan los flujos de reservas dentro de Reservas, y las secciones Liquidez y Empleo e ingresos. No se incorporan los bloques experimentales de comercio, colocaciones de deuda ni el duplicado de pagos y recursos. La copia `version-local-ampliada` es un borrador anterior, no la fuente de publicación. La versión vigente se genera desde `site/` y `pipeline/` en `main`.

`pipeline/ampliacion.py` se ejecuta dentro de la corrida existente. Descarga las series diarias del BCRA cada tres horas y salarios/SIPA cada doce horas; reintenta después de fallas. Guarda observaciones y fuentes en `data/raw/ampliacion-cache.json`, y exporta `data/ampliacion.json`. Ambos archivos se conservan en la rama `datos`. `exportar.py` integra las series con prefijo `amp_` y sus metadatos al JSON completo. No depende de los datos congelados de la copia local ni de PDFs de Drive.

- **Reservas brutas:** series BCRA 77 a 82. Sumas mensuales de variación total y cinco factores sobre fechas diarias comunes. No se rellenan faltantes. Se controla que componentes y total coincidan dentro del redondeo de la fuente. No cambia el método de reservas netas ni súper netas. La presentación de V. Werning del 5/10/2026, página 5, es referencia conceptual; las cifras provienen de la API.
- **Liquidez:** cuenta corriente de entidades en BCRA (19) / depósitos en pesos de los sectores público y privado no financieros (91) × 100, en fechas exactas. Ratio descriptivo tomado del informe de Balanz del 6/10/2026; no estima encajes excedentes ni replica su modelo econométrico. TAMAR (44) y BADLAR (7) aportan contexto.
- **Base monetaria:** total 46; divisas privadas 47; Tesoro 48 a 51; instrumentos 52 a 58; otras operaciones 59. Se suman flujos mensuales nominales sobre fechas comunes. No se estima esterilización ni causalidad. El último mes informa la fecha hasta la que se acumulan movimientos.
- **Empleo:** SIPA, cuadro T.2.2, asalariados privados registrados, miles de personas, ajuste estacional oficial. El enlace del archivo se descubre en la página oficial, sin fijar un mes. Conserva datos provisorios y no extrapola meses faltantes.
- **Salarios reales:** índices INDEC de privados registrados y públicos / IPC nacional del mismo mes, reescalados a diciembre de 2023 = 100. Solo meses comunes observados.
- **Crédito por línea:** series BCRA 110 a 117, promedio de saldos diarios por mes cerrado / IPC del mismo mes; diciembre de 2023 = 100. No son desembolsos ni una clasificación por destino efectivo.

Ante una descarga fallida, se conservan los datos previos y se informa la falla en el estado de fuentes. Si falla el cálculo o una conciliación, no se reemplaza la última ampliación válida. Si nunca se generó, las secciones muestran un mensaje de falta de datos. La publicación y la actualización de datos se comprueban en GitHub Actions, no se deducen de las pruebas locales.
