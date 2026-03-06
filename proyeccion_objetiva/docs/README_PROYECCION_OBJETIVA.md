# Módulo de Proyección Objetiva — WSR DYM

## Objetivo

El WSR (Weekly Sales Report) de DYM actualmente depende al 100% de las proyecciones de cierre de mes que hacen los gerentes regionales. Esto es valioso porque los gerentes conocen su territorio, pero tiene una limitación: es **una sola perspectiva**, subjetiva, sin un punto de referencia objetivo para validarla.

Este módulo agrega **dos proyecciones nuevas basadas en datos** que se muestran lado a lado con la proyección del gerente. No reemplaza al gerente — lo complementa. Los directores ahora pueden ver:

- ¿El gerente está siendo optimista o conservador vs lo que dicen los datos?
- ¿Dónde está el driver del cambio? ¿Es por menos clientes, menos conversión, o menor ticket?
- ¿Cuánta confianza tienen los modelos en su proyección?

---

## Los tres pilares

El WSR ahora muestra **3 proyecciones lado a lado** para cada marca y cada ciudad:

| Pilar | Nombre | ¿Qué hace? | Fuente de datos |
|-------|--------|------------|-----------------|
| 🧑‍💼 | **PY Gerente** | El gerente dice cuánto cree que va a cerrar el mes | `fact_proyecciones` (ya existía en el WSR) |
| 📊 | **PY Estadística** | Un algoritmo mira 24-36 meses de historial y predice el cierre usando patrones de tendencia y estacionalidad | `td_ventas_bob_historico` |
| 🎯 | **PY Operativa** | Descompone la venta en 3 factores (Cobertura × Hit Rate × Drop Size) y proyecta cada uno por separado | `FactVentas` + `fact_eficiencia_hitrate` |

Además calcula automáticamente:

- **Spread**: diferencia porcentual entre PY Gerente y PY Estadística
- **Diagnóstico**: clasificación automática ("Alto consenso", "Gerente optimista vs datos", "Gerente conservador vs datos")

---

## Pilar 2: PY Estadística — Holt-Winters (detalle)

### ¿Qué es Holt-Winters?

Es un método de forecasting llamado **suavizado exponencial triple** que captura tres componentes de una serie temporal:

1. **Nivel**: el valor base alrededor del cual fluctúa la serie
2. **Tendencia**: ¿las ventas vienen subiendo o bajando mes a mes?
3. **Estacionalidad**: ¿hay meses que históricamente venden más o menos? (ej: diciembre siempre sube, febrero siempre baja)

El modelo "suaviza" cada componente dando más peso a los datos recientes y menos a los antiguos (de ahí "exponencial"). La variante que usamos tiene **tendencia amortiguada** (damped trend), que evita que el modelo extrapole una tendencia de crecimiento o caída indefinidamente — en vez de decir "si venimos subiendo 5% cada mes, el mes 24 vendemos el triple", dice "la tendencia se va aplanando con el tiempo". Esto produce proyecciones más conservadoras y realistas.

### ¿Cómo decide qué modelo usar?

Depende de cuántos meses de datos hay disponibles:

| Meses disponibles | Modelo | Captura | Confianza |
|-------------------|--------|---------|-----------|
| **25 o más** | Triple Exp (Holt-Winters completo) | Nivel + Tendencia + Estacionalidad | Alta |
| **12 a 24** | Double Exp | Nivel + Tendencia (sin estacionalidad, porque necesita 2 ciclos completos para detectarla) | Media |
| **Menos de 12** | Ninguno | No se genera proyección — dice "datos insuficientes" | — |
| **>70% ceros** | Ninguno | Serie intermitente, no se puede modelar con este método | — |

### ¿Qué pasa con los outliers?

Antes de modelar, el motor limpia **outliers bajos** (caídas anómalas) usando un rolling mean con z-score unilateral. Esto es importante porque una caída puntual (ej: un mes en que no hubo stock de un producto) distorsionaría la estacionalidad. Solo se limpian outliers **bajos**, no altos — un pico de ventas puede ser real y no queremos eliminarlo.

