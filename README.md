# Proyecto Office Max

Proyecto de analisis de elasticidad promocional para Office Max. El front publicado en GitHub Pages contiene el simulador de elasticidad; este README documenta el modelo CRISP-DM, los modelos estadisticos que alimentan el simulador y las metricas principales de evaluacion.

## Reporte Visual Para Revision

### Flujo CRISP-DM Del Proyecto

```mermaid
flowchart LR
    A["1. Negocio<br/>Definir problema de pricing y promociones"] --> B["2. Datos<br/>Ventas, precios, costos, catalogo y tiendas"]
    B --> C["3. Preparacion<br/>Limpieza, precio real y base SKU x tienda x mes"]
    C --> D["4. Modelado<br/>Elasticidad log-log y modelo con controles"]
    D --> E["5. Evaluacion<br/>R2, n observaciones, betas validas y diagnostico"]
    E --> F["6. Despliegue<br/>Simulador web en GitHub Pages"]
    F -. retroalimentacion .-> A
```

### Resumen Ejecutivo Del Modelo Del Simulador

| Pregunta de revision | Respuesta del proyecto |
|---|---|
| Que predice el modelo? | El cambio esperado en unidades vendidas ante cambios de precio. |
| Que variable usa el simulador? | `beta_precio`, que representa elasticidad precio-demanda. |
| Cual es el modelo base? | Regresion log-log: `log(unidades + 1) = alpha + beta * log(precio_real)`. |
| Cual es la granularidad? | `SKU x tienda x mes`. |
| Por que esa granularidad? | Permite varias observaciones por SKU dentro de una ventana mensual usando tiendas. |
| Como se mide calidad? | R2, numero de observaciones y porcentaje de betas calculables. |
| Modelo recomendado para simulador | Modelo 1, porque genera mas betas y es mas interpretable. |
| Modelo de validacion | Modelo 2, porque agrega controles y mejora R2 cuando hay datos suficientes. |

### Indicadores Clave

| Indicador | Modelo 1: log-log simple | Modelo 2: con controles |
|---|---:|---:|
| SKUs analizados | 1750 | 1750 |
| Ventanas evaluadas | 46266 | 46266 |
| Betas calculadas | 9924 | 6889 |
| Cobertura de betas | 21.45% | 14.89% |
| R2 promedio | 0.3225 | 0.6590 |
| R2 mediana | 0.1111 | 0.7349 |
| Beta mediana | -0.1621 | -0.5850 |
| N mediana | 8 | 12 |

### Calidad Del Modelo Por Ventana

| Modelo | Ventana | Betas validas | SKUs con beta | R2 promedio | R2 mediana | Interpretacion |
|---|---|---:|---:|---:|---:|---|
| Modelo 1 | Mensual | 1311 | 365 | 0.4774 | 0.3333 | Mejor ventana del modelo simple para reaccion mensual. |
| Modelo 1 | Trimestral | 3523 | 528 | 0.3537 | 0.1423 | Balance entre cobertura y estabilidad. |
| Modelo 1 | Semestral | 5090 | 559 | 0.2610 | 0.0686 | Mayor cobertura, pero menor ajuste mediano. |
| Modelo 2 | Mensual | 607 | 145 | 0.7117 | 0.7956 | Alto ajuste, pero menor cobertura. |
| Modelo 2 | Trimestral | 2346 | 339 | 0.6973 | 0.7920 | Buen ajuste con controles. |
| Modelo 2 | Semestral | 3936 | 430 | 0.6281 | 0.6823 | Mejor cobertura del modelo controlado. |

### Lectura De Calidad

El Modelo 1 es el modelo operativo del simulador porque produce mas elasticidades disponibles por SKU y mantiene una interpretacion directa: el coeficiente `beta_precio` indica cuanto cambia la demanda cuando cambia el precio. Su R2 no siempre es alto porque usa solo precio como variable explicativa; esto es esperado en ventas reales, donde tambien influyen tienda, estacionalidad, marca, inventario y otros factores.

