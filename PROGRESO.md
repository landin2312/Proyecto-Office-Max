# PROGRESO

## Proyecto

Office Max Elasticidad Promocional

## Estado Actual

Se procesaron las carpetas de promociones de **JUNIO a OCTUBRE**.

| Métrica | Valor |
|---|---:|
| Archivos procesados | 275 |
| Filas extraídas | 8500 |
| Errores críticos | 0 |
| Advertencias | 237 |
| Archivos para revisión manual | 71 |

## Hallazgos De Calidad

| Campo | % NULL |
|---|---:|
| SKU (`prod_nbr`) | 0.08% |
| `descuento_pct` | 14.59% |
| `prod_nm` | 33.61% |
| `fecha_inicio` | 84.87% |
| `fecha_fin` | 99.48% |
| `departamento` | 98.67% |

## Tipos Detectados

| tipo_promo | Filas |
|---|---:|
| descuento | 2582 |
| 3x2 | 2306 |
| regalo | 1864 |
| 2x1 | 122 |
| precio | 241 |

## Promociones Por Mes

| mes_carpeta | Filas |
|---|---:|
| JUNIO | 1167 |
| JULIO | 1964 |
| AGOSTO | 4169 |
| SEPTIEMBRE | 544 |
| OCTUBRE | 656 |

## Pendiente Para La Siguiente Sesión

Buscar fechas dentro de `promo_texto` usando patrones:

- `dd/mm/yyyy`
- `dd-mm-yyyy`
- `del X al Y`
- `vigencia`
- `válido hasta`
- `hasta el`

Mostrar:

- 20 ejemplos
- porcentaje con fecha detectable

## Avance 2026-05-19

Se creo `scripts/analizar_fechas_promo_texto.py` y se ejecuto sobre `output/promociones_master.csv`.

Hallazgo nuevo:

Se detectaron fechas en `promo_texto` para 149 de 204 promociones unicas (73.04%).

Resultados sobre promociones unicas (`promo_id` + `archivo_origen`):

| Metrica | Valor |
|---|---:|
| Promociones unicas analizadas | 204 |
| Promociones con fecha detectable en `promo_texto` | 149 |
| Porcentaje con fecha detectable | 73.04% |

Salida generada:

- `output/fechas_promo_texto.csv`

Conteo de hallazgos por patron:

| Patron | Hallazgos |
|---|---:|
| `vigencia` | 151 |
| `dd al dd mes yyyy` | 100 |
| `dd/mm/yyyy` | 48 |
| `del X al Y` | 15 |
| `dd-dd mes yyyy` | 15 |
| `dd.mm.yy` | 13 |
| `hasta el` | 7 |
| `hasta dia mes` | 1 |

Conclusion:

Las promociones si contienen vigencias detectables, lo que permitira unir promociones y ventas por periodo.

Siguiente paso recomendado:

- Normalizar los hallazgos de `promo_texto` a fechas ISO y usarlos para completar `fecha_inicio`, `fecha_fin` y `duracion_dias` cuando el extractor original no las haya poblado.

## Objetivo Posterior

Cruzar:

- `promociones_master`
- `Catalogo_Producto`
- `Ventas_2024_2026`
- `Precios_Producto`

para crear `MASTER_FINAL`.

## Avance MASTER_FINAL 2026-05-19

Se creo `scripts/crear_master_final_elasticidad.py` para construir una base SKU-MES y calcular elasticidad dinamica.

Insumos usados:

- `Ventas_2024_2026 - Ventas_2024_2026.csv`
- `Precios_Producto - Precios_Producto.csv`
- `Catalogo_Producto - Catalogo_Producto.csv`
- `output/promociones_master.csv`

Salidas generadas:

- `output/MASTER_FINAL_SKU_MES.csv`
- `output/elasticidad_dinamica_betas.csv`

Resumen `MASTER_FINAL_SKU_MES`:

| Metrica | Valor |
|---|---:|
| Filas SKU-MES | 16322 |
| SKUs | 3150 |
| Meses | 28 |
| Rango fecha | 2024-01 a 2026-04 |
| Filas con promocion | 719 |

Variables creadas:

- `unidades_vendidas`
- `precio_promedio`
- `descuento_promedio`
- `indicador_promocion`
- `fecha`

Resumen elasticidad dinamica:

| tipo_ventana | Filas | Betas calculables |
|---|---:|---:|
| mensual | 16322 | 0 |
| trimestral | 16322 | 5261 |
| semestral | 16322 | 7967 |

Nota metodologica:

