# Phase 1: Data Integrity - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Align PY Gerente and SOP values between the Section 4 chart and the Section 4 summary table. Both must use marca_totales pipeline as the single source of truth. No visual changes, no new features — only correct the data source so numbers match.

</domain>

<decisions>
## Implementation Decisions

### Data source alignment
- Chart Section 4 currently queries `fact_proyecciones` (via `get_proyecciones_semanales_nacional()`) and `factpresupuesto_mensual` (via `get_sop_oruro_trinidad()`) directly — this produces different totals than marca_totales
- Fix: Both chart and summary table must derive PY Gerente and SOP from the `marca_totales` pipeline, which is already the authoritative source for Sections 1-3
- The monthly totals must match exactly; weekly distribution within the chart is Claude's discretion

### Scope of fix
- Only the current month's values need to match (the chart shows weekly breakdown of the current month)
- No visual or layout changes to Section 4 — only the underlying data source changes
- The chart should continue to show the same 4 signals: Venta Real, SOP, PY Gerente, PY Sistema

### Claude's Discretion
- How to distribute the marca_totales monthly total across weeks for the chart (weekly granularity approach)
- Whether to refactor the query methods or inject corrected values at the orchestrator level
- Logging or diagnostic output for verifying alignment
- Any intermediate data structures needed for the fix

</decisions>

<specifics>
## Specific Ideas

No specific requirements — the user confirmed this is purely a numbers-matching fix. The chart visual appearance should remain unchanged.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `marca_totales` pipeline in `core/data_processor.py`: Already consolidated and validated, used by Sections 1-3
- `TrendChartGenerator` in `core/trend_chart_generator.py`: Processes weekly data and generates Chart.js HTML
- `process_weekly_data()` (line 103): Takes ventas_df and proyecciones_df, outputs chart data dict
- `_get_proyeccion_semana()` (line 179): Extracts weekly projection from DataFrame — can be adapted for new source

### Established Patterns
- Monkey-patch pattern in `wsr_generator_main.py` (line 598+): Injects data into html_generator via lambda assignments
- `_merge_py_est` helper (line 163): Case-insensitive merge between projection data and WSR DataFrames (UPPER normalization)
- Weekly SOP distribution patterns for Oruro/Trinidad hardcoded in 3 places (database.py lines 377-412, 867-890, 1042-1078)

### Integration Points
- `_generate_trend_chart()` in `wsr_generator_main.py` (line 818): Orchestrates chart data fetching — this is where the data source switch happens
- `_fetch_all_data()` (line 388): Already fetches marca_totales for other sections — the corrected values are available here
- Chart data flows: `wsr_generator_main._generate_trend_chart()` → `trend_chart_generator.process_weekly_data_multi_city()` → `generate_chart_html()`

### Root Cause
- Chart queries `fact_proyecciones` and `factpresupuesto_mensual` directly at national level
- Summary table sums from `marca_totales` (consolidated pipeline by brand)
- Difference: ~5M BOB in PY Gerente, ~1.4M in SOP

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-integrity*
*Context gathered: 2026-03-09*
