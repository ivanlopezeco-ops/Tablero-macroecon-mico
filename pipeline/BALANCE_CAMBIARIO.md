# Balance cambiario: coberturas y conciliaciones

Corrección autorizada el 30/10/2026. El usuario eligió conservar la historia del Excel y mostrar aparte las cifras ajustadas verificadas del PDF. No se empalman ni se aplica una resta fija por tarjetas. Se mantienen las consultas cada 12 horas y la programación existente.

## Fuentes y alcance

- El anexo `anexo-estadistico-mercado-cambios-balance-cambiario.xlsx` conserva las cuentas del balance y la historia sectorial. El registro sectorial incluye cancelaciones de deudas locales por tarjetas; el resultado sectorial del PDF las excluye. La diferencia no es una revisión del mismo indicador.
- `balance_pdf.py` consulta el informe del mes que efectivamente contiene el anexo, sin depender del mes calendario actual. Lee personas humanas y los sectores destacados con cifras explícitas en el texto. No imputa cifras no publicadas ni extrae valores aproximados de gráficos. Valida período, signos y consistencia entre menciones; contrasta cuenta corriente y financiera con el anexo (tolerancia de medio millón por redondeo del PDF). Conserva PDF original, URL y SHA256.
- La tabla del informe y la historia del anexo se presentan por separado, con fecha y cobertura. En el resumen general se explicita que la cifra histórica de personas humanas incluye cancelaciones por tarjetas.
- Si no se reconoce un informe o no coincide con el anexo, la fuente falla de forma visible, conserva la base anterior y bloquea la publicación de una versión no conciliada. No se presenta el dato previo como una consulta nueva exitosa.

## Aperturas

- Billetes/divisas del SPNF: `mlc089/090/091/093/094/095`, todos del mismo universo que `bal040`. Incluye ingresos y egresos de billetes, inversión directa y otras inversiones. No equivale a la estimación de ahorro externo del PDF.
- Cobros de bienes: cinco modalidades, incluido `mlc009` (otros cobros). Pagos por modalidad: `mlc011/012/013`, contrastados con `mlc010`, el total del mercado de cambios. Este total no se equipara al balance cambiario, que también incluye operaciones directas con reservas. La diferencia histórica de coberturas no se rellena ni se atribuye arbitrariamente.
- Deuda por instrumento: financiaciones locales, préstamos/títulos del exterior y líneas de crédito. Conciliación con `bal031`.
- Rentas: utilidades y dividendos (`mlc057`) separados de remuneraciones (`mlc058`) y otras rentas (`mlc059`). Intereses incluyen también otros pagos del Gobierno (`bal015`). Total de egresos = `-(bal011 + bal018)`; no es el ingreso primario neto.
- `viajes001` se etiqueta como agregado de tarjetas, otros viajes y pasajes. La estimación estricta de viajes/pasajes sigue siendo `viajes026`.
- Cuenta financiera: incluye compraventa de títulos (`bal046`) y otras operaciones del sector público (`bal047`). `bal049`, concepto no informado, se agrega en el resultado global, fuera de la cuenta financiera.
- El anexo consultado tiene diferencias internas de hasta USD 5,1543 millones en la apertura financiera de 2019-2022. Se conservan los totales oficiales y se expone la diferencia aritmética como tal, sin asignarle causa económica. Se rechaza cualquier diferencia superior a USD 0,002 millones en los últimos 24 meses. No se usa esta diferencia para tapar fallas recientes.

## Controles automáticos

`balance_control.completar` realiza 13 conciliaciones sobre toda la cobertura disponible (285 meses para las cuentas y 15 para la estimación de viajes al 30/10/2026). Tolerancia de entrada: USD 0,002 millones, por precisión de los archivos. Se rechazan aperturas faltantes y meses con componentes ausentes; no se interpretan huecos como cero.

La exportación conserva dos decimales para las series monetarias del balance. La validación publicada permite solamente el máximo redondeo de 0,005 por importe. `python pipeline/balance_control.py site/data.json` comprueba las sumas, la versión de la fuente y la coincidencia del período PDF/anexo antes de desplegar. La migración de fuente fuerza una única consulta aunque no hayan vencido las 12 horas; luego se respeta el intervalo.

Pruebas: `python -m unittest discover -s tests -p test_balance.py`, controles existentes y corrida completa en GitHub. Casos PDF: período incorrecto, signos, reordenamiento de sectores, contradicciones y listas desalineadas. Casos de conciliación: faltantes, totales incorrectos y límites de redondeo.
