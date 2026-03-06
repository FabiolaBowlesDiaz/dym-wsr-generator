# Pilar 2: PY Estadística — Holt-Winters (Explicación detallada)

## ¿Qué problema resuelve?

Tienes 24-36 meses de ventas históricas de cada marca en cada ciudad:

```
Ene-24: 800K    Feb-24: 750K    Mar-24: 820K    Abr-24: 780K ...
Ene-25: 850K    Feb-25: 790K    Mar-25: 870K    Abr-25: 830K ...
Ene-26: 900K    Feb-26: ???
```

La pregunta es: **¿cuánto va a vender esta marca en esta ciudad el próximo mes?**

---

## Paso a paso: ¿qué hace el algoritmo?

### Paso 1: Limpiar los datos (outlier cleaning)

Antes de analizar, limpiamos **caídas anómalas**. Ejemplo: si en julio 2024 hubo un problema de stock y BRANCA solo vendió 100K (cuando normalmente vende 800K), ese dato distorsiona todo.

```
Jul-24: 100K  ← Esto es una anomalía, no refleja la demanda real
```

El algoritmo detecta estos puntos con una regla simple:
- Calcula el **promedio móvil** de los 5 meses alrededor
- Si un valor está **muy por debajo** del promedio (más de 2.5 desviaciones estándar abajo Y menos del 40% del promedio), lo reemplaza con el promedio

Solo limpiamos caídas, no picos. Si un mes vendió el doble, puede ser real (una promoción fuerte, un evento).

### Paso 2: Detectar los tres componentes de la serie

El algoritmo mira la historia y separa tres cosas:

**Componente 1 — Nivel**: el valor base. "BRANCA en Santa Cruz vende alrededor de 800K por mes"

**Componente 2 — Tendencia**: ¿viene subiendo o bajando? "Está creciendo ~5% interanual"

**Componente 3 — Estacionalidad**: ¿hay meses que siempre venden más o menos? "Febrero siempre cae 6% vs enero, diciembre siempre sube 15%"

```
                    Venta real
                    ┌─────────┐
                    │         │
        Nivel       │  800K   │  ← Base estable
      + Tendencia   │  +40K   │  ← Viene subiendo
      + Estacional  │  -50K   │  ← Febrero siempre baja
                    │ ─────── │
      = Proyección  │  790K   │
                    └─────────┘
```

### Paso 3: Suavizado exponencial (el "Holt-Winters")

El algoritmo **no trata todos los meses iguales**. Le da **más peso a los datos recientes** y menos a los antiguos. De ahí el nombre "exponencial" — el peso decae exponencialmente hacia el pasado.

```
Feb-26 (hoy):     peso máximo ████████████
Ene-26 (hace 1m): peso alto   ██████████
Dic-25 (hace 2m): peso medio  ████████
Nov-25 (hace 3m): peso menor  ██████
...
Ene-24 (hace 25m): peso mínimo █
```

Esto es lógico: lo que pasó hace 2 meses es más relevante para predecir el próximo mes que lo que pasó hace 2 años.

El método tiene tres parámetros de suavizado (alpha, beta, gamma) — uno para cada componente (nivel, tendencia, estacionalidad). Dejamos que `statsmodels` los **optimice automáticamente** buscando la combinación que mejor explica la historia.

### Paso 4: Tendencia amortiguada (damped trend)

Sin amortiguamiento, si una marca viene creciendo 5% mensual, el modelo diría "en 12 meses va a estar vendiendo 80% más". Eso no tiene sentido — ningún crecimiento es infinito.

Con **tendencia amortiguada**, el crecimiento se va aplanando:

```
Sin amortiguar:    +5% → +5% → +5% → +5% → ...  (crece para siempre)
Con amortiguar:    +5% → +4% → +3% → +2% → +1%  (se estabiliza)
```

Esto produce proyecciones más realistas y conservadoras.

### Paso 5: Generar la proyección

Con los tres componentes calibrados, el modelo proyecta el siguiente mes:

```
Proyección Feb-26 = Nivel actualizado + Tendencia amortiguada + Factor estacional de febrero
```

---

## ¿Qué pasa si no hay suficientes datos?

| Meses disponibles | Modelo | Qué captura | Confianza |
|-------------------|--------|-------------|-----------|
| **25 o más** | Triple Exp (Holt-Winters completo) | Nivel + Tendencia + Estacionalidad | Alta |
| **12 a 24** | Double Exp | Nivel + Tendencia (sin estacionalidad, necesita 2 ciclos para detectarla) | Media |
| **Menos de 12** | Ninguno | No se genera proyección — dice "datos insuficientes" | — |
| **>70% ceros** | Ninguno | Serie intermitente, no se puede modelar | — |

