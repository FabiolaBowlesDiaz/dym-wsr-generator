# Plan: Módulo de Proyección Objetiva para el WSR de DYM

## Objetivo

Implementar un módulo de proyección objetiva basado en datos que complemente las proyecciones subjetivas de los gerentes regionales en el WSR (Weekly Sales Report) de DYM.

## Fuentes de datos

| Fuente | Ubicación | Descripción |
|--------|-----------|-------------|
| `wsr_generator_main.py` | `/c/aa_dym_wsr_proyecto_20Septiembre/` | Orquestador principal del WSR |
| `core/html_generator.py` | `/c/aa_dym_wsr_proyecto_20Septiembre/core/` | Generador de reportes HTML |
| `core/database.py` | `/c/aa_dym_wsr_proyecto_20Septiembre/core/` | Queries SQL al DWH (PostgreSQL) |
| `core/data_processor.py` | `/c/aa_dym_wsr_proyecto_20Septiembre/core/` | Consolidación de datos y cálculo de KPIs |
| `FactVentas` | DWH `dwh_saiv` (192.168.80.85) | Tabla de ventas para cobertura y drop size |
| `fact_eficiencia_hitrate` | DWH `dwh_saiv` | Hit rate por ciudad (sin marca) |
| `td_ventas_bob_historico` | DWH `dwh_saiv` | Ventas mensuales históricas (24+ meses) |
| `fact_proyecciones` | DWH `dwh_saiv` | Proyecciones de gerentes (existente) |

## Outputs generados

| Archivo | Descripción |
|---------|-------------|
| `proyeccion_objetiva/__init__.py` | Package init |
| `proyeccion_objetiva/config.py` | Constantes, umbrales, nombres de tablas |
| `proyeccion_objetiva/data_fetcher.py` | Queries SQL para FactVentas e históricos |
| `proyeccion_objetiva/statistical_engine.py` | Motor Holt-Winters standalone (~150 líneas) |
| `proyeccion_objetiva/decomposition_engine.py` | Revenue Tree: Cobertura × HitRate × DropSize (~200 líneas) |
| `proyeccion_objetiva/projection_processor.py` | Orquestador que conecta ambos motores (~150 líneas) |
| `proyeccion_objetiva/projection_html_generator.py` | Tablas HTML de comparación triple pilar (~300 líneas) |
| `proyeccion_objetiva/projection_chart_generator.py` | Gráfico Chart.js de barras agrupadas (~200 líneas) |
| `proyeccion_objetiva/tests/test_validate_factventas.py` | Validar esquema de FactVentas contra DWH real |
| `proyeccion_objetiva/tests/test_statistical_engine.py` | Tests unitarios del motor estadístico |
| `proyeccion_objetiva/tests/test_decomposition_engine.py` | Tests unitarios del motor de descomposición |
| `proyeccion_objetiva/tests/test_projection_processor.py` | Tests de integración del orquestador |

---

## Contexto

El WSR de DYM actualmente depende al 100% de las proyecciones de los gerentes regionales. Los directores quieren un **segundo punto de vista objetivo, basado en datos**, para complementar (no reemplazar) el juicio de los gerentes. Las mejores empresas de bebidas del mundo (AB InBev, Diageo, Coca-Cola) usan un enfoque de **tres pilares**: (1) forecast estadístico, (2) descomposición operativa, (3) inteligencia comercial (gerentes). Implementaremos los pilares 1 y 2.

## Enfoque: Tres Pilares de Proyección

El WSR mostrará 3 proyecciones lado a lado:

| Pilar | Nombre | Método | Fuente |
|-------|--------|--------|--------|
| 🧑‍💼 | **PY Gerente** (existente) | Híbrido: semanas reales + pronóstico gerente | `fact_proyecciones` |
| 📊 | **PY Estadística** (nuevo) | Holt-Winters (tendencia + estacionalidad) | `td_ventas_bob_historico` (24+ meses) |
| 🎯 | **PY Operativa** (nuevo) | Cobertura × Hit Rate × Drop Size | `FactVentas` + `fact_eficiencia_hitrate` |

---

## Estructura de archivos

