# CLAUDE.md -- Pilar 3: Drivers Operativos

## Proposito

Descompone la venta en sus 3 drivers multiplicativos:
**Venta = Cobertura x Hit Rate x Drop Size**

Esto permite diagnosticar POR QUE sube o baja una marca, no solo CUANTO.

## Arquitectura

```
drivers_engine.py        -- Motor: queries a fact_ventas_detallado, calculo de tendencias
drivers_narrative.py     -- Narrativa IA: prompt a Claude (OpenRouter) para diagnostico por marca
DRIVERS.md               -- Documentacion completa del pilar
```

## Fuente de datos

- **Tabla**: `fact_ventas_detallado` (schema `auto` / `dym_stg`)
- **Granularidad**: item-level con `cod_cliente`, `cuf_factura`, `marca`, `ciudad`, `fecha`
- **IMPORTANTE**: La columna `marca` en esta tabla es mas granular que `marcadir` en `td_ventas_bob_historico`. Contiene marcas micro (Septima, Absolut, Finlandia, Torres, etc.) que NO aparecen en las tablas de performance del WSR.
- **Filtro aplicado**: Se filtran contra la lista de `marcadir` del WSR principal (`estructura_marca['marca_totales']`) para excluir micro-marcas. Ademas se excluyen "NINGUNA", "SIN MARCA ASIGNADA" y ciudad "TURISMO".

## Definiciones de drivers

| Driver | Formula | Que mide |
|--------|---------|----------|
| Cobertura (cli) | `COUNT(DISTINCT cod_cliente)` | Clientes unicos que compraron -- ALCANCE |
| Hit Rate (ped/cli) | `COUNT(DISTINCT cuf_factura) / Cobertura` | Pedidos por cliente -- FRECUENCIA |
| Drop Size (BOB/ped) | `SUM(ingreso_neto_bob) / Pedidos` | Venta promedio por pedido -- TICKET |
| Check | `Cob x HR x DS = Venta total` | Identidad multiplicativa exacta |

## Metodologia: Same-to-Date (STD) con fallback YoY

### Modo STD (preferido -- cuando fact_ventas_detallado tiene datos del mes actual)
- **Valores**: acumulado del mes actual al dia N (ej: Marzo 1-8, 2026)
- **Comparacion**: mismos dias del año anterior (ej: Marzo 1-8, 2025)
- **Ventaja**: comparacion justa (mismos dias), datos actuales, accionable
- **Columnas extra**: `ref_dia` (dia de corte), `is_std=True`

### Modo Fallback YoY (cuando no hay datos del mes actual)
- **Valores**: ultimo mes completo disponible en fact_ventas_detallado
- **Comparacion**: mismo mes del año anterior (YoY)
- **Columnas extra**: `ref_dia=None`, `is_std=False`

### Comun a ambos modos
- **Delta YoY** = `(valor_periodo_actual / valor_mismo_periodo_AA) - 1`
- Umbral: >+2% = mejorando, <-2% = deteriorando, entre = estable
- Si no hay dato YoY (marca nueva), se muestra "-" y el insight dice "sin dato YoY"

## Narrativa IA

- **Modelo**: `anthropic/claude-opus-4.6` via OpenRouter (fallback: `claude-sonnet-4`)
- **Prompt**: Pide analisis para CADA marca (no solo top 3-4)
- **Formato obligatorio**: `**MARCA -- titular.** Analisis de 2-3 oraciones.`
- **max_tokens**: 3000 (necesario para ~15 marcas x 2-3 oraciones cada una)
- **Parsing**: `_parse_narrative_per_marca()` en `html_tables.py` extrae per-marca del HTML
- **Matching**: Fuzzy cascade en `_generate_drivers_table()`: (1) exact UPPER match, (2) primeros 5 chars startswith, (3) substring contains. Ejemplo: LLM escribe "Beefeater" → UPPER="BEEFEATER" → startswith("BEEFE") matchea "BEEFEATEAR"
- **Fallback**: Si el LLM no menciona una marca, `_generate_driver_insight()` genera insight programatico basado en datos

## Tabla HTML (en html_tables.py)

- Columnas: Marca | Cob (cli) | Δ YoY | Freq. | Δ YoY | DS (BOB) | Δ YoY | Resumen Ejecutivo
- Leyenda debajo del titulo con definicion de cada columna y formulas
- `table-layout: fixed` con `<colgroup>` para anchos controlados
- Celda de Resumen: `white-space: normal; word-wrap: break-word` para parrafos
- Font: 11px datos, 10.5px resumen

## Logica de diagnostico automatico (fallback)

| Cobertura | Hit Rate | Drop Size | Diagnostico |
|-----------|----------|-----------|-------------|
| baja | estable | estable | Problema de ruta/cobertura |
| estable | baja | estable | Problema de conversion/frecuencia |
| estable | estable | baja | Problema de mix/precio |
| sube | baja | * | Expansion sin retencion |
| baja | baja | baja | Problema sistemico |
| sube | sube | sube | Dinamica positiva |

## Niveles de calculo

1. **Por marca** (nacional) -- acompana tabla Performance por Marca
2. **Por marca + submarca** (drilldown) -- disponible pero no renderizado aun
3. **Por ciudad** -- acompana tabla Performance por Ciudad
4. **Por ciudad + marca** (drilldown) -- disponible pero no renderizado aun

## Flujo de datos completo

```
fact_ventas_detallado (DWH)
  |
  v
DriversEngine.calculate_all() -- 4 queries (marca, marca+sub, ciudad, ciudad+marca)
  |
  v
DriversNarrativeGenerator.generate_diagnostic() -- LLM genera analisis por marca
  |
  v
wsr_generator_main.py -- filtra micro-marcas contra marcadir del WSR
  |
  v
html_tables.generate_drivers_section() -- parsea narrativa, genera tabla con resumen inline
  |
  v
WSR HTML -- tabla Drivers con Resumen Ejecutivo por marca
```