El Modelo 2 funciona como comprobacion estadistica adicional. Al incluir controles, su R2 promedio sube de `0.3225` a `0.6590` y su R2 mediana sube de `0.1111` a `0.7349`. Esto confirma que las variables adicionales explican mejor la cantidad vendida, aunque el modelo calcula menos ventanas porque necesita mas observaciones para evitar sobreajuste.

### Criterio Minimo De Uso: R2 >= 0.50

Para tomar decisiones con el simulador se define como criterio minimo que la estimacion tenga `R2 >= 0.50`. Un R2 menor a 0.50 indica que el modelo explica menos de la mitad de la variacion observada, por lo que la recomendacion debe considerarse de baja confianza.

| Modelo | Betas calculadas | Betas con R2 >= 0.50 | % con R2 >= 0.50 |
|---|---:|---:|---:|
| Modelo 1 | 9924 | 2757 | 27.78% |
| Modelo 2 | 6889 | 4522 | 65.64% |

| Modelo | Mensual con R2 >= 0.50 | Trimestral con R2 >= 0.50 | Semestral con R2 >= 0.50 |
|---|---:|---:|---:|
| Modelo 1 | 578 | 1083 | 1096 |
| Modelo 2 | 451 | 1643 | 2428 |

Con este criterio, el Modelo 2 es mas fuerte para justificar calidad predictiva. El Modelo 1 se mantiene como lectura base de elasticidad, pero el simulador debe priorizar resultados que cumplan:

```text
R2 >= 0.50
n_observaciones >= 8
beta_precio < 0
beta_precio >= -5
```

### Como Mejorar El Modelo 1

El Modelo 1 queda mas bajo porque intenta explicar las unidades vendidas usando solamente el precio. En ventas reales, el precio no es la unica causa de variacion: tambien influyen tienda, mes, marca, disponibilidad, margen, costo y comportamiento por departamento.

Mejoras recomendadas:

| Mejora | Impacto esperado |
|---|---|
| Filtrar betas con `R2 >= 0.50` | Evita que el simulador use elasticidades de baja confianza. |
| Exigir `n_observaciones >= 8` | Reduce regresiones inestables por pocas observaciones. |
| Excluir betas extremas, por ejemplo `beta < -5` | Evita decisiones basadas en coeficientes causados por poca variacion de precio. |
| Usar ventanas trimestrales o semestrales cuando mensual sea debil | Aumenta observaciones y estabilidad. |
| Usar Modelo 2 como fallback | Mejora explicabilidad al controlar tienda, mes, marca, costo y margen. |
| Crear fallback por subdepartamento o departamento | Permite recomendar cuando un SKU tiene pocos datos. |

Estrategia operativa del simulador:

1. Usar beta del SKU si cumple `R2 >= 0.50`, `n_observaciones >= 8` y beta negativa razonable.
2. Si no cumple, usar Modelo 2 para el mismo SKU y ventana.
3. Si tampoco cumple, usar una elasticidad agregada por subdepartamento.
4. Si no hay suficiente evidencia, mostrar "baja confianza" y no recomendar una decision automatica.

Implementacion en el front:

- El simulador reconoce columnas `r2`, `n_observaciones`, `modelo` y `tipo_ventana`.
- Por cada SKU selecciona la mejor beta disponible que cumpla los criterios de calidad.
- Prioriza estimaciones del modelo con controles cuando existen.
- Si una beta no cumple `R2 >= 0.50`, `n_observaciones >= 8`, `beta_precio < 0` y `beta_precio >= -5`, la marca como baja confianza.
- Para SKUs de baja confianza, el simulador no debe interpretar la elasticidad como recomendacion automatica.
- Visualmente, el simulador muestra un semaforo: verde para buena probabilidad, amarillo para proyeccion neutral y rojo para alto riesgo estadistico.
- El dashboard incluye un interpretador automatico de tarjetas y graficas con lectura ejecutiva, riesgo del modelo, insights, recomendaciones y conclusiones del escenario.
- La vista predictiva incluye filtros propios de departamento, categoria y SKU, tarjetas incrementales y graficas de comparacion base vs simulado y curva de descuento.
- La grafica principal de escenarios compara ingresos y utilidad incremental contra el precio actual; se evita tratar las columnas simuladas como promociones reales porque la base no contiene campana, vigencia o mecanica promocional observada.