- La ventana mensual no genera beta calculable porque `MASTER_FINAL` esta agregado a nivel SKU-MES y cada ventana mensual contiene una sola observacion. Las ventanas trimestral y semestral si permiten estimar `ln(qty) ~ ln(price)` cuando hay al menos dos meses validos y variacion de precio.

## Correccion MASTER_FINAL SKU-FECHA 2026-05-19

Problema detectado:

- `MASTER_FINAL_SKU_MES` agregaba demasiado temprano y eliminaba variacion necesaria para estimar beta mensual.

Se creo `scripts/crear_master_final_sku_fecha_elasticidad.py` para mantener mayor granularidad antes de calcular elasticidades.

Nuevo master:

- `output/MASTER_FINAL_SKU_FECHA.csv`

Variables principales:

- `prod_nbr`
- `fecha`
- `precio`
- `qty`
- `promocion`
- `descuento`

Resumen `MASTER_FINAL_SKU_FECHA`:

| Metrica | Valor |
|---|---:|
| Filas SKU-FECHA | 29362 |
| SKUs | 3150 |
| Fechas | 841 |
| Rango fecha | 2024-01-02 a 2026-04-25 |
| Filas con promocion | 1510 |

Nueva salida de elasticidad:

- `output/elasticidad_dinamica_betas_sku_fecha.csv`

Columnas:

- `SKU`
- `periodo_inicio`
- `periodo_fin`
- `tipo_ventana`
- `beta`
- `r2`
- `n_observaciones`

Resumen de betas:

| tipo_ventana | Filas | Betas calculables |
|---|---:|---:|
| mensual | 16322 | 2007 |
| trimestral | 24778 | 6935 |
| semestral | 29249 | 11864 |

Conclusion:

- Al conservar granularidad SKU-FECHA, si se pudieron calcular betas mensuales: 2007.
- Las ventanas trimestrales y semestrales se calculan como ventanas moviles de meses consecutivos sobre observaciones diarias.

## Validacion Ventanas Moviles 2026-05-19

Se valido la metodologia de ventanas moviles contra el criterio del profesor:

- Mensual: `1`, `2`, `3`, `4`
- Trimestral: `1-3`, `2-4`, `3-5`, `4-6`
- Semestral: `1-6`, `2-7`, `3-8`, `4-9`

Correccion aplicada:

- El calculo anterior desplazaba ventanas +1, pero trimestral/semestral estaban ancladas hacia atras respecto al mes de cierre.
- Se actualizo `scripts/crear_master_final_sku_fecha_elasticidad.py` para usar ventanas forward, donde `periodo_inicio` es el primer mes del bloque y `periodo_fin` es el ultimo dia del ultimo mes del bloque.

Salidas regeneradas:

- `output/elasticidad_dinamica_betas_sku_fecha.csv`
- `output/MASTER_FINAL_SKU_FECHA.csv`

Resumen despues de corregir ventanas:

| tipo_ventana | Filas | Betas calculables |
|---|---:|---:|
| mensual | 16322 | 2007 |
| trimestral | 19600 | 6154 |
| semestral | 18820 | 9168 |

Validacion SKU ejemplo:

- SKU: `50106204`
- CSV: `output/validacion_ventanas_50106204.csv`
- Grafica: `output/beta_temporal_50106204.png`

## Entrega Departamento PAPEL 2026-05-19

Contexto:

- Para la entrega del equipo se limita el analisis a `dept_nm = PAPEL`.
- El objetivo es entregar betas dinamicas y graficas para SKUs del departamento Papel.

Script creado:

- `scripts/filtrar_departamento_papel.py`

Salidas especificas de Papel:

- `output/MASTER_FINAL_SKU_FECHA_PAPEL.csv`
- `output/elasticidad_dinamica_betas_papel.csv`
- `output/diagnostico_betas_papel.csv`
- `output/graficas_betas_papel/`
- `output/cambios_importantes_betas_papel.csv`
- `output/resumen_cambios_betas_papel.csv`

Resumen `MASTER_FINAL_SKU_FECHA_PAPEL`:

| Metrica | Valor |
|---|---:|
| Filas SKU-FECHA | 4396 |
| SKUs | 202 |
| Fechas | 832 |
| Filas con promocion | 266 |

Resumen betas Papel:

| tipo_ventana | Total ventanas | Betas validas | % valido |
|---|---:|---:|---:|
| mensual | 1857 | 223 | 12.01% |
| trimestral | 2227 | 660 | 29.64% |
| semestral | 2091 | 951 | 45.48% |

SKUs con beta mensual valida:

- 56 de 202 SKUs (27.72%).

Razones de exclusion en Papel:

