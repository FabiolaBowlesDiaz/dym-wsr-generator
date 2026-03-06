# Pilar 3: PY Operativa — Revenue Tree (Explicacion detallada)

## Que problema resuelve?

El Pilar 2 (Holt-Winters) responde: **cuanto va a vender esta marca este mes?**

Pero no responde: **por que ese numero? que lo esta moviendo?**

Si BRANCA en Santa Cruz vendio 900K el mes pasado y el modelo proyecta 850K para este mes, el director necesita saber: baja por menos clientes? menos conversion? menor ticket? Sin esa respuesta, no puede tomar accion.

El Pilar 3 resuelve exactamente eso. Descompone la venta en **tres palancas operativas** que la generan:

```
Venta Mensual = Cobertura x Hit Rate x Drop Size
```

---

## Los tres componentes

### 1. Cobertura (clientes unicos)

**Que mide**: Cuantos clientes distintos compraron en el mes.

No importa si un cliente compro 1 vez o 5 veces en el mes — cuenta como 1 cliente unico. Esto mide el **alcance** de la fuerza de ventas.

**Fuente de datos**: `FactVentas` → `COUNT(DISTINCT cod_cliente_padre)` agrupado por marca, ciudad y mes.

**Ejemplo**: En enero 2026, BRANCA en Santa Cruz tuvo **450 clientes unicos** que realizaron al menos una compra.

**Si baja**: Indica un problema de **ruta o cobertura**. Los vendedores no estan llegando a suficientes clientes. Accion: revisar rutas, agregar vendedores, o identificar clientes inactivos.

---

### 2. Hit Rate (tasa de conversion)

**Que mide**: Del total de clientes que fueron **visitados** por un vendedor, que porcentaje efectivamente **compro**.

```
Hit Rate = Clientes que compraron / Clientes que fueron visitados x 100
```

**Fuente de datos**: `fact_eficiencia_hitrate` → Tabla que registra visitas y ventas por cliente.

**Ejemplo**: Si se visitaron 625 clientes y 450 compraron:
```
Hit Rate = 450 / 625 x 100 = 72%
```

**LIMITACION CRITICA — Hit Rate no tiene marca**:

La tabla `fact_eficiencia_hitrate` actualmente **NO tiene una columna que identifique la marca**. Solo registra visitas y ventas por **ciudad** y **cliente**, sin indicar que marca se vendio.

Esto significa:

| Nivel de analisis | Que Hit Rate se usa? | Precision |
|-------------------|---------------------|-----------|
| **Por ciudad** (ej: Santa Cruz) | HR directo de esa ciudad | **Alta** — datos reales |
| **Por marca** (ej: BRANCA nacional) | HR promedio nacional ponderado | **Baja** — es un proxy |

**El impacto practico**: Si BRANCA tiene un HR real de 85% y CASA REAL tiene 55%, ambas se proyectan con el HR nacional (~70%). Esto **subestima** a BRANCA y **sobreestima** a CASA REAL en la PY Operativa por marca.

**Que se necesita para resolverlo**: El equipo de sistemas debe agregar a `fact_eficiencia_hitrate` una columna que permita vincular la visita con la marca vendida (por ejemplo, un `id_factura` que se pueda cruzar con `FactVentas`). Mientras esto no exista, **la PY Operativa por marca tiene esta imprecision conocida**. La PY Operativa por ciudad NO tiene este problema.

**Si baja**: Indica un problema de **conversion/selling**. Los vendedores estan visitando pero no cierran la venta. Accion: capacitacion, revision de precios, o analisis de competencia.

---

### 3. Drop Size (venta promedio por cliente)

**Que mide**: Cuanto compra en promedio cada cliente que si compro. Es el **ticket promedio por cliente**.

```
Drop Size = Venta total del mes / Numero de clientes que compraron
```

**Fuente de datos**: `FactVentas` → `SUM(total_venta) / COUNT(DISTINCT cod_cliente_padre)` por marca, ciudad y mes.

**Ejemplo**: Si la venta total fue BOB 1,350,000 y compraron 450 clientes:
```
Drop Size = 1,350,000 / 450 = BOB 3,000 por cliente
```

**Si baja**: Indica un problema de **mix o precio**. Los clientes compran pero compran menos. Accion: revisar mix de productos, politica de descuentos, o promover SKUs de mayor valor.

---

## El calculo paso a paso

