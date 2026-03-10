# Phase 3: Driver Data Verification - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate that cobertura, frecuencia (hit rate), and drop size values displayed in the Drivers de Performance por Marca table are correct — cross-validated against direct DWH queries. This is a data integrity audit, not a feature change.

</domain>

<decisions>
## Implementation Decisions

### Formula validation
- Formulas reviewed and confirmed correct by the user:
  - Cobertura = `COUNT(DISTINCT cod_cliente)` — clientes únicos que compraron
  - Hit Rate = `COUNT(DISTINCT cuf_factura) / COUNT(DISTINCT cod_cliente)` — frecuencia de compra (pedidos/cliente)
  - Drop Size = `SUM(ingreso_neto_bob) / COUNT(DISTINCT cuf_factura)` — ticket promedio por pedido (BOB/pedido)
  - VSLY = `(valor_actual / valor_año_anterior) - 1` — cambio porcentual year-over-year
- Hit Rate is explicitly frequency, NOT conversion rate (no visit data exists in fact_ventas_detallado)
- Multiplicative identity: `Cobertura × Hit Rate × Drop Size = Venta total` (minor rounding discrepancies expected from SQL ROUND(..., 2))

### Verification approach
- Standalone Python validation script that runs independently of the WSR engine
- Script runs its own direct SQL queries against `fact_ventas_detallado` in the DWH
- Compares results against what `DriversEngine.calculate_by_marca()` produces
- Print comparative table in console with PASS/FAIL per brand

### Period to validate
- STD mode: March 2026, day 1 through current day (same-to-date)
- This validates the real production scenario, not a historical snapshot
- YoY comparison period: March 1-{current_day}, 2025

### Grouping level
- Validate only at marca (brand) level — the primary table visible in the WSR
- Other grouping levels (ciudad, marca+submarca, ciudad+marca) use the same SQL query template, so if marca validates correctly, the pattern is sound

### Output format
- Console print: comparative table showing Engine values vs Direct query values per brand
- PASS/FAIL indicator per brand per metric (cobertura, hit_rate, drop_size, VSLY trends)
- Summary line: X/Y brands passed all checks

### Claude's Discretion
- Exact tolerance threshold for floating-point comparison (rounding differences)
- Whether to validate the multiplicative identity (Cob × HR × DS ≈ Venta) as an additional check
- Script location and naming
- Logging verbosity

</decisions>

<specifics>
## Specific Ideas

- User wants to first see and understand the formulas before running validation — educational/audit approach, not blind testing
- The validation script should be re-runnable anytime (not a one-shot check)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DriversEngine` in `proyeccion_objetiva/pilar3_operativa/drivers_engine.py`: The engine being validated. Has `calculate_by_marca()` method that returns DataFrame with cobertura, hit_rate, drop_size, trends
- `DatabaseManager` in `core/database.py`: PostgreSQL connection manager, reusable for direct validation queries
- `.env` file: Contains DB credentials (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

### Established Patterns
- SQL queries use `ROUND(..., 2)` at the database level for hit_rate and drop_size
- STD mode in `_compute_std()`: Builds date ranges from `current_date`, fetches current + YoY periods, merges and computes trends
- Excluded brands: "NINGUNA", "SIN MARCA ASIGNADA"; Excluded cities: "TURISMO"
- Schema auto-detection: `self.schema` resolves to `dym_stg` or `auto`

### Integration Points
- Validation script connects to same DWH (192.168.80.85:5432, requires VPN)
- Can instantiate `DriversEngine` directly with a `DatabaseManager` to get engine output
- Direct queries bypass the engine to get ground truth from `fact_ventas_detallado`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-driver-data-verification*
*Context gathered: 2026-03-10*