Esta lógica viene directamente del proyecto FORECAST-DM de Marcelo (`dym-forecast-marcelo/libraries/forecast/src/forecast/models/exponential_smoothing/triple.py`), adaptada como standalone sin las dependencias pesadas del proyecto original.

### Ajuste por eventos móviles (Carnaval, Semana Santa)

Holt-Winters aprende estacionalidad fija por mes, pero eventos como Carnaval cambian de mes entre años (Carnaval 2025 en marzo, 2026 en febrero). El motor aplica un **ajuste post-forecast**:

1. Holt-Winters genera su forecast normalmente
2. El `EventCalendar` compara el mes target vs los años de entrenamiento
3. Si un evento es **nuevo** en el mes (no estaba en años anteriores) → boost (+15% para Carnaval)
4. Si un evento **se fue** del mes (estaba y ya no está) → reducción (-15% para Carnaval)

El calendario usa `utils/business_days.py` que ya tiene los festivos móviles de Bolivia (2025-2026). Ver `explicacion_pilar2_proyeccion_estadistica.md` para explicación completa.

### ¿Qué librerías usa?

- `statsmodels.tsa.holtwinters.ExponentialSmoothing` — la misma librería que usa el FORECAST-DM
- Si `statsmodels` no está instalado, el motor simplemente no se ejecuta y el WSR se genera sin esta sección

### Ejemplo concreto

Si BRANCA en Santa Cruz vendió esto en los últimos 26 meses:

```
Ene-24: 800K    Feb-24: 750K    Mar-24: 820K    ...
Ene-25: 850K    Feb-25: 790K    Mar-25: 870K    ...
Ene-26: 900K    Feb-26: ???
```

El modelo Triple Exp ve:
- **Tendencia**: ventas subiendo ~5% interanual
- **Estacionalidad**: febrero históricamente cae ~6% vs enero
- **Proyección Feb-26**: ~850K (sube por tendencia, pero baja por estacionalidad de febrero)

---

## Pilar 3: PY Operativa — Revenue Tree (detalle)

### ¿Qué es el Revenue Tree?

Es una descomposición de la venta en tres factores multiplicativos:

```
Venta Mensual = Cobertura × Hit Rate × Drop Size
```

Donde:

| Factor | ¿Qué mide? | Fuente | Ejemplo |
|--------|-----------|--------|---------|
| **Cobertura** | Clientes únicos que compraron en el mes | `FactVentas` (columna `cod_cliente_padre`) | 450 clientes |
| **Hit Rate** | % de clientes visitados que efectivamente compraron | `fact_eficiencia_hitrate` | 72% |
| **Drop Size** | Venta promedio por cliente que compró (en BOB) | `FactVentas` (total_venta / clientes) | BOB 2,910 |

**Venta = 450 × 0.72 × 2,910 = BOB 943,020**

### ¿Por qué es útil?

Porque permite **diagnosticar** dónde está el problema. Si la venta baja, ¿por qué?

| Escenario | Cobertura | Hit Rate | Drop Size | Diagnóstico |
|-----------|-----------|----------|-----------|-------------|
| Menos clientes visitados | ↓ | → | → | Problema de ruta/cobertura |
| Mismos clientes pero compran menos | → | ↓ | → | Problema de conversión/selling |
| Compran igual pero menor ticket | → | → | ↓ | Problema de mix/precio |
| Todo baja | ↓ | ↓ | ↓ | Problema sistémico |

### ¿Cómo proyecta cada componente?

Cada factor se proyecta de forma independiente usando:

1. **Promedio Móvil Ponderado (WMA) de 3 meses**: da más peso al mes más reciente
   - Mes más reciente: peso 50%
   - Mes anterior: peso 30%
   - Hace 2 meses: peso 20%