Para cada componente (Cobertura, Hit Rate, Drop Size), el algoritmo hace exactamente lo mismo en dos pasos. Vamos a recorrerlo con numeros reales.

### Datos de ejemplo: Cobertura de BRANCA en Santa Cruz

```
Mes        Clientes unicos
---------  ---------------
Sep-25     380
Oct-25     400
Nov-25     395
Dic-25     420
Ene-26     440
Feb-26     460
```

---

### Paso 1: Promedio Movil Ponderado (WMA) de 3 meses

Toma los **ultimos 3 meses** y calcula un promedio, pero **no igual** — le da mas peso al mes mas reciente.

**Pesos** (configurados en `config.py`):

```
Mes mas reciente (Feb-26):     peso = 0.5  (50%)
Mes anterior (Ene-26):         peso = 0.3  (30%)
Hace 2 meses (Dic-25):         peso = 0.2  (20%)
                                Total: 1.0 (100%)
```

**Calculo**:

```
WMA = (Dic-25 x 0.2) + (Ene-26 x 0.3) + (Feb-26 x 0.5)
    = (420 x 0.2)     + (440 x 0.3)     + (460 x 0.5)
    = 84               + 132              + 230
    = 446 clientes
```

**Por que pesos desiguales?** Porque lo que paso hace 1 mes es mas relevante para el proximo mes que lo que paso hace 3 meses. Si en febrero subio a 460 clientes, eso pesa mas que los 420 de diciembre.

**Por que no usar solo el ultimo mes?** Porque un solo mes puede tener ruido (una semana atipica, un feriado). El promedio de 3 meses suaviza ese ruido pero sigue siendo reactivo a cambios recientes.

---

### Paso 2: Factor de Ajuste Estacional

Este paso **solo se aplica si hay 13 o mas meses de historia** (necesita al menos el mismo mes del ano anterior para comparar).

**Objetivo**: Detectar si hay un patron estacional. Por ejemplo, si marzo siempre vende mas que febrero, el factor debe reflejar eso.

**Calculo**:

```
Paso 2a: Calcular el factor bruto
  Factor_bruto = valor_del_ultimo_mes / mismo_mes_del_ano_anterior

  Ejemplo (si estamos proyectando para Marzo 2026):
    Feb-26: 460 clientes  (ultimo mes real)
    Feb-25: 430 clientes  (mismo mes, ano anterior)
    Factor_bruto = 460 / 430 = 1.070
```

Esto dice: "febrero 2026 tuvo 7% mas clientes que febrero 2025".

```
Paso 2b: Amortiguar el factor (no aplicar el 100% del efecto)
  Factor_amortiguado = 0.7 + (0.3 x Factor_bruto)
                     = 0.7 + (0.3 x 1.070)
                     = 0.7 + 0.321
                     = 1.021
```

**Por que amortiguar?** Sin amortiguamiento, si un ano tuvo un febrero excepcional (ej: 50% mas), el modelo proyectaria un marzo 50% mas alto que el promedio. Eso es sobreajustar. El amortiguamiento aplica **solo el 30% del efecto estacional** y mantiene un 70% de base neutral.

| Factor bruto | Sin amortiguar | Con amortiguar (30%) | Efecto real |
|:------------:|:--------------:|:--------------------:|:-----------:|
| 1.50 (+50%) | +50% | +15% | Moderado |
| 1.20 (+20%) | +20% | +6% | Sutil |
| 1.00 (igual) | 0% | 0% | Ninguno |
| 0.80 (-20%) | -20% | -6% | Sutil |
| 0.60 (-40%) | -40% | -12% | Moderado |

```
Paso 2c: Limitar el factor entre 0.5 y 2.0 (cap de seguridad)
  Si el factor amortiguado es < 0.5, se fuerza a 0.5
  Si el factor amortiguado es > 2.0, se fuerza a 2.0

  Esto evita distorsiones extremas si el ano anterior tuvo datos anomalos.
  En nuestro ejemplo: 1.021 esta dentro del rango, no se modifica.
```

**Si hay menos de 13 meses de historia**: El factor estacional es simplemente **1.0** (neutro). No hay con que comparar.

---

### Paso 3: Calcular la proyeccion del componente

```
Componente_proyectado = WMA x Factor_estacional
                      = 446 x 1.021
                      = 455 clientes
```

**Garantia de no-negativo**: Si el calculo diera un numero negativo (imposible en la practica pero por seguridad), se fuerza a 0.