### Clasificacion De Resultados

| Modelo | Elasticos `beta < -1` | Inelasticos `-1 < beta < 0` | Beta positiva / revision |
|---|---:|---:|---:|
| Modelo 1 | 3588 | 1758 | 4578 |
| Modelo 2 | 3405 | 291 | 3193 |

Las betas positivas se marcan como revision porque una relacion positiva precio-cantidad puede deberse a estacionalidad, mezcla de tiendas, disponibilidad, cambios de demanda o ruido en ventanas pequenas. El simulador debe priorizar betas con R2 aceptable y suficiente `n_observaciones`.

### Evidencia Para El Profesor

| Elemento solicitado | Donde esta documentado |
|---|---|
| Metodologia CRISP-DM visual | Diagrama y seccion `Modelo CRISP-DM` de este README. |
| Modelo que usa el simulador | Seccion `Modelo 1: Elasticidad Log-Log Simple`. |
| Modelo de comparacion | Seccion `Modelo 2: Log-Log Con Controles`. |
| Tabla de R2 | Secciones `Indicadores Clave` y `Calidad Del Modelo Por Ventana`. |
| Diagnostico de datos insuficientes | Seccion `Razones Principales De Exclusion`. |
| Archivos de resultados | `output/entrega_base19mayo/`. |
| Front del simulador | `index.html` y GitHub Pages. |

## Simulador Interactivo

- Front: `index.html`
- GitHub Pages: `https://landin2312.github.io/Proyecto-Office-Max/`
- Uso local: abrir `index.html` en el navegador.

El simulador permite cargar bases CSV, filtrar SKUs, revisar elasticidad, probar descuentos y estimar impacto esperado en unidades, ingresos y margen. La logica del simulador usa elasticidades estimadas con modelos log-log y muestra confianza del modelo con base en R2 y numero de observaciones.

## Modelo CRISP-DM

### 1. Entendimiento Del Negocio

El objetivo del proyecto es estimar que tan sensible es la demanda de productos de Office Max ante cambios de precio y promociones. La pregunta central es:

> Si se aplica un descuento a un SKU, cuanto podria cambiar la cantidad vendida y que impacto tendria en ingresos y margen?

El resultado esperado es un simulador que apoye decisiones de pricing y promociones por SKU, separando productos elasticos, inelasticos y casos que requieren revision.

### 2. Entendimiento De Los Datos

Se revisaron fuentes historicas de ventas, precios, catalogo, costos y promociones. La base oficial actual es `BASE_FINAL_OM - Oficial.csv`, con **26,980 filas x 58 columnas** a nivel linea de ticket por SKU, tienda y fecha. La llave operativa mas cercana es:

```text
store_nbr + tran_date + tran_nbr + sku
```

La base contiene las variables necesarias para estimar y simular elasticidad de forma consistente:

- SKU (`sku`)
- tienda (`store_nbr`)
- nombre de tienda (`store_nm`)
- fecha de venta (`tran_date`)
- numero de ticket (`tran_nbr`)
- unidades vendidas (`unidades`)
- precio observado real (`precio_real`)
- precio listado (`precio`)
- venta neta (`venta_neta`)
- margen (`margen`)
- costo unitario calculado (`costo_calculado`)
- utilidad (`utilidad`)
- departamento, subdepartamento, clase, proveedor, marca y tipo de marca

La variable recomendada de precio es `precio_real`, porque coincide con `venta_neta / unidades`. No se recomienda usar `precio` como variable principal porque en 12,445 filas difiere del precio efectivamente pagado por mas de 0.02.

La base tambien contiene columnas de escenarios simulados (`precio_nuevo_*`, `unidades_sim_*`, `ingresos_sim_*`) y outputs de modelos previos (`beta_utilizada`, `alpha`, `r2`, `n_observaciones`, `clasificacion_elasticidad`). Estas columnas pueden usarse para el dashboard y validacion, pero deben excluirse del entrenamiento de un modelo nuevo para evitar fuga de informacion.

### 3. Preparacion De Datos

El script principal de entrega es:

- `scripts/analisis_elasticidad_entrega.py`

