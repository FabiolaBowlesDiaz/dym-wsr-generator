# External Integrations

**Analysis Date:** 2026-03-09

## APIs & External Services

**LLM / AI (OpenRouter):**
- OpenRouter API - Generates AI narrative analysis for 4 distinct use cases
  - SDK/Client: Raw `requests` library (NOT the `openai` SDK)
  - Auth: `OPENROUTER_API_KEY` env var (Bearer token)
  - Base URL: `https://openrouter.ai/api/v1` (configurable via `OPENROUTER_BASE_URL`)
  - Endpoint: `POST /chat/completions` (OpenAI-compatible format)
  - Primary model: `anthropic/claude-opus-4.6` (env: `DEFAULT_MODEL`)
  - Fallback model: `anthropic/claude-sonnet-4` (env: `FALLBACK_MODEL`, triggered on HTTP 429)
  - Temperature: 0.3 (low, for consistency)
  - Timeout: 30 seconds per request

**LLM usage points (4 separate callers, each instantiates its own client):**

| Module | File | Purpose | max_tokens |
|--------|------|---------|------------|
| Comment Analysis | `utils/llm_processor.py` (`CommentProcessor`) | Analyzes raw manager comments into executive summary | 1000 |
| Projection Narrative | `proyeccion_objetiva/narrative_generator.py` (`ProjectionNarrativeGenerator`) | Analyzes PY Sistema (Nowcast) vs PY Gerente divergence by brand | ~2000 |
| Drivers Narrative (marca) | `proyeccion_objetiva/pilar3_operativa/drivers_narrative.py` (`DriversNarrativeGenerator`) | Diagnoses Cobertura/HitRate/DropSize trends per brand | 3000 |
| Drivers Narrative (ciudad/canal) | Same file, called 3x | Same engine for ciudad and canal breakdowns | 3000 |

**LLM request pattern (all modules follow the same pattern):**
```python
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://dym-wsr-generator.com",
    "X-Title": "DYM WSR Generator"
}
data = {
    "model": model_to_use,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3,
    "max_tokens": N
}
response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
```

**Graceful degradation:** All LLM calls are wrapped in try/except. If OpenRouter fails, the report generates without narrative sections. `utils/llm_processor.py` falls back to `_basic_processing()` (passthrough of raw comments).

**Chart.js CDN:**
- Chart.js loaded via CDN `<script>` tag in generated HTML output
- Used for: trend charts (`core/trend_chart_generator.py`), projection comparison charts (`proyeccion_objetiva/visualizacion/projection_chart_generator.py`)
- No server-side rendering; charts render in the viewer's browser

## Data Storage

**Databases:**
- PostgreSQL (DWH SAIV)
  - Host: `192.168.80.85:5432` (internal network, requires VPN)
  - Database: `dwh_saiv`
  - Schema: `dym_stg` (auto-detected when `DB_SCHEMA=auto`)
  - Client: `psycopg2` (direct SQL, no ORM)
  - User: `automatizacion` (read-only)
  - Connection: env vars `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
  - Connection manager: `core/database.py` (`DatabaseManager` class)

**Key DWH tables:**

| Table | Schema | Purpose | Used by |
|-------|--------|---------|---------|
| `td_ventas_bob_historico` | `dym_stg` | Monthly sales by brand/city/channel (36 months) - HW training data | `core/database.py`, `proyeccion_objetiva/data_fetcher.py` |
| `FactVentas` | `dym_stg` | Granular sales by client (coverage, drop size) | `core/database.py` |
| `fact_eficiencia_hitrate` | `dym_stg` | Hit rate and efficiency by city | `core/database.py` |
| `fact_proyecciones` | `dym_stg` | Manager projections (PY Gerente) | `core/database.py` |
| `fact_ventas_detallado` | `auto`/`dym_stg` | Item-level sales with cod_cliente + cuf_factura | `proyeccion_objetiva/pilar3_operativa/drivers_engine.py` |

**Data characteristics:**
- `td_ventas_bob_historico` updates incrementally during the day (ETL)
- Historical data can change between runs (credit notes, adjustments)
- Missing months produce zeros that destabilize HW model

**File Storage:**
- Local filesystem only
- Output HTML files: `output/WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html`
- Log file: `wsr_generator.log` in project root

**Caching:**
- None - all data fetched fresh on each run

## Authentication & Identity

**Auth Provider:**
- None (no user authentication)
- Database uses a shared read-only service account (`automatizacion`)
- OpenRouter API key is a single shared key

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking service)

**Logs:**
- Python `logging` module with `FileHandler` + `StreamHandler`
- Log file: `wsr_generator.log` (root directory)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Level: configurable via `LOG_LEVEL` env var (default: `INFO`)
- `colorlog` dependency listed but standard logging format used in main

## CI/CD & Deployment

**Hosting:**
- Local Windows machine (developer's workstation)
- No server deployment

**CI Pipeline:**
- None - no CI/CD, no automated testing pipeline
- Manual execution: `python wsr_generator_main.py`

## Environment Configuration

**Required env vars:**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL connection
- `OPENROUTER_API_KEY` - LLM narratives (optional, degrades gracefully without it)
- `DEFAULT_MODEL` - LLM model selection (has sensible default)

**Secrets location:**
- `.env` file in project root (not version controlled)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (the OpenRouter API calls are request/response, not webhook-based)

## Network Dependencies

**Required connectivity:**
- VPN to `192.168.80.85` (DWH PostgreSQL) - MANDATORY for any execution
- Internet access to `openrouter.ai` - Optional (report generates without AI narratives)
- Internet access for Chart.js CDN - Required for charts to render in output HTML (could be embedded for offline use)

## Integration Architecture Notes

- All integrations are outbound (this system only reads data and calls APIs)
- No inbound APIs, no webhooks, no event-driven triggers
- Each LLM module independently initializes its own API client (no shared singleton)
- Database connection is managed as a single connection per run (connect at start, disconnect at end)
- No connection pooling (single-user batch process)

---

*Integration audit: 2026-03-09*