| Razon | Ventanas | % |
|---|---:|---:|
| `n<3` | 2710 | 62.43% |
| `precio constante` | 871 | 20.06% |
| `datos insuficientes` | 615 | 14.17% |
| `qty constante` | 145 | 3.34% |

Graficas:

- Se generaron 20 graficas para los SKUs de Papel con mas betas validas.
- Directorio: `output/graficas_betas_papel/`
- Se detectaron 467 cambios importantes usando `abs(delta_beta) >= 1.0` o cambio de signo.

## Dashboard Papel 2026-05-19

Se creo un dashboard HTML autonomo para presentar el analisis de elasticidad del departamento `PAPEL`.

Script:

- `scripts/generar_dashboard_papel.py`

Salida:

- `output/dashboard_elasticidad_papel.html`

Filtros:

- SKU
- Tipo de ventana: mensual, trimestral, semestral
- R2 minimo
- N minimo de observaciones

Visualizaciones incluidas:

- Linea temporal de beta.
- Precio promedio y cantidad mensual.
- Heatmap de beta.
- Heatmap de R2.
- Heatmap de numero de observaciones.
- Heatmap de promocion.
- Scatter log(precio) vs log(qty).
- Tabla de cambios importantes de beta.

Datos cargados:

- 202 SKUs de `PAPEL`.
- Betas de `output/elasticidad_dinamica_betas_papel.csv`.
- Series mensuales derivadas de `output/MASTER_FINAL_SKU_FECHA_PAPEL.csv`.
- Cambios importantes desde `output/cambios_importantes_betas_papel.csv`.

## Reporte PDF Papel 2026-05-19

Debido a problemas practicos con el filtro dinamico del dashboard, se genero una version estatica para entrega.

Script:

- `scripts/generar_reporte_pdf_papel.py`

Salida:

- `output/reporte_elasticidad_papel.pdf`

Contenido:

- Portada con metodologia y resumen del departamento `PAPEL`.
- Pagina de insights principales.
- Tabla de betas validas por tipo de ventana.
- Tabla de razones de exclusion.
- Barras de beta mediana por ventana.
- Barras de R2 mediana por ventana.
- Barras de N mediana por ventana.
- Histograma de betas validas.
- Histograma de R2.
- Heatmap agregado de beta mediana.
- Heatmap agregado de R2.
- Heatmap agregado de N observaciones.
- Heatmap de porcentaje de filas con promocion.
- Scatter `ln(precio)` vs `ln(qty)`.
- Comparativo precio/qty con promocion vs sin promocion.
- Top 20 SKUs de Papel con mas betas validas.
- Tabla de cambios importantes de beta por SKU y ventana.
- 20 graficas SKU con beta mensual, trimestral y semestral.

## Reporte Estilo Ejemplo Mejorado 2026-05-19

Se reviso `Ejemplos/elasticidad_visualizaciones.pdf` y se genero una version equivalente para el departamento `PAPEL`, usando nuestro flujo y ventanas corregidas.

Script:

- `scripts/generar_reporte_papel_estilo_ejemplo.py`

Salida:

- `output/reporte_elasticidad_papel_estilo_ejemplo.pdf`

Contenido:

- Portada con KPIs del departamento Papel.
- Insights principales.
- Heatmap de beta por SKU y trimestre.
- Heatmap de R2 por SKU y trimestre.
- Estacionalidad trimestral: beta promedio/mediana y porcentaje de SKUs elasticos.
- Evolucion de beta por SKU en paneles.
- Top 15 SKUs mas elasticos.
- Top 15 SKUs con beta positiva/anomala.
- Evidencia precio-cantidad: scatter `ln(precio)` vs `ln(qty)` y comparativo promocion/no promocion.

Metricas del reporte:

| Metrica | Valor |
|---|---:|
| SKUs Papel | 202 |
| SKUs con beta trimestral valida | 71 |
| Estimaciones trimestrales validas | 660 |
| Estimaciones con R2 >= 0.20 | 222 |
| Estimaciones elasticas beta < -1 | 257 |
| Estimaciones anomalas beta >= 0 | 315 |

## Nueva Base OfficeMax 19 Mayo 2026-05-19

Se recibio `Base_OfficeMax19mayo.csv`, una base mas limpia con precio, qty, tienda, fecha, costos, utilidad y margen.

Hallazgo importante:

- La nueva base no contiene `dept_nm = PAPEL`.
- Departamentos disponibles:
  - `SUMINISTROS DE OFICINA`
  - `CARPETAS`
  - `ARCHIVO Y ACCESORIOS`
  - `ARTICULOS ESCOLARES`

Cambio metodologico:

