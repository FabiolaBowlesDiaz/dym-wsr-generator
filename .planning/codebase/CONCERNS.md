# Codebase Concerns

**Analysis Date:** 2026-03-09

## Tech Debt

**SQL String Interpolation (No Parameterized Queries):**
- Issue: Every SQL query in `core/database.py` (1833 lines, 40+ methods) and `proyeccion_objetiva/data_fetcher.py` (468 lines) uses Python f-strings to inject parameters directly into SQL. Example: `WHERE anio = {year} AND mes = {month} AND dia <= {day}`. While parameters come from internal code (not user input), this prevents query plan caching in PostgreSQL and is fragile against future changes.
- Files: `core/database.py`, `proyeccion_objetiva/data_fetcher.py`, `proyeccion_objetiva/pilar3_operativa/drivers_engine.py`
- Impact: No SQL injection risk currently (all params are integers from `datetime.now()`), but PostgreSQL cannot cache query plans, leading to repeated parsing of identical query structures. Also prevents any future use of user-provided filter values.
- Fix approach: Migrate to parameterized queries using `psycopg2` `%s` placeholders. The `execute_query` method at `core/database.py:136` would need to accept a `params` tuple alongside the query string. This is a large refactor (40+ methods) but mechanical.

**Massive Query Duplication in `core/database.py`:**
- Issue: The hybrid projection logic (ventas reales + proyecciones gerentes + SOP ponderado for Oruro/Trinidad) is copy-pasted across 4 methods with near-identical CTE structures: `get_proyecciones_marca()` (line 228), `get_proyecciones_ciudad_hibrido()` (line 761), `get_proyecciones_ciudad_marca_hibrido()` (line 905), and the SOP weekly weighting logic. Each query is 100-170 lines of SQL. The Oruro/Trinidad weekly percentages (S1=8%/25%, S2=12%/18%, etc.) are hardcoded in 3 separate places.
- Files: `core/database.py` lines 228-435, 761-903, 905-1095
- Impact: A change to weekly SOP percentages or hybrid logic requires updating 3+ locations. High risk of drift between marca/ciudad/ciudad-marca views.
- Fix approach: Extract a shared SQL builder method that accepts `GROUP BY` columns and returns the CTE structure. The SOP percentages should come from a config dict (similar to `proyeccion_objetiva/config.py` pattern).

**Monkey-Patching in `wsr_generator_main.py`:**
- Issue: `_generate_html_report()` (line 580) replaces methods on `self.html_generator` at runtime using lambda assignments: `self.html_generator._generate_marca_tables = lambda df: ...`. This is done 5 times (lines 598-626) to inject projection data and drivers narratives into the HTML generator without modifying the `HTMLGenerator` class.
- Files: `wsr_generator_main.py` lines 598-626, `core/html_generator.py`
- Impact: Breaks IDE navigation, makes the actual method signatures opaque, and creates implicit coupling between the orchestrator and the HTML generator's internal API. If `HTMLGenerator` changes its method names, the monkey-patches silently stop working (no error, just missing sections).
- Fix approach: Extend `HTMLGenerator` to accept optional `projection_data` and `drivers_data` kwargs in its constructor or `generate_complete_report()` method, then delegate to `HTMLTableGenerator` internally.

**Duplicate Imports in `wsr_generator_main.py`:**
- Issue: `import sys` and `import os` appear twice each (lines 7-8 and 16-17).
- Files: `wsr_generator_main.py` lines 6-8, 16-18
- Impact: Cosmetic, no runtime effect. Indicates hasty editing.
- Fix approach: Remove duplicate imports at lines 16-17.

**Debug Scripts Committed to Project Root:**
- Issue: 6 debug scripts (`debug_branca_py2025.py`, `debug_campos_solana_py2025.py`, `debug_casa_real_py2025.py`, `debug_ctes_separadas.py`, `debug_havana_py2025.py`, `debug_query_proyecciones.py`) and 7 `tmpclaude-*` directories sit in the project root. These are development artifacts, not production code.
- Files: `debug_*.py` (6 files, ~1000 lines total), `tmpclaude-*` (7 directories)
- Impact: Clutters the project root, confuses onboarding. The debug scripts may contain hardcoded connection strings.
- Fix approach: Move debug scripts to a `debug/` directory (or delete). Add `debug/` and `tmpclaude-*` to `.gitignore`. Clean up temp directories.

**Hardcoded Exchange Rate:**
- Issue: The BOB/USD exchange rate (`6.96`) is hardcoded in two separate locations with no single source of truth.
- Files: `core/database.py` line 31 (`self.tipo_cambio = 6.96`), `proyeccion_objetiva/config.py` line 80 (`TIPO_CAMBIO = 6.96`)
- Impact: If the exchange rate changes, both files must be updated. The `DatabaseManager` does not reference `config.py`.
- Fix approach: Single constant in `proyeccion_objetiva/config.py` (or a shared config), imported by `DatabaseManager`.