```
proyeccion_objetiva/
├── __init__.py
├── config.py                        # Constantes, umbrales, nombres de tablas
├── data_fetcher.py                  # Queries nuevos: FactVentas, ventas mensuales históricas
├── statistical_engine.py            # Holt-Winters adaptado del FORECAST-DM
├── decomposition_engine.py          # Revenue Tree: Cobertura × HitRate × DropSize
├── projection_processor.py          # Orquestador: ejecuta ambos motores, produce comparación
├── projection_html_generator.py     # Genera sección HTML para el reporte
├── projection_chart_generator.py    # Gráfico Chart.js de comparación
└── tests/
    ├── __init__.py
    ├── test_validate_factventas.py   # Validar esquema de FactVentas contra DWH real
    ├── test_statistical_engine.py
    ├── test_decomposition_engine.py
    └── test_projection_processor.py
```

---

## Fases de implementación

### Fase 1: Descubrimiento de datos y validación (Día 1-2)

**Objetivo**: Confirmar que los datos necesarios existen en el DWH y tienen la profundidad suficiente.

**Paso 1.1**: Crear `proyeccion_objetiva/config.py` con constantes.

**Paso 1.2**: Crear `proyeccion_objetiva/data_fetcher.py` con clase `ProjectionDataFetcher` que recibe el `DatabaseManager` existente y ejecuta:

- **Query 0 — Descubrimiento de esquema**: Validar que `FactVentas` tiene `cod_cliente_padre`, `total_venta`, `c9l`, `marcadir`, `ciudad`, `canal`, `anio`, `mes`.
- **Query 1 — Cobertura mensual**: `COUNT(DISTINCT cod_cliente_padre)` por marca/ciudad/mes desde FactVentas.
- **Query 2 — Drop Size mensual**: `SUM(total_venta) / COUNT(DISTINCT cod_cliente_padre)` y `SUM(c9l) / COUNT(DISTINCT cod_cliente_padre)` por marca/ciudad/mes.
- **Query 3 — Hit Rate mensual por ciudad**: Extender el patrón existente de `get_hitrate_mensual()` en `core/database.py` (línea ~1430) para obtener historial de 12+ meses. Nota: Hit Rate solo disponible a nivel ciudad (no marca), porque `fact_eficiencia_hitrate` no tiene columna de marca.
- **Query 4 — Ventas mensuales históricas (24+ meses)**: `SUM(fin_01_ingreso)` y `SUM(c9l)` por marca/ciudad/mes desde `td_ventas_bob_historico`.

**Paso 1.3**: Crear `tests/test_validate_factventas.py` para ejecutar contra el DWH real y confirmar datos.

**Entregable**: DataFrames validados de cobertura, hit rate, drop size y ventas históricas mensuales.

---

### Fase 2: Motor de Descomposición Operativa (Día 2-4)

**Objetivo**: Implementar la proyección `Venta = Cobertura × Hit Rate × Drop Size`.

**Archivo**: `proyeccion_objetiva/decomposition_engine.py`

**Clase `RevenueTreeEngine`**:

1. `project_component(series, method='wma')` — Proyecta un componente individual hacia adelante:
   - Promedio móvil ponderado de 3 meses (pesos: 0.5 reciente, 0.3 medio, 0.2 antiguo)
   - Factor de ajuste estacional: ratio vs mismo-mes-año-anterior
   - Fórmula: `Componente_proyectado = WMA_3m × Factor_estacional`

2. `calculate_projection(cob_hist, hr_hist, ds_hist)` — Para una combinación marca/ciudad:
   - Proyecta cada componente independientemente
   - Multiplica: `PY_Operativa = Cob_proj × HR_proj × DS_proj`
   - Retorna componentes individuales + resultado (para transparencia)

3. `run_all_groups(cobertura_df, hitrate_df, dropsize_df, level)` — Itera todas las combinaciones.

**Nota de diseño sobre Hit Rate**: Actualmente `fact_eficiencia_hitrate` no tiene marca, pero el equipo de sistemas está trabajando en agregar un identificador de factura para llegar a efectividad por marca. Mientras tanto:
- **Nivel ciudad**: Cobertura_ciudad × HR_ciudad × DS_ciudad (todos disponibles directamente)
- **Nivel marca**: Cobertura_marca × HR_ciudad_correspondiente × DS_marca (HR se toma de la ciudad como proxy)
- **Futuro**: Cuando sistemas agregue el identificador de factura, actualizar para tener HR por marca directamente

---

### Fase 3: Motor Estadístico Holt-Winters (Día 4-6)

**Objetivo**: Implementar forecast estadístico adaptado del proyecto FORECAST-DM.

**Archivo**: `proyeccion_objetiva/statistical_engine.py`

**Clase `StatisticalEngine`** — Adaptación simplificada y standalone de `TripleExpModel` (`dym-forecast-marcelo/libraries/forecast/src/forecast/models/exponential_smoothing/triple.py`):