- Se adopto agregacion `SKU x tienda x mes`, similar al ejemplo recibido.
- Esto permite que una ventana mensual tenga multiples observaciones por tiendas, evitando el problema de una sola observacion por SKU-mes.
- Regresion: `ln(qty) ~ ln(precio)`.
- Ventanas forward:
  - mensual: `1`, `2`, `3`
  - trimestral: `1-3`, `2-4`, `3-5`
  - semestral: `1-6`, `2-7`, `3-8`

Script nuevo:

- `scripts/modelo_elasticidad_base19mayo.py`

Salidas base completa:

- `output/base19mayo/MASTER_SKU_TIENDA_MES.csv`
- `output/base19mayo/betas_dinamicas.csv`
- `output/base19mayo/diagnostico_betas.csv`

Resumen base completa:

| Metrica | Valor |
|---|---:|
| Filas base | 26980 |
| Filas SKU-tienda-mes | 25907 |
| SKUs | 1750 |
| Tiendas | 85 |
| Meses | 28 |
| Betas mensuales validas | 798 |
| Betas trimestrales validas | 2584 |
| Betas semestrales validas | 4264 |

Se generaron tambien salidas separadas por departamento en `output/base19mayo/`.

Resumen por departamento:

| Departamento | Filas SKU-tienda-mes | SKUs | Beta mensual | Beta trimestral | Beta semestral |
|---|---:|---:|---:|---:|---:|
| `CARPETAS` | 8289 | 736 | 259 | 837 | 1367 |
| `ARCHIVO Y ACCESORIOS` | 5657 | 238 | 178 | 598 | 1016 |
| `SUMINISTROS DE OFICINA` | 8914 | 342 | 288 | 892 | 1431 |
| `ARTICULOS ESCOLARES` | 3047 | 434 | 73 | 257 | 450 |

Reporte estilo ejemplo para nueva base:

- Script: `scripts/generar_reporte_base19mayo.py`
- Salida: `output/base19mayo/reporte_base19mayo_estilo_ejemplo.pdf`

Metricas del reporte completo:

| Metrica | Valor |
|---|---:|
| SKUs | 1750 |
| Tiendas | 85 |
| Estimaciones trimestrales validas | 2584 |
| Estimaciones con R2 >= 0.20 | 685 |
| Estimaciones elasticas beta < -1 | 987 |
| Estimaciones anomalas beta >= 0 | 1198 |

## Tarea Modelos 1 y 2 Base 19 Mayo 2026-05-19

Se completo lo pedido por el profesor usando `Base_OfficeMax19mayo.csv`.

Modelo 1:

- Modelo log-log simple: `ln(qty) ~ ln(precio)`.
- Granularidad: `SKU x tienda x mes`.
- Ventanas:
  - mensual: mes `1`, `2`, `3`, ...
  - trimestral: `1-3`, `2-4`, `3-5`, ...
  - semestral: `1-6`, `2-7`, `3-8`, ...
- Salidas:
  - `output/base19mayo/MASTER_SKU_TIENDA_MES.csv`
  - `output/base19mayo/betas_dinamicas.csv`
  - `output/base19mayo/diagnostico_betas.csv`

Modelo 2:

- Modelo log-log multivariable:
  - `ln(qty) ~ ln(precio) + margen + ln(costo_unitario) + fechas_venta + mes + anio + tienda + departamento + subdepartamento + tipo_marca`
- Se excluyo `net_sale` como variable explicativa porque contiene `precio x cantidad`.
- Salidas:
  - `output/base19mayo/modelo2_multivariable_resumen.csv`
  - `output/base19mayo/modelo2_multivariable_coeficientes.csv`
  - `output/base19mayo/modelo2_multivariable_sku.csv`
  - `output/base19mayo/modelo2_multivariable_por_departamento.csv`

Resultado Modelo 2 global:

| Metrica | Valor |
|---|---:|
| Observaciones | 25907 |
| SKUs | 1750 |
| R2 global | 0.2099 |
| Beta precio global | 0.0097 |

Resultado Modelo 2 por departamento:

| Departamento | R2 | Beta precio |
|---|---:|---:|
| `ARCHIVO Y ACCESORIOS` | 0.2339 | 0.0414 |
| `ARTICULOS ESCOLARES` | 0.1415 | -0.0788 |
| `CARPETAS` | 0.1903 | -0.0449 |
| `SUMINISTROS DE OFICINA` | 0.1958 | 0.0426 |

Nota metodologica:

- El Modelo 1 es mejor para elasticidad dinamica por SKU.
- El Modelo 2 es mejor para explicar cantidad vendida de forma general.
- A nivel SKU, el Modelo 2 casi no es viable porque muchos SKUs tienen precio constante en la nueva base.