**Tipo de Cambio Used Inconsistently in SQL:**
- Issue: Currency conversion (`* 6.96`) is done inside SQL queries in `core/database.py` using `self.tipo_cambio`, but the `proyeccion_objetiva/` module uses its own constant. If one changes and the other does not, projections and actuals will be in different currencies.
- Files: `core/database.py` (all projection queries), `proyeccion_objetiva/config.py` line 80
- Impact: Silent data corruption if exchange rates diverge between the two constants.
- Fix approach: Unify to a single source, referenced by both modules.

## Known Bugs

**No Connection Cleanup on Error:**
- Symptoms: If `generate()` throws an exception after `connect()` succeeds but before `disconnect()` is called (line 373), the database connection is leaked.
- Files: `wsr_generator_main.py` lines 96-386, `core/database.py` lines 112-134
- Trigger: Any unhandled exception in `_fetch_all_data()`, `_generate_html_report()`, or projection processing.
- Workaround: The outer `except` at line 384 catches exceptions, but `disconnect()` is only called in the happy path (line 373). The `psycopg2` connection will eventually be garbage-collected, but this may leave server-side connections open.

**`generate_report.py` Defines Unused `clean_log()` Function:**
- Symptoms: `clean_log()` (line 33) strips emojis from log messages but is never called anywhere. The emoji encoding issue it was meant to solve is documented in CLAUDE.md but not actually fixed in the logging pipeline.
- Files: `generate_report.py` lines 33-36
- Trigger: Running on Windows with cp1252 console encoding still produces `UnicodeEncodeError` for emoji-containing log messages.
- Workaround: Set `PYTHONIOENCODING=utf-8` before running.

## Security Considerations

**API Key Handling:**
- Risk: The `OPENROUTER_API_KEY` is loaded from `.env` via `python-dotenv` in 3 separate locations: `wsr_generator_main.py` (line 40, `load_dotenv()`), `utils/llm_processor.py` (line 28, `load_dotenv()` inside `__init__`), and `proyeccion_objetiva/narrative_generator.py` (line 23, `load_dotenv()` inside `__init__`). Each module independently loads and reads the API key.
- Files: `wsr_generator_main.py` line 40, `utils/llm_processor.py` lines 27-30, `proyeccion_objetiva/narrative_generator.py` lines 22-25, `proyeccion_objetiva/pilar3_operativa/drivers_narrative.py` (similar pattern)
- Current mitigation: `.env` is in `.gitignore` (line 45). API key is never logged.
- Recommendations: Centralize API key loading to a single config module. Pass the key as a constructor parameter rather than having each class load `.env` independently.

**Database Credentials in Environment:**
- Risk: Database credentials (`DB_HOST`, `DB_USER`, `DB_PASSWORD`) are loaded from `.env` and passed directly to `psycopg2.connect()`. The password is stored in plaintext in `.env`.
- Files: `wsr_generator_main.py` lines 71-77, `.env` (exists, not read)
- Current mitigation: `.env` in `.gitignore`. Database user is read-only (`automatizacion`).
- Recommendations: Acceptable for current internal-VPN-only deployment. If exposed externally, consider connection pooling with credential rotation.

**LLM Prompt Injection Surface:**
- Risk: Manager comments from `fact_proyecciones.comentario_semana*` are passed directly into LLM prompts in `utils/llm_processor.py` line 80. A malicious comment could theoretically manipulate the LLM output.
- Files: `utils/llm_processor.py` lines 80-115 (prompt construction), `core/database.py` lines 593-632 (comment retrieval)
- Current mitigation: The LLM output is rendered as HTML in the report. The prompt includes strict formatting instructions. Comments come from internal users (managers on company intranet).
- Recommendations: Low risk given internal-only data source. If opening to external input, sanitize comments before prompt injection.

## Performance Bottlenecks

**30+ Sequential Database Queries:**
- Problem: `_fetch_all_data()` in `wsr_generator_main.py` (lines 388-548) executes 30+ queries sequentially. Each query is a separate round-trip to PostgreSQL over VPN.
- Files: `wsr_generator_main.py` lines 388-548
- Cause: Each `get_*` method calls `execute_query()` which calls `pd.read_sql()` with a new cursor. No connection pooling, no parallelism.
- Improvement path: Group related queries into a single CTE-based query (e.g., all marca data could be one query with multiple CTEs). Alternatively, use `asyncio` or threading for parallel query execution.

