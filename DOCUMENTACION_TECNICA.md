# PromoIntel AI — Documentación Técnica y Presentación Final
### Proyecto de Análisis de Elasticidad Promocional · OfficeMax México · 2024–2026

---

## Narrativa Central

**Problema:** OfficeMax no contaba con una forma sistemática de saber qué tan sensible es la demanda de sus productos ante cambios de precio, ni qué tipo de promoción genera más impacto real por SKU y departamento.

**Solución:** PromoIntel AI es un simulador web interactivo que estima la elasticidad precio-demanda de cada SKU usando un modelo estadístico con controles, y permite simular escenarios de descuento en tiempo real para proyectar impacto en ventas, ingresos y margen.

**Impacto:** El equipo comercial puede tomar decisiones de pricing basadas en evidencia — sabiendo exactamente qué SKUs responden más a una promoción, cuánto impacto esperar en volumen e ingresos, y con qué nivel de confianza estadística.

---

## 1. ARQUITECTURA DE LA SOLUCIÓN

### Visión general

La solución se divide en dos capas claramente separadas: un **backend de análisis en Python** que procesa los datos históricos y entrena los modelos, y un **frontend web** que consume esos resultados para simular y visualizar escenarios en tiempo real.

```
DATOS HISTÓRICOS (CSV)
        │
        ▼
┌─────────────────────────────┐
│   BACKEND — Python          │
│                             │
│  1. Limpieza y agregación   │
│  2. Construcción de         │
│     ventanas temporales     │
│  3. Modelo 1: log-log simple│  ← referencia histórica
│  4. Modelo 2: log-log con   │  ← MODELO ACTIVO
│     controles               │
│  5. Exportación de betas    │
│     por SKU / ventana       │
└─────────────┬───────────────┘
              │  CSVs con betas (modelo2_betas_con_controles.csv)
              ▼
┌─────────────────────────────┐
│   FRONTEND — HTML/JS        │
│                             │
│  Vista 1: Análisis          │
│    Descriptivo              │
│  Vista 2: Simulador         │
│    Prescriptivo             │
│  Semáforo de confianza      │
│  Recomendación ejecutiva    │
└─────────────┬───────────────┘
              │
              ▼
     GitHub Pages
  (URL pública accesible)
```

### Tecnologías utilizadas y por qué

| Tecnología | Rol | Por qué se eligió |
|---|---|---|
| **Python 3** | Backend / análisis | Estándar de la industria para ciencia de datos; bibliotecas maduras de regresión |
| **pandas** | Manipulación de datos | Permite agregar millones de filas por SKU × tienda × mes de forma eficiente |
| **NumPy** | Cálculo numérico | Logaritmos y álgebra lineal necesarios para la regresión log-log |
| **scikit-learn** | Regresión lineal | `LinearRegression` y `r2_score` con una API simple y resultados reproducibles |
| **HTML / CSS / JavaScript** | Frontend completo | Un solo archivo desplegable; sin servidor adicional ni framework pesado |
| **Chart.js** | Gráficas | Librería ligera, interactiva y compatible con todos los navegadores |
| **GitHub Pages** | Hosting | Despliegue gratuito, automático en cada commit, URL pública permanente |
| **Qwen2 (Ollama)** | Interpretaciones IA | Modelo local de lenguaje natural para generar texto analítico sin costo por llamada |

### Flujo de información de principio a fin

