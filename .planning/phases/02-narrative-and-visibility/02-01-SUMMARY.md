---
phase: 02-narrative-and-visibility
plan: 01
subsystem: ui, llm
tags: [html-rendering, llm-prompts, config-flags, narrative]

# Dependency graph
requires:
  - phase: 01-data-integrity
    provides: "marca_totales as authoritative data source, trend chart pipeline"
provides:
  - "Markdown bold to HTML strong conversion in CommentFormatter"
  - "Terminology rules (productos, referencias/presentaciones) in both LLM prompts"
  - "SHOW_ACCURACY_SECTION config flag to hide/show accuracy section"
affects: [narrative-quality, report-rendering]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config flag pattern for section visibility (early return in generator)"
    - "Static helper method for markdown-to-HTML conversion"

key-files:
  created: []
  modified:
    - utils/llm_processor.py
    - proyeccion_objetiva/narrative_generator.py
    - proyeccion_objetiva/config.py
    - core/trend_chart_generator.py

key-decisions:
  - "Used static helper method _convert_bold for markdown conversion rather than inline regex"
  - "Used try/except ImportError for config flag to gracefully handle missing config module"
  - "Set SHOW_ACCURACY_SECTION=False by default, preserving all existing code with early return"

patterns-established:
  - "Config flag pattern: add constant in config.py, import with try/except in consumer, early return when disabled"

requirements-completed: [NARR-01, NARR-02, VIS-01]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 02 Plan 01: Narrative and Visibility Summary

**Markdown bold rendering fix, commercial terminology rules in LLM prompts, and accuracy section hidden via config flag**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T12:54:53Z
- **Completed:** 2026-03-10T12:56:38Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Regional comments now render **bold** text as HTML `<strong>` tags instead of raw asterisks
- Both LLM prompts (comments and projection narrative) enforce commercial terminology: "productos" not "SKUs", "referencias/presentaciones" not "lenguas"
- Accuracy section hidden from WSR output via `SHOW_ACCURACY_SECTION = False` config flag, fully reversible

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix markdown bold rendering and add terminology rules** - `e9efa99` (feat)
2. **Task 2: Add config flag to hide accuracy section** - `a81b273` (feat)

## Files Created/Modified
- `utils/llm_processor.py` - Added `_convert_bold` static method and terminology rule to regional comments prompt
- `proyeccion_objetiva/narrative_generator.py` - Added terminology rule to projection narrative prompt
- `proyeccion_objetiva/config.py` - Added `SHOW_ACCURACY_SECTION = False` config constant
- `core/trend_chart_generator.py` - Added early return in `generate_chart_html` when config flag is False

## Decisions Made
- Used a static helper method `_convert_bold` instead of inline replacement for cleaner separation of concerns
- Config flag uses try/except ImportError pattern so trend_chart_generator works even if config module is unavailable
- All existing accuracy section code preserved (zero lines deleted) -- setting flag to True restores it immediately

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Narrative rendering is clean for browser display
- LLM prompts will produce commercial-friendly terminology on next generation
- Accuracy section can be re-enabled by changing one config value
- Full integration test requires VPN connection to DWH (`python wsr_generator_main.py`)

---
*Phase: 02-narrative-and-visibility*
*Completed: 2026-03-10*