---

### Paso 4: Repetir para los 3 componentes

El mismo calculo se hace para Hit Rate y Drop Size:

```
COBERTURA:
  Ultimos 3 meses: 420, 440, 460
  WMA = 420x0.2 + 440x0.3 + 460x0.5 = 446 clientes
  Factor estacional = 1.021
  Proyeccion = 446 x 1.021 = 455 clientes

HIT RATE:
  Ultimos 3 meses: 70%, 72%, 75%
  WMA = 70x0.2 + 72x0.3 + 75x0.5 = 73.1%
  Factor estacional = 1.015
  Proyeccion = 73.1 x 1.015 = 74.2%

DROP SIZE:
  Ultimos 3 meses: BOB 2,800, BOB 2,900, BOB 3,000
  WMA = 2800x0.2 + 2900x0.3 + 3000x0.5 = BOB 2,930
  Factor estacional = 1.030
  Proyeccion = 2930 x 1.030 = BOB 3,018
```

---

### Paso 5: Multiplicar los 3 componentes

```
PY Operativa = Cobertura x Hit Rate x Drop Size
             = 455 x (74.2 / 100) x 3,018
             = 455 x 0.742 x 3,018
             = BOB 1,018,600
```

Nota: El Hit Rate se divide entre 100 porque en los datos viene como porcentaje (74.2%), pero en la multiplicacion necesitamos el decimal (0.742).

---

### Paso 6: Calcular la tendencia de cada componente

Para cada componente, se calcula cuanto esta creciendo o cayendo. Esto es lo que aparece como flechas verdes o rojas en la tabla del reporte.

```
Tendencia = (promedio ultimos 3 meses / promedio 3 meses anteriores) - 1

Cobertura:
  Promedio Dic-Ene-Feb = (420 + 440 + 460) / 3 = 440.0
  Promedio Sep-Oct-Nov = (380 + 400 + 395) / 3 = 391.7
  Tendencia = (440.0 / 391.7) - 1 = +12.3%  → ↑12.3% (verde)

Hit Rate:
  Promedio Dic-Ene-Feb = (70 + 72 + 75) / 3 = 72.3
  Promedio Sep-Oct-Nov = (68 + 69 + 71) / 3 = 69.3
  Tendencia = (72.3 / 69.3) - 1 = +4.3%  → ↑4.3% (verde)

Drop Size:
  Promedio Dic-Ene-Feb = (2800 + 2900 + 3000) / 3 = 2,900
  Promedio Sep-Oct-Nov = (2700 + 2750 + 2780) / 3 = 2,743
  Tendencia = (2900 / 2743) - 1 = +5.7%  → ↑5.7% (verde)
```

Si la tendencia fuera negativa, la flecha seria roja (↓).

---

## Como se ve en el reporte

### Tabla de descomposicion operativa (por ciudad)

```
┌─────────────┬───────────────┬───────┬──────────────┬───────┬───────────────┬───────┬──────────────┐
│ Ciudad      │ Cobertura     │ Tend. │ Hit Rate (%) │ Tend. │ Drop Size     │ Tend. │ PY Operativa │
│             │ (clientes)    │       │              │       │ (BOB)         │       │ (BOB)        │
├─────────────┼───────────────┼───────┼──────────────┼───────┼───────────────┼───────┼──────────────┤
│ Santa Cruz  │ 455           │ ↑12%  │ 74.2%        │ ↑4%   │ 3,018         │ ↑6%   │ 1,018,600    │
│ La Paz      │ 280           │ ↑3%   │ 68.5%        │ ↓2%   │ 2,650         │ ↑1%   │ 508,200      │
│ Cochabamba  │ 210           │ ↓5%   │ 71.0%        │ ↑1%   │ 2,400         │ ↓3%   │ 357,800      │
└─────────────┴───────────────┴───────┴──────────────┴───────┴───────────────┴───────┴──────────────┘
```

Con esta tabla, el director puede decir inmediatamente:

- **Santa Cruz**: Todo sube, situacion saludable
- **La Paz**: Cobertura sube pero Hit Rate baja → los vendedores estan visitando mas clientes pero convirtiendo menos. Posible problema de capacitacion o de competencia en esos nuevos clientes
- **Cochabamba**: Cobertura baja Y Drop Size baja → se estan perdiendo clientes Y los que quedan compran menos. Alerta roja, necesita investigacion

### Tabla comparativa triple pilar (por marca)