```
BASE_FINAL_OM.csv
    26,980 filas · 58 columnas
    Nivel: ticket × SKU × tienda × fecha
          │
          ▼
  Limpieza (Python)
  · Conversión de tipos
  · precio_real = venta_neta / unidades
  · Filtro: unidades > 0 y precio > 0
          │
          ▼
  Agregación a SKU × tienda × mes
  (reduce ruido de tickets individuales)
          │
          ▼
  Construcción de ventanas temporales
  · Mensual (1 mes)
  · Trimestral (3 meses)  ← ventana preferida
  · Semestral (6 meses)
          │
          ▼
  Modelo 2: regresión log-log con controles
  por cada SKU × tienda × ventana
          │
          ▼
  modelo2_betas_con_controles.csv
  (46,266 ventanas · 6,889 betas calculadas)
          │
          ▼
  Usuario carga el CSV en PromoIntel AI
          │
          ▼
  Frontend selecciona la mejor beta por SKU
  (R² más alto · ventana trimestral preferida)
          │
          ▼
  Simulador calcula impacto de descuento:
  ΔQ = Q_base × (P_nueva / P_base)^beta × temporada
          │
          ▼
  Resultado: ventas, ingresos y margen proyectados
  + semáforo de confianza + recomendación ejecutiva
```

---

## 2. COMPONENTES DEL APLICATIVO

### Componente 1 — Pipeline de datos y modelos (Backend Python)

**Archivo principal:** `scripts/analisis_elasticidad_entrega.py`

**Qué hace:**
- Carga y limpia la base histórica de ventas de OfficeMax (2024–2026)
- Agrega datos a nivel SKU × tienda × mes para eliminar ruido de transacciones individuales
- Construye ventanas temporales deslizantes (mensual, trimestral, semestral) para estimar cómo varía la elasticidad en el tiempo
- Entrena dos modelos de regresión log-log por cada combinación SKU × tienda × ventana
- Exporta los resultados a CSV listos para ser consumidos por el simulador

**Valor para el usuario:** El trabajo pesado estadístico se hace una sola vez en Python; el usuario no necesita conocer regresión para usar el simulador.

---

### Componente 2 — Dashboard Descriptivo (Vista 1)

**Qué hace:**
- Muestra el impacto histórico de cada tipo de promoción en ingresos y utilidad por departamento
- Visualiza la distribución de elasticidades de todos los SKUs (scatter: cuáles son más sensibles al precio)
- Grafica el comportamiento temporal de ventas antes, durante y después de una promoción
- Filtra por departamento, categoría, SKU, tipo de promoción y rango de fechas
- Genera interpretaciones dinámicas de cada gráfica (texto que cambia con el filtro activo)
- Incluye recomendación ejecutiva estilo consultoría al final de la vista

**Valor para el usuario:** En 30 segundos el equipo comercial puede ver qué promociones han funcionado históricamente y qué SKUs de su departamento son más sensibles al precio, sin necesidad de abrir Excel ni correr código.

---

### Componente 3 — Motor Predictivo / Simulador (Vista 2)

**Qué hace:**
- Permite seleccionar un SKU específico y simular un descuento entre 0% y 40%
- Aplica la fórmula de elasticidad con la beta del Modelo 2 para proyectar el cambio en unidades vendidas
- Calcula automáticamente ventas, ingresos, demanda y margen esperados vs. escenario base
- Muestra el impacto en 4, 8 o 12 semanas con multiplicadores de temporada (Regreso a Clases, Navidad, Buen Fin, etc.)
- Soporta diferentes tipos de promoción (descuento %, 3x2, 2x1, 2do al 50%)
- Genera gráficas de comparación base vs. simulado y curva de descuento
- Incluye semáforo de confianza del modelo con métricas reales (R², n, beta)
- Genera recomendación ejecutiva automática que resume el escenario simulado

**Valor para el usuario:** Antes de lanzar una promoción, el equipo puede ver en segundos cuántas unidades adicionales esperar, si el ingreso incremental justifica el descuento, y qué tan confiable es esa proyección.

---

### Componente 4 — Semáforo de Confianza del Modelo

**Qué hace:**
- Evalúa cada SKU con tres criterios del Modelo 2: R², número de observaciones y validez de la beta
- Asigna un nivel de confianza: Verde (alta), Amarillo (media) o Rojo (baja)
- Muestra el motivo exacto de cada clasificación en un tooltip