**Redundant Schema Validation Calls:**
- Problem: `proyeccion_objetiva/data_fetcher.py` calls `validate_factventas_schema()` (which queries `information_schema.columns`) 3 separate times: once in `get_cobertura_mensual()` (line 98), once in `get_dropsize_mensual()` (line 175), and once in `fetch_all()` (line 434).
- Files: `proyeccion_objetiva/data_fetcher.py` lines 34-84, 89-104, 166-180, 419-468
- Cause: Each method independently validates the schema before deciding which query variant to use.
- Improvement path: Cache the schema validation result as an instance variable on first call. The schema does not change during a report generation run.

**Large Hybrid Projection Queries:**
- Problem: The hybrid projection queries in `core/database.py` (marca: 200 lines, ciudad-marca: 170 lines) use 6-8 CTEs each. These are complex queries that join multiple tables and apply conditional logic per-week.
- Files: `core/database.py` lines 228-435 (marca), 761-903 (ciudad), 905-1095 (ciudad-marca)
- Cause: The hybrid real+projected logic requires cross-referencing ventas_reales, proyecciones, and SOP tables with week-based conditional aggregation.
- Improvement path: Pre-compute weekly ranges once and pass as parameters. Consider materializing intermediate results (e.g., ventas_reales_semanales) in a temp table if query time exceeds 5s.

## Fragile Areas

**The Orchestrator Method `generate()` in `wsr_generator_main.py`:**
- Files: `wsr_generator_main.py` lines 91-386
- Why fragile: The `generate()` method is a 296-line sequential pipeline with 10+ numbered steps. Steps 7.5 through 7.8 (lines 146-356) are deeply nested `try/except` blocks (3 levels deep) for projection processing, nowcasting, and narrative generation. Each block catches `Exception` broadly and falls back to "continue without this feature." A failure in step 7.6 (merge PY Estadistica) silently produces a report with missing projection columns, and the only evidence is a warning in the log.
- Safe modification: Test any changes to projection merge logic with the existing `proyeccion_objetiva/tests/test_projection_processor.py`. Verify output HTML contains expected sections after changes.
- Test coverage: The generate() orchestrator itself has zero automated tests. Only the projection processor and statistical engine have unit tests.

**Case Sensitivity Between WSR Core and Projection Module:**
- Files: `wsr_generator_main.py` lines 163-183 (the `_merge_py_est` function)
- Why fragile: The WSR core uses Title Case for marca names (e.g., "Branca"), while the DWH returns UPPER CASE (e.g., "BRANCA"). The `_merge_py_est` helper (defined inline in `generate()`) creates temporary UPPER columns for merging, then drops them. If a new merge is added without this normalization, the join silently produces NaN values (left join with no match).
- Safe modification: Always use the `_merge_py_est` helper for any merge between projection data and WSR DataFrames. Never merge directly on `marcadir`.
- Test coverage: No automated test for case-insensitive merge correctness.

**SOP Weekly Percentage Weights for Oruro and Trinidad:**
- Files: `core/database.py` lines 377-412, 867-890, 1042-1078
- Why fragile: Hardcoded percentages (Oruro: 8%/12%/20%/28%/32%, Trinidad: 25%/18%/22%/20%/15%) are embedded in SQL CASE statements in 3 separate query methods. These represent historical weekly sales distribution patterns for cities without sales managers.
- Safe modification: If adding a new city without a manager, update `_get_ciudades_sin_gerente()` AND add the new city's percentages to all 3 query methods. Verify the percentages sum to 100%.
- Test coverage: None. A test that verifies percentages sum to 100% for each city would catch misconfigurations.

**Drivers Engine `marca` vs `marcadir` Column Name:**
- Files: `proyeccion_objetiva/pilar3_operativa/drivers_engine.py` line 77 (`WHERE UPPER(marca) NOT IN...`)
- Why fragile: The `fact_ventas_detallado` table uses column `marca` (granular brand names like "Absolut", "Finlandia") while the WSR uses `marcadir` (brand directory names like "PERNOD RICARD"). The filtering in `wsr_generator_main.py` (line 593-595) post-processes to exclude micro-brands, but if the WSR marca list changes, the filtering may miss new entries.
- Safe modification: Always pass `valid_marcas` from `estructura_marca['marca_totales']` when calling drivers section generation.
- Test coverage: None for the marca-filtering logic.

## Scaling Limits

**Single-Threaded Report Generation:**
- Current capacity: Full report generation takes 2-5 minutes (estimated based on 30+ DB queries + 3-4 LLM API calls at 30-60s timeout each).
- Limit: Cannot generate multiple reports concurrently. No queuing mechanism.
- Scaling path: If multiple concurrent reports are needed, extract the generator into a task queue (e.g., Celery) with connection pooling.