Reporte final:

- `output/base19mayo/reporte_tarea_modelos_base19mayo.pdf`

## Entrega Elasticidad Consigna Final 2026-05-19

Se creo `scripts/analisis_elasticidad_entrega.py` para generar la entrega solicitada con la base limpia `Base_OfficeMax19mayo.csv` y los archivos existentes del proyecto.

Revision de columnas:

- Se revisaron columnas de:
  - `output/MASTER_FINAL_SKU_FECHA.csv`
  - `output/elasticidad_dinamica_betas_sku_fecha.csv`
  - `Catalogo_Producto - Catalogo_Producto.csv`
  - `Ventas_2024_2026 - Ventas_2024_2026.csv`
  - `Precios_Producto - Precios_Producto.csv`
  - `output/promociones_master.csv`

Base de calculo:

- Se uso `Base_OfficeMax19mayo.csv`.
- Granularidad analitica: `SKU x tienda x mes`.
- Variable de precio: `precio_real = net_sale / unidades`.
- Modelo 1: `log(unidades + 1) = alpha + beta * log(precio_real)`.
- Modelo 2: `log(unidades + 1) = alpha + beta * log(precio_real) + controles disponibles`.

Variables adicionales usadas en Modelo 2 cuando existen y tienen variacion:

- `margen`
- `log(costo_unitario)`
- `fechas_venta`
- `mes`
- `tienda`
- `marca`
- `tipo_marca`
- `departamento`
- `subdepartamento`
- `clase`

Variables omitidas por no existir en `Base_OfficeMax19mayo.csv`:

- `indicador_promocion`
- `descuento_pct`
- `tipo_promo`

Salidas validas para entrega final usando solo `Base_OfficeMax19mayo.csv`:

- `output/entrega_base19mayo/modelo1_betas_loglog.csv`
- `output/entrega_base19mayo/modelo2_betas_con_controles.csv`
- `output/entrega_base19mayo/resumen_elasticidad_entrega.xlsx`
- `output/entrega_base19mayo/skus_graficados_base19mayo.csv`
- `output/entrega_base19mayo/graficas_elasticidad/elasticidad_sku_50066389.png`
- `output/entrega_base19mayo/graficas_elasticidad/elasticidad_sku_50066390.png`
- `output/entrega_base19mayo/graficas_elasticidad/elasticidad_sku_50062115.png`

Nota operativa:

- Los archivos en la raiz de `output/` corresponden a corridas previas o quedaron bloqueados por permisos/archivos abiertos.
- Desde este punto, la carpeta oficial de entrega es `output/entrega_base19mayo/`.

Hojas del Excel:

- `resumen_general`
- `modelo1_betas`
- `modelo2_betas`
- `diagnostico`
- `top_skus_elasticos`
- `top_skus_inelasticos`
- `betas_positivas_revision`

Resultados Modelo 1:

| Metrica | Valor |
|---|---:|
| SKUs analizados | 1750 |
| Ventanas totales | 46266 |
| Betas calculadas | 9924 |
| Betas mensuales | 1311 |
| Betas trimestrales | 3523 |
| Betas semestrales | 5090 |
| % beta positiva | 9.89% |
| % elasticas | 7.76% |
| % inelasticas | 3.80% |

Resultados Modelo 2:

| Metrica | Valor |
|---|---:|
| SKUs analizados | 1750 |
| Ventanas totales | 46266 |
| Betas calculadas | 6889 |
| Betas mensuales | 607 |
| Betas trimestrales | 2346 |
| Betas semestrales | 3936 |
| % beta positiva | 6.90% |
| % elasticas | 7.36% |
| % inelasticas | 0.63% |

Principales razones no calculables:

| Modelo | Razon | Ventanas |
|---|---|---:|
| Modelo 1 | `n<3` | 28330 |
| Modelo 2 | `n<3` | 28330 |
| Modelo 1 | `precio constante` | 4634 |
| Modelo 2 | `precio constante` | 4634 |
| Modelo 1 | `unidades constantes` | 3378 |
| Modelo 2 | `unidades constantes` | 3378 |
| Modelo 2 | `controles>observaciones` | 3035 |

Nota sobre graficas:

- Los SKUs `50106204`, `50084493` y `50077229` no existen en `Base_OfficeMax19mayo.csv`.
- Para no mezclar bases ni inventar datos, la entrega final usa SKUs seleccionados de la base del 19 de mayo.
- SKUs graficados en la entrega final: `50066389`, `50066390`, `50062115`.