| Color | Criterio técnico | Significado para el negocio |
|---|---|---|
| 🟢 VERDE | Modelo 2 confirmado · R² ≥ 0.50 · n ≥ 8 · beta entre −5 y 0 | La proyección tiene respaldo estadístico sólido. Se puede usar para tomar decisiones comerciales |
| 🟡 AMARILLO | Beta razonable pero R² < 0.50 o n < 8, o sin confirmación de M2 | La proyección es orientativa. Validar con el equipo comercial antes de implementar |
| 🔴 ROJO | Beta positiva o extrema, o sin datos suficientes del Modelo 2 | No usar para decisiones automáticas. Revisar el SKU o usar agregado por departamento |

**Valor para el usuario:** El usuario nunca ve un número sin contexto de confiabilidad. Sabe inmediatamente si puede actuar sobre una proyección o si necesita más análisis.

---

### Componente 5 — Interpretaciones automáticas y Recomendación Ejecutiva

**Qué hace:**
- Genera texto analítico dinámico para cada gráfica del dashboard descriptivo
- Cuando Qwen2 (IA local) está disponible: genera párrafos contextuales con lenguaje natural
- Cuando Qwen2 no está disponible: genera texto basado en plantilla con los datos reales del filtro activo (departamento, SKU más elástico, % de elasticidad, mejor tipo de promoción)
- Al final de cada vista genera una "Recomendación Ejecutiva" estilo cierre de consultoría con título, párrafo analítico y pills de métricas clave

**Valor para el usuario:** Convierte datos y gráficas en lenguaje de negocio, sin que el usuario tenga que interpretar manualmente los resultados estadísticos.

---

### Componente 6 — Carga de CSV y plantilla descargable

**Qué hace:**
- Permite al usuario cargar su propio CSV con datos reales de OfficeMax (resultados del modelo)
- El simulador detecta automáticamente las columnas relevantes usando aliases (ej: `beta_precio`, `elasticidad`, `e`, `coeficiente` son todos reconocidos como la misma variable)
- Ofrece una plantilla CSV descargable con el formato exacto esperado y 7 filas de ejemplo
- Al cargar un CSV con datos reales, todos los filtros, gráficas y semáforos se actualizan automáticamente

**Valor para el usuario:** El equipo puede conectar sus propios resultados del modelo sin modificar el código — solo cargando el CSV correcto.

---

## 3. MODELO DE INTELIGENCIA ARTIFICIAL

### ¿Qué modelo utilizamos?

Implementamos un **modelo de regresión log-log con variables de control** (Modelo 2), entrenado por separado para cada combinación de SKU × tienda × ventana temporal del historial de ventas 2024–2026.

La fórmula base es:

```
log(unidades + 1) = α + β × log(precio_real) + controles
```

Donde:
- `β` (beta) es la **elasticidad precio-demanda**: cuánto cambia porcentualmente la demanda cuando el precio cambia 1%
- `α` es la constante del modelo (intercepto)
- Los **controles** son variables adicionales que explican variaciones en ventas más allá del precio

### Variables de control incluidas en el Modelo 2

| Variable | Tipo | Por qué se incluye |
|---|---|---|
| `log(costo_unitario)` | Continua | Correlaciona con calidad del producto y variaciones de precio |
| `margen` | Continua | Refleja la posición competitiva del SKU |
| `fechas_venta` | Continua | Cuántos días distintos tuvo ventas en la ventana |
| `mes_num` | Numérica | Captura estacionalidad mensual |
| `tienda` | Categórica (dummies) | Efectos fijos por sucursal |
| `tipo_marca` | Categórica | Diferencia marcas propias de terceros |
| `marca` | Categórica | Efectos específicos de cada marca |
| `departamento` | Categórica | Diferencias estructurales entre categorías |
| `subdepartamento` | Categórica | Granularidad adicional dentro del depto. |
| `clase` | Categórica | Tipo de producto dentro del subdepartamento |

**Nota:** Las variables categóricas solo se incluyen si tienen variación suficiente dentro de la ventana y si el número de parámetros no excede el número de observaciones (control de sobreajuste).

