# Pilar 2: PY Estadistica — Flujo de Datos Completo

## Objetivo

Documentar el flujo completo de datos, calculos y decisiones del motor de Proyeccion Estadistica (Holt-Winters) del modulo de Proyeccion Objetiva del WSR DYM.

## Fuentes de datos

| Archivo | Ruta | Descripcion |
|---------|------|-------------|
| `data_fetcher.py` | `proyeccion_objetiva/data_fetcher.py` | Queries SQL contra el DWH |
| `statistical_engine.py` | `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py` | Motor Holt-Winters |
| `event_calendar.py` | `proyeccion_objetiva/pilar2_estadistica/event_calendar.py` | Ajuste por eventos moviles |
| `config.py` | `proyeccion_objetiva/config.py` | Constantes y umbrales |
| `business_days.py` | `utils/business_days.py` | Calendario de feriados de Bolivia |
| `projection_processor.py` | `proyeccion_objetiva/projection_processor.py` | Orquestador central |

## Outputs generados

| Output | Descripcion |
|--------|-------------|
| `py_est_marca` | DataFrame con proyeccion estadistica por marca |
| `py_est_ciudad` | DataFrame con proyeccion estadistica por ciudad |
| Spread + Diagnostico | Comparacion con PY Gerente, clasificacion automatica |

---

## 1. Origen de datos: Query SQL (Query 4)

### Tabla fuente

```
Tabla:   td_ventas_bob_historico
Motor:   PostgreSQL
Schema:  variable (parametro 'schema' del DatabaseManager)
```

### Campos utilizados

| Campo | Tipo | Uso |
|-------|------|-----|
| `marcadir` | VARCHAR | Nombre de la marca directorio (BRANCA, HAVANA, etc.) |
| `ciudad` | VARCHAR | Ciudad de la venta (SANTA CRUZ, LA PAZ, etc.) |
| `canal` | VARCHAR | Canal de venta (usado solo para filtrar TURISMO) |
| `anio` | INT | Ano de la venta |
| `mes` | INT | Mes de la venta (1-12) |
| `fin_01_ingreso` | NUMERIC | Venta en BOB (bolivianos) |
| `c9l` | NUMERIC | Venta en cajas de 9 litros (unidad estandar de la industria de bebidas) |

### Query SQL exacta

```sql
SELECT
    marcadir,
    ciudad,
    anio,
    mes,
    SUM(CAST(fin_01_ingreso AS NUMERIC)) AS venta_bob,
    SUM(CAST(c9l AS NUMERIC)) AS venta_c9l
FROM {schema}.td_ventas_bob_historico
WHERE (anio * 12 + mes) >= (
        EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
        + EXTRACT(MONTH FROM CURRENT_DATE)::INT
        - 36
      )
  AND UPPER(ciudad) NOT IN ('TURISMO')
  AND UPPER(canal) NOT IN ('TURISMO')
  AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
GROUP BY marcadir, ciudad, anio, mes
ORDER BY marcadir, ciudad, anio, mes
```

### Filtros aplicados

| Filtro | Valor | Razon |
|--------|-------|-------|
| Window temporal | Ultimos 36 meses | Holt-Winters necesita 25+ meses para modelo completo |
| Ciudades excluidas | `TURISMO` | No es una ciudad real, es un canal especial |
| Canales excluidos | `TURISMO` | Consistente con los filtros del WSR existente |
| Marcas excluidas | `NINGUNA`, `SIN MARCA ASIGNADA` | Registros sin marca valida |

### Nota sobre el filtro temporal

La formula `(anio * 12 + mes)` convierte ano+mes en un numero de mes absoluto, lo que permite comparar meses sin date arithmetic complejo:

```
Ejemplo: Marzo 2026 = 2026*12 + 3 = 24315
         36 meses atras = 24315 - 36 = 24279
         Eso corresponde a Marzo 2023 = 2023*12 + 3 = 24279
```

---

## 2. Agregacion por nivel

El DataFrame crudo viene a nivel `(marcadir, ciudad, anio, mes)`. Para Holt-Winters, se agrega a dos niveles:

### Nivel marca (sumar todas las ciudades)

```python
marca_mensual = ventas_df.groupby(['marcadir', 'anio', 'mes'])['venta_bob'].sum().reset_index()
```

**Resultado**: Una serie temporal por marca. Ejemplo: BRANCA tiene un valor por mes que es la suma de todas las ciudades.

