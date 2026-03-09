# Architecture

**Analysis Date:** 2026-03-09

## Pattern Overview

**Overall:** Pipeline Orchestrator with modular processors (ETL-like: Extract from DWH, Transform/Calculate, Render to HTML)

**Key Characteristics:**
- Single entry point orchestrator (`WSRGeneratorSystem`) that coordinates all modules sequentially
- Each module is a single-responsibility class (database access, data processing, HTML generation, projections)
- Graceful degradation via try/except: projection module, AI narratives, and trend charts are optional -- the report generates without them if they fail
- Monkey-patch extension pattern: `wsr_generator_main.py` injects lambdas into `HTMLGenerator` to extend it with projection-aware table generation without modifying the core class
- All data flows as pandas DataFrames between modules; no intermediate file persistence

## Layers

**Data Access Layer:**
- Purpose: Connect to PostgreSQL DWH and execute SQL queries, return DataFrames
- Location: `core/database.py` (1833 lines), `proyeccion_objetiva/data_fetcher.py` (468 lines)
- Contains: `DatabaseManager` class with ~40 query methods (ventas, presupuesto, SOP, proyecciones, hit rate, stock by marca/ciudad/canal), `ProjectionDataFetcher` for historical series
- Depends on: psycopg2, `.env` credentials, DWH schema `dym_stg`
- Used by: `WSRGeneratorSystem`, `ProjectionProcessor`, `DriversEngine`

**Data Processing Layer:**
- Purpose: Consolidate raw query results into unified DataFrames with calculated KPIs
- Location: `core/data_processor.py` (1096 lines)
- Contains: `DataProcessor` class -- merges multiple query results per dimension (marca, ciudad, canal), calculates percentage changes, sorts by volume, builds hierarchical structures (marca->subfamilia, ciudad->marca)
- Depends on: Data Access Layer outputs (DataFrames)
- Used by: `WSRGeneratorSystem`

**Projection Layer:**
- Purpose: Generate statistical forecasts and operational driver analysis
- Location: `proyeccion_objetiva/` (entire directory)
- Contains: Three "pilares" -- PY Gerente (manager input, from DWH), PY Estadistica (Holt-Winters forecast), PY Operativa (Cobertura x Freq x Drop Size decomposition), plus Nowcast blending engine
- Depends on: Data Access Layer, statsmodels, business_days calculator
- Used by: `WSRGeneratorSystem` (optional module, loaded with try/except)

**AI Narrative Layer:**
- Purpose: Generate executive summaries and diagnostic text using LLM
- Location: `utils/llm_processor.py` (341 lines), `proyeccion_objetiva/narrative_generator.py` (378 lines), `proyeccion_objetiva/pilar3_operativa/drivers_narrative.py` (357 lines)
- Contains: Three separate narrative generators -- comments analysis, projection narrative, drivers diagnostic. All call Claude via OpenRouter REST API.
- Depends on: OpenRouter API (OPENROUTER_API_KEY env var), processed DataFrames for context
- Used by: `WSRGeneratorSystem`

**Presentation Layer:**
- Purpose: Render final HTML report with tables, charts, and styling
- Location: `core/html_generator.py` (1101 lines), `utils/html_tables.py` (2213 lines), `core/trend_chart_generator.py` (749 lines), `proyeccion_objetiva/visualizacion/` (704 lines combined)
- Contains: `HTMLGenerator` (report skeleton, CSS, executive summary), `HTMLTableGenerator` (all performance tables with drilldown), `TrendChartGenerator` (Chart.js interactive charts), `ProjectionHTMLGenerator` + `ProjectionChartGenerator` (projection-specific visuals)
- Depends on: Processed DataFrames, Chart.js (CDN)
- Used by: `WSRGeneratorSystem`

## Data Flow

**Main Report Generation Pipeline:**

1. `WSRGeneratorSystem.__init__()` -- Read `.env`, initialize all component classes with current date
2. `DatabaseManager.connect()` -- Establish PostgreSQL connection via psycopg2
3. `_fetch_all_data()` -- Execute ~30 SQL queries organized by dimension (marca, marca_subfamilia, ciudad, ciudad_marca, canal, comentarios). Returns nested dict of DataFrames
4. `DataProcessor.consolidate_marca_subfamilia_data()` -- Merge query results per marca with outer joins, calculate KPIs (% change YoY, % vs budget, price evolution), build hierarchical dict `{'marca_totales': df, 'marca_subfamilia': df}`
5. Same for ciudad and canal dimensions
6. `DataProcessor.calculate_executive_summary()` -- Compute national-level KPIs from consolidated DataFrames
7. `ProjectionProcessor.generate_projections()` -- Run Holt-Winters on 36-month historical series (Pilar 2), run Drivers decomposition on fact_ventas_detallado (Pilar 3)
8. Merge PY Estadistica columns back into main DataFrames via `_merge_py_est()` helper (case-insensitive join)
9. `NowcastEngine.calculate()` -- Blend HW forecast with Run Rate using Bayesian credibility weight (business days elapsed / total)
10. AI narrative generation -- Three separate LLM calls for projections, drivers by marca, drivers by ciudad
11. `_generate_html_report()` -- Compose full HTML: CSS + header + executive summary + marca tables + ciudad tables + canal tables + trend chart + projection section + footer
12. `_save_report()` -- Write to `output/WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html`
13. `webbrowser.open()` -- Auto-open in default browser