**LLM API Rate Limits:**
- Current capacity: Each report makes 3-4 calls to OpenRouter (comments analysis, projection narrative, drivers narrative x3 levels). At 30-60s per call, this adds 2-4 minutes.
- Limit: OpenRouter rate limiting (429 responses). Current fallback is a single retry with a cheaper model.
- Scaling path: Pre-generate narratives in a cache keyed by data hash. Only call LLM if data has changed since last generation.

## Dependencies at Risk

**`psycopg2-binary` Without Connection Pooling:**
- Risk: Using raw `psycopg2.connect()` without a pool (`psycopg2.pool` or `sqlalchemy`). Each report run creates and destroys a single connection.
- Impact: Acceptable for current weekly-report cadence. Would become a bottleneck if generating reports more frequently or concurrently.
- Migration plan: Wrap with `psycopg2.pool.SimpleConnectionPool` or migrate to SQLAlchemy for connection management.

**`openai` Package Listed but Not Used:**
- Risk: `requirements.txt` includes `openai>=1.0.0` but the codebase uses `requests` to call OpenRouter directly. Unnecessary dependency.
- Impact: Bloated install, potential version conflicts.
- Migration plan: Remove `openai` from `requirements.txt`.

**`pydantic` and `colorlog` Listed but Not Used:**
- Risk: `requirements.txt` includes `pydantic>=1.10.0` and `colorlog>=6.6.0` but neither is imported anywhere in the codebase.
- Impact: Unnecessary install dependencies.
- Migration plan: Remove unused packages from `requirements.txt`.

## Missing Critical Features

**No Connection Context Manager:**
- Problem: `DatabaseManager` has `connect()` and `disconnect()` but no `__enter__`/`__exit__` for use with `with` statements. This means connection cleanup relies on explicit `disconnect()` calls in the right places.
- Blocks: Safe resource management. If an exception occurs between `connect()` and `disconnect()`, the connection leaks.

**No Data Validation Layer:**
- Problem: DataFrames returned from queries are used directly without schema validation. If a DWH table schema changes (column renamed, type changed), the error surfaces as a cryptic KeyError deep in `data_processor.py` or `html_tables.py`.
- Blocks: Resilient operation against DWH schema changes. `pydantic` is already in requirements but unused.

## Test Coverage Gaps

**Orchestrator (`wsr_generator_main.py`) Has Zero Tests:**
- What's not tested: The entire `WSRGeneratorSystem` class including `generate()`, `_fetch_all_data()`, `_generate_html_report()`, all monkey-patching, and the `_merge_py_est` inline function.
- Files: `wsr_generator_main.py` (879 lines)
- Risk: Any refactoring to the orchestrator (the most complex file) has no safety net. The merge logic, reconciliation, and nowcast blending all run untested in production.
- Priority: High

**Core Modules (`core/database.py`, `core/data_processor.py`, `core/html_generator.py`) Have Zero Unit Tests:**
- What's not tested: All 30+ database query methods, data consolidation, KPI calculation, HTML generation.
- Files: `core/database.py` (1833 lines), `core/data_processor.py` (1096 lines), `core/html_generator.py` (1101 lines)
- Risk: Query logic bugs (especially hybrid projections) can silently produce incorrect numbers in the report. No regression protection.
- Priority: High

**Root-Level Test Files Are Integration Tests, Not Unit Tests:**
- What's not tested: The 11 `test_*.py` files at the project root (e.g., `test_hitrate.py`, `test_trend_chart.py`) appear to be integration/debug scripts that connect to the actual database, not isolated unit tests with mocks. They cannot run without VPN access.
- Files: `test_*.py` (11 files in project root)
- Risk: These tests are not runnable in CI/CD. They test specific debugging scenarios rather than systematic coverage.
- Priority: Medium

**`utils/llm_processor.py` and `utils/html_tables.py` Have Zero Tests:**
- What's not tested: LLM comment processing, HTML table generation (the largest util at 2213 lines), comment formatting.
- Files: `utils/llm_processor.py` (341 lines), `utils/html_tables.py` (2213 lines)
- Risk: HTML table rendering is the most visible output. Formatting bugs, missing columns, or broken drill-down logic would be caught only by manual inspection.
- Priority: Medium

**Projection Module Has Partial Test Coverage:**
- What's tested: `proyeccion_objetiva/tests/test_projection_processor.py` (258 lines, 7 tests), `test_statistical_engine.py` (157 lines), `test_validate_factventas.py` (159 lines).
- What's not tested: `narrative_generator.py`, `nowcast_engine.py`, `data_fetcher.py`, `drivers_engine.py`, `drivers_narrative.py`, `event_calendar.py`, all visualization modules.
- Files: `proyeccion_objetiva/` (entire module minus the 3 test files)
- Risk: The Holt-Winters engine has basic tests, but the narrative generation, nowcasting blend, and drivers engine are untested.
- Priority: Medium

---

*Concerns audit: 2026-03-09*