### Nivel ciudad (sumar todas las marcas)

```python
ciudad_mensual = ventas_df.groupby(['ciudad', 'anio', 'mes'])['venta_bob'].sum().reset_index()
```

**Resultado**: Una serie temporal por ciudad. Ejemplo: SANTA CRUZ tiene un valor por mes que es la suma de todas las marcas.

---

## 3. Conversion a serie temporal

Para que `statsmodels` funcione, necesita una `pd.Series` con `DatetimeIndex` y frecuencia explicita `'MS'` (Month Start).

```python
# Convertir (anio, mes) -> fecha
temp['date'] = pd.to_datetime(anio + '-' + mes_zfill + '-01')
# Ejemplo: anio=2024, mes=3 -> 2024-03-01

# Ordenar cronologicamente
temp = temp.sort_values('date')

# Crear serie con indice de fecha
series = temp.set_index('date')['venta_bob']

# Forzar frecuencia mensual (inserta NaN si falta un mes)
series = series.asfreq('MS')

# Rellenar meses faltantes con 0
series = series.fillna(0)
```

**Nota sobre `fillna(0)`**: Si un mes no tiene registro en la query, se asume venta cero. Esto es correcto para DYM: si una marca no vendio nada en un mes, la venta realmente fue cero. No aplica para meses recientes que aun no se cargaron al DWH — esos simplemente no estan en el window de 36 meses.

### Ejemplo de serie resultante

```
Fecha        Venta BOB
2024-01-01   850,000
2024-02-01   790,000
2024-03-01   870,000
...
2025-12-01   920,000
2026-01-01   900,000
```

---

## 4. Limpieza de outliers

**Archivo**: `statistical_engine.py` → `_clean_outliers()`

**Objetivo**: Detectar y corregir caidas anomalas (outliers bajos) que distorsionarian el modelo. Solo corrige outliers **bajos**, no picos altos (un pico de ventas puede ser real).

### Parametros (config.py)

```python
OUTLIER_WINDOW = 5       # Ventana rolling para deteccion
OUTLIER_Z_THRESH = 2.5   # Umbral Z-score
```

### Algoritmo paso a paso

**Paso 4.1: Media movil centrada**

```python
roll_center = series.rolling(window=5, center=True, min_periods=1).mean()
```

Para cada punto, calcula el promedio de los 5 valores circundantes (2 antes, el punto, 2 despues). Si no hay suficientes vecinos (inicio/final de la serie), usa los que haya.

**Paso 4.2: Desviacion estandar rolling**

```python
roll_std = series.rolling(window=5, center=True, min_periods=2).std()
```

Si la std rolling es 0 o NaN (todos los valores iguales en la ventana), usa la std global de la serie como fallback.

**Paso 4.3: Z-score relativo**

```python
z = (series - roll_center) / roll_std
```

Mide cuantas desviaciones estandar esta cada punto por debajo (z negativo) o por encima (z positivo) de su media local.

**Paso 4.4: Umbral adaptativo**

```python
effective_z_thresh = min(z_thresh, (window - 1) / sqrt(window) * 0.95)
# Con window=5: min(2.5, (4/2.236)*0.95) = min(2.5, 1.70) = 1.70
```

**Por que adaptativo?** Con solo 5 puntos en una ventana, el z-score maximo teorico de un solo punto extremo es ~1.79. Un umbral de 2.5 nunca detectaria nada. La formula ajusta al tamano de ventana.

**Paso 4.5: Doble condicion de outlier**

```python
outlier_bajo = (z < -effective_z_thresh) AND (valor < 0.4 * roll_center)
```

Un punto debe cumplir **ambas** condiciones:
1. Su z-score es muy negativo (estadisticamente anomalo)
2. Es menos del 40% de la media local (absolutamente bajo)

La doble condicion evita falsos positivos.

**Paso 4.6: Reemplazo**

```python
series[outlier_bajo] = roll_center[outlier_bajo]
```

Los outliers bajos se reemplazan con la media movil local.

### Ejemplo

```
Original:   800K  750K  820K  100K  780K  850K
                              ^^^^
                              outlier (desabasto puntual)

roll_center:      793K        ~800K
z-score:                      -3.2 (< -1.70)
ratio:            100/800 = 0.125 (< 0.40)

Limpiado:   800K  750K  820K  ~800K  780K  850K
```

---

## 5. Modelo Holt-Winters

**Archivo**: `statistical_engine.py` → `forecast_single_series()`