1. `_clean_outliers(series)` — Adaptado de `replace_low_outliers_rolling()` (línea 90 de triple.py): ventana=5, z_thresh=2.5, reemplaza outliers bajos con rolling mean.

2. `forecast_single_series(monthly_series, horizon=1)` — Para una serie temporal mensual:
   - Si N ≥ 25 meses: **TripleExpModel** (Holt-Winters con estacionalidad aditiva, tendencia amortiguada)
   - Si 12 ≤ N < 25: **DoubleExpModel** (tendencia sin estacionalidad)
   - Si N < 12 o >70% ceros: Retorna `None` ("datos insuficientes")
   - Usa `statsmodels.tsa.holtwinters.ExponentialSmoothing` (misma librería que FORECAST-DM)
   - Retorna: forecast, tipo de modelo usado, confianza

3. `run_all_groups(monthly_sales_df, level)` — Itera combinaciones marca/ciudad, siguiendo el patrón de `exp_smoothing_predict_groups()` de `helper_functions.py` (línea 4-57).

**Dependencia nueva**: `statsmodels>=0.14.0` (agregar a `requirements.txt`).

**Decisión de diseño**: NO importamos las librerías del FORECAST-DM directamente. Extraemos solo la lógica core (~100 líneas) porque el FORECAST-DM tiene dependencias pesadas (Docker, Poetry, 7 paquetes internos) y su arquitectura (DataControlCenter/Features/Frame) es sobredimensionada para nuestro caso. Copiamos la lógica probada en producción, no la infraestructura.

---

### Fase 4: Orquestación e integración con WSR (Día 6-8)

**Objetivo**: Conectar ambos motores al pipeline existente del WSR.

**Archivo**: `proyeccion_objetiva/projection_processor.py`

**Clase `ProjectionProcessor`**:
- Recibe `db_manager` y `current_date`
- Método principal `generate_projections()`:
  1. Llama a `data_fetcher` para obtener todos los datos
  2. Ejecuta `statistical_engine.run_all_groups()` → PY Estadística
  3. Ejecuta `decomposition_engine.run_all_groups()` → PY Operativa
  4. Merge con PY Gerente (ya disponible en el pipeline principal)
  5. Calcula spread y diagnóstico (consensus vs divergencia)
  6. Retorna dict con DataFrames por marca, ciudad, y resumen nacional

**Integración en `wsr_generator_main.py`**:
- Importar `ProjectionProcessor` (línea ~19)
- Después del análisis de comentarios (línea ~119): ejecutar `projection_processor.generate_projections()`
- Envolver en `try/except`: si falla, `projection_data = None` y el reporte se genera igual sin la sección nueva (zero impacto en WSR existente)
- Pasar `projection_data` a `html_generator.generate_complete_report()` como nuevo parámetro

**Modificaciones en `core/html_generator.py`**:
- Agregar parámetro `projection_data=None` a `generate_complete_report()` (línea 216)
- Nueva sección "4. PROYECCIÓN OBJETIVA" después del gráfico de tendencia (línea ~275)
- Renumerar Stock a sección 5, HitRate a sección 6

---

### Fase 5: Visualización HTML (Día 8-10)

**Objetivo**: Crear las tablas y gráficos interactivos para la sección de proyección objetiva.

**Archivo**: `proyeccion_objetiva/projection_html_generator.py`

**Sección 4.1 — Comparativo Triple Pilar por Marca** (tabla principal):

| Marca | Avance | PY Gerente 🧑‍💼 | PY Estadística 📊 | PY Operativa 🎯 | Spread | Diagnóstico |
|-------|--------|-------------|---------------|-------------|--------|-------------|
| BRANCA | 1.2M | 1.35M | 1.28M | 1.31M | +5.5% | Gerente optimista |

- Spread = (PY Gerente / PY Estadística) - 1
- Diagnóstico automático:
  - Spread > +10%: "Gerente optimista vs datos"
  - Spread < -10%: "Gerente conservador vs datos"
  - |Spread| < 5%: "Alto consenso"

**Sección 4.2 — Descomposición Operativa** (revenue tree):

| Ciudad | Cobertura (clientes) | Tend. | Hit Rate (%) | Tend. | Drop Size (BOB) | Tend. | PY Operativa |
|--------|---------------------|-------|--------------|-------|-----------------|-------|--------------|
| Santa Cruz | 450 | ↑3% | 72% | ↓2% | 2,910 | ↑4% | 943K |