---

## Origen del código

La lógica viene del proyecto FORECAST-DM de Marcelo (`dym-forecast-marcelo/`), específicamente de tres piezas:

| De Marcelo (`triple.py`) | Lo nuestro (`statistical_engine.py`) | Qué hace |
|---------------------------|--------------------------------------|----------|
| `replace_low_outliers_rolling()` | `_clean_outliers()` | Limpia caídas anómalas |
| `TripleExpModel.train()` | Dentro de `forecast_single_series()` | Configura el modelo Holt-Winters |
| `exp_smoothing_predict_groups()` | `run_by_marca()` / `run_by_ciudad()` | Itera grupos y elige Triple vs Double |

El proyecto de Marcelo es un framework completo con Docker, 7 paquetes internos, y 10+ modelos (incluyendo ML como CatBoost, LightGBM, XGBoost). Nosotros solo extrajimos las ~100 líneas de lógica Holt-Winters, sin heredar la infraestructura pesada.

La librería matemática subyacente es la misma: `statsmodels.tsa.holtwinters.ExponentialSmoothing`.

---

## ¿Es correcto para proyecciones mensuales de ventas de bebidas?

**Sí. Es uno de los métodos más probados que existen para este caso de uso.**

Holt-Winters fue creado en los años 1950-60 por Charles Holt y Peter Winters, específicamente para forecasting de ventas e inventarios. Tiene 60+ años de uso en producción.

Es particularmente adecuado cuando:
- Los datos son **mensuales** (como los de DYM)
- Hay **estacionalidad** (meses que siempre venden más o menos)
- Se quiere proyectar **pocos períodos adelante** (1-3 meses)
- No hay variables externas complicadas que modelar

---

## ¿Lo usan empresas grandes del mismo rubro?

**Sí. Es literalmente el estándar de la industria de bebidas y consumo masivo.**

### AB InBev (Budweiser, Corona, Stella Artois)
Usa exponential smoothing como **capa base** de sus modelos de demand planning. Sobre esa base agrega ML con su sistema SenseAI y su plataforma en Azure.

### Coca-Cola
Estudios académicos y documentos internos muestran que usan time series forecasting con **moving averages, exponential smoothing y ARIMA** como métodos core para proyectar ventas.

### Industria de alimentos y bebidas en general
Un paper académico (ResearchGate, 2018) que compara modelos para demanda estacional en manufactura de bebidas concluye que **Holt-Winters y Decomposition obtuvieron los mejores resultados** en métricas de performance vs otros métodos.

### El patrón de la industria: approach en capas

Las empresas grandes de CPG (Consumer Packaged Goods) usan capas complementarias:

```
Capa 1 (base):     Holt-Winters / Exponential Smoothing    ← ESTO implementamos
Capa 2 (mejora):   ML (LightGBM, XGBoost, Prophet)         ← Esto es el FORECAST-DM de Marcelo
Capa 3 (ajuste):   Juicio del demand planner / gerente      ← Esto ya existe en el WSR
```

Nosotros implementamos la Capa 1, que era la que faltaba en el WSR.

---

## Paso 6: Ajuste por Eventos Móviles (Carnaval, Semana Santa)

### El problema

Holt-Winters aprende **estacionalidad fija**: "febrero siempre se comporta de X manera, marzo de Y manera". Pero en Bolivia hay eventos que **cambian de mes entre años**:

| Evento | 2025 | 2026 | Efecto |
|--------|------|------|--------|
| **Carnaval** | Marzo (3-4 Mar) | Febrero (16-17 Feb) | Mueve mucha bebida, 2-3 días de fiesta masiva |
| **Viernes Santo** | Abril (18 Abr) | Abril (3 Abr) | Mismo mes, efecto menor |
| **Corpus Christi** | Junio (19 Jun) | Junio (4 Jun) | Mismo mes, efecto despreciable |

**El problema concreto con Carnaval 2026:**

```
Lo que el modelo "aprendió":
  Febrero 2024: sin Carnaval → venta normal
  Febrero 2025: sin Carnaval → venta normal
  → "Febrero siempre es normal"

  Marzo 2024: sin Carnaval → venta normal
  Marzo 2025: CON Carnaval → venta alta
  → "Marzo viene subiendo" (confunde Carnaval con tendencia)

Lo que va a pasar en realidad:
  Febrero 2026: CON Carnaval → debería ser alto
  Marzo 2026: sin Carnaval → debería ser normal
```