### Decision del modelo

| Condicion | Modelo | Captura | Confianza |
|-----------|--------|---------|-----------|
| N >= 25 meses | Triple Exponential Smoothing | Nivel + Tendencia + Estacionalidad | `high` |
| 12 <= N < 25 | Double Exponential Smoothing | Nivel + Tendencia | `medium` |
| N < 12 | Ninguno → retorna `None` | — | — |
| >70% ceros | Ninguno → retorna `None` | — | — |

### Constantes (config.py)

```python
MIN_MONTHS_TRIPLE = 25   # Minimo para modelo completo (2+ ciclos estacionales)
MIN_MONTHS_DOUBLE = 12   # Minimo para modelo con tendencia
MIN_MONTHS_MINIMUM = 12  # Por debajo de esto, no se genera proyeccion
ZERO_THRESHOLD = 0.70    # Si >70% son ceros, serie intermitente
SEASONAL_PERIOD = 12     # 12 meses = 1 ciclo estacional
```

### Triple Exponential Smoothing (N >= 25)

```python
model = ExponentialSmoothing(
    series,
    trend='add',           # Tendencia aditiva
    seasonal='add',        # Estacionalidad aditiva
    seasonal_periods=12,   # Ciclo de 12 meses
    damped_trend=True      # Tendencia amortiguada
).fit(optimized=True)      # Optimizar alpha, beta, gamma automaticamente

forecast = model.forecast(1).clip(lower=0)
```

### Componentes del modelo

El modelo descompone la serie en tres componentes:

```
Forecast(t+1) = Nivel(t) + Tendencia_amortiguada(t) + Estacionalidad(t+1)
```

**Nivel (Level)**: El valor base suavizado de la serie.

```
L(t) = alpha * Y(t) + (1 - alpha) * [L(t-1) + phi * b(t-1)]
```

**Tendencia (Trend)**: La pendiente (cuanto sube o baja por periodo).

```
b(t) = beta * [L(t) - L(t-1)] + (1 - beta) * phi * b(t-1)
```

**Estacionalidad (Seasonal)**: Factor estacional para cada mes.

```
s(t) = gamma * [Y(t) - L(t)] + (1 - gamma) * s(t - 12)
```

**Forecast**:

```
F(t+h) = L(t) + (phi + phi^2 + ... + phi^h) * b(t) + s(t + h - 12)
```

Donde:
- `alpha` = parametro de suavizado del nivel (0 a 1)
- `beta` = parametro de suavizado de la tendencia (0 a 1)
- `gamma` = parametro de suavizado de la estacionalidad (0 a 1)
- `phi` = parametro de amortiguamiento de tendencia (0 a 1)
- Todos se optimizan automaticamente por `statsmodels` minimizando SSE

### Por que tendencia amortiguada (damped)?

```
Sin amortiguar:  +5%/mes → +5%/mes → +5%/mes → ... (infinito)
Con amortiguar:  +5%/mes → +4%/mes → +3%/mes → +2% → +1% (se estabiliza)
```

Sin amortiguamiento, una marca que crece 5% mensual proyectaria ventas infinitas. Con `phi < 1`, el efecto de la tendencia se reduce geometricamente:

```
Efecto en h periodos = phi^1 * b + phi^2 * b + ... + phi^h * b
```

Con phi tipico ~0.95: efecto a 6 meses = 0.95^1 + ... + 0.95^6 = 5.03 * b (vs 6 * b sin amortiguar)

### Double Exponential Smoothing (12 <= N < 24)

```python
model = ExponentialSmoothing(
    series,
    trend='add',
    seasonal=None,         # SIN estacionalidad
    damped_trend=True
).fit(optimized=True)
```

Captura nivel y tendencia, pero no estacionalidad (necesita al menos 2 ciclos completos = 24 meses para detectar patrones estacionales confiables).

### Post-procesamiento

```python
forecast_values = model.forecast(1).clip(lower=0)
```

`.clip(lower=0)` garantiza que el forecast nunca sea negativo. Posible con tendencia fuertemente descendente en series pequenas.

### Epsilon shift

```python
y = y + 1e-6
```

Se suma un epsilon antes del modelado para evitar problemas numericos con ceros exactos en la serie. Es una practica estandar en Holt-Winters.

---

## 6. Ajuste por eventos moviles (Carnaval, Semana Santa)

**Archivo**: `event_calendar.py`

### El problema