- Flechas verdes/rojas para tendencia de cada componente
- Permite diagnosticar: "la caída es por Hit Rate, no por cobertura"

**Sección 4.3 — Comparativo por Ciudad** (misma estructura que 4.1 pero por ciudad)

**Archivo**: `proyeccion_objetiva/projection_chart_generator.py`

- Gráfico de barras agrupadas (Chart.js): 3 barras por marca (Gerente/Estadística/Operativa)
- Colores: Gerente=#94A3B8, Estadística=#3B82F6, Operativa=#10B981
- Usa Chart.js que ya está cargado en el reporte por el gráfico de tendencia

**CSS nuevo** (agregar a `html_generator.py._get_css_styles()`):
- Cards de proyección con borde lateral por pilar
- Clases `.trend-up` (verde) y `.trend-down` (rojo) para flechas
- `.consensus-high` (fondo verde claro) y `.consensus-low` (fondo naranja)

---

### Fase 6 (Futura): FVA Tracking

**No implementar ahora**, pero diseñar la estructura para el futuro:
- Archivo `fva_tracker.py`: comparar proyecciones vs actuals al cierre de cada mes
- Nueva tabla `fact_fva_tracking` en PostgreSQL
- Medir MAPE de cada pilar para determinar cuál es más confiable
- Mostrar en el reporte: "Este mes, la PY Estadística tuvo error de 3.2% vs 8.1% del gerente"

---

## Archivos críticos a modificar

| Archivo | Cambio |
|---------|--------|
| `wsr_generator_main.py` (línea ~19, ~119, ~131) | Import, llamada al módulo, pasar datos al HTML |
| `core/html_generator.py` (línea ~216, ~275) | Nuevo parámetro, nueva sección HTML |
| `requirements.txt` | Agregar `statsmodels>=0.14.0` |

## Archivos nuevos a crear

| Archivo | Propósito |
|---------|-----------|
| `proyeccion_objetiva/__init__.py` | Package init |
| `proyeccion_objetiva/config.py` | Constantes y configuración |
| `proyeccion_objetiva/data_fetcher.py` | Queries SQL para FactVentas e históricos |
| `proyeccion_objetiva/statistical_engine.py` | Holt-Winters standalone (~150 líneas) |
| `proyeccion_objetiva/decomposition_engine.py` | Revenue Tree Cob×HR×DS (~200 líneas) |
| `proyeccion_objetiva/projection_processor.py` | Orquestador que conecta todo (~150 líneas) |
| `proyeccion_objetiva/projection_html_generator.py` | Tablas HTML de comparación (~300 líneas) |
| `proyeccion_objetiva/projection_chart_generator.py` | Gráfico Chart.js de barras (~200 líneas) |
| `proyeccion_objetiva/tests/*.py` | Tests unitarios y de validación |

## Archivos de referencia (solo lectura, copiar lógica)

| Archivo | Qué copiar |
|---------|-----------|
| `dym-forecast-marcelo/.../triple.py` líneas 90-175, 221-281, 315-359 | Outlier cleaning, Holt-Winters train/predict |
| `dym-forecast-marcelo/.../helper_functions.py` líneas 4-57 | Patrón de iteración por grupo con fallback Double/Triple |
| `core/database.py` líneas ~1430+ | Patrón de queries de hit rate |

## Verificación

1. **Test de esquema**: Ejecutar `test_validate_factventas.py` contra DWH real → confirmar columnas
2. **Test unitario de motores**: Series sintéticas con resultados conocidos
3. **Test de sanidad**: Proyecciones deben estar entre 50%-200% del mismo-mes-año-anterior
4. **Test de integración**: Generar WSR completo → verificar que nueva sección aparece sin romper las existentes
5. **Test de resiliencia**: Forzar fallo del módulo → verificar que WSR se genera igual sin la sección

## Riesgo principal y mitigación

| Riesgo | Mitigación |
|--------|-----------|
| FactVentas no tiene las columnas esperadas | Fase 1 empieza con schema discovery. Si falta `cod_cliente_padre`, se usa proxy con `td_ventas_bob_historico` (cobertura aproximada por combinaciones únicas de subfamilia) |
| Datos insuficientes para Holt-Winters en algunas marcas/ciudades | Fallback a DoubleExp (12-24 meses) o mostrar "Datos insuficientes" en la tabla |
| Romper el WSR existente | Todo el módulo envuelto en try/except. Si falla, el reporte se genera exactamente igual que antes |
