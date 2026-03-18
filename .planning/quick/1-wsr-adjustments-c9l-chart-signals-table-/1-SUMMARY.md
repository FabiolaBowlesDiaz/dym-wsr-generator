---
phase: quick
plan: 1
subsystem: wsr-visual-enhancements
tags: [c9l, chart, signals-table, hit-rate, chartjs]
dependency_graph:
  requires: []
  provides: [c9l-chart, expanded-signals-table, hitrate-line-chart]
  affects: [wsr-html-output]
tech_stack:
  added: []
  patterns: [chart.js-line-chart, iife-pattern, 5-column-table]
key_files:
  created: []
  modified:
    - proyeccion_objetiva/data_fetcher.py
    - proyeccion_objetiva/visualizacion/projection_chart_generator.py
    - proyeccion_objetiva/visualizacion/projection_html_generator.py
    - wsr_generator_main.py
    - core/html_generator.py
decisions:
  - C9L SOP and PY Gerente shown as single current-month points (no historical data in DB)
  - C9L chart uses same colors and structure as BOB chart for visual consistency
metrics:
  duration: 4min
  completed: 2026-03-18
---

# Quick Task 1: WSR C9L Chart, Signals Table, Hit Rate Line Chart Summary

C9L monthly evolution chart with 4 series, 5-column signals table (BOB + C9L), and Chart.js line chart replacing CSS horizontal bars for Hit Rate vs Eficiencia.

## Task Results

### Task 1: C9L historical queries + chart + expanded signals table

| Aspect | Detail |
|--------|--------|
| Commit | `a0254eb` |
| Files | data_fetcher.py, projection_chart_generator.py, projection_html_generator.py, wsr_generator_main.py |

**Changes:**
- `data_fetcher.py`: Added `SUM(CAST(c9l AS NUMERIC)) AS venta_c9l` to `get_ventas_nacionales_historicas()` query. Single query now returns both BOB and C9L.
- `projection_chart_generator.py`: New `generate_historical_chart_c9l()` method. Venta Real C9L uses full 12-month history; SOP, PY Gerente, PY Sistema shown as single current-month points (no historical C9L data in DB for those series). Unique canvas ID `resumenEjecutivoChartC9L`. Tooltip shows "C9L" prefix.
- `projection_html_generator.py`: `generate_full_section()` now accepts C9L parameters and renders C9L chart below BOB chart. `_generate_resumen_table()` expanded to 5 columns: SENAL, MONTO (BOB), vs SOP, MONTO (C9L), vs SOP (C9L). Table max-width widened to 900px.
- `wsr_generator_main.py`: Computes C9L totals from `marca_totales` (avance_c9l, sop_c9l, py_c9l, py_sistema_c9l), generates C9L chart, and passes all values to `generate_full_section()`.

### Task 2: Hit Rate vs Eficiencia line chart

| Aspect | Detail |
|--------|--------|
| Commit | `2c59ce7` |
| Files | core/html_generator.py |

**Changes:**
- Replaced CSS horizontal bar visualization with Chart.js line chart
- Two series: Hit Rate (blue #3b82f6) and Eficiencia (green #10b981) with data points
- X-axis: month labels, Y-axis: percentage with % suffix
- Tooltips show formatted percentage values
- IIFE pattern matching existing Chart.js charts in the project
- Added `import json` to module imports

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **C9L SOP/PY Gerente as single points**: Historical C9L data for SOP and PY Gerente is not available in the DB (`factpresupuesto_mensual` and `fact_proyecciones` store BOB only). These are shown as single current-month points using values from `marca_totales`, while Venta Real C9L has full 12-month history from `td_ventas_bob_historico.c9l`.

2. **C9L chart visual consistency**: Same colors, same chart structure as BOB chart. SOP and PY Gerente shown as marker-only (no lines) since they are single points, unlike the BOB chart where they have historical lines.

## Verification

- All 3 module imports succeed without errors
- C9L table columns (MONTO C9L, vs SOP C9L) verified present in generated HTML
- Hit Rate Chart.js line chart verified with canvas ID, Chart instantiation, and both series

## Self-Check: PASSED

All 5 modified files exist. Both commits (a0254eb, 2c59ce7) verified in git log.