Holt-Winters aprende estacionalidad fija: "febrero siempre se comporta de X manera". Pero eventos como Carnaval cambian de mes entre anos:

| Ano | Carnaval | Viernes Santo | Corpus Christi |
|-----|----------|---------------|----------------|
| 2024 | Febrero (12-13) | Marzo (29) | Mayo (30) |
| 2025 | Marzo (3-4) | Abril (18) | Junio (19) |
| 2026 | Febrero (16-17) | Abril (3) | Junio (4) |

### Fuente de datos

```python
# utils/business_days.py → BusinessDaysCalculator.mobile_holidays
{
    2024: [(2,12), (2,13), (3,29), (5,30)],
    2025: [(3,3), (3,4), (4,18), (6,19)],
    2026: [(2,16), (2,17), (4,3), (6,4)],
}
```

### Mapeo de eventos (por posicion en la lista)

```python
event_map = [
    'carnaval',       # Posicion 0: Carnaval Lunes
    'carnaval',       # Posicion 1: Carnaval Martes (dedup)
    'viernes_santo',  # Posicion 2: Viernes Santo
    'corpus_christi',  # Posicion 3: Corpus Christi
]
```

### Factores de impacto (config.py)

```python
EVENT_IMPACTS = {
    'carnaval': 0.15,        # +15% (2-3 dias de fiesta masiva, alto consumo)
    'viernes_santo': -0.02,  # -2% (leve baja en consumo)
    'corpus_christi': 0.0,   # 0% (sin impacto medible)
}
```

### Algoritmo de ajuste

El ajuste es **post-forecast** (no modifica los datos historicos ni el modelo):

```
1. Holt-Winters genera forecast base normalmente
2. Se determina training_years = [target_year - 2, target_year - 1]
3. Para cada evento en el mes target:
   a. Si el evento es NUEVO (no estaba en este mes en >=50% de training years)
      → factor *= (1 + impacto)
   b. Si el evento SE FUE (estaba en >=50% de training years, ya no esta)
      → factor *= (1 - impacto)
4. forecast_ajustado = forecast_base * factor
```

### Ejemplo: Proyeccion para Marzo 2026

```
Target: Marzo 2026
training_years: [2024, 2025]

Eventos en Marzo 2026: Ninguno (Carnaval esta en Feb, ViernesSanto en Abr)

Eventos en Marzo en training:
  2024: Viernes Santo (29 Mar) → viernes_santo
  2025: Carnaval (3-4 Mar) → carnaval

  carnaval: 1 de 2 anos >= threshold(1) → historicamente presente en Marzo
  viernes_santo: 1 de 2 anos >= threshold(1) → historicamente presente en Marzo

Eventos que SE FUERON de Marzo: [carnaval, viernes_santo]
  carnaval: factor *= (1 - 0.15) = 0.85
  viernes_santo: factor *= (1 - (-0.02)) = 1.02

Factor final: 0.85 * 1.02 = 0.867
→ Forecast de Marzo 2026 se reduce ~13% (se fue Carnaval, se fue ViernesSanto)
```

### Ejemplo: Proyeccion para Febrero 2026

```
Target: Febrero 2026
training_years: [2024, 2025]

Eventos en Febrero 2026: [carnaval]

Eventos en Febrero en training:
  2024: Carnaval (12-13 Feb) → carnaval (1 vez)
  2025: Ningun evento en Febrero (0 veces)

  carnaval: 1 de 2 anos >= threshold(1) → historicamente presente

Eventos NUEVOS en Feb: ninguno (carnaval ya estaba en Feb 2024)
Eventos que SE FUERON: ninguno

Factor final: 1.0 → Sin ajuste
→ Febrero 2026 no necesita ajuste porque el modelo ya tiene
  un febrero con Carnaval (2024) en su training data.
```

### Nota sobre el threshold

```python
threshold = max(1, valid_training_years / 2)
```

Con 2 anos validos: threshold = 1. Un evento necesita haber estado en al menos 1 de los 2 anos de training para considerarse "historicamente presente". Esto es conservador: incluso si el evento solo estuvo una vez, el modelo ya lo "vio".

---

## 7. Spread y diagnostico

**Archivo**: `projection_processor.py`

### Formula del spread

```
Spread = (PY_Gerente / PY_Estadistica) - 1
```

Solo se calcula si ambos valores existen y PY_Estadistica > 0.

### Clasificacion automatica

