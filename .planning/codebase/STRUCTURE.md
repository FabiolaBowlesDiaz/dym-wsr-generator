# Codebase Structure

**Analysis Date:** 2026-03-09

## Directory Layout

```
project-root/
├── core/                          # Core report modules (data, HTML, charts)
│   ├── __init__.py
│   ├── database.py                # PostgreSQL DWH queries (1833 lines)
│   ├── data_processor.py          # Data consolidation + KPI calculation (1096 lines)
│   ├── html_generator.py          # HTML report skeleton + CSS + formatting (1101 lines)
│   └── trend_chart_generator.py   # Chart.js trend charts (749 lines)
├── utils/                         # Shared utilities
│   ├── __init__.py
│   ├── html_tables.py             # Performance tables with drilldown (2213 lines, largest file)
│   ├── llm_processor.py           # Manager comment analysis via OpenRouter (341 lines)
│   └── business_days.py           # Bolivia business day calculator (209 lines)
├── proyeccion_objetiva/           # Projection module (optional, loaded via try/except)
│   ├── __init__.py                # Exports ProjectionProcessor
│   ├── config.py                  # Constants: thresholds, colors, events, table names (81 lines)
│   ├── data_fetcher.py            # DWH queries for projection data (468 lines)
│   ├── projection_processor.py    # Orchestrator: runs engines, merges results (295 lines)
│   ├── narrative_generator.py     # AI narrative for PY Sistema (378 lines)
│   ├── nowcast_engine.py          # Bayesian blend: HW + Run Rate (108 lines)
│   ├── pilar2_estadistica/        # Statistical forecasting
│   │   ├── __init__.py
│   │   ├── statistical_engine.py  # Holt-Winters Triple/Double Exp Smoothing (593 lines)
│   │   └── event_calendar.py      # Carnaval/Easter adjustment factors (218 lines)
│   ├── pilar3_operativa/          # Operational drivers
│   │   ├── __init__.py
│   │   ├── drivers_engine.py      # Cob x Freq x DS from fact_ventas_detallado (428 lines)
│   │   ├── drivers_narrative.py   # AI diagnostic per marca/ciudad/canal (357 lines)
│   │   └── DRIVERS.md             # Driver methodology documentation
│   ├── visualizacion/             # Projection-specific HTML/charts
│   │   ├── __init__.py
│   │   ├── projection_html_generator.py  # Projection section HTML (427 lines)
│   │   └── projection_chart_generator.py # Chart.js comparison chart (277 lines)
│   ├── tests/                     # Projection module tests
│   │   ├── __init__.py
│   │   ├── test_projection_processor.py  # 7 unit tests (258 lines)
│   │   ├── test_statistical_engine.py
│   │   └── test_validate_factventas.py
│   └── docs/                      # Projection documentation
├── output/                        # Generated HTML reports (timestamped)
├── data/                          # Empty -- data comes from DWH at runtime
├── templates/                     # Empty -- HTML is generated programmatically
├── logs/                          # Log files
├── tests/                         # Empty test directory (root level)
├── manuales/                      # User/admin manuals
│   ├── 01_manual_de_uso/
│   ├── 02_manual_de_instalacion/
│   ├── 03_manual_de_mantenimiento/
│   └── convertir_md_a_html.py     # Manual converter script
├── venv/                          # Python virtual environment
├── wsr_generator_main.py          # PRIMARY ENTRY POINT - orchestrator (879 lines)
├── generate_report.py             # Secondary entry point - Windows UTF-8 fix (71 lines)
├── setup.py                       # Project setup script (227 lines)
├── requirements.txt               # Python dependencies
├── CLAUDE.md                      # AI assistant context (comprehensive project docs)
├── README.md                      # Project readme
├── .env                           # Credentials (not committed)
├── wsr_generator.log              # Runtime log file
├── debug_*.py                     # Debug scripts for specific brands (5 files)
├── test_*.py                      # Ad-hoc test scripts at root level (11 files)
└── verify_calculation.py          # Calculation verification script
```

## Directory Purposes

**`core/`:**
- Purpose: Core report generation modules that exist since v1
- Contains: Database access, data processing, HTML generation, trend charts
- Key files: `database.py` (all SQL queries), `data_processor.py` (all KPI logic), `html_generator.py` (report structure), `html_tables.py` was moved to `utils/` but is conceptually core

**`utils/`:**
- Purpose: Shared utilities used across modules
- Contains: HTML table generation (largest file at 2213 lines), LLM comment processing, business day calculator
- Key files: `html_tables.py` is the workhorse -- generates all performance tables (marca/ciudad/canal BOB/C9L, drilldowns, drivers sections)

**`proyeccion_objetiva/`:**
- Purpose: Self-contained projection module added later. Loaded optionally via try/except
- Contains: Three sub-modules for statistical forecasting, operational drivers, and visualization
- Key files: `projection_processor.py` orchestrates the module, `statistical_engine.py` implements Holt-Winters, `drivers_engine.py` calculates Cob x Freq x DS

**`output/`:**
- Purpose: Generated HTML report files
- Contains: Timestamped HTML files named `WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html`
- Generated: Yes
- Committed: No (in .gitignore)

**`manuales/`:**
- Purpose: End-user and admin documentation
- Contains: Three manual categories (uso, instalacion, mantenimiento)

## Key File Locations

**Entry Points:**
- `wsr_generator_main.py`: Primary entry -- run with `python wsr_generator_main.py`
- `generate_report.py`: Windows-friendly entry with UTF-8 encoding fix

**Configuration:**
- `.env`: Database credentials, OpenRouter API key, log level (NEVER committed)
- `proyeccion_objetiva/config.py`: All projection constants (thresholds, colors, exclusions, event impacts)
- `utils/business_days.py`: Bolivia holiday calendar (must update mobile holidays for new years)

