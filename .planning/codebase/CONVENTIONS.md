# Coding Conventions

**Analysis Date:** 2026-03-09

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `data_processor.py`, `html_generator.py`, `business_days.py`
- Test files at root level: `test_{feature}.py` (e.g., `test_hitrate.py`, `test_trend_chart.py`)
- Test files in submodules: `tests/test_{module}.py` (e.g., `proyeccion_objetiva/tests/test_projection_processor.py`)
- Debug/exploratory scripts: `debug_{feature}.py` at root (e.g., `debug_branca_py2025.py`)

**Classes:**
- Use `PascalCase`: `DatabaseManager`, `DataProcessor`, `HTMLGenerator`, `TrendChartGenerator`
- Use `PascalCase` with acronyms preserved: `WSRGeneratorSystem`, `HTMLTableGenerator`, `NowcastEngine`
- Single class per file, class name matches file purpose

**Functions/Methods:**
- Use `snake_case`: `calculate_business_days()`, `generate_projections()`, `format_number()`
- Private methods prefixed with underscore: `_fetch_all_data()`, `_build_prompt()`, `_clean_outliers()`
- Query methods prefixed with `get_`: `get_ventas_historicas_marca()`, `get_hitrate_mensual()`
- Calculation methods prefixed with `calculate_`: `calculate_executive_summary()`, `calculate_business_days()`
- Generation methods prefixed with `generate_`: `generate_complete_report()`, `generate_chart_html()`

**Variables:**
- Use `snake_case` for all variables: `current_date`, `dias_laborales_mes`, `py_estadistica_bob`
- DataFrame variables often match their business meaning: `marcas_df`, `ciudades_df`, `canales_df`
- Column names use `snake_case` with year/currency suffix: `avance_2026_bob`, `py_estadistica_c9l`, `vendido_2025_bob`
- Constants use `UPPER_SNAKE_CASE`: `TIPO_CAMBIO`, `MIN_MONTHS_TRIPLE`, `EXCLUDED_BRANDS`

**Types/Constants:**
- Constants defined at module level in `proyeccion_objetiva/config.py`
- Business constants (tipo de cambio, thresholds) centralized in config
- Color constants use hex strings: `COLOR_PY_GERENTE = "#94A3B8"`

## Code Style

**Formatting:**
- `black` listed in `requirements.txt` but no config file (`.pyproject.toml`, `setup.cfg`) detected -- not enforced
- Indentation: 4 spaces (standard Python)
- Max line length: not enforced; lines frequently exceed 100 chars (SQL queries, long method signatures)
- String formatting: f-strings used consistently throughout (no `.format()` or `%` formatting)

**Linting:**
- `flake8` listed in `requirements.txt` but no `.flake8` or `setup.cfg` config detected -- not enforced
- No `pyproject.toml` or `setup.cfg` at project root
- No pre-commit hooks configured

## Import Organization

**Order:**
1. Standard library imports (`os`, `sys`, `datetime`, `logging`, `calendar`, `json`)
2. Third-party imports (`pandas`, `numpy`, `psycopg2`, `requests`, `dotenv`)
3. Local/project imports (`from core.database import DatabaseManager`, `from .config import ...`)

**Path manipulation:**
- Root scripts use `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` for local imports
- This pattern appears in `wsr_generator_main.py`, `test_hitrate.py`, `test_full_query.py`, `generate_report.py`

**Relative imports:**
- Used within packages: `from .projection_processor import ProjectionProcessor` in `proyeccion_objetiva/__init__.py`
- Used for config: `from .. import config as cfg` in `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py`
- Used for sibling modules: `from .data_fetcher import ProjectionDataFetcher` in `proyeccion_objetiva/projection_processor.py`

**Path Aliases:**
- None configured. All imports are relative to the project root via `sys.path.insert(0, ...)`.

## Error Handling

**Patterns:**

1. **Graceful degradation with try/except + warning log** (dominant pattern):
   ```python
   try:
       from proyeccion_objetiva import ProjectionProcessor
       PROJECTION_MODULE_AVAILABLE = True
   except ImportError as e:
       PROJECTION_MODULE_AVAILABLE = False
       logging.getLogger(__name__).warning(f"Modulo no disponible: {e}")
   ```
   Used in: `wsr_generator_main.py` (lines 28-37), `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py` (lines 22-36)

2. **Try/except with fallback** for external services (LLM):
   ```python
   try:
       response = self._call_llm(prompt)
       if response:
           return response
       else:
           return self._basic_processing(raw_comments)
   except Exception as e:
       logger.error(f"Error procesando con LLM: {e}")
       return self._basic_processing(raw_comments)
   ```
   Used in: `utils/llm_processor.py` (lines 54-68), `proyeccion_objetiva/narrative_generator.py` (lines 41-56)

3. **Boolean return for connection success**:
   ```python
   def connect(self) -> bool:
       try:
           self.conn = psycopg2.connect(...)
           return True
       except Exception as e:
           logger.error(f"Error conectando: {e}")
           return False
   ```
   Used in: `core/database.py` (lines 112-128)

4. **Nested try/except in orchestrator** -- each feature wrapped independently so failures don't block the report:
   ```python
   # 7.5 Projections
   try:
       projection_data = proj_processor.generate_projections(...)
   except Exception as e:
       logger.warning(f"Modulo fallo (WSR se genera sin esta seccion): {e}")
       projection_data = None
   ```
   Used throughout: `wsr_generator_main.py` (lines 147-356, multiple nested try/except blocks)