```python
SPREAD_OPTIMISTA_THRESHOLD = 0.10     # >+10%
SPREAD_CONSERVADOR_THRESHOLD = -0.10  # <-10%
SPREAD_CONSENSO_THRESHOLD = 0.05     # |spread| < 5%
```

| Condicion | Diagnostico |
|-----------|-------------|
| spread > +10% | "Gerente optimista vs datos" |
| spread < -10% | "Gerente conservador vs datos" |
| \|spread\| < 5% | "Alto consenso" |
| 5% a 10% (positivo o negativo) | "Leve divergencia" |

### Orden de evaluacion

El codigo evalua en este orden (importante porque los rangos se solapan):

```python
if spread > 0.10:        # Primero: optimista
    return "Gerente optimista vs datos"
elif spread < -0.10:     # Segundo: conservador
    return "Gerente conservador vs datos"
elif abs(spread) < 0.05: # Tercero: consenso
    return "Alto consenso"
else:                     # Cuarto: leve divergencia (5-10%)
    return "Leve divergencia"
```

### Ejemplo

```
BRANCA: PY Gerente = 1,350,000 | PY Estadistica = 1,280,000
Spread = (1,350,000 / 1,280,000) - 1 = +5.5%
|5.5%| > 5% pero < 10% → "Leve divergencia"
```

---

## 8. Flujo completo (diagrama)

```
                    DWH PostgreSQL
                         |
                         v
              +-----------------------+
              |   data_fetcher.py     |
              |   Query 4:            |
              |   td_ventas_bob_      |
              |   historico            |
              |   36 meses            |
              |   GROUP BY marca,     |
              |   ciudad, anio, mes   |
              +-----------+-----------+
                          |
                          v
              DataFrame (marcadir, ciudad, anio, mes, venta_bob)
                          |
             +------------+------------+
             |                         |
             v                         v
    run_by_marca()              run_by_ciudad()
    groupby(marcadir)           groupby(ciudad)
    sum(venta_bob)              sum(venta_bob)
             |                         |
             v                         v
    _df_to_monthly_series()     _df_to_monthly_series()
    DatetimeIndex + asfreq(MS)  DatetimeIndex + asfreq(MS)
    fillna(0)                   fillna(0)
             |                         |
             v                         v
    Para cada marca:            Para cada ciudad:
             |                         |
             v                         v
    +--------------------+      +--------------------+
    | _clean_outliers()  |      | _clean_outliers()  |
    | Rolling mean w=5   |      | Rolling mean w=5   |
    | Z-score adaptativo |      | Z-score adaptativo |
    | Solo outliers bajos|      | Solo outliers bajos|
    +--------+-----------+      +--------+-----------+
             |                         |
             v                         v
    +--------------------+      +--------------------+
    | forecast_single_   |      | forecast_single_   |
    | series()           |      | series()           |
    |                    |      |                    |
    | N>=25: Triple Exp  |      | N>=25: Triple Exp  |
    | 12<=N<25: Double   |      | 12<=N<25: Double   |
    | N<12: None         |      | N<12: None         |
    | >70% ceros: None   |      | >70% ceros: None   |
    |                    |      |                    |
    | damped_trend=True  |      | damped_trend=True  |
    | seasonal='add'     |      | seasonal='add'     |
    | optimized=True     |      | optimized=True     |
    +--------+-----------+      +--------+-----------+
             |                         |
             v                         v
    +--------------------+      +--------------------+
    | _apply_event_      |      | _apply_event_      |
    | adjustment()       |      | adjustment()       |
    |                    |      |                    |
    | Carnaval: +-15%    |      | Carnaval: +-15%    |
    | ViernesSanto: +-2% |      | ViernesSanto: +-2% |
    | CorpusChristi: 0%  |      | CorpusChristi: 0%  |
    +--------+-----------+      +--------+-----------+
             |                         |
             v                         v
    py_est_marca                py_est_ciudad
    (marcadir, py_estadistica_bob,     (ciudad, py_estadistica_bob,
     model_type, confidence,            model_type, confidence,
     n_months, event_adjustment)        n_months, event_adjustment)
             |                         |
             +------------+------------+
                          |
                          v
              +-----------------------+
              | projection_           |
              | processor.py          |
              |                       |
              | _build_comparativo()  |
              |   merge con PY        |
              |   Gerente             |
              |   + PY Operativa      |
              |                       |
              | _calculate_spread()   |
              | _diagnose_spread()    |
              +-----------+-----------+
                          |
                          v
              comparativo_marca / comparativo_ciudad
              (entidad, py_gerente, py_estadistica,
               py_operativa, spread, diagnostico)
```