2. **Factor de ajuste estacional**: compara el último valor vs el mismo mes del año anterior
   - Se amortigua (70% base + 30% estacional) para no sobreajustar
   - Se limita entre 0.5x y 2.0x

**Fórmula**: `Componente_proyectado = WMA_3_meses × Factor_estacional`

### Limitación actual del Hit Rate

La tabla `fact_eficiencia_hitrate` **no tiene columna de marca**. Solo tiene ciudad. Esto significa:

- **A nivel ciudad**: Cob_ciudad × HR_ciudad × DS_ciudad → todo directo, datos completos
- **A nivel marca**: Cob_marca × HR_ciudad_como_proxy × DS_marca → el Hit Rate se toma de la ciudad como aproximación

El equipo de sistemas está trabajando en agregar un identificador de factura a la tabla de hit rate para poder llegar a efectividad por marca. Cuando eso esté listo, se actualiza este módulo.

### Fallback si FactVentas no tiene `cod_cliente_padre`

El módulo primero verifica el esquema de `FactVentas`. Si no tiene la columna `cod_cliente_padre` (necesaria para contar clientes únicos), automáticamente usa `td_ventas_bob_historico` con `subfamilia` como proxy de cobertura. No es lo mismo, pero es una aproximación útil hasta que se confirme el esquema.

---

## Estructura de archivos

```
proyeccion_objetiva/
│
├── __init__.py                        ← Exporta ProjectionProcessor como API pública
├── config.py                          ← Constantes compartidas:
│                                         • Tablas del DWH, umbrales, pesos WMA
│                                         • Factores de impacto de eventos (Carnaval +15%)
│                                         • Spread (±5% consenso, ±10% alerta)
│                                         • Colores de visualización
├── data_fetcher.py                    ← Conexión al DWH. Ejecuta 5 queries:
│                                         Q0: Validar esquema FactVentas
│                                         Q1-Q2: Cobertura y Drop Size mensual
│                                         Q3: Hit Rate por ciudad (12+ meses)
│                                         Q4: Ventas históricas (24-36 meses)
├── projection_processor.py            ← Orquestador central:
│                                         Ejecuta ambos pilares, merge con PY Gerente,
│                                         calcula spread y diagnóstico
│
├── pilar2_estadistica/                ← PILAR 2: PY Estadística (Holt-Winters)
│   ├── __init__.py                    ← Exporta StatisticalEngine
│   ├── statistical_engine.py          ← Motor Holt-Winters:
│   │                                     • _clean_outliers(): limpia caídas anómalas
│   │                                     • forecast_single_series(): Triple o Double Exp
│   │                                     • _apply_event_adjustment(): ajuste eventos
│   │                                     • run_by_marca() / run_by_ciudad()
│   └── event_calendar.py             ← Ajuste por eventos móviles:
│                                         • Usa utils/business_days.py como fuente
│                                         • Detecta si Carnaval/Semana Santa cambió de mes
│                                         • Factor multiplicativo post-forecast
│
├── pilar3_operativa/                  ← PILAR 3: PY Operativa (Revenue Tree)
│   ├── __init__.py                    ← Exporta RevenueTreeEngine
│   └── decomposition_engine.py        ← Motor Cob x HR x DS:
│                                         • project_component(): WMA + estacionalidad
│                                         • calculate_projection(): multiplicación
│                                         • run_by_marca() / run_by_ciudad()
│
├── visualizacion/                     ← Generación de HTML y gráficos
│   ├── __init__.py                    ← Exporta generadores
│   ├── projection_html_generator.py   ← Tablas comparativas, descomposición,
│   │                                     cards de resumen, CSS
│   └── projection_chart_generator.py  ← Gráfico Chart.js de barras agrupadas
│
├── docs/                              ← Documentación
│   ├── README_PROYECCION_OBJETIVA.md  ← Este documento
│   ├── PLAN_PROYECCION_OBJETIVA.md    ← Plan original de implementación
│   └── explicacion_pilar2_proyeccion_estadistica.md ← Holt-Winters en detalle
│
└── tests/
    ├── test_validate_factventas.py    ← Valida esquema contra DWH real
    ├── test_statistical_engine.py     ← Tests Pilar 2 con series sintéticas
    ├── test_decomposition_engine.py   ← Tests Pilar 3: WMA, estacionalidad
    └── test_projection_processor.py   ← Tests integración: spread, resiliencia
```

