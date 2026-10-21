/* Textos del desplegable "Qué estamos midiendo". Cada tarjeta toma uno por su clave (cfg.mide en app.js).
   Un párrafo por elemento. Lo que se afirma acá sale del cálculo del pipeline o de las fuentes citadas al pie. */
"use strict";

const MIDE = {
  // ---------------------------------------------------------------- calendario
  calendario: "Próximas fechas de publicación del INDEC (calendario anual de difusión), del BCRA (REM, balance cambiario e informe monetario, según su página de fechas de publicación) y de la próxima licitación del Tesoro, que aparece cuando Finanzas publica el llamado, dos o tres días hábiles antes. El cronograma anual de licitaciones es un PDF que marca los días solo con colores y no se puede leer automáticamente. Las que dicen \"En el tablero\" alimentan series del tablero: la inflación, el EMAE, el comercio exterior, el IPI manufacturero y el ISAC. El tablero lee el calendario del semestre en curso y del siguiente y se actualiza solo.",

  // ---------------------------------------------------------------- reservas
  reservas_netas: [
    "Reservas netas y súper netas. Las netas son las reservas brutas menos los encajes en dólares, el swap con China, los pasivos con el BIS y los repos. Las súper netas restan además el Bopreal a un año y los depósitos del Tesoro en dólares en el BCRA.",
    "El swap está pactado en yuanes y se valúa con el tipo de pase del BCRA. La regla de liquidez del BCRA queda afuera del cálculo. El tramo punteado se estima por calibración contra el gráfico que publica Machado, con una precisión aproximada de 500 millones de USD.",
  ],
  tabla_reservas: [
    "Muestra cómo se pasa de reservas brutas a netas y súper netas en dos fechas a elección. Cada componente se resta con su signo negativo y la última columna da la diferencia entre ambas fechas.",
    "Los asteriscos marcan valores estimados por calibración contra el gráfico de Machado: BIS y repos antes de julio de 2026, y Bopreal a un año antes del 30 de septiembre de 2026.",
  ],
  reservas_brutas: "Stock de reservas internacionales brutas del BCRA al cierre de cada día, en millones de USD. El BCRA las publica con dos o tres días hábiles de rezago y ningún canal público las tiene antes.",
  compras: "Compras (positivo) y ventas (negativo) del BCRA en el mercado de cambios, por día y en millones de USD. El BCRA publica este dato con unos cuatro días hábiles de rezago. Cuando el período supera dos años, las barras se suman por mes.",
  compras_pct: "Compras diarias del BCRA divididas por el volumen operado en el mercado de cambios (FOREX MAE, A3 Mercados), en %. Se descartan los días con volumen menor a USD 100 millones y los cocientes fuera de ±100%. Con períodos largos se muestra el promedio mensual.",
  dep_tesoro: "Depósitos del gobierno en moneda extranjera en el BCRA. El BCRA los informa en pesos y se convierten a dólares con el A3500 de cada día. Se restan de las reservas netas para llegar a las súper netas.",

  // ---------------------------------------------------------------- cambiario
  banda: "El A3500 es el tipo de cambio mayorista de referencia que publica el BCRA. El gráfico lo muestra junto al piso y el techo de la banda cambiaria. La distancia al techo del título se calcula como techo / A3500 - 1.",
  tcr_bilateral: [
    "El tipo de cambio real bilateral con EE.UU. lleva el A3500 a precios de un mes base, que es el último con IPC publicado. Se multiplica el A3500 por los precios de EE.UU. (CPI) y se divide por los de Argentina (IPC del INDEC). Los índices mensuales se interpolan por día.",
    "El piso y el techo de la banda reciben el mismo ajuste. El tramo punteado usa una inflación del mes en curso estimada con el REM.",
  ],
  tcrm: "El ITCRM es el índice de tipo de cambio real multilateral del BCRA, con base 17-12-15 = 100. Compara el peso con las monedas de los principales socios comerciales, ajustado por inflación relativa. Un valor más alto indica un tipo de cambio real más alto. Las bandas se expresan en la misma escala: ITCRM x banda / A3500 del día.",
  ccl_mep: [
    "El MEP y el contado con liquidación (CCL) se calculan con el AL30 a 24 horas en BYMA: MEP = AL30 en pesos / AL30D y CCL = AL30 en pesos / AL30C.",
    "En la rueda se usa el último precio operado, con 20 minutos de demora, marcado como provisorio hasta que sale el cierre. Antes del primer dato propio la serie sale de ArgentinaDatos (tramo punteado).",
  ],
  brecha_canje: "La brecha es el CCL dividido por el A3500 menos 1. El canje es el CCL dividido por el MEP menos 1. Ambos se expresan en %.",
  futuro: "Cotización del dólar futuro en Matba Rofex (A3 Mercados) para el contrato más corto, que vence a fin del mes corriente, y para el próximo diciembre. Expresa el tipo de cambio que el mercado pacta hoy para esas fechas, en pesos por dólar.",
  volumen_mlc: "Monto diario operado en el mercado de cambios (FOREX MAE de A3 Mercados), en millones de USD. En períodos largos se muestra el promedio mensual.",

  // ---------------------------------------------------------------- tasas
  tasas_bancos: "Tasas de referencia que publica el BCRA, en % nominal anual. La TAMAR y la BADLAR corresponden a depósitos a plazo fijo de grandes montos en bancos privados. La TAMAR se publica desde octubre de 2024. El eje se corta cuando hay picos fuera de escala.",
  caucion: "Caución bursátil a un día en pesos (A3 Mercados, promedio ponderado por monto), tasa de pases entre terceros del BCRA y tasa a un día de la rueda REPO de A3. Son las tasas de corto plazo del mercado, en % nominal anual.",
  tasa_real: "Tasa real ex ante. La TAMAR y la BADLAR se pasan a tasa efectiva mensual (TNA x 30 / 365) y se comparan con la inflación esperada del mes siguiente que releva el REM del BCRA: (1 + tasa mensual) / (1 + inflación esperada) - 1. La serie usa expectativas de inflación.",
  curva_lecap: "Tasa efectiva mensual (TEM) implícita en el precio de cada LECAP y BONCAP, ordenadas por vencimiento. Se calcula con el precio de BYMA y el pago final, que surge de capitalizar 100 a la TEM de emisión de la ficha técnica. La liquidación es al día hábil siguiente. Las letras con menos de 10 días al vencimiento se excluyen porque el redondeo distorsiona la tasa.",

  inflacion_implicita: [
    "Compara los bonos que ajustan por CER con las LECAP y BONCAP de tasa fija a igual plazo. De cada bono CER cero cupón se obtiene la tasa real que paga su precio: precio = 100 x CER hoy / CER de emisión x (1 + tasa real) a la menos plazo. La inflación implícita es la que iguala la tasa fija con la tasa real: (1 + tasa fija) / (1 + tasa real) - 1, expresada como promedio mensual.",
    "La tasa fija se interpola entre las letras del día y no se extrapola, de modo que solo hay dato donde la curva de tasa fija tiene plazo comparable. Cada línea es el promedio mensual esperado hasta 2, 4 o 6 meses. El CER se ajusta con diez días hábiles de rezago, según la ficha de los bonos. Los dos instrumentos tienen prima de plazo y de liquidez, de modo que el resultado se parece a una expectativa sin ser una expectativa pura.",
  ],
  curva_inflacion: "Última inflación implícita de cada bono CER, ordenada por vencimiento: el promedio mensual que iguala su tasa real con la tasa fija a igual plazo. La línea punteada es la inflación a 12 meses que espera el REM, llevada a promedio mensual. Los bonos con vencimiento fuera del tramo que cubre la curva de tasa fija quedan sin dato.",

  // ---------------------------------------------------------------- bonos
  tabla_bonos: [
    "Precio de BYMA de cada bono a 24 horas, por cada 100 nominales, con la variación del día, de 7 y de 30 días. El precio de BYMA incluye los intereses corridos. La TIR es efectiva anual, con días reales sobre 365, y la duration es modificada y se expresa en años.",
    "Los flujos salen de las fichas técnicas de BYMA y quedan explícitos en el repositorio. La TIR y la duration usan el dólar MEP, o el CCL si lo elegís. Se contrastaron con El Dashboard, Bonistas.com y Portfolio Personal, con diferencias de hasta 0,07 puntos de TIR. La serie histórica de BYMA viene ajustada por cada pago de cupón o cuota, de modo que las variaciones de precio no registran la caída del día de pago. Los Bopreales Serie 1 A, B y C (marcados con †) tienen una opción de rescate anticipado del tenedor, que se paga en pesos al tipo de cambio A3500 del día en que se ejerce y rige desde el 30/4/25, el 30/4/26 y el 30/4/27 respectivamente; también pueden usarse para pagar impuestos en ciertos períodos. La Serie 1 D no la tiene. La TIR no modela la opción porque el valor de rescate no figura en las fuentes consultadas.",
  ],
  curva_bonos: "Cada punto es un bono con su duration modificada (distancia horizontal, sensibilidad al precio ante un cambio de tasa) y su TIR (altura). Los Bopreales se muestran aparte por color porque tienen vencimientos cortos y condiciones distintas de la curva de Bonares y Globales.",
  tir_2030: "TIR del AL30 (ley argentina) y del GD30 (ley Nueva York). Ambos tienen el mismo cronograma de pagos, así que la distancia entre las dos líneas refleja la diferencia de precio entre las dos legislaciones. Para calcular la serie histórica se deshace el ajuste que BYMA aplica a los precios por cada pago de cupón o cuota.",
  tir_largos: "TIR de los Globales 2035, 2038, 2041 y 2046 con el precio en dólar MEP o CCL. Para calcular la serie histórica se deshace el ajuste que BYMA aplica a los precios por cada pago de cupón o cuota.",
  precio_2030: "Precio del AL30 y del GD30 en dólar MEP, por cada 100 nominales. La serie de BYMA viene ajustada por cada pago de cupón o cuota: no cae el día de pago, de modo que sirve para seguir el rendimiento total.",
  precio_largos: "Precio de los Globales largos en dólar MEP, por cada 100 nominales, con la serie ajustada por cada pago que publica BYMA.",
  precio_bopreales: "Precio de los Bopreales en dólar MEP, por cada 100 nominales. Los Bopreales Serie 1 (A, B, C y D) vencen en octubre de 2027 y los de la Serie 4 (A y B), en octubre de 2028.",

  servicio_deuda: [
    "Pagos de capital e intereses que surgen de los cronogramas de las fichas técnicas de BYMA, multiplicados por el monto nominal en circulación de cada bono, por mes y en millones de USD. Cubre 21 bonos en dólares: 9 Bonares, 6 Globales y 6 Bopreales. Los Bonares y Globales pagan en enero y julio, y los Bopreales en abril y octubre; los Bonares 2027, 2028 y 2029 pagan intereses todos los meses.",
    "Los montos incluyen los bonos en poder del sector público y no incluyen los pagos al FMI y a otros organismos ni los bonos en pesos. Los montos en circulación son los de la ficha de BYMA al 20/10/26 y cambian con canjes y recompras. La comparación con las reservas netas pone un flujo anual frente a un stock.",
  ],

  // ---------------------------------------------------------------- riesgo país
  riesgo_ppal: [
    "El riesgo país es el spread de los bonos soberanos sobre los bonos del Tesoro de EE.UU., en puntos básicos. Se usa el EMBI Global Diversified de JP Morgan que publica el Banco Central de la República Dominicana. El dato del día de Argentina sale de Ámbito y es provisorio hasta que publica el BCRD.",
    "Los promedios de comparación se calculan acá con los spreads por país y exigen al menos 70% de los países del grupo con dato. En septiembre de 2026 JP Morgan cambió su metodología y recalculó la historia; el quiebre se concentra en el agregado regional, así que el grupo por defecto excluye a Venezuela y a Argentina.",
  ],
  riesgo_desc: "Separa la variación acumulada del riesgo país de Argentina en tres partes: región (el grupo elegido), contexto global (VIX y rendimiento del Tesoro a 10 años) y propio de Argentina, que es el residuo. Surge de una regresión de variaciones diarias con los datos del período elegido; si tiene menos de 60 ruedas se usan las últimas 250. Describe asociaciones estadísticas y no prueba causalidad.",
  riesgo_global: "Riesgo país de Argentina junto a un indicador del contexto global, según el botón: el VIX (volatilidad implícita del S&P 500), el rendimiento del Tesoro de EE.UU. a 10 años o el DXY (el dólar frente a una canasta de monedas).",
  riesgo_largo: "El riesgo país de Argentina desde 2007 con el EMBI Global Diversified del BCRD, junto al promedio regional. Antes de octubre de 2007 la serie sale de ArgentinaDatos (Ámbito) y se muestra punteada.",
  riesgo_tabla: "Último valor de cada país y grupo, con la variación en una semana, en un mes y en el período elegido, en puntos básicos y en %. Una suba del spread se marca en naranja y una baja en azul. El orden depende de la variación en el período.",
  riesgo_ranking: "Último dato de cada país del EMBI Global Diversified, ordenado de menor a mayor. Venezuela queda fuera del gráfico por escala.",

  // ---------------------------------------------------------------- dinero y crédito
  m2: "M2 privado transaccional y base monetaria, deflactados por el IPC nacional del INDEC y expresados en billones de pesos a precios del último mes con IPC publicado. La serie arranca en diciembre de 2016, cuando empieza el IPC nacional.",
  prestamos: "Préstamos en pesos al sector privado, deflactados por el IPC nacional del INDEC, en billones de pesos a precios del último mes con IPC publicado. La serie arranca en diciembre de 2016.",
  depositos_usd: "Depósitos y préstamos en dólares del sector privado, en millones de USD, según las estadísticas monetarias del BCRA.",

  // ---------------------------------------------------------------- precios y actividad
  ipc: "Variación mensual del índice de precios al consumidor nacional del INDEC, nivel general y núcleo, calculada con el nivel del índice (diciembre de 2016 = 100). Se lee directo del INDEC, que publica antes que datos.gob.ar.",
  rem: "Mediana de las expectativas de inflación a 12 meses del Relevamiento de Expectativas de Mercado (REM) del BCRA, en % interanual. Se publica una vez por mes.",
  emae: "Estimador Mensual de Actividad Económica (EMAE) del INDEC, serie desestacionalizada, con índice 2004 = 100. Se publica entre siete y ocho semanas después del cierre del mes y se lee directo del INDEC.",
  demanda_elec: "Energía demandada en el sistema eléctrico, en MWh por día, según CAMMESA. CAMMESA publica solo el día anterior, de modo que el tablero acumula la serie desde octubre de 2026.",
  comercio: "Exportaciones e importaciones de bienes del intercambio comercial argentino del INDEC, en millones de USD por mes.",
  resultado_primario: [
    "Resultado primario y financiero del sector público nacional en base caja, según la Secretaría de Hacienda del Ministerio de Economía (vía datos.gob.ar), deflactados por el IPC del INDEC. Se expresan en miles de millones de pesos a precios del último mes con IPC publicado.",
    "El resultado financiero se calcula como el primario menos los intereses netos de la deuda, que se muestran con signo negativo (datos.gob.ar no devuelve la serie de resultado financiero). Hacienda suele publicar cada mes en la segunda quincena del mes siguiente.",
  ],
  recaudacion: "Recaudación tributaria nacional de ARCA: total, impositiva (DGI) y aduanera (DGA). La de la seguridad social no se muestra porque datos.gob.ar no la devuelve. Cada mes se compara con el mismo mes del año anterior y se descuenta la inflación del IPC nacional del período. ARCA publica la recaudación el primer día hábil del mes siguiente; el tablero la toma de datos.gob.ar, que la replica con algunos días de demora.",
  licitaciones: [
    "Valor efectivo ofertado y adjudicado en cada licitación por efectivo del Tesoro, en billones de pesos corrientes, según el comunicado de resultados que publica la Secretaría de Finanzas en argentina.gob.ar. Los instrumentos en dólares se convierten a pesos al A3500 del día anterior, como hace el comunicado.",
    "No incluye canjes, conversiones, segundas vueltas ni emisiones en dólares. En los comunicados de 2024 que no traen la frase de totales, el adjudicado es la suma de los instrumentos.",
    "El rollover no se calcula: los comunicados no informan cuánto vencía y la cifra que circula en la prensa usa los vencimientos en manos privadas, que Finanzas no publica en un formato estable.",
  ],
  tabla_licitaciones: "Instrumentos adjudicados en las últimas seis licitaciones: valor efectivo en billones de pesos y TIREA de corte (tasa interna de retorno efectiva anual). En las LECAP y BONCAP que ya cotizaban, la tasa de corte se compara con la de mercado del día hábil anterior en BYMA, llevada a tasa efectiva anual: una diferencia positiva indica que el Tesoro convalidó una tasa mayor que la del mercado. En los bonos CER la TIREA es real y en los dólar linked, en dólares. Cuando la letra es nueva y el comunicado no trae el ticker, se muestra su vencimiento.",

  carry: [
    "Carry trade: cuánto rinde por mes, medido en dólares, quedarse en tasa fija en pesos si el dólar termina donde lo paga hoy el futuro. Es (1 + TEM de la tasa fija) / (1 + devaluación implícita mensual) - 1.",
    "La devaluación implícita sale de cada contrato de dólar futuro contra el A3500 del día; la tasa fija, de la curva de LECAP y BONCAP interpolada al mismo plazo. Las series a 3 y 6 meses interpolan entre contratos. Para reconstruir la curva de antes, las letras ya vencidas se toman de los comunicados de licitación (vencimiento, TEM de emisión y emisión dos días hábiles después de la licitación).",
  ],
  carry_curva: "Para cada vencimiento de dólar futuro: tasa fija en pesos (TEM interpolada en la curva de LECAP y BONCAP), devaluación implícita mensual en el futuro y carry. Solo hay dato donde la curva de tasa fija cubre el plazo, sin extrapolar. El título indica el dólar al que se empata: si al vencimiento el A3500 queda por debajo, la tasa fija rindió más que comprar dólares hoy.",
  futuros_banda: [
    "Precio de cada contrato de dólar futuro, techo de la banda cambiaria proyectado a esa fecha y dólar que empata la tasa fija (A3500 de hoy capitalizado a la TEM de la curva al mismo plazo).",
    "Desde enero de 2026 el techo se ajusta cada mes por la última inflación publicada por el INDEC, la de dos meses antes. Para los meses cuyo IPC ya salió se usa el dato; para los demás, la mediana del REM. Con los datos de 2026 la regla reproduce el techo de fin de mes con diferencias menores a 0,3%.",
  ],

  // ---------------------------------------------------------------- acciones
  merval_usd: [
    "Merval dividido por el contado con liqui del mismo día: muestra cuánto vale la bolsa argentina en dólares. Antes del primer dato propio del CCL (calculado con el AL30) se usa el CCL de ArgentinaDatos.",
    "Desde el 19/10/26 el índice lo calcula MSCI (MSCI MERVAL) en lugar de S&P. El MSCI MERVAL arranca en 100.000 puntos el 16/10/26, último día del S&P Merval; el tablero lo lleva a la escala del S&P Merval multiplicándolo por el cierre de ese día, de modo que la serie queda empalmada. Las composiciones de los dos índices difieren.",
  ],
  merval: "Índice Merval en pesos. Hasta el 16/10/26 es el S&P Merval (Yahoo Finance) y desde el 19/10/26 el MSCI MERVAL de BYMA, llevado a la escala del S&P Merval. BYMA no ofrece la historia del índice nuevo: el tablero la acumula día a día. Durante la rueda se muestra el último valor, como provisorio.",
  adr_base100: "Cotización en Nueva York de los ADR de Galicia, YPF, Pampa, Macro y Vista, con valor 100 al inicio del período elegido. Precios de cierre en dólares por ADR, sin ajustar por dividendos, según Yahoo Finance.",
  tabla_adrs: "Último cierre de los ADR argentinos en Nueva York y su variación en el día, en 30 días, en el año y en 12 meses, en dólares, según Yahoo Finance. Las variaciones no incluyen dividendos.",

  // ---------------------------------------------------------------- industria
  ipi: "Índice de producción industrial manufacturero (IPI) e Indicador sintético de la actividad de la construcción (ISAC) del INDEC, series desestacionalizadas, base 2004 = 100. El título compara el último mes contra el anterior. Se leen directo de los Excel del INDEC, que publica unas cinco o seis semanas después del cierre del mes.",
  ipi_metalmecanica: "IPI manufacturero desestacionalizado de las divisiones metalmecánicas: industrias metálicas básicas (siderurgia, aluminio, fundición), productos de metal, maquinaria y equipo, vehículos automotores y autopartes, y otros equipos (aparatos eléctricos, electrónicos e instrumentos). Base 2004 = 100.",
  ipi_subclases: "Variación interanual de subclases del IPI manufacturero en serie original: industria siderúrgica, vehículos automotores, autopartes y maquinaria agropecuaria. La serie original tiene estacionalidad, por eso se compara contra el mismo mes del año anterior.",
  ipi_bienes_metal: "Variación interanual de subclases del IPI manufacturero en serie original: maquinaria de uso general, aparatos de uso doméstico (línea blanca) y productos metálicos para uso estructural.",
  isac_insumos: "Variación interanual de dos insumos del ISAC en serie original, cemento portland y hierro redondo y aceros para la construcción, y del ISAC total. Son índices del INDEC, base 2004 = 100.",

  tcrm_bilat: "El ITCRM es el índice de tipo de cambio real multilateral del BCRA, con base 17-12-15 = 100. Las otras dos líneas son los índices bilaterales con Brasil y con EE.UU. Un valor más alto indica un tipo de cambio real más alto.",

  // ---------------------------------------------------------------- balance cambiario
  bc_global: "Resultado de las cuentas corriente, capital y financiera del balance cambiario del BCRA y variación de las reservas por transacciones. El balance cambiario registra las operaciones que pasan por el mercado de cambios, en millones de USD. Un valor positivo indica ingreso de divisas y uno negativo, salida.",
  bc_cc: "Componentes de la cuenta corriente cambiaria: bienes, servicios, ingreso primario (intereses y utilidades) e ingreso secundario. Netos en millones de USD.",
  bc_bienes: "Cobros de exportaciones y pagos de importaciones de bienes por el mercado de cambios, con los pagos en negativo, y el saldo entre ambos. Se miden por el momento en que se cobra o se paga, de modo que difieren del comercio por embarques del INDEC.",
  bc_expo_mod: "Cobros de exportaciones por modalidad: cobros, anticipados, prefinanciaciones del exterior y financiaciones locales. Corresponde a la hoja MC por concepto del balance cambiario.",
  bc_impo_mod: "Pagos de importaciones por modalidad: diferidos y otros, a la vista y anticipados, con signo negativo. Corresponde a la hoja MC por concepto del balance cambiario.",
  bc_viajes: "Turismo en el balance cambiario: viajes y pasajes según la estimación del BCRA, consumos con tarjeta en el exterior y servicios totales. Netos en millones de USD.",
  bc_intereses: "Pagos de intereses por acreedor (FMI, otros organismos y otros) y giro de utilidades y dividendos, en millones de USD.",
  bc_cf: "Componentes de la cuenta financiera cambiaria: billetes y divisas del sector privado no financiero, préstamos y títulos de deuda, inversión directa, portafolio, FMI y otros organismos, entre otros. La línea es el total. Netos en millones de USD.",
  bc_cf_sector: "La cuenta financiera cambiaria abierta por sector: privado no financiero, financiero y gobierno general y BCRA. Corresponde a la hoja de cuenta financiera por sector, en millones de USD.",
  bc_personas: "Operaciones de personas humanas en el mercado de cambios, netas, en millones de USD. Un valor negativo indica demanda neta de divisas.",
  bc_fae: "Formación de activos externos del sector privado no financiero: compras y ventas de billetes y divisas sin fines específicos, otras inversiones en el exterior e inversión directa en el exterior. La línea es el neto en millones de USD.",
  bc_deuda: "Préstamos financieros, títulos de deuda y líneas de crédito: ingresos, cancelaciones y neto, en millones de USD.",
  bc_deuda_instr: "Deuda por instrumento: financiaciones locales y préstamos del exterior y títulos, en ingresos menos cancelaciones, en millones de USD.",
  bc_no_res: "Inversión de no residentes en el país, directa y de portafolio, en términos netos y en millones de USD.",
  bc_organismos: "Operaciones con el FMI y con otros organismos internacionales: desembolsos menos pagos de capital, en millones de USD.",
  bc_sec_expo: "Posición neta en el mercado de cambios de los sectores exportadores: agro (oleaginosos y cerealeros), energía (petróleo, gas y electricidad) y minería. Netos en millones de USD, positivo cuando el sector aporta divisas.",
  bc_sec_ind: "Posición neta en el mercado de cambios de ramas industriales: automotriz, maquinarias y equipos, metales comunes y química. Netos en millones de USD, negativo cuando el sector demanda divisas.",
  bc_sec_com: "Posición neta en el mercado de cambios de alimentos, comercio y sector público. Netos en millones de USD.",
  bc_sec_energia: "Posición neta en el mercado de cambios de las ramas de energía: petróleo, gas y electricidad. Netos en millones de USD.",

  // ---------------------------------------------------------------- internacional
  ust: "Rendimiento de los bonos del Tesoro de EE.UU. a 2, 10 y 30 años, en %, según el US Treasury. Es la tasa libre de riesgo que se usa para medir el riesgo país.",
  vix: "Índice de volatilidad implícita del S&P 500 (VIX). Valores altos indican más incertidumbre en los mercados. El eje se corta cuando hay picos fuera de escala.",
  sp500: "Nivel del índice bursátil S&P 500 de EE.UU., en puntos, según Yahoo Finance.",
  dxy: "Índice del dólar (DXY): el valor del dólar frente a una canasta de monedas, según Yahoo Finance. Una suba indica un dólar más fuerte.",
  brl: "Cotización del real brasileño, en reales por dólar, según Yahoo Finance. Una suba indica un real más débil.",
  brent: "Precio del petróleo Brent para el contrato más cercano, en USD por barril, según Yahoo Finance.",
  gas: "Precio del gas natural Henry Hub para el contrato más cercano, en USD por MMBtu, según Yahoo Finance. El eje se corta cuando hay picos fuera de escala.",
  soja: "Precio de la soja en Chicago (CBOT) para el contrato más cercano. La cotización original en centavos de dólar por bushel se convierte a USD por tonelada.",
  maiz: "Precio del maíz en Chicago (CBOT) para el contrato más cercano. La cotización original en centavos de dólar por bushel se convierte a USD por tonelada.",
  trigo: "Precio del trigo en Chicago (CBOT) para el contrato más cercano. La cotización original en centavos de dólar por bushel se convierte a USD por tonelada.",
  oro: "Precio del oro para el contrato más cercano, en USD por onza troy, según Yahoo Finance.",
  cobre: "Precio del cobre en Nueva York (COMEX) para el contrato más cercano. La cotización original en USD por libra se convierte a USD por tonelada.",
};

