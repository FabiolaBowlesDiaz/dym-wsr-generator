# Testing Patterns

**Analysis Date:** 2026-03-09

## Test Framework

**Runner:**
- pytest >= 7.0.0 (listed in `requirements.txt`)
- No `pytest.ini`, `pyproject.toml`, or `setup.cfg` with pytest configuration detected
- No `conftest.py` files detected

**Assertion Library:**
- Native `assert` statements (pytest-style)
- No third-party assertion libraries (no `assertpy`, `hamcrest`, etc.)

**Run Commands:**
```bash
pytest proyeccion_objetiva/tests/test_projection_processor.py -v   # Unit tests (7 tests, no DWH needed)
pytest proyeccion_objetiva/tests/test_statistical_engine.py -v      # HW engine tests (no DWH needed)
pytest proyeccion_objetiva/tests/test_validate_factventas.py -v     # Integration tests (requires DWH VPN)
python test_business_days.py                                         # Manual script (not pytest)
python test_hitrate.py                                               # Manual script (requires DWH VPN)
python test_trend_chart.py                                           # Manual script (generates HTML)
```

## Test File Organization

**Location:**
- Two patterns coexist:
  1. **Root-level scripts** (`test_*.py`): Manual test/debug scripts run via `python test_*.py`, NOT discoverable by pytest (no `class Test*` or `def test_*` functions in pytest sense, or require live DB)
  2. **Submodule test directory** (`proyeccion_objetiva/tests/`): Proper pytest tests with `class Test*` and `def test_*` methods

**Root-level test scripts (manual, NOT pytest):**
- `test_business_days.py` -- manual verification of business day calculations
- `test_hitrate.py` -- manual DB query verification (requires VPN)
- `test_trend_chart.py` -- generates HTML test file, visual verification
- `test_trend_chart_full_month.py` -- full month trend chart test
- `test_trend_chart_multi_city_simple.py` -- multi-city chart test
- `test_trend_chart_with_sop.py` -- trend chart with SOP data
- `test_trend_multi_city.py` -- multi-city variant
- `test_full_query.py` -- raw SQL query test (requires VPN)
- `test_py2025_c9l.py` -- C9L projection test
- `test_sop_join.py` -- SOP join verification
- `test_stock_marcadirectorio.py` -- stock data test
- `test_ciudad_values.py` -- city value verification
- `verify_calculation.py` -- calculation verification script

**Proper pytest test files:**
- `proyeccion_objetiva/tests/__init__.py` -- empty package init
- `proyeccion_objetiva/tests/test_projection_processor.py` -- 7 tests across 3 classes
- `proyeccion_objetiva/tests/test_statistical_engine.py` -- 8 tests across 3 classes
- `proyeccion_objetiva/tests/test_validate_factventas.py` -- 8 tests across 5 classes (integration, requires DWH)

**Empty test directory:**
- `tests/` at project root exists but is empty (created by `setup.py`)

**Naming:**
- Test files: `test_{module_name}.py`
- Test classes: `class Test{Feature}` (e.g., `TestCleanOutliers`, `TestSanityChecks`, `TestResiliencia`)
- Test methods: `def test_{what_is_tested}` (e.g., `test_build_comparativo_spread`, `test_mostly_zeros_returns_none`)

## Test Structure

**Suite Organization:**
```python
# proyeccion_objetiva/tests/test_statistical_engine.py
@pytest.fixture
def engine():
    from proyeccion_objetiva.pilar2_estadistica.statistical_engine import StatisticalEngine
    return StatisticalEngine()


def _make_monthly_series(values, start_year=2024, start_month=1):
    """Helper: crea Serie con DatetimeIndex mensual."""
    dates = pd.date_range(
        start=f"{start_year}-{start_month:02d}-01",
        periods=len(values),
        freq='MS'
    )
    return pd.Series(values, index=dates, dtype=float)


class TestCleanOutliers:
    """Tests para la limpieza de outliers."""

    def test_no_outliers_unchanged(self, engine):
        values = [100, 105, 98, 102, 110, 95, 108, 100, 103, 97]
        series = _make_monthly_series(values)
        cleaned = engine._clean_outliers(series)
        assert np.allclose(cleaned.values, series.values, atol=1)

    def test_low_outlier_replaced(self, engine):
        values = [100, 105, 98, 102, 5, 95, 108, 100, 103, 97]
        series = _make_monthly_series(values)
        cleaned = engine._clean_outliers(series)
        assert cleaned.iloc[4] > 50, "Outlier bajo no fue corregido"
```