---

## Archivos del WSR existente que se modificaron

| Archivo | Qué cambió |
|---------|-----------|
| `wsr_generator_main.py` | Import protegido del módulo nuevo + llamada al procesador entre paso 7 (Hit Rate) y paso 8 (generar HTML) + paso de datos al generador HTML |
| `core/html_generator.py` | Nuevo parámetro `projection_html` en `generate_complete_report()`, numeración dinámica de secciones (Stock y HitRate se renumeran si hay proyección), CSS de proyección, Chart.js CDN en head |
| `requirements.txt` | Agregado `statsmodels>=0.14.0` y `scipy>=1.10.0` |

---

## Protección ante fallos (fail-safe)

El módulo tiene **tres capas de protección** para nunca romper el WSR existente:

```
Capa 1 — Import
  Si statsmodels no está instalado o el módulo tiene un error de sintaxis:
  → PROJECTION_MODULE_AVAILABLE = False
  → El WSR se genera exactamente como antes

Capa 2 — Ejecución
  Si el DWH no tiene datos o las queries fallan:
  → projection_data = None
  → El WSR se genera exactamente como antes

Capa 3 — HTML
  Si projection_data es None o vacío:
  → projection_html = "" (string vacío)
  → La sección simplemente no aparece en el reporte
  → Stock sigue siendo sección 4, HitRate sección 5
```

---

## Cómo se ve en el reporte

Cuando todo funciona, el WSR v3.0 tiene esta estructura:

```
WEEKLY SALES REPORT - DYM (Versión 3.0)

  RESUMEN EJECUTIVO
  1. PERFORMANCE POR MARCA
  2. PERFORMANCE POR CIUDAD
  3. PERFORMANCE POR CANAL
  [Gráfico de tendencia]
  4. PROYECCIÓN OBJETIVA — COMPARATIVO TRIPLE PILAR    ← NUEVO
     4.1 Comparativo triple pilar por marca (tabla + gráfico)
     4.2 Descomposición operativa por ciudad (Cob/HR/DS)
     4.3 Comparativo triple pilar por ciudad
     [Cards de resumen nacional]
  5. ANÁLISIS DE STOCK Y COBERTURA
  6. HIT RATE Y EFICIENCIA
  NOTAS METODOLÓGICAS
```

Cuando el módulo no está disponible o falla, el reporte queda:

```
WEEKLY SALES REPORT - DYM

  RESUMEN EJECUTIVO
  1. PERFORMANCE POR MARCA
  2. PERFORMANCE POR CIUDAD
  3. PERFORMANCE POR CANAL
  [Gráfico de tendencia]
  4. ANÁLISIS DE STOCK Y COBERTURA
  5. HIT RATE Y EFICIENCIA
  NOTAS METODOLÓGICAS
```

Idéntico al WSR actual — zero impacto.

---

## Dependencias nuevas

| Paquete | Versión | Para qué |
|---------|---------|----------|
| `statsmodels` | >=0.14.0 | Holt-Winters (ExponentialSmoothing) |
| `scipy` | >=1.10.0 | Dependencia de statsmodels para optimización de parámetros |

Instalación: `pip install statsmodels scipy`

---

## Próximos pasos

1. Instalar dependencias y correr tests unitarios
2. Correr el WSR completo contra el DWH real para validar datos
3. Revisar las proyecciones generadas y ajustar umbrales si es necesario
4. **Futuro**: FVA Tracking (comparar proyecciones vs actuals al cierre de cada mes para medir cuál pilar es más confiable)