```
┌──────────┬──────────┬───────────────┬────────────────┬───────────────┬─────────┬─────────────────────┐
│ Marca    │ Avance   │ PY Gerente    │ PY Estadistica │ PY Operativa  │ Spread  │ Diagnostico         │
├──────────┼──────────┼───────────────┼────────────────┼───────────────┼─────────┼─────────────────────┤
│ BRANCA   │ 1.2M     │ 1.35M         │ 1.28M          │ 1.31M         │ +5.5%   │ Leve divergencia    │
│ HAVANA   │ 800K     │ 1.10M         │ 920K           │ 950K          │ +19.6%  │ Gerente optimista   │
│ CASA REAL│ 500K     │ 650K          │ 680K           │ 670K          │ -4.4%   │ Alto consenso       │
└──────────┴──────────┴───────────────┴────────────────┴───────────────┴─────────┴─────────────────────┘
```

Aqui el director ve que para HAVANA, el gerente dice 1.10M pero los datos dicen ~930K. El gerente esta siendo optimista en un 20%. Requiere conversacion.

---

## Diferencias entre nivel ciudad y nivel marca

| Aspecto | Por ciudad | Por marca |
|---------|-----------|-----------|
| **Cobertura** | Suma de clientes unicos en esa ciudad | Suma de clientes unicos de esa marca (todas las ciudades) |
| **Hit Rate** | HR **directo** de esa ciudad | HR **nacional** como proxy (**PENDIENTE: falta columna de marca en `fact_eficiencia_hitrate`**) |
| **Drop Size** | Venta total de la ciudad / clientes de la ciudad | Venta total de la marca / clientes de la marca |
| **Precision** | Alta (todos los datos son directos) | Media (HR es proxy) |

---

## Fallback: cuando no hay datos de FactVentas

El sistema verifica automaticamente si `FactVentas` tiene la columna `cod_cliente_padre` (necesaria para contar clientes unicos reales). Si **no la tiene**:

| Componente | Con FactVentas (ideal) | Sin FactVentas (fallback) |
|------------|----------------------|--------------------------|
| Cobertura | `COUNT(DISTINCT cod_cliente_padre)` | `COUNT(DISTINCT subfamilia)` de `td_ventas_bob_historico` |
| Drop Size | `SUM(total_venta) / COUNT(DISTINCT cod_cliente_padre)` | `SUM(fin_01_ingreso) / COUNT(DISTINCT subfamilia)` |
| Hit Rate | Sin cambio (viene de otra tabla) | Sin cambio |

El fallback usa **subfamilias unicas como proxy de clientes**. No es lo mismo (una subfamilia no es un cliente), pero da una aproximacion del volumen de "puntos de contacto" diferentes.

---

## Por que WMA y no Holt-Winters para el Pilar 3?

Podriamos usar Holt-Winters para cada componente tambien, pero no lo hacemos por tres razones:

1. **Series mas cortas**: Los componentes (Cobertura, HR, DS) pueden tener solo 12-18 meses de historia. Holt-Winters necesita 25+ para funcionar bien con estacionalidad. WMA funciona con solo 3 meses.

2. **Transparencia**: El Pilar 3 debe ser facil de explicar a los gerentes. "Es un promedio ponderado de los ultimos 3 meses" es mas intuitivo que "es un suavizado exponencial con tendencia amortiguada y estacionalidad aditiva".

3. **Complementariedad**: El valor del Pilar 3 no es la precision del forecast individual — para eso ya esta el Pilar 2. El valor es el **diagnostico**: ver que componente esta moviendo la venta. Si usaramos el mismo metodo en ambos pilares, agregarian menos informacion al director.

---

## Codigo: donde esta cada cosa

```
pilar3_operativa/
├── __init__.py                    ← Exporta RevenueTreeEngine
└── decomposition_engine.py        ← Toda la logica:
    ├── project_component()        ← Paso 1-3: WMA + estacional para 1 componente
    ├── calculate_projection()     ← Paso 4-5: Multiplica Cob x HR x DS
    ├── run_by_ciudad()            ← Itera todas las ciudades
    ├── run_by_marca()             ← Itera todas las marcas (HR como proxy)
    └── _extract_series()          ← Convierte DataFrame a Serie temporal
```