### ¿Qué lo diferencia del Modelo 1?

| Aspecto | Modelo 1 (log-log simple) | Modelo 2 (con controles) — MODELO ACTIVO |
|---|---|---|
| Variables | Solo `log(precio_real)` | Precio + tienda + mes + marca + costo + margen + clase |
| R² promedio | 0.3225 | **0.6590** |
| R² mediana | 0.1111 | **0.7349** |
| Betas calculadas | 9,924 | 6,889 |
| % betas con R² ≥ 0.50 | 27.78% | **65.64%** |
| Interpretación | Beta mezcla el efecto del precio con efectos de tienda, temporada y marca | Beta aísla el efecto REAL del precio, controlando el resto |
| Uso en el simulador | Solo referencia histórica | **Alimenta todos los resultados** |

El Modelo 2 tiene menos betas totales porque requiere más observaciones para estimar los parámetros adicionales, pero las que genera son estadísticamente más confiables.

### ¿Cómo se entrenó / implementó?

**Entrenamiento (offline, en Python):**

1. Por cada SKU, se agrupan sus ventas históricas por tienda y mes
2. Se construyen ventanas temporales deslizantes (mensual: 1 mes, trimestral: 3 meses, semestral: 6 meses)
3. Para cada ventana con al menos 3 observaciones y variación suficiente en precio y unidades, se ejecuta `LinearRegression` de scikit-learn
4. La beta del `log(precio_real)` es la elasticidad estimada para ese SKU en esa ventana y tienda
5. Los resultados se guardan en `modelo2_betas_con_controles.csv` (46,266 filas)

**Implementación en el simulador (online, en JS):**

1. El usuario carga el CSV con betas
2. Para cada SKU, el simulador selecciona la mejor fila del Modelo 2 disponible, priorizando R² más alto y ventana trimestral
3. Esta beta alimenta la fórmula de simulación de demanda

**Regla de negocio para selección de la mejor beta:**

```
Criterio de uso:
  1. Solo filas de modelo2 (columna "modelo" contiene "2" o "control")
  2. Priorizar: usable > R² más alto > n más alto > trimestral > semestral > mensual
  3. Si no hay filas modelo2: marcar como "sin datos modelo2" → semáforo ROJO
```

### ¿Qué tan confiables son los resultados?

**Métricas de calidad del Modelo 2:**

| Ventana | Betas válidas | SKUs cubiertos | R² promedio | R² mediana |
|---|---|---|---|---|
| Mensual | 607 | 145 | 0.7117 | 0.7956 |
| Trimestral | 2,346 | 339 | 0.6973 | 0.7920 |
| Semestral | 3,936 | 430 | 0.6281 | 0.6823 |

Un **R² de 0.79** (mediana mensual) significa que el modelo explica el 79% de la variación observada en ventas. Para datos de ventas minoristas reales — donde también influyen inventario, visibilidad en anaquel, publicidad y factores externos — este es un resultado sólido.

**Clasificación de la elasticidad estimada:**

| Tipo | Criterio | Interpretación |
|---|---|---|
| Elástico | beta < −1 | Un aumento del 10% en precio reduce la demanda más del 10%. Muy sensibles a promociones |
| Inelástico | −1 < beta < 0 | Un aumento del 10% en precio reduce la demanda menos del 10%. Menos sensibles |
| Revisión | beta ≥ 0 | Relación atípica. Puede deberse a escasez, estacionalidad o pocas observaciones |

**Limitaciones conocidas y cómo se manejan:**

- **Baja cobertura:** Solo el 14.89% de las 46,266 ventanas tienen beta calculada en Modelo 2 (vs 21.45% en Modelo 1), porque se necesitan más observaciones. El simulador lo informa con semáforo ROJO cuando no hay datos.
- **Betas positivas:** El 46.3% de las betas calculadas son positivas o de revisión. El simulador las marca en rojo y no las recomienda para decisiones automáticas.
- **Sin datos de promoción explícita:** La base no incluye campos de campaña, vigencia o mecánica promocional. El modelo mide sensibilidad precio-demanda, no el efecto causal completo de una promoción.