Sin corrección, el modelo subestima febrero 2026 y sobreestima marzo 2026.

### La solución: Ajuste post-forecast

No modificamos los datos históricos ni el modelo — eso es riesgoso porque Holt-Winters es sensible a cambios en la serie. En cambio, hacemos un **ajuste multiplicativo después** del forecast:

```
                         Holt-Winters
                         ┌──────────┐
  Serie histórica ─────→ │  Modelo  │ ─────→ Forecast base
  (sin modificar)        └──────────┘         │
                                              │
                         Calendario           │
                         ┌──────────┐         ▼
  mobile_holidays ─────→ │ Detectar │ ─→ × factor de ajuste
  (business_days.py)     │ cambios  │
                         └──────────┘         │
                                              ▼
                                        Forecast ajustado
```

**¿Cómo funciona la detección?**

Para el mes que estamos proyectando (ej: febrero 2026):

1. **¿Hay un evento en este mes este año?** → Carnaval SÍ está en febrero 2026
2. **¿Estaba este evento en este mismo mes en los años de entrenamiento?** → Carnaval NO estaba en febrero 2024 ni 2025
3. **Conclusión**: Carnaval es **nuevo** en febrero → aplicar boost de +15%

```
Forecast base (Holt-Winters):     BOB 800,000
Factor de ajuste:                  × 1.15 (Carnaval nuevo en febrero)
Forecast ajustado:                 BOB 920,000
```

### Factores de impacto

Los factores son estimaciones conservadoras basadas en la magnitud de cada evento:

| Evento | Impacto estimado | Justificación |
|--------|-----------------|---------------|
| **Carnaval** | ±15% | 2-3 días de fiesta masiva, alto consumo de bebidas. Es el evento de mayor impacto en ventas. |
| **Viernes Santo** | ±2% | 1 día, más religioso/familiar, leve baja en bares pero compensada por reuniones familiares. |
| **Corpus Christi** | 0% | 1 día sin impacto medible en el patrón de bebidas. |

El signo depende de la dirección:
- **Evento NUEVO en el mes** (+): el modelo no lo esperaba, hay que sumar el efecto
- **Evento SE FUE del mes** (-): el modelo lo esperaba (por el año anterior), hay que restar

### Ejemplo concreto: Febrero 2026

```
Paso 1: Holt-Winters genera forecast base para Feb 2026
  → Basado en Feb 2024 y Feb 2025 (ambos sin Carnaval)
  → Forecast base: BOB 800,000 (feb "normal")

Paso 2: Calendario detecta que Carnaval 2026 es en Febrero
  → Carnaval NO estaba en Febrero en 2024 ni 2025
  → Carnaval es NUEVO en este mes

Paso 3: Aplicar ajuste
  → Factor: 1 + 0.15 = 1.15
  → Forecast ajustado: 800,000 × 1.15 = 920,000

En el reporte aparece:
  PY Estadística: BOB 920,000
  (Ajuste: +15% por CARNAVAL nuevo en mes 2)
```

### Fuente de datos

El calendario viene del archivo que ya existe en el proyecto: `utils/business_days.py`, clase `BusinessDaysCalculator`. Este archivo ya tiene:

- **Festivos fijos** de Bolivia (Año Nuevo, 22 de Enero, 1 de Mayo, etc.)
- **Festivos móviles** para 2025 y 2026 (Carnaval, Viernes Santo, Corpus Christi)

No se creó un calendario nuevo — se reutiliza el que ya estaba en producción.

### Limitaciones actuales

1. **Los factores de impacto (15%, 2%, 0%) son estimaciones iniciales.** Idealmente se calibrarían con datos históricos de ventas durante eventos vs meses normales. Esto se puede hacer como mejora futura cuando haya más años de datos.

2. **Solo se tienen festivos móviles para 2025-2026.** Para años futuros, hay que agregarlos al diccionario `mobile_holidays` en `business_days.py`.

3. **El ajuste es uniforme por mes.** No distingue si el impacto es mayor en una marca vs otra. Carnaval probablemente impacta más a bebidas alcohólicas que a aguas. Esto se podría segmentar por categoría como mejora futura.

---

## Niveles de análisis: ¿a qué nivel se presentan los resultados?

### Niveles implementados actualmente