**Patterns:**
- Group related tests in classes (`class TestCleanOutliers`, `class TestForecastSingleSeries`)
- Use `@pytest.fixture` for shared setup (module-scope for DB connections, function-scope for engines)
- Helper functions at module level with `_` prefix: `_make_monthly_series()`, `_mock_data_fetcher()`
- Test docstrings describe expected behavior in Spanish

## Mocking

**Framework:** `unittest.mock` (MagicMock, patch)

**Patterns:**
```python
# proyeccion_objetiva/tests/test_projection_processor.py
from unittest.mock import MagicMock, patch

class TestProjectionProcessorUnit:
    def test_full_pipeline_with_mock(self):
        mock_db = MagicMock()
        processor = ProjectionProcessor(mock_db, datetime(2026, 2, 22))

        # Mock the data fetcher's fetch_all method
        mock_data = self._mock_data_fetcher()
        processor.data_fetcher.fetch_all = MagicMock(return_value=mock_data)

        py_ger_marca = pd.DataFrame({
            'marcadir': ['BRANCA', 'HAVANA', 'CASA REAL'],
            'py_2026_bob': [1500000, 1200000, 900000]
        })

        result = processor.generate_projections(py_gerente_marca=py_ger_marca)

        assert 'by_marca' in result
        assert not result['by_marca'].empty
```

**What to Mock:**
- `DatabaseManager` (always mock with `MagicMock()` for unit tests)
- `data_fetcher.fetch_all()` -- mock return value with synthetic DataFrames
- External API calls (OpenRouter) -- not currently mocked in tests

**What NOT to Mock:**
- `StatisticalEngine` -- tested directly with synthetic series data
- `DriversEngine.diagnose_trend()` -- pure function, tested directly
- `ProjectionHTMLGenerator` -- tested with empty/real data for resilience

**Mock data factory pattern:**
```python
def _mock_data_fetcher(self):
    """Crea datos mock que simulan lo que retornaria el DWH."""
    rows_ventas = []
    for marca in ['BRANCA', 'HAVANA', 'CASA REAL']:
        for ciudad in ['SANTA CRUZ', 'LA PAZ', 'COCHABAMBA']:
            for year in [2024, 2025]:
                for month in range(1, 13):
                    base_venta = 500000 + np.random.normal(0, 20000)
                    rows_ventas.append({
                        'marcadir': marca, 'ciudad': ciudad,
                        'anio': year, 'mes': month,
                        'venta_bob': base_venta,
                    })
    return {'ventas_historicas': pd.DataFrame(rows_ventas), ...}
```

## Fixtures and Factories

**Test Data:**
```python
# Synthetic time series with known properties
@pytest.fixture
def engine():
    from proyeccion_objetiva.pilar2_estadistica.statistical_engine import StatisticalEngine
    return StatisticalEngine()

# Synthetic monthly data for HW testing
np.random.seed(42)
values = (np.arange(18) * 10 + 100 + np.random.normal(0, 5, 18)).tolist()
series = _make_monthly_series(values)

# Database connection fixture (integration tests only)
@pytest.fixture(scope="module")
def db_manager():
    config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    dm = DatabaseManager(config, schema)
    if not dm.connect():
        pytest.skip("No se pudo conectar al DWH")
    yield dm
    dm.disconnect()
```

**Location:**
- Fixtures defined inline in each test file (no shared `conftest.py`)
- Factory methods as class methods: `_mock_data_fetcher()` in `TestProjectionProcessorUnit`
- Seed-controlled randomness: `np.random.seed(42)` for reproducible synthetic data

## Coverage

**Requirements:** None enforced. No coverage configuration, no CI pipeline.

**View Coverage:**
```bash
pytest --cov=proyeccion_objetiva proyeccion_objetiva/tests/ -v    # If pytest-cov installed
```

## Test Types