---

## 4. LÓGICA DEL APLICATIVO

### Razonamiento detrás de la solución

La elasticidad precio-demanda es el concepto económico que cuantifica la reacción de los consumidores ante cambios de precio. Un SKU con elasticidad −1.85 responde mucho más a un descuento del 15% que uno con elasticidad −0.45. Sin ese número por SKU, cualquier decisión de descuento es una apuesta.

El modelo log-log es el estándar de la industria para estimar elasticidad porque:
1. El coeficiente beta se interpreta directamente como elasticidad (cambio porcentual en demanda / cambio porcentual en precio)
2. Es robusto ante la distribución no normal de ventas minoristas
3. La transformación log(unidades+1) maneja correctamente los SKUs con ventas en cero

### ¿Cómo toma decisiones el aplicativo?

**En el análisis descriptivo:**
```
Filtro activo (departamento, SKU, fechas)
    → filterData() filtra el array de SKUs y filas del CSV
    → updateCharts() recalcula las 3 gráficas
    → updateInterpSync() genera texto dinámico basado en los datos filtrados
    → modelQuality() evalúa cada SKU para el semáforo
    → updateExecRecV1() genera la recomendación ejecutiva
```

**En el simulador predictivo:**
```
Selección de SKU + ajuste de descuento
    → activeSKU.e (beta del Modelo 2) + disc (%) + season (multiplicador)
    → P_nueva = P_base × (1 − disc/100)
    → Q_simulada = Q_base × (P_nueva/P_base)^beta × season
    → Ingresos = P_nueva × Q_simulada × periodo_semanas
    → Margen = (P_nueva − Costo) × Q_simulada × periodo_semanas
    → ΔIngresos, ΔMargen, ΔUnidades vs. escenario base
    → modelQuality(activeSKU) → nivel del semáforo
    → renderResultCards() + renderForecastCharts()
    → updateExecRecV2() → recomendación ejecutiva del escenario
```

### ¿Qué pasa con los datos desde que entran hasta que generan un resultado?

**Datos desde el CSV histórico hasta la beta:**

```
BASE_FINAL_OM.csv (26,980 filas)
    ↓ Limpieza: tipos, fechas, precio_real = venta_neta/unidades
    ↓ Agregación: SKU × tienda × mes (grupos de ventas)
    ↓ Ventanas: sliding window de 1, 3 o 6 meses
    ↓ Filtros de validez: n ≥ 3, variación en precio y unidades
    ↓ LinearRegression.fit() → extrae coef_[log_precio_real] = beta
    ↓ r2_score(y, pred) → calidad del ajuste
    → modelo2_betas_con_controles.csv (46,266 filas)
```

**Datos desde la beta hasta la pantalla:**

```
CSV cargado en el navegador
    ↓ parseCSVText() → normaliza columnas con alias
    ↓ buildSKUsFromRows() → agrupa por SKU
    ↓ selectBestModelRow() → elige la mejor fila modelo2 por SKU
    ↓ modelQuality() → evalúa R², n, beta, fuente
    → SKUS[] con e, r2, nObs, modelSource, semáforo
    ↓ Usuario ajusta descuento en el slider
    ↓ updateSim() → calcula ΔQ, ΔRevenue, ΔMargin
    → Gráficas + KPIs + semáforo + recomendación ejecutiva
```

### Fórmula central de simulación

```
Cambio esperado en demanda:
  ΔQ% = beta × ΔP%

Demanda simulada:
  Q_sim = Q_base × (P_nueva / P_base)^beta × multiplicador_temporada

Ejemplo:
  SKU: Papel Copia OMX 92 75G
  Beta (Modelo 2): −1.85
  Precio base: $1,120
  Descuento: 20% → P_nueva = $896
  ΔP% = −20%
  ΔQ% = −1.85 × (−20%) = +37%
  Si Q_base = 18,300 unidades → Q_sim ≈ 25,071 unidades en 8 semanas
```