**State Management:**
- No persistent state between runs. Each execution is a fresh pipeline from DB to HTML.
- All intermediate data lives in pandas DataFrames passed between methods.
- Configuration state (date, year, month) is set once in `__init__` and propagated to all components.

## Key Abstractions

**Hierarchical Data Structures:**
- Purpose: Represent parent-child relationships for drilldown tables (marca->subfamilia, ciudad->marca)
- Examples: `estructura_marca` dict in `wsr_generator_main.py` (line ~107), `estructura_ciudad` dict (line ~113)
- Pattern: Dict with keys `marca_totales` (parent DataFrame) and `marca_subfamilia` (child DataFrame), linked by shared column `marcadir`

**Dual Currency (BOB/C9L):**
- Purpose: Report in both Bolivianos (BOB) and cases of 9 liters (C9L, industry unit)
- Examples: Every table is generated twice -- `generate_marca_performance_bob()` and `generate_marca_performance_c9l()` in `utils/html_tables.py`
- Pattern: Column naming convention `{metric}_{year}_{currency}` (e.g., `avance_2026_bob`, `vendido_2025_c9l`)

**Calendar Week Ranges:**
- Purpose: Split monthly data into up to 5 calendar weeks (Mon-Sun)
- Examples: `get_calendar_week_ranges()` duplicated in `core/database.py` (line 49), `core/html_generator.py` (line 42), `core/trend_chart_generator.py` (line 44)
- Pattern: Returns list of (day_start, day_end) tuples. Used for weekly breakdown tables and charts.

**Projection Triple Pilar:**
- Purpose: Compare three independent projections to triangulate month-end estimate
- Examples: `proyeccion_objetiva/projection_processor.py` orchestrates all three
- Pattern: PY Gerente (human judgment) vs PY Estadistica (Holt-Winters model) vs PY Operativa (Cob x Freq x DS). Spread = divergence between pillars.

## Entry Points

**Primary: `wsr_generator_main.py`**
- Location: `wsr_generator_main.py`
- Triggers: Manual execution via `python wsr_generator_main.py` (requires VPN to DWH)
- Responsibilities: Orchestrates entire report generation pipeline. Contains `WSRGeneratorSystem` class and `main()` function.

**Secondary: `generate_report.py`**
- Location: `generate_report.py`
- Triggers: Alternative entry point with UTF-8 encoding fix for Windows console
- Responsibilities: Imports and delegates to `WSRGeneratorSystem` from `wsr_generator_main.py`. Strips emojis from log output to avoid Windows cp1252 encoding errors.

**Setup: `setup.py`**
- Location: `setup.py`
- Triggers: One-time project setup
- Responsibilities: Creates directory structure, checks dependencies, generates `.env.example`

## Error Handling

**Strategy:** Defensive try/except with graceful degradation. Optional modules (projections, AI narratives, trend charts) fail silently with warnings, allowing the core report to generate.

**Patterns:**
- Module-level import guards: `try: import X; AVAILABLE = True; except ImportError: AVAILABLE = False` (see `wsr_generator_main.py` lines 28-37, `statistical_engine.py` lines 31-39)
- Feature-level try/except: Each optional section (projections, narratives, drivers, nowcast) is wrapped in its own try/except block in `generate()` method (lines 147-356)
- LLM fallback chain: Primary model (claude-opus-4.6) -> fallback model (claude-sonnet-4) -> basic text processing without AI
- Database connection check: `if not self.db_manager.connect(): return False` early exit

## Cross-Cutting Concerns

**Logging:**
- Python standard `logging` module with both file handler (`wsr_generator.log`) and console handler
- Log level configurable via `LOG_LEVEL` env var (default: INFO)
- Uses emoji prefixes in log messages for visual scanning
- Every module creates its own logger: `logger = logging.getLogger(__name__)`

**Validation:**
- Schema validation for `FactVentas` table in `data_fetcher.py` (checks expected columns exist)
- Sanity bounds on projections: forecast must be between 50% and 200% of same-month-previous-year (`config.py` SANITY_MIN/MAX_FACTOR)
- Zero threshold: series with >70% zeros are rejected by HW engine
- `fillna(0)` applied universally after DataFrame merges in `data_processor.py`

**Authentication:**
- Database credentials loaded from `.env` via `python-dotenv`
- OpenRouter API key from `OPENROUTER_API_KEY` env var
- No auth middleware -- this is a batch script, not a web service

**Business Days:**
- Bolivia-specific calendar in `utils/business_days.py` with fixed holidays + mobile holidays (Carnaval, Viernes Santo, Corpus Christi) defined per year
- Used for: Nowcast credibility weight, month progress percentage, weekly breakdown alignment
- Mobile holidays must be manually added for future years (currently defined through 2026)

---

*Architecture analysis: 2026-03-09*