**Unit Tests (no external dependencies):**
- `proyeccion_objetiva/tests/test_statistical_engine.py` -- 8 tests
  - Outlier cleaning validation
  - Insufficient data handling (returns None)
  - Mostly-zeros handling (returns None)
  - Double/Triple exponential model selection by data length
  - Forecast sanity bounds (50%-200% of average)
  - `run_by_marca` / `run_by_ciudad` output shape validation
- `proyeccion_objetiva/tests/test_projection_processor.py` -- 7 tests
  - Spread calculation correctness
  - Spread diagnosis categorization (optimista/conservador/consenso/divergencia)
  - Full pipeline with mock data
  - Projections-positive sanity check
  - Resilience: empty data handling
  - Resilience: DriversEngine.diagnose_trend with None
  - Resilience: HTML generator with empty data

**Integration Tests (require DWH VPN):**
- `proyeccion_objetiva/tests/test_validate_factventas.py` -- 8 tests
  - Schema validation (FactVentas columns)
  - Cobertura data availability and column presence
  - Drop size positivity
  - Hit rate reasonable range (0-100)
  - Ventas historicas data availability and depth (>= 12 months)
  - `fetch_all()` returns all expected keys
  - Uses `pytest.skip()` if DB connection fails

**Manual Verification Scripts (not pytest, require VPN):**
- Root-level `test_*.py` files -- run via `python test_*.py`
- These are exploratory/debug scripts that print results to console
- Some generate HTML files in `output/` for visual verification
- Pattern: connect to DB, run queries, print results, disconnect

**E2E Tests:**
- Not implemented as automated tests
- The full E2E test is running `python wsr_generator_main.py` and inspecting the HTML output

## Common Patterns

**Async Testing:**
- Not applicable. All code is synchronous.

**Error/Edge Case Testing:**
```python
# Testing None handling
def test_diagnose_trend_handles_none(self):
    result = DriversEngine.diagnose_trend(None, 0.01, -0.05)
    assert result == "Datos insuficientes"

# Testing empty data resilience
def test_html_generator_with_empty_data(self):
    gen = ProjectionHTMLGenerator()
    html = gen.generate_full_section({
        'by_marca': pd.DataFrame(),
        'by_ciudad': pd.DataFrame(),
        'decomposition_ciudad': pd.DataFrame(),
        'decomposition_marca': pd.DataFrame(),
        'resumen_nacional': {}
    })
    assert isinstance(html, str)
```

**Assertion patterns:**
```python
# Value correctness with tolerance
assert abs(float(branca['spread']) - 0.10) < 0.01

# Array closeness
assert np.allclose(cleaned.values, series.values, atol=1)

# DataFrame shape assertions
assert isinstance(result, pd.DataFrame)
assert 'marcadir' in result.columns
assert len(result) == 2

# Non-empty result assertion
assert not result['by_marca'].empty

# String contains assertion
assert 'optimista' in processor._diagnose_spread(0.15).lower()

# Positivity assertion with custom message
assert row['py_estadistica_bob'] >= 0, f"Proyeccion negativa para {row['marcadir']}"
```

## Test Gaps and Recommendations

**Not tested:**
- `core/database.py` -- no unit tests for SQL query construction or DB methods
- `core/data_processor.py` -- no unit tests for consolidation logic or KPI calculations
- `core/html_generator.py` -- no unit tests for HTML output
- `core/trend_chart_generator.py` -- manual scripts only, no pytest
- `utils/html_tables.py` -- no tests
- `utils/llm_processor.py` -- no tests (LLM calls)
- `utils/business_days.py` -- manual script only, not proper pytest
- `wsr_generator_main.py` -- no automated tests for the orchestrator

**When adding new tests:**
- Place pytest-compatible tests in `proyeccion_objetiva/tests/` for projection module
- Place core module tests in `tests/` directory (currently empty, needs `conftest.py`)
- Use `MagicMock()` for `DatabaseManager` in unit tests
- Use `np.random.seed()` for reproducible synthetic data
- Use `pytest.skip()` for tests requiring DWH connection
- Group related tests in a `class Test{Feature}` with descriptive docstrings

---

*Testing analysis: 2026-03-09*