---

## 5. BENEFICIO DE LA SOLUCIÓN

### ¿Qué problemas resuelve para OfficeMax?

**Problema 1 — Decisiones de descuento sin base cuantitativa:**
Antes, el equipo decidía qué productos poner en promoción basándose en intuición o en resultados generales del departamento. PromoIntel AI responde: "si aplicas un 15% de descuento a este SKU específico, espera X unidades adicionales y Y pesos de ingreso incremental, con un nivel de confianza estadística Z."

**Problema 2 — Promociones con retorno negativo:**
No todos los descuentos aumentan la utilidad. Un producto inelástico (beta cercana a 0) que recibe un descuento del 20% vende pocas unidades adicionales pero pierde margen en las que ya iba a vender. El simulador muestra esto en segundos con las gráficas de margen incremental.

**Problema 3 — Sin visibilidad de qué tan confiable es un análisis:**
El semáforo de confianza (Verde/Amarillo/Rojo) convierte métricas estadísticas abstractas (R², n observaciones) en un indicador de negocio inmediatamente accionable.

**Problema 4 — Análisis dispersos en múltiples archivos:**
Todo el análisis vive en un solo URL accesible desde cualquier navegador. No requiere instalación, servidor propio ni conocimiento de Python para usarlo.

### ¿Cuál es el valor de negocio más impactante?

**Cuantificación del impacto de una decisión ANTES de ejecutarla.**

Antes de PromoIntel AI, saber el impacto estimado de un descuento requería días de análisis manual en Excel. Con el simulador, un gerente de categoría puede evaluar 10 escenarios distintos en menos de 5 minutos y presentarlos con números concretos.

**Ejemplo de valor concreto** (usando datos del simulador con descuento 20%, 8 semanas):

| SKU | Ingreso incremental proyectado | Confianza | Acción |
|---|---|---|---|
| Papel Copia OMX 92 75G | +$198M | 🟢 VERDE | Promover |
| Bolígrafo azul Bic | +$2.1M | 🟢 VERDE | Promover |
| Papel Reciclado 60g | Beta positiva | 🔴 ROJO | No promover |

### ¿Cómo impacta en la operación y en la toma de decisiones?

**Operación:**
- El equipo de pricing puede correr simulaciones de temporada (Regreso a Clases, Buen Fin, Navidad) antes del evento y dimensionar inventario acordemente
- El análisis descriptivo permite comparar qué tipo de promoción (descuento %, 3x2, 2x1) ha tenido más impacto histórico por departamento
- La plantilla CSV estandariza el formato para que cualquier analista pueda actualizar los modelos y cargarlos al simulador

**Toma de decisiones:**
- Jerarquía clara de confianza: no todos los SKUs tienen el mismo respaldo estadístico
- Transparencia del modelo: el simulador muestra la beta, el R² y el número de observaciones para que el decisor pueda juzgar por sí mismo
- Simulación de temporada: multiplicadores calibrados para Regreso a Clases (+30%), Navidad (+45%), Buen Fin (+60%) y Verano (−15%)

---

## 6. GUÍA DE USO DEL SIMULADOR

### Para el análisis descriptivo (Vista 1)
1. Selecciona un departamento en el filtro superior izquierdo
2. Observa las 3 gráficas: escenarios de precio, sensibilidad de SKUs y efecto temporal de promociones
3. Las interpretaciones a la derecha de cada gráfica se actualizan automáticamente
4. Al final de la vista verás la Recomendación Ejecutiva del departamento seleccionado
5. Descarga la plantilla CSV para saber qué columnas necesitas