// Tipo de dato de cada tarjeta, por clave de MIDE.
const TIPOS = {
  "Oficial": "Dato publicado por el organismo, sin transformar.",
  "Mercado": "Cotización de mercado. En la rueda se muestra el último precio operado, con 20 minutos de demora, marcado como provisorio.",
  "Cálculo propio": "Calculado por el tablero a partir de datos oficiales o de mercado.",
  "Encuesta": "Mediana de las expectativas relevadas.",
};

const TIPO = {
  carry: "Cálculo propio",
  carry_curva: "Cálculo propio",
  futuros_banda: "Cálculo propio",
  merval_usd: "Cálculo propio",
  merval: "Mercado",
  adr_base100: "Mercado",
  tabla_adrs: "Mercado",
  recaudacion: "Cálculo propio",
  licitaciones: "Oficial",
  tabla_licitaciones: "Oficial",
  ipi: "Oficial",
  ipi_metalmecanica: "Oficial",
  ipi_subclases: "Cálculo propio",
  ipi_bienes_metal: "Cálculo propio",
  isac_insumos: "Cálculo propio",
  inflacion_implicita: "Cálculo propio",
  curva_inflacion: "Cálculo propio",
  servicio_deuda: "Cálculo propio",
  calendario: "Oficial",
  reservas_netas: "Cálculo propio",
  tabla_reservas: "Cálculo propio",
  reservas_brutas: "Oficial",
  compras: "Oficial",
  compras_pct: "Cálculo propio",
  dep_tesoro: "Cálculo propio",
  banda: "Oficial",
  tcr_bilateral: "Cálculo propio",
  tcrm: "Oficial",
  ccl_mep: "Cálculo propio",
  brecha_canje: "Cálculo propio",
  futuro: "Mercado",
  volumen_mlc: "Mercado",
  tasas_bancos: "Oficial",
  caucion: "Mercado",
  tasa_real: "Cálculo propio",
  curva_lecap: "Cálculo propio",
  tabla_bonos: "Mercado",
  curva_bonos: "Cálculo propio",
  tir_2030: "Cálculo propio",
  tir_largos: "Cálculo propio",
  precio_2030: "Mercado",
  precio_largos: "Mercado",
  precio_bopreales: "Mercado",
  riesgo_ppal: "Mercado",
  riesgo_desc: "Cálculo propio",
  riesgo_global: "Mercado",
  riesgo_largo: "Mercado",
  riesgo_tabla: "Mercado",
  riesgo_ranking: "Mercado",
  m2: "Cálculo propio",
  prestamos: "Cálculo propio",
  depositos_usd: "Oficial",
  ipc: "Oficial",
  rem: "Encuesta",
  emae: "Oficial",
  demanda_elec: "Oficial",
  comercio: "Oficial",
  resultado_primario: "Cálculo propio",
  tcrm_bilat: "Oficial",
  bc_global: "Oficial",
  bc_cc: "Oficial",
  bc_bienes: "Oficial",
  bc_expo_mod: "Oficial",
  bc_impo_mod: "Oficial",
  bc_viajes: "Oficial",
  bc_intereses: "Oficial",
  bc_cf: "Oficial",
  bc_cf_sector: "Oficial",
  bc_personas: "Oficial",
  bc_fae: "Oficial",
  bc_deuda: "Oficial",
  bc_deuda_instr: "Oficial",
  bc_no_res: "Oficial",
  bc_organismos: "Oficial",
  bc_sec_expo: "Oficial",
  bc_sec_ind: "Oficial",
  bc_sec_com: "Oficial",
  bc_sec_energia: "Oficial",
  ust: "Oficial",
  vix: "Mercado",
  sp500: "Mercado",
  dxy: "Mercado",
  brl: "Mercado",
  brent: "Mercado",
  gas: "Mercado",
  soja: "Mercado",
  maiz: "Mercado",
  trigo: "Mercado",
  oro: "Mercado",
  cobre: "Mercado",
};