---

## 9. Libreria matematica

```
Libreria:  statsmodels.tsa.holtwinters.ExponentialSmoothing
Version:   >= 0.14.0
Dependencia: scipy >= 1.10.0 (optimizacion de parametros)
```

**Origen del codigo**: Adaptacion del proyecto FORECAST-DM de Marcelo (`dym-forecast-marcelo/`), especificamente de `libraries/forecast/src/forecast/models/exponential_smoothing/triple.py`. Se extrajeron ~150 lineas de logica core sin heredar la infraestructura pesada (Docker, Poetry, DataControlCenter, etc.).

**Referencia de industria**: Holt-Winters (1950-60) es el estandar de la industria de bebidas y consumo masivo. AB InBev, Coca-Cola y las principales empresas de CPG lo usan como capa base de demand planning.

---

## 10. Configuracion completa (config.py)

```python
# Tablas
TABLE_VENTAS_HISTORICO = "td_ventas_bob_historico"

# Motor Estadistico
MIN_MONTHS_TRIPLE = 25    # Modelo completo
MIN_MONTHS_DOUBLE = 12    # Solo tendencia
MIN_MONTHS_MINIMUM = 12   # Minimo absoluto
ZERO_THRESHOLD = 0.70     # Serie intermitente

# Limpieza de outliers
OUTLIER_WINDOW = 5
OUTLIER_Z_THRESH = 2.5    # Efectivo: min(2.5, 1.70) = 1.70

# Estacionalidad
SEASONAL_PERIOD = 12

# Spread
SPREAD_OPTIMISTA_THRESHOLD = 0.10
SPREAD_CONSERVADOR_THRESHOLD = -0.10
SPREAD_CONSENSO_THRESHOLD = 0.05

# Eventos moviles
EVENT_IMPACTS = {
    'carnaval': 0.15,
    'viernes_santo': -0.02,
    'corpus_christi': 0.0,
}
TRAINING_YEARS_LOOKBACK = 2

# Sanidad
SANITY_MIN_FACTOR = 0.50
SANITY_MAX_FACTOR = 2.00
```

---

## 11. Tests

**Archivo**: `tests/test_statistical_engine.py`

| Test | Que valida |
|------|-----------|
| `test_no_outliers_unchanged` | Serie limpia no se modifica |
| `test_low_outlier_replaced` | Outlier bajo se corrige |
| `test_insufficient_data_returns_none` | <12 meses → None |
| `test_mostly_zeros_returns_none` | >70% ceros → None |
| `test_double_exp_for_12_to_24_months` | 18 meses → modelo 'double', confianza 'medium' |
| `test_triple_exp_for_25_plus_months` | 30 meses → modelo 'triple', confianza 'high' |
| `test_forecast_within_sanity_bounds` | Forecast entre 30%-300% del promedio |
| `test_run_by_marca_returns_dataframe` | Estructura correcta del output por marca |
| `test_run_by_ciudad_returns_dataframe` | Estructura correcta del output por ciudad |

Ejecutar:

```bash
pytest proyeccion_objetiva/tests/test_statistical_engine.py -v
```

---

## 12. Limitaciones conocidas

1. **Solo proyecta 1 mes adelante** (`horizon=1`). El modelo *puede* proyectar mas periodos, pero la precision decae rapidamente despues del primer mes.

2. **No hay nivel marca x ciudad**. Holt-Winters se ejecuta a nivel marca (suma de ciudades) y a nivel ciudad (suma de marcas), pero no para cada combinacion. Las series individuales serian mas ruidosas y muchas no alcanzarian los 25 meses necesarios.

3. **`mobile_holidays` necesita actualizacion manual** para anos futuros. Si no se agregan las fechas de 2027+, el ajuste por eventos retorna factor 1.0 (sin ajuste). No falla, pero pierde la correccion.

4. **El mapeo de eventos por posicion es fragil**. Si alguien reordena las entradas en `business_days.py`, el mapeo en `event_calendar.py` se rompe silenciosamente. Se mitiga con el hecho de que el archivo rara vez cambia.

5. **Estacionalidad aditiva**. Se asume que la estacionalidad es un monto fijo, no un porcentaje. Para marcas que crecen mucho en volumen, la multiplicativa podria ser mas precisa. Con tendencia amortiguada, la diferencia es minima en la practica.
