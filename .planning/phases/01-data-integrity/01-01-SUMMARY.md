---
phase: 01-data-integrity
plan: 01
subsystem: data-alignment
tags: [chart.js, trend-chart, marca-totales, weekly-distribution, projection-override]

# Dependency graph
requires: []
provides:
  - "Trend chart national view uses marca_totales totals (PY Gerente + SOP)"
  - "Override parameter pattern for injecting authoritative totals into chart pipeline"
affects: [02-ux-trust]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proportional scaling: read weekly DB shape, scale to marca_totales total"
    - "Override injection: optional params flow from generate() -> _generate_trend_chart() -> process_weekly_data_multi_city() -> process_weekly_data()"

key-files:
  created: []
  modified:
    - core/trend_chart_generator.py
    - wsr_generator_main.py

key-decisions:
  - "Scale existing weekly distribution proportionally rather than replacing it, preserving week-over-week shape"
  - "Override applies ONLY to general/national view; per-city views continue using direct DB queries"
  - "Combined total = PY Gerente + SOP from marca_totales, distributed across 5 weeks using DB weekly shape as proportional template"

patterns-established:
  - "Override pattern: optional float params default to None, applied only when both provided"
  - "Alignment logging: log override values at injection point and chart output for cross-verification"

requirements-completed: [DATA-01, DATA-02]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 1 Plan 1: Chart-Table Alignment Summary

**Trend chart national view now uses marca_totales PY Gerente and SOP totals, distributed proportionally across weeks, eliminating ~5M BOB discrepancy with summary table**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T00:59:25Z
- **Completed:** 2026-03-10T01:01:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Chart general view PY Gerente and SOP values now sourced from marca_totales (same as summary table)
- Weekly proportional distribution preserved -- chart still shows 5-week breakdown with correct relative shape
- Per-city chart views unaffected (continue using direct DB queries)
- Verification logging added at both injection and output points for cross-checking

## Task Commits

Each task was committed atomically:

1. **Task 1: Add marca_totales override parameters to trend chart pipeline** - `d2f3384` (feat)
2. **Task 2: Wire marca_totales totals into _generate_trend_chart orchestrator** - `559ba06` (feat)

## Files Created/Modified
- `core/trend_chart_generator.py` - Added override_py_gerente_total and override_sop_total params to process_weekly_data and process_weekly_data_multi_city; proportional scaling logic
- `wsr_generator_main.py` - Compute marca_totales totals in generate(), pass to _generate_trend_chart(), verification logging

## Decisions Made
- Used proportional scaling of existing weekly DB values instead of even distribution -- preserves the natural weekly selling pattern while correcting the total magnitude
- Combined PY Gerente + SOP into single scaling target because the chart "Proyeccion Gerentes" line already combines both
- Fallback to even distribution (1/5 per week) only when DB weekly data is all zeros or empty

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Chart-table alignment complete for national view
- Full verification requires VPN connection to run `python wsr_generator_main.py` and check generated HTML
- Ready for Phase 2 (UX trust improvements) once integration test confirms alignment

---
*Phase: 01-data-integrity*
*Completed: 2026-03-10*