| Nivel | Descripción | Ejemplo de output | Estado |
|:-----:|-------------|-------------------|:------:|
| **1. Nacional total** | Un solo número para todo DYM | "DYM va a vender BOB 12.5M este mes" | Implementado |
| **2. Por marca** | Una proyección por marca (suma de todas las ciudades) | "BRANCA: BOB 3.2M, HAVANA: BOB 2.8M, ..." | Implementado |
| **3. Por ciudad** | Una proyección por ciudad (suma de todas las marcas) | "Santa Cruz: BOB 5.1M, La Paz: BOB 3.8M, ..." | Implementado |
| **4. Por marca × ciudad** | Una proyección por cada combinación | "BRANCA en Santa Cruz: BOB 1.4M" | **No implementado** |

```
                     NACIONAL TOTAL                   ← Nivel 1 (implementado)
                    /              \
            POR MARCA          POR CIUDAD             ← Niveles 2 y 3 (implementados)
           /    |    \        /    |    \
        BRANCA HAVANA ...  SCZ   LPZ  CBBA
           \    |    /        \    |    /
            POR MARCA × CIUDAD                        ← Nivel 4 (no implementado)
         BRANCA-SCZ, BRANCA-LPZ,
         HAVANA-SCZ, HAVANA-LPZ, ...
```

### ¿Cómo funciona cada nivel?

**Nivel 1 — Nacional**: Suma las proyecciones de todas las marcas (o todas las ciudades). Es el número macro para directorio.

**Nivel 2 — Por marca**: Holt-Winters recibe una serie de 24-36 meses donde la venta de cada mes es la **suma de todas las ciudades** de esa marca. Ejemplo: BRANCA vendió 3.2M en enero = SCZ 1.4M + LPZ 0.9M + CBBA 0.5M + otras. El modelo ve esa serie agregada y proyecta un siguiente mes.

**Nivel 3 — Por ciudad**: Holt-Winters recibe una serie donde la venta de cada mes es la **suma de todas las marcas** de esa ciudad. Ejemplo: Santa Cruz vendió 5.1M en enero = BRANCA 1.4M + HAVANA 1.2M + otras. El modelo ve esa serie agregada.

### Nivel 4 — Por marca × ciudad (no implementado, pero posible)

Los datos en el DWH **sí vienen a nivel marca × ciudad** (cada query trae `GROUP BY marcadir, ciudad, anio, mes`). Lo que no existe hoy es el código que itere sobre cada combinación.

**¿Se puede implementar?** Sí, técnicamente. Pero tiene una consideración importante:

**Series más cortas y con más ruido**: Al abrir por marca × ciudad, cada serie individual tiene menos volumen. Una marca pequeña en una ciudad pequeña podría tener solo 50K por mes con alta variabilidad. Holt-Winters necesita 25+ meses con señal estable para funcionar bien. Combinaciones con series muy ruidosas o con muchos ceros (>70%) serían descartadas automáticamente.

**Recomendación**: Es viable para las combinaciones grandes (ej: BRANCA en Santa Cruz, HAVANA en La Paz), pero probablemente la mitad de las combinaciones pequeñas no tendría datos suficientes y diría "datos insuficientes". Hay que evaluar si el valor de esas proyecciones granulares justifica la complejidad adicional.

### Pregunta para el equipo

**¿Es necesario el nivel marca × ciudad?** ¿Los directores necesitan ver la proyección de BRANCA específicamente en Santa Cruz, o con saber el total de BRANCA (nacional) y el total de Santa Cruz (todas las marcas) es suficiente? Si la respuesta es "sí, necesitamos marca × ciudad", se puede agregar — los datos ya están, solo falta el código.

---

## Referencias

- [Time Series Forecasting for Seasonal Demands in Beverage Manufacturing (ResearchGate)](https://www.researchgate.net/publication/323004243_The_Application_of_Time_Series_Model_in_Forecasting_Seasonal_Demands_of_Product_Brands_in_the_Manufacturing_Industry)
- [Demand Forecasting of Coca-Cola (Scribd)](https://www.scribd.com/presentation/388495061/Demand-Forecasting-of-The-Coca-Cola-Comapny-pptx)
- [Coca-Cola AI Strategy in CPG (Klover.ai)](https://www.klover.ai/coca-cola-ai-strategy-market-dominance-in-consumer-packaged-goods/)
- [Forecasting Coca-Cola Global Volume 2025-2027 (ResearchGate)](https://www.researchgate.net/publication/387855125_Forecasting_the_Next_3_Years_2025-2027_Global_Unit_Volume_of_the_Coca-Cola_Company_in_Billions_from_2015-2024)