Transformaciones principales:

- Limpieza y conversion de variables numericas.
- Conversion de `tran_date` a periodo mensual.
- Filtrado de registros con unidades y precio validos.
- Uso de `precio_real = venta_neta / unidades` como precio observado.
- Agregacion recomendada a `SKU x tienda x semana` para reducir ruido de ticket individual.
- Agregacion alternativa a `SKU x tienda x fecha` cuando exista suficiente volumen.
- Creacion de ventanas moviles:
  - mensual: 1 mes
  - trimestral: 3 meses
  - semestral: 6 meses
- Exclusion de ventanas no modelables por `n<3`, precio constante, unidades constantes o exceso de controles frente al numero de observaciones.

Variables que deben excluirse del entrenamiento:

- Simulaciones: `precio_nuevo_*`, `unidades_sim_*`, `ingresos_sim_*`.
- Outputs previos: `beta_utilizada`, `alpha`, `r2`, `n_observaciones`, `clasificacion_elasticidad`.
- Columnas ambiguas: `-10%_dup`, `-5%_dup`, `5%_dup`, `10%_dup`.
- Constantes: `bl` y `mess_unit`.
- Redundante: `ingresos_reales`, si ya se usa `venta_neta`.

Variables de promocion real como campana, vigencia, cupon o mecanica promocional no existen en la base oficial. Por eso el modelo mide sensibilidad precio-demanda y no efecto causal completo de promocion.

### 4. Modelado

Se construyeron dos modelos para trabajar con el simulador.

#### Modelo 1: Elasticidad Log-Log Simple

Formula:

```text
log(unidades + 1) = alpha + beta * log(precio_real)
```

Uso principal:

- Estimar elasticidad dinamica por SKU.
- Alimentar el simulador con una beta interpretable.
- Comparar sensibilidad por ventana mensual, trimestral y semestral.

Interpretacion de beta:

- `beta < -1`: producto elastico.
- `-1 < beta < 0`: producto inelastico.
- `beta >= 0`: caso anomalo o candidato a revision, porque la relacion precio-cantidad no sigue el comportamiento esperado.

#### Modelo 2: Log-Log Con Controles

Formula base:

```text
log(unidades + 1) = alpha + beta * log(precio_real) + controles
```

Controles usados cuando existen y tienen variacion suficiente:

- margen
- `log(costo_unitario)`
- fechas de venta
- semana, mes, dia de semana y temporada derivadas de `tran_date`
- tienda (`store_nbr` / `store_nm`)
- marca
- tipo de marca
- departamento
- subdepartamento
- clase
- proveedor (`vendor_nm`)
- producto ecologico (`ecologicos`)
- clasificacion retail y estatus operativo de tienda

Uso principal:

- Evaluar si variables adicionales mejoran la explicacion de unidades vendidas.
- Comparar una beta de precio controlada contra el modelo simple.
- Dar una lectura mas completa cuando hay suficientes observaciones por ventana.

## Resultados De Modelos

Archivos oficiales de entrega:

- `output/entrega_base19mayo/modelo1_betas_loglog.csv`
- `output/entrega_base19mayo/modelo2_betas_con_controles.csv`
- `output/entrega_base19mayo/resumen_elasticidad_entrega.xlsx`
- `output/entrega_base19mayo/graficas_elasticidad/`

### Resumen General

| Metrica | Modelo 1: log-log simple | Modelo 2: con controles |
|---|---:|---:|
| SKUs analizados | 1750 | 1750 |
| Ventanas totales | 46266 | 46266 |
| Betas calculadas | 9924 | 6889 |
| Betas mensuales | 1311 | 607 |
| Betas trimestrales | 3523 | 2346 |
| Betas semestrales | 5090 | 3936 |
| R2 promedio | 0.3225 | 0.6590 |
| R2 mediana | 0.1111 | 0.7349 |
| Beta mediana | -0.1621 | -0.5850 |
| N mediana | 8 | 12 |

### Tabla De R2 Por Ventana