```
data_fetcher.py                    ← Queries SQL:
    ├── validate_factventas_schema()         ← Q0: Verificar columnas
    ├── get_cobertura_mensual()              ← Q1: Clientes unicos/mes
    │   ├── _cobertura_from_factventas()     ← Ruta ideal
    │   └── _cobertura_from_historico()      ← Fallback
    ├── get_dropsize_mensual()               ← Q2: Venta/cliente/mes
    │   ├── _dropsize_from_factventas()      ← Ruta ideal
    │   └── _dropsize_from_historico()       ← Fallback
    ├── get_hitrate_mensual_historico()       ← Q3: HR por ciudad
    └── get_ventas_mensuales_historicas()     ← Q4: Para Pilar 2
```

---

## Resumen del flujo completo

```
            DWH (PostgreSQL)
                 │
                 ▼
        ┌──────────────────┐
        │  data_fetcher.py │  Ejecuta 5 queries SQL
        │                  │  Cobertura, Drop Size, Hit Rate, Ventas
        └────────┬─────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
┌──────────────┐  ┌──────────────────┐
│   PILAR 2    │  │     PILAR 3      │
│ Holt-Winters │  │  Revenue Tree    │
│              │  │                  │
│ Input:       │  │ Input:           │
│  Ventas 24-  │  │  Cobertura       │
│  36 meses    │  │  Hit Rate        │
│              │  │  Drop Size       │
│ Output:      │  │                  │
│  "Va a       │  │ Output:          │
│   vender X"  │  │  "Porque Cob=A,  │
│              │  │   HR=B, DS=C"    │
└──────┬───────┘  └────────┬─────────┘
       │                   │
       └───────┬───────────┘
               ▼
    ┌────────────────────┐
    │ projection_        │  Merge con PY Gerente
    │ processor.py       │  Calcula spread y diagnostico
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ visualizacion/     │  Genera tablas HTML
    │                    │  Graficos Chart.js
    └────────┬───────────┘
             │
             ▼
         WSR v3.0
    (Seccion 4: Proyeccion Objetiva)
```

---

## Niveles de analisis: a que nivel se presentan los resultados?

### Niveles implementados actualmente

| Nivel | Descripcion | Ejemplo de output | Estado |
|:-----:|-------------|-------------------|:------:|
| **1. Nacional total** | Un solo numero para todo DYM | "DYM: Cob=2,100, HR=71%, DS=BOB 2,850 → PY Operativa BOB 4.3M" | Implementado |
| **2. Por marca** | Una proyeccion por marca (suma de todas las ciudades) | "BRANCA: Cob=850, HR=71%*, DS=BOB 3,000 → PY Operativa BOB 1.8M" | Implementado |
| **3. Por ciudad** | Una proyeccion por ciudad (suma de todas las marcas) | "Santa Cruz: Cob=900, HR=74%, DS=BOB 2,950 → PY Operativa BOB 1.97M" | Implementado |
| **4. Por marca x ciudad** | Una proyeccion por cada combinacion | "BRANCA en Santa Cruz: Cob=350, HR=74%, DS=BOB 3,100" | **No implementado** |

*El asterisco (*) en HR por marca indica que es un proxy (HR nacional), no HR real de esa marca.

```
                     NACIONAL TOTAL                   ← Nivel 1 (implementado)
                    /              \
            POR MARCA          POR CIUDAD             ← Niveles 2 y 3 (implementados)
           /    |    \        /    |    \
        BRANCA HAVANA ...  SCZ   LPZ  CBBA
           \    |    /        \    |    /
            POR MARCA x CIUDAD                        ← Nivel 4 (no implementado)
         BRANCA-SCZ, BRANCA-LPZ,
         HAVANA-SCZ, HAVANA-LPZ, ...
```

### Como funciona cada nivel?

**Nivel 1 — Nacional**: Suma las proyecciones de todas las ciudades (o todas las marcas). Da una vision macro para directorio. Los 3 componentes (Cob, HR, DS) se suman/promedian a nivel pais.

**Nivel 2 — Por marca**: Cobertura y Drop Size se calculan con datos reales de esa marca (suma de todas las ciudades). **El Hit Rate es un proxy** (promedio nacional ponderado), porque `fact_eficiencia_hitrate` no tiene columna de marca. Esto significa que la PY Operativa por marca tiene una imprecision conocida en el componente de HR.

**Nivel 3 — Por ciudad**: Los tres componentes son datos **directos** de esa ciudad. Cobertura = clientes unicos en la ciudad. Hit Rate = HR real de esa ciudad. Drop Size = venta/clientes de esa ciudad. **Este es el nivel mas preciso del Pilar 3**, porque todos los datos son reales sin proxys.