**Core Logic:**
- `core/database.py`: All ~40 SQL query methods against the DWH
- `core/data_processor.py`: Data consolidation (merges), KPI calculation, hierarchical structures
- `utils/html_tables.py`: All HTML table rendering with conditional formatting, drilldowns, drivers
- `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py`: Holt-Winters implementation
- `proyeccion_objetiva/pilar3_operativa/drivers_engine.py`: Revenue tree decomposition

**Testing:**
- `proyeccion_objetiva/tests/test_projection_processor.py`: 7 unit tests for projections
- `test_*.py` (root level): 11 ad-hoc test scripts (not pytest-organized)

**AI/LLM Integration:**
- `utils/llm_processor.py`: Comment analysis (CommentProcessor class)
- `proyeccion_objetiva/narrative_generator.py`: PY Sistema narrative (ProjectionNarrativeGenerator)
- `proyeccion_objetiva/pilar3_operativa/drivers_narrative.py`: Drivers diagnostic (DriversNarrativeGenerator)

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules: `data_processor.py`, `html_generator.py`, `drivers_engine.py`
- `test_*.py` prefix for test files (both root and `proyeccion_objetiva/tests/`)
- `debug_*.py` prefix for debug/investigation scripts at root level

**Directories:**
- `snake_case` for all directories: `proyeccion_objetiva/`, `pilar2_estadistica/`, `pilar3_operativa/`
- Numbered prefix for manual subdirectories: `01_manual_de_uso/`, `02_manual_de_instalacion/`

**Classes:**
- `PascalCase`: `WSRGeneratorSystem`, `DatabaseManager`, `DataProcessor`, `HTMLGenerator`, `HTMLTableGenerator`, `StatisticalEngine`, `DriversEngine`, `NowcastEngine`, `ProjectionProcessor`

**Methods/Functions:**
- `snake_case`: `generate_projections()`, `calculate_executive_summary()`, `get_ventas_historicas_marca()`
- Private methods prefixed with `_`: `_fetch_all_data()`, `_merge_py_est()`, `_build_query()`

**DataFrame Columns:**
- Pattern: `{metric}_{year}_{currency}` -- e.g., `avance_2026_bob`, `vendido_2025_c9l`, `py_2026_bob`
- Projection columns: `py_estadistica_bob`, `py_sistema_bob`, `run_rate_bob`, `spread_sistema`
- Driver columns: `cobertura`, `hit_rate`, `drop_size`, `venta_total`, `delta_yoy_cobertura`

**Output Files:**
- Pattern: `WSR_DYM_{YEAR}_{MONTH}_{YYYYMMDD_HHMMSS}.html`

## Where to Add New Code

**New Data Dimension (e.g., by vendedor):**
1. Add SQL query methods in `core/database.py` (follow pattern of `get_ventas_historicas_marca()`)
2. Add consolidation method in `core/data_processor.py` (follow `consolidate_marca_data()`)
3. Add table generation methods in `utils/html_tables.py` (follow `generate_marca_performance_bob()`)
4. Wire into `wsr_generator_main.py` `_fetch_all_data()` and `_generate_html_report()`

**New Projection Engine (e.g., ML model):**
1. Create new sub-package under `proyeccion_objetiva/pilar4_ml/`
2. Add `__init__.py` and engine class following `statistical_engine.py` pattern
3. Wire into `proyeccion_objetiva/projection_processor.py` `generate_projections()`
4. Add merge logic in `wsr_generator_main.py` (follow `_merge_py_est()` pattern)

**New AI Narrative Section:**
1. Create narrative generator class following `proyeccion_objetiva/narrative_generator.py` pattern
2. Use OpenRouter API with `OPENROUTER_API_KEY` env var
3. Return HTML string that gets injected into table generation via `utils/html_tables.py`
4. Wire into `wsr_generator_main.py` with try/except for graceful degradation

**New Chart/Visualization:**
1. Add chart generator in `core/` (for core charts) or `proyeccion_objetiva/visualizacion/` (for projection charts)
2. Follow `TrendChartGenerator` pattern: process data, emit Chart.js HTML string
3. Inject HTML into report via `html_generator.py` `generate_complete_report()`

**New SQL Query:**
- Add method to `core/database.py` `DatabaseManager` class
- Follow naming convention: `get_{what}_{dimension}()` (e.g., `get_ventas_historicas_marca()`)
- Use `self.schema` for table references
- Return `pd.DataFrame`

**New Test:**
- For projection module: add to `proyeccion_objetiva/tests/`
- For core modules: add to root level as `test_*.py` (current pattern) or ideally organize into `tests/` directory

## Special Directories

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`output/`:**
- Purpose: Generated WSR HTML reports
- Generated: Yes (by each run of `wsr_generator_main.py`)
- Committed: No (in .gitignore)
- Note: Accumulates files -- no automatic cleanup. Currently has 50+ reports.

**`data/`:**
- Purpose: Placeholder for data files (currently empty)
- Generated: No
- Committed: No (CSVs excluded in .gitignore)

**`templates/`:**
- Purpose: Placeholder for HTML templates (currently empty -- all HTML is generated programmatically in Python)
- Generated: No
- Committed: Yes (empty)

**Root-level `test_*.py` and `debug_*.py`:**
- Purpose: Ad-hoc test and debug scripts (11 test + 5 debug files)
- These are NOT organized into the `tests/` directory
- Some are brand-specific debugging: `debug_branca_py2025.py`, `debug_havana_py2025.py`
- Should ideally be moved to `tests/` directory

**Root-level `tmpclaude-*-cwd/`:**
- Purpose: Temporary directories created by Claude Code sessions
- Generated: Yes
- Committed: Should not be

---

*Structure analysis: 2026-03-09*