| Modelo | Ventana | Betas validas | SKUs con beta | R2 promedio | R2 mediana | Beta mediana | N mediana |
|---|---|---:|---:|---:|---:|---:|---:|
| Modelo 1 | Mensual | 1311 | 365 | 0.4774 | 0.3333 | -0.9451 | 5 |
| Modelo 1 | Trimestral | 3523 | 528 | 0.3537 | 0.1423 | -0.2686 | 8 |
| Modelo 1 | Semestral | 5090 | 559 | 0.2610 | 0.0686 | -0.0313 | 10 |
| Modelo 2 | Mensual | 607 | 145 | 0.7117 | 0.7956 | -0.0489 | 9 |
| Modelo 2 | Trimestral | 2346 | 339 | 0.6973 | 0.7920 | -0.1284 | 11 |
| Modelo 2 | Semestral | 3936 | 430 | 0.6281 | 0.6823 | -1.1283 | 13 |

Lectura de la tabla:

- El Modelo 1 calcula mas betas y es mas directo para simular elasticidad por SKU.
- El Modelo 2 tiene mayor R2 porque agrega controles, pero calcula menos ventanas por falta de observaciones suficientes en algunos casos.
- En el simulador conviene mostrar beta junto con R2 y `n_observaciones`, porque una beta extrema con bajo soporte puede ser inestable.

### Clasificacion De Elasticidad

| Modelo | Elasticos (`beta < -1`) | Inelasticos (`-1 < beta < 0`) | Beta positiva / revision |
|---|---:|---:|---:|
| Modelo 1 | 3588 | 1758 | 4578 |
| Modelo 2 | 3405 | 291 | 3193 |

### Razones Principales De Exclusion

| Modelo | Razon | Ventanas |
|---|---|---:|
| Modelo 1 | `n<3` | 28330 |
| Modelo 2 | `n<3` | 28330 |
| Modelo 1 | `precio constante` | 4634 |
| Modelo 2 | `precio constante` | 4634 |
| Modelo 1 | `unidades constantes` | 3378 |
| Modelo 2 | `unidades constantes` | 3378 |
| Modelo 2 | `controles>observaciones` | 3035 |

## Como Trabajan Los Modelos En El Simulador

1. El usuario selecciona o carga SKUs.
2. Para cada SKU se usa la elasticidad estimada (`beta_precio`) de la ventana disponible.
3. El descuento simulado ajusta el precio base.
4. La elasticidad transforma el cambio de precio en cambio esperado de unidades.
5. El simulador calcula impacto estimado en ventas, ingresos y margen.
6. La confianza se interpreta con R2 y numero de observaciones.

Regla de negocio usada:

```text
cambio esperado en unidades ~= elasticidad * cambio porcentual en precio
```

Ejemplo: si la elasticidad es `-1.5` y el precio baja `10%`, el modelo espera un aumento aproximado de `15%` en unidades, antes de considerar restricciones operativas o de inventario.

## Evaluacion

El Modelo 1 es el mas adecuado para el simulador porque produce una elasticidad simple, interpretable y disponible para mas ventanas. El Modelo 2 sirve como validacion complementaria porque mejora la explicacion estadistica al incluir controles, aunque requiere mas observaciones.

Limitaciones principales:

- No todas las ventanas tienen suficientes datos.
- Algunos SKUs tienen precio constante, por lo que no se puede estimar sensibilidad al precio.
- Las betas positivas deben revisarse antes de usarse como recomendacion automatica.
- La base final no contiene variables explicitas de promocion, por lo que el modelo mide sensibilidad precio-cantidad, no el efecto causal completo de una promocion.

## Despliegue

El front esta publicado con GitHub Pages desde `index.html`. Cada cambio en `main` puede publicarse automaticamente con GitHub Actions si Pages esta configurado como `GitHub Actions`.

## Contenido Del Repositorio

- `index.html`: simulador interactivo de PromoIntel AI.
- `scripts/`: procesamiento, modelado y generacion de reportes.
- `output/entrega_base19mayo/`: resultados oficiales finales.
- `output/`: corridas previas, diagnosticos y reportes.
- `Promociones/`: documentos fuente de promociones.
- `PROGRESO.md`: bitacora completa del avance.
- `requirements.txt`: dependencias necesarias para ejecutar los scripts.