### Nivel 4 — Por marca x ciudad (no implementado, pero posible)

Los datos en el DWH **si vienen a nivel marca x ciudad** para Cobertura y Drop Size (cada query trae `GROUP BY marcadir, ciudad, anio, mes`). Lo que no existe hoy es el codigo que itere sobre cada combinacion.

**Consideraciones especificas del Pilar 3 para este nivel:**

| Componente | Disponibilidad a nivel marca x ciudad | Precision |
|------------|---------------------------------------|-----------|
| **Cobertura** | Si — `COUNT(DISTINCT cod_cliente_padre)` por marca y ciudad | Alta |
| **Hit Rate** | **No** — `fact_eficiencia_hitrate` solo tiene ciudad | **Baja** (proxy de ciudad) |
| **Drop Size** | Si — `SUM(total_venta) / COUNT(DISTINCT cod_cliente_padre)` por marca y ciudad | Alta |

El problema: a nivel marca x ciudad, el Hit Rate seguiria siendo el de **la ciudad** (no de la marca en esa ciudad). BRANCA en Santa Cruz y HAVANA en Santa Cruz tendrian el **mismo HR** (el de Santa Cruz). Esto limita el valor diagnostico porque no se puede saber si una marca convierte mejor que otra en la misma ciudad.

**Recomendacion**: El nivel marca x ciudad se puede implementar para Cobertura y Drop Size (datos reales), pero el HR seria identico entre marcas de la misma ciudad. El diagnostico seria parcial: "BRANCA en SCZ baja por menos clientes" (si), "BRANCA en SCZ baja por peor conversion" (no se puede distinguir). **Primero resolver el HR por marca (pregunta 4) y despues agregar este nivel.**

### Comparacion de precision por nivel

| Nivel | Cobertura | Hit Rate | Drop Size | Precision general |
|-------|:---------:|:--------:|:---------:|:-----------------:|
| Nacional | Real | Real (promedio) | Real | Alta |
| Por ciudad | Real | **Real** | Real | **Muy alta** |
| Por marca | Real | **Proxy** | Real | Media |
| Por marca x ciudad | Real | **Proxy de ciudad** | Real | Media-baja |

**El nivel mas confiable del Pilar 3 es "por ciudad"**, a diferencia del Pilar 2 (Holt-Winters) donde el nivel por marca y por ciudad son igualmente confiables.

---

## Preguntas para el equipo

1. **Los pesos del WMA (50/30/20) son adecuados?** Si el negocio de DYM tiene mucha variabilidad mes a mes, quizas dar aun mas peso al ultimo mes (60/25/15). Si es mas estable, pesos mas parejos (40/35/25).

2. **El factor estacional al 30% es correcto?** Actualmente solo el 30% del efecto estacional se aplica (`0.7 + 0.3 x factor`). Si hay estacionalidad fuerte en bebidas (diciembre alto, febrero bajo), podria subirse a 40-50%.

3. **El cap de 0.5 - 2.0 del factor estacional es razonable?** Es decir, nunca se proyecta menos del 50% ni mas del 200% del WMA base, por efecto estacional. Si hay meses que realmente se cuadruplican (ej: diciembre en licores), quizas el cap de 2.0 es muy restrictivo.

4. **PRIORIDAD: tener HR por marca.** La limitacion mas grande de este pilar es que `fact_eficiencia_hitrate` no tiene columna de marca. Esto hace que la PY Operativa **por marca** sea menos precisa que **por ciudad**. Se necesita que el equipo de sistemas agregue una columna (ej: `id_factura` o `marcadir`) a la tabla de hit rate para vincular visitas con marcas. Hasta que esto suceda, el HR por marca es un promedio nacional que no distingue entre marcas con alta y baja conversion.

5. **Es necesario el nivel marca x ciudad?** Los directores necesitan ver la descomposicion (Cob/HR/DS) de BRANCA especificamente en Santa Cruz, o con saber el total de BRANCA (nacional) y el total de Santa Cruz (todas las marcas) es suficiente? Si la respuesta es "si, necesitamos marca x ciudad", se puede agregar — pero tener en cuenta que el HR seria el mismo para todas las marcas en la misma ciudad (hasta que se resuelva la pregunta 4). Se recomienda primero resolver HR por marca y luego agregar este nivel.
