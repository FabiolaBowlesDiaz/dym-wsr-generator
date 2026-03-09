# Technology Stack

**Analysis Date:** 2026-03-09

## Languages

**Primary:**
- Python 3.8+ (3.13 in development environment) - All application code

**Secondary:**
- SQL (PostgreSQL dialect) - Inline queries in `core/database.py` and `proyeccion_objetiva/data_fetcher.py`
- HTML/CSS/JavaScript - Inline in Python string templates for report output (`core/html_generator.py`, `utils/html_tables.py`, `proyeccion_objetiva/visualizacion/`)

## Runtime

**Environment:**
- CPython 3.13 (development machine: `C:\Users\Lenovo\AppData\Local\Programs\Python\Python313\python.exe`)
- Minimum supported: Python 3.8+ (per `requirements.txt`)
- Virtual environment: `venv/` directory present in project root

**Package Manager:**
- pip (via venv)
- Lockfile: Not present (no `requirements.lock` or `pip freeze` output committed)

## Frameworks

**Core:**
- No web framework - This is a CLI batch application (`python wsr_generator_main.py`)
- Output is a self-contained HTML file with embedded CSS/JS

**Testing:**
- pytest >=7.0.0 - Unit tests in `proyeccion_objetiva/tests/`

**Build/Dev:**
- black >=22.0.0 - Code formatting (listed in requirements, usage optional)
- flake8 >=4.0.0 - Linting (listed in requirements, usage optional)

## Key Dependencies

**Critical (data pipeline):**
- `pandas` >=1.5.0 - All data manipulation, DataFrame-centric architecture
- `numpy` >=1.23.0 - Numerical operations within pandas pipelines
- `psycopg2-binary` >=2.9.0 - PostgreSQL database driver (only DB connector)
- `python-dotenv` >=0.20.0 - Environment variable loading from `.env`

**Critical (forecasting):**
- `statsmodels` >=0.14.0 - Holt-Winters (ExponentialSmoothing) for sales projections in `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py`
- `scipy` >=1.10.0 - Statistical support for statsmodels

**Critical (AI/LLM):**
- `requests` >=2.28.0 - HTTP client for OpenRouter API calls (NOT using the `openai` SDK despite it being listed)
- `openai` >=1.0.0 - Listed in requirements but NOT imported anywhere; all LLM calls use raw `requests` to OpenRouter

**Infrastructure:**
- `colorlog` >=6.6.0 - Colored log output
- `pydantic` >=1.10.0 - Data validation (listed, minimal usage observed)

**Frontend (embedded in HTML output, loaded via CDN):**
- Chart.js - Interactive charts in generated HTML reports (`core/trend_chart_generator.py`, `proyeccion_objetiva/visualizacion/projection_chart_generator.py`)

## Configuration

**Environment:**
- `.env` file present in project root - Contains all secrets and configuration
- Loaded via `python-dotenv` at startup in `wsr_generator_main.py` and each LLM processor module

**Required environment variables:**

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENROUTER_API_KEY` | API key for LLM narrative generation | `sk-or-...` |
| `DEFAULT_MODEL` | Primary LLM model | `anthropic/claude-opus-4.6` |
| `FALLBACK_MODEL` | Fallback LLM model on rate limit | `anthropic/claude-sonnet-4` |
| `OPENROUTER_BASE_URL` | OpenRouter API base (default: `https://openrouter.ai/api/v1`) | - |
| `DB_HOST` | PostgreSQL DWH host | `192.168.80.85` |
| `DB_PORT` | PostgreSQL port (default: `5432`) | `5432` |
| `DB_NAME` | Database name | `dwh_saiv` |
| `DB_USER` | Database user (read-only) | `automatizacion` |
| `DB_PASSWORD` | Database password | - |
| `DB_SCHEMA` | Schema (default: `auto`, resolves to `dym_stg`) | `auto` |
| `LOG_LEVEL` | Logging level (default: `INFO`) | `INFO` |

**Build:**
- No build step - pure Python, run directly
- No `setup.py`, `pyproject.toml`, or `setup.cfg`

## Platform Requirements

**Development:**
- Windows 11 (primary development environment)
- VPN connection required to reach DWH at `192.168.80.85`
- Python 3.8+ with venv
- `PYTHONIOENCODING=utf-8` recommended for clean console output (emoji in log messages cause `UnicodeEncodeError` on Windows cp1252)

**Production:**
- Same as development - runs on developer's machine via CLI
- No containerization, no CI/CD, no deployment pipeline
- Output: `output/WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html` opened in default browser

## Execution

```bash
# Standard execution (requires VPN)
python wsr_generator_main.py

# With clean console encoding
PYTHONIOENCODING=utf-8 python wsr_generator_main.py

# Run tests
pytest proyeccion_objetiva/tests/test_projection_processor.py -v
```

## Constants

- **Exchange rate:** 6.96 BOB/USD - hardcoded in `core/database.py` (line 31) and `proyeccion_objetiva/config.py` (line 80)
- **Seasonal period:** 12 months - `proyeccion_objetiva/config.py`
- **HW minimum months:** 25 (triple), 12 (double) - `proyeccion_objetiva/config.py`

---

*Stack analysis: 2026-03-09*