**Anti-pattern to avoid:** Bare `except Exception` catching -- used extensively but appropriate here since the system prioritizes report generation over strict error propagation.

## Logging

**Framework:** Python `logging` module (standard library)

**Configuration:** Set up in `wsr_generator_main.py` (lines 43-51):
```python
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsr_generator.log'),
        logging.StreamHandler()
    ]
)
```

**Per-module logger pattern:**
```python
logger = logging.getLogger(__name__)
```
Used at the top of every module: `core/database.py`, `core/data_processor.py`, `utils/llm_processor.py`, all `proyeccion_objetiva/` modules.

**Log level conventions:**
- `logger.info()` -- progress markers with emoji: `logger.info("📊 Generando proyecciones...")`
- `logger.warning()` -- non-fatal degradation: `logger.warning(f"Modulo no disponible: {e}")`
- `logger.error()` -- failures with `exc_info=True`: `logger.error(f"Error: {e}", exc_info=True)`
- `logger.debug()` -- query results: `logger.debug(f"Query ejecutado, {len(df)} filas")`

**Emoji in logs:** Extensively used (`logger.info("📅 Fecha: ...")`, `logger.info("✅ Completado")`). Causes `UnicodeEncodeError` on Windows cp1252 console -- cosmetic only, does not affect HTML output. Workaround: `PYTHONIOENCODING=utf-8`.

## Comments

**When to Comment:**
- Module-level docstrings in triple-quoted strings on all `.py` files -- always present
- Class docstrings -- always present, brief description of purpose
- Method docstrings with `Args:`/`Returns:` -- present on public methods in core modules (`core/database.py`, `core/data_processor.py`, `utils/business_days.py`)
- Inline comments for business logic (Spanish): `# Domingos son 6 en weekday()`, `# BOB/USD`
- SQL queries commented inline explaining join logic

**Docstring format:**
```python
def execute_query(self, query: str) -> pd.DataFrame:
    """
    Ejecutar query y retornar DataFrame

    Args:
        query: Query SQL a ejecutar

    Returns:
        DataFrame con los resultados
    """
```

**Language:** Mixed Spanish/English. Docstrings and comments in Spanish. Code identifiers mostly in English with Spanish business terms (`marcadir`, `ciudad`, `ventas`, `avance`, `ppto`).

## Function Design

**Size:** Functions range from 5-50 lines typically. Some orchestration methods are very long (e.g., `generate()` in `wsr_generator_main.py` is ~300 lines). Data fetching methods in `database.py` are short (query + execute).

**Parameters:** Use type hints on key classes (`config: dict`, `schema: str = 'auto'`, `current_date: datetime`). Not all functions have type hints -- especially helper lambdas and inline functions.

**Return Values:**
- DataFrames for data operations: `pd.DataFrame`
- Dicts for structured results: `Dict` with documented keys
- Strings for HTML generation
- Booleans for success/failure
- None-safe: many functions return empty DataFrame or empty string on failure rather than None

## Module Design

**Exports:**
- Packages use `__init__.py` with explicit `__all__`: `proyeccion_objetiva/__init__.py` exports `ProjectionProcessor`
- Core and utils `__init__.py` files are empty (no barrel exports)

**Barrel Files:**
- `proyeccion_objetiva/__init__.py` acts as barrel: `from .projection_processor import ProjectionProcessor`
- Other packages (`core/`, `utils/`) have empty `__init__.py` -- import directly from modules

**Monkey-patching pattern:**
- `wsr_generator_main.py` uses lambda injection to extend `HTMLGenerator` without modifying core:
  ```python
  self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(
      df, estructura_jerarquica=estructura_marca, narrative_html=narrative_html
  )
  ```
- Used for: `_generate_marca_tables`, `_generate_ciudad_tables`, `_generate_canal_tables`, `_generate_stock_analysis`, `_generate_footer`

## SQL Conventions

**Query construction:**
- Inline f-string SQL in `core/database.py` and `proyeccion_objetiva/data_fetcher.py`
- No parameterized queries (read-only access, controlled inputs)
- Schema prefix: `{self.schema}.table_name`
- Column names UPPERCASED in WHERE clauses: `UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')`
- Excluded entities defined as constants: `EXCLUDED_BRANDS`, `EXCLUDED_CITIES`, `EXCLUDED_CHANNELS`

**Column naming in queries:**
- Aliases use snake_case: `venta_bob`, `clientes_unicos`, `hit_rate`
- Year-parametrized columns: `avance_{year}_bob`, `py_{year}_bob`

## Data Conventions

**DataFrame column naming:**
- Business metrics: `{metric}_{year}_{currency}` (e.g., `avance_2026_bob`, `vendido_2025_c9l`)
- KPI ratios: `AV_PG` (avance/presupuesto general), `AV_SOP`, `PY_V`
- Projection columns: `py_estadistica_bob`, `py_sistema_bob`, `run_rate_bob`, `spread_sistema`
- Driver columns: `cobertura`, `hit_rate`, `drop_size`, `venta_total`

**Merge strategy:**
- Left/outer merges on business keys (`marcadir`, `ciudad`, `canal`)
- `fillna(0)` after merges for numeric columns
- Case-insensitive merges via temporary UPPER columns (see `_merge_py_est()` in `wsr_generator_main.py`)

---

*Convention analysis: 2026-03-09*