### Para el simulador predictivo (Vista 2)
1. Carga tu CSV con betas del Modelo 2 (opcional — sin CSV funciona con datos demo)
2. Selecciona un departamento y un SKU
3. Mueve el slider de descuento para simular el impacto
4. Observa el semáforo de confianza — solo actúa sobre SKUs VERDES o AMARILLOS con precaución
5. Cambia la temporada si planeas lanzar la promoción en un evento especial
6. Cambia el periodo de análisis (4 / 8 / 12 semanas) según la duración esperada de la campaña
7. Al final de la página verás la Recomendación Ejecutiva del escenario simulado
8. Exporta los resultados a CSV para incluirlos en tu presentación o reporte

### Para probar localmente
```bash
# Opción 1 — Abrir directamente en el navegador:
open /ruta/al/repo/index.html

# Opción 2 — Servidor local simple (si el navegador bloquea file://):
cd /ruta/al/repo
python3 -m http.server 8080
# Luego abrir http://localhost:8080 en el navegador

# Opción 3 — GitHub Pages (ya desplegado):
https://landin2312.github.io/Proyecto-Office-Max/
```

---

## 7. ESTRUCTURA DEL REPOSITORIO

```
Proyecto-Office-Max/
│
├── index.html                          ← Aplicativo web completo (frontend)
├── README.md                           ← Documentación del modelo estadístico
├── DOCUMENTACION_TECNICA.md            ← Este archivo
│
├── scripts/
│   ├── analisis_elasticidad_entrega.py ← Script principal: limpieza + Modelo 1 + Modelo 2
│   ├── modelo_elasticidad_base19mayo.py← Versiones anteriores del pipeline
│   ├── modelo_multivariable_base19mayo.py
│   └── ...                             ← Scripts auxiliares de análisis
│
├── output/
│   └── entrega_base19mayo/
│       ├── modelo1_betas_loglog.csv    ← Betas del Modelo 1 (referencia histórica)
│       ├── modelo2_betas_con_controles.csv ← Betas del Modelo 2 (ACTIVO en simulador)
│       ├── resumen_elasticidad_entrega.xlsx
│       └── graficas_elasticidad/      ← Gráficas generadas por Python
│
└── BASE FINAL.csv                      ← Datos históricos de ventas (fuente de verdad)
```

---

## 8. RESUMEN DE CAMBIOS REALIZADOS EN EL FRONTEND

Durante el desarrollo del proyecto se realizaron las siguientes iteraciones sobre `index.html`:

| Cambio | Propósito |
|---|---|
| Corrección de interpretaciones congeladas en "PAPEL" | Las interpretaciones ahora se actualizan sincrónicamente al cambiar cualquier filtro |
| Reemplazo de `MOCK_TEXTS` estático por `getMockTexts()` dinámico | El texto de fallback refleja el departamento real activo, no siempre "Papel" |
| Uso de `deptLabel` (nombre visible) en lugar de `dept` (value interno) | Las interpretaciones muestran "Archivo y Accesorios" no "ARCHIVO" |
| Función `updateInterpSync()` sincrónica | Garantiza que el texto se actualice inmediatamente sin depender del ciclo async de Qwen |
| Plantilla CSV descargable | El usuario sabe exactamente qué columnas necesita para cargar sus datos |
| Recomendación Ejecutiva en ambas vistas | Cierre estilo consultoría con texto dinámico, pills de métricas y diseño navy |
| Migración al Modelo 2 exclusivo en `selectBestModelRow()` | El simulador solo usa betas del modelo con controles |
| SKUS demo actualizados con R², nObs y modelSource | El semáforo funciona correctamente incluso sin CSV cargado |
| Nuevo `modelQuality()` con criterios de Modelo 2 | Semáforo Verde/Amarillo/Rojo basado en R², n, beta válida y confirmación de modelo2 |
| `renderSKUTable()` con columnas Beta (M2), R², n obs, Ventana, Confianza | La tabla del motor pricing muestra toda la información estadística relevante |
| Leyenda visual del semáforo en la tabla | El usuario entiende qué significa cada color sin necesidad de explicación verbal |

---

*Documento generado para la presentación final del proyecto PromoIntel AI · OfficeMax México · Junio 2026*
