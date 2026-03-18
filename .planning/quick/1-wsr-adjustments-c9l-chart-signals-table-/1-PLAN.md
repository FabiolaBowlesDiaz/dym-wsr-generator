---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - proyeccion_objetiva/data_fetcher.py
  - proyeccion_objetiva/visualizacion/projection_chart_generator.py
  - proyeccion_objetiva/visualizacion/projection_html_generator.py
  - wsr_generator_main.py
  - core/html_generator.py
autonomous: true
requirements: [WSR-C9L-CHART, WSR-SIGNALS-TABLE, WSR-HITRATE-LINE]
must_haves:
  truths:
    - "WSR HTML shows two monthly evolution charts: one BOB, one C9L, with identical structure and 4 series each"
    - "Signals summary table has 5 columns: SENAL, MONTO (BOB), vs SOP, MONTO (C9L), vs SOP (C9L)"
    - "Hit Rate vs Eficiencia section shows a Chart.js line chart instead of CSS horizontal bars"
  artifacts:
    - path: "proyeccion_objetiva/data_fetcher.py"
      provides: "C9L historical queries for national ventas, SOP, PY Gerente"
    - path: "proyeccion_objetiva/visualizacion/projection_chart_generator.py"
      provides: "C9L chart generation method"
    - path: "proyeccion_objetiva/visualizacion/projection_html_generator.py"
      provides: "Expanded signals table with C9L columns"
    - path: "core/html_generator.py"
      provides: "Line chart for Hit Rate vs Eficiencia"
  key_links:
    - from: "wsr_generator_main.py"
      to: "projection_chart_generator.py"
      via: "generate_historical_chart_c9l call with C9L historical data"
    - from: "wsr_generator_main.py"
      to: "projection_html_generator.py"
      via: "generate_full_section call now includes C9L totals + C9L chart_html"
---

<objective>
Add three visual enhancements to the WSR HTML report:
1. A new C9L monthly evolution chart (identical to the existing BOB chart but using C9L data)
2. Expand the signals summary table from 3 to 5 columns (adding C9L MONTO and vs SOP)
3. Convert the Hit Rate vs Eficiencia chart from CSS horizontal bars to a Chart.js line chart

Purpose: Give decision-makers both BOB and C9L perspectives on closing signals, and improve the Hit Rate chart readability.
Output: Modified generator files that produce the enhanced WSR HTML.
</objective>

<execution_context>
@C:/Users/Lenovo/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Lenovo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@proyeccion_objetiva/data_fetcher.py
@proyeccion_objetiva/visualizacion/projection_chart_generator.py
@proyeccion_objetiva/visualizacion/projection_html_generator.py
@wsr_generator_main.py
@core/html_generator.py
@proyeccion_objetiva/config.py

<interfaces>
<!-- Key data flow for C9L chart -->

From proyeccion_objetiva/data_fetcher.py (existing BOB queries to replicate for C9L):
- get_ventas_nacionales_historicas() returns: anio, mes, venta_bob  (line 419-448)
  The table td_ventas_bob_historico has column `c9l` — add `SUM(CAST(c9l AS NUMERIC)) AS venta_c9l`
- get_sop_nacional_historico() returns: anio, mes, sop_bob  (line 453-483)
  The table factpresupuesto_mensual has `c9l` column — need C9L equivalent query
- get_py_gerente_nacional_historico() returns: anio, mes, py_gerente_bob  (line 488-540)
  PY Gerente is stored in BOB only in fact_proyecciones — C9L PY Gerente is NOT in this table

From wsr_generator_main.py (line 644-693):
- marca_totales already has these C9L columns: sop_c9l, avance_{year}_c9l, py_sistema_c9l
- These are computed by nowcast.calculate() with value_suffix='c9l' (lines 288-307)
- NOTE: There is NO py_{year}_c9l from fact_proyecciones (PY Gerente only exists in BOB)
  BUT database.py line 750 shows: `s.sop_bob as py_{year}_c9l` — PY Gerente C9L uses SOP C9L as proxy

From projection_chart_generator.py:
- generate_historical_chart() builds 4 series: Venta Real, SOP, PY Gerente, PY Sistema
- Uses Chart.js line chart with specific colors from config

From projection_html_generator.py:
- generate_full_section() receives: chart_html, sop_nacional, py_gerente_nacional, py_sistema_nacional, avance_nacional
- _generate_resumen_table() builds 3-column table: SENAL, MONTO (BOB), vs SOP

From core/html_generator.py:
- _generate_hitrate_chart() at line 939-997 builds CSS horizontal bars
- Receives df with columns: mes, hit_rate, eficiencia
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add C9L historical queries + C9L chart + expanded signals table</name>
  <files>
    proyeccion_objetiva/data_fetcher.py,
    proyeccion_objetiva/visualizacion/projection_chart_generator.py,
    proyeccion_objetiva/visualizacion/projection_html_generator.py,
    wsr_generator_main.py
  </files>
  <action>
**1. data_fetcher.py — Add C9L to existing national queries:**

Modify `get_ventas_nacionales_historicas()` (line 431-448): Add `SUM(CAST(c9l AS NUMERIC)) AS venta_c9l` to the SELECT. The table `td_ventas_bob_historico` already has the `c9l` column. This way one query returns both BOB and C9L.

Modify `get_sop_nacional_historico()` (line 464-483): The table `factpresupuesto_mensual` — check if it has a `c9l` column. If yes, add `SUM(CAST(c9l_column AS NUMERIC)) AS sop_c9l`. If not, return sop_c9l as NULL/0 (the C9L SOP is available from marca_totales anyway via `sop_c9l` column in database.py line 697).

For PY Gerente C9L historical: fact_proyecciones does NOT have C9L data. Database.py line 750 uses `sop_bob as py_{year}_c9l` as a proxy. For the chart, PY Gerente C9L will NOT have historical data — use None for past months. Only current month PY Gerente C9L is available from marca_totales (it's actually SOP C9L used as proxy per database.py).

**2. projection_chart_generator.py — New C9L chart method:**

Add method `generate_historical_chart_c9l()` to `ProjectionChartGenerator`. This is nearly identical to `generate_historical_chart()` but:
- Title: "Senales de Cierre — Evolucion Mensual Nacional (C9L)"
- Uses `venta_c9l` instead of `venta_bob` from ventas_df
- Uses `sop_c9l` instead of `sop_bob` from sop_df (if available, else skip SOP series)
- PY Gerente C9L: only show for months where data exists (likely only current month or none — use py_ger_c9l_df if provided)
- PY Sistema C9L: single point for current month (from py_sistema_c9l in marca_totales)
- Avance C9L: for current month partial data
- chart_id defaults to "resumenEjecutivoChartC9L" (unique canvas ID, critical)
- Y-axis tooltip: show "C9L" instead of "BOB"
- Same colors, same chart style, same options

Accept the data Dict with keys: 'ventas_nacionales' (now with venta_c9l column), 'sop_nacional' (with sop_c9l if available), 'py_gerente_nacional' (may not have C9L).

Signature:
```python
def generate_historical_chart_c9l(
    self,
    historico_nacional: Dict,
    py_sistema_c9l: float = 0,
    avance_c9l: float = 0,
    py_gerente_c9l: float = 0,
    sop_c9l: float = 0,
    current_year: int = 2026,
    current_month: int = 3,
    chart_id: str = "resumenEjecutivoChartC9L"
) -> str:
```

For the C9L chart, since historical C9L data for SOP and PY Gerente may be sparse:
- Venta Real C9L: use `venta_c9l` column from ventas_nacionales (should have full 12 months)
- SOP C9L: use `sop_c9l` from sop_nacional if available; if column missing, show SOP only for current month using the `sop_c9l` parameter (single point like PY Sistema)
- PY Gerente C9L: probably not available historically. Only show current month point using `py_gerente_c9l` parameter (if > 0). Show as point like PY Sistema.
- PY Sistema C9L: single point for current month

**3. projection_html_generator.py — Expand signals table + add C9L chart:**

Modify `generate_full_section()` signature to accept additional C9L parameters:
```python
def generate_full_section(
    self,
    chart_html: str,
    sop_nacional: float,
    py_gerente_nacional: float,
    py_sistema_nacional: float,
    avance_nacional: float,
    narrative_html: str = "",
    chart_html_c9l: str = "",          # NEW
    sop_nacional_c9l: float = 0,       # NEW
    py_gerente_nacional_c9l: float = 0, # NEW
    py_sistema_nacional_c9l: float = 0, # NEW
    avance_nacional_c9l: float = 0     # NEW
) -> str:
```

In the body, after inserting `chart_html`, also insert `chart_html_c9l` (the C9L chart appears right below the BOB chart).

Modify `_generate_resumen_table()` to accept C9L values and render 5 columns:
```python
def _generate_resumen_table(
    self,
    sop: float, py_gerente: float, py_sistema: float, avance: float,
    sop_c9l: float = 0, py_gerente_c9l: float = 0,
    py_sistema_c9l: float = 0, avance_c9l: float = 0
) -> str:
```

Table structure becomes:
| SENAL | MONTO (BOB) | vs SOP | MONTO (C9L) | vs SOP (C9L) |

The `vs SOP (C9L)` column uses the same logic as `vs_sop()` but compares C9L values against `sop_c9l`. For "Avance actual" row, show `pct_sop` equivalent for C9L.

Widen the table: change `max-width: 700px` to `max-width: 900px` to accommodate the 2 new columns.

**4. wsr_generator_main.py — Wire C9L data to chart and table:**

In the projection section (around lines 640-693), after computing BOB totals, also compute C9L totals from `marca_totales`:
```python
avance_col_c9l = f'avance_{self.current_year}_c9l'
avance_nacional_c9l = marca_totales[avance_col_c9l].sum() if avance_col_c9l in marca_totales.columns else 0
sop_nacional_c9l = marca_totales['sop_c9l'].sum() if 'sop_c9l' in marca_totales.columns else 0
py_gerente_c9l_col = f'py_{self.current_year}_c9l'
py_gerente_nacional_c9l = marca_totales[py_gerente_c9l_col].sum() if py_gerente_c9l_col in marca_totales.columns else 0
py_sistema_nacional_c9l = marca_totales['py_sistema_c9l'].sum() if 'py_sistema_c9l' in marca_totales.columns else 0
```

Generate the C9L chart:
```python
chart_html_c9l = proj_chart_gen.generate_historical_chart_c9l(
    historico_nacional,
    py_sistema_c9l=py_sistema_nacional_c9l,
    avance_c9l=avance_nacional_c9l,
    py_gerente_c9l=py_gerente_nacional_c9l,
    sop_c9l=sop_nacional_c9l,
    current_year=self.current_year,
    current_month=self.current_month
)
```

Pass all C9L values to `generate_full_section()`:
```python
projection_html = proj_html_gen.generate_full_section(
    chart_html=chart_html,
    sop_nacional=sop_nacional,
    py_gerente_nacional=py_gerente_nacional,
    py_sistema_nacional=py_sistema_nacional,
    avance_nacional=avance_nacional,
    chart_html_c9l=chart_html_c9l,
    sop_nacional_c9l=sop_nacional_c9l,
    py_gerente_nacional_c9l=py_gerente_nacional_c9l,
    py_sistema_nacional_c9l=py_sistema_nacional_c9l,
    avance_nacional_c9l=avance_nacional_c9l
)
```
  </action>
  <verify>
    <automated>cd "C:\Users\Lenovo\OneDrive - theblankinc.com\IA Consulting\DyM\aa_v3_dym_wsr_proyecto_2209_sia(ultimo en produccion dym)" && python -c "from proyeccion_objetiva.visualizacion.projection_chart_generator import ProjectionChartGenerator; from proyeccion_objetiva.visualizacion.projection_html_generator import ProjectionHTMLGenerator; p=ProjectionChartGenerator(); h=ProjectionHTMLGenerator(); html=h.generate_full_section('', 1000, 900, 950, 500, chart_html_c9l='', sop_nacional_c9l=100, py_gerente_nacional_c9l=90, py_sistema_nacional_c9l=95, avance_nacional_c9l=50); assert 'MONTO (C9L)' in html; assert 'vs SOP' in html; print('OK: C9L table columns present')"</automated>
  </verify>
  <done>
    - data_fetcher returns venta_c9l in ventas_nacionales query
    - ProjectionChartGenerator has generate_historical_chart_c9l() producing a Chart.js line chart with title "(C9L)"
    - ProjectionHTMLGenerator.generate_full_section accepts C9L params and renders C9L chart below BOB chart
    - Signals table has 5 columns: SENAL, MONTO (BOB), vs SOP, MONTO (C9L), vs SOP (C9L)
    - wsr_generator_main.py wires C9L totals from marca_totales into both chart and table
  </done>
</task>

<task type="auto">
  <name>Task 2: Convert Hit Rate vs Eficiencia chart from horizontal bars to Chart.js line chart</name>
  <files>core/html_generator.py</files>
  <action>
Replace the `_generate_hitrate_chart()` method in `HTMLGenerator` (lines 939-997).

Current implementation: Pure CSS/HTML horizontal bars with month labels on Y-axis and two bars (Hit Rate blue, Eficiencia green) per month.

New implementation: Chart.js line chart with two series (Hit Rate and Eficiencia) as lines with dots over time (months on X-axis).

The method receives `df` with columns: `mes` (month name string like "ENE", "FEB", "MAR"), `hit_rate` (float %), `eficiencia` (float %).

Generate a unique canvas ID to avoid conflicts with other Chart.js charts on the page: `hitRateEficienciaChart`.

Implementation:
```python
def _generate_hitrate_chart(self, df: pd.DataFrame) -> str:
    if df.empty:
        return ""

    import json

    labels = [row['mes'][:3].upper() for _, row in df.iterrows()]
    hr_data = [round(row['hit_rate'], 1) for _, row in df.iterrows()]
    ef_data = [round(row['eficiencia'], 1) for _, row in df.iterrows()]

    labels_json = json.dumps(labels, ensure_ascii=False)
    hr_json = json.dumps(hr_data)
    ef_json = json.dumps(ef_data)

    # Max Y slightly above 100 or data max
    max_y = max(max(hr_data + ef_data, default=100), 100) * 1.05

    return f"""
    <div style="margin: 30px 0; background: #f9fafb; padding: 20px; border-radius: 8px;">
        <h4 style="margin-bottom: 15px; color: #1e3a8a; font-size: 13px;">
            Evolucion Hit Rate vs Eficiencia
        </h4>
        <div style="position: relative; height: 300px; width: 100%;">
            <canvas id="hitRateEficienciaChart"></canvas>
        </div>
    </div>
    <script>
    (function() {{
        var ctx = document.getElementById('hitRateEficienciaChart');
        if (!ctx) return;

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {labels_json},
                datasets: [
                    {{
                        label: 'Hit Rate',
                        data: {hr_json},
                        borderColor: '#3b82f6',
                        backgroundColor: '#3b82f6',
                        borderWidth: 2.5,
                        tension: 0.3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        fill: false
                    }},
                    {{
                        label: 'Eficiencia',
                        data: {ef_json},
                        borderColor: '#10b981',
                        backgroundColor: '#10b981',
                        borderWidth: 2.5,
                        tension: 0.3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        position: 'top',
                        labels: {{
                            usePointStyle: true,
                            padding: 15,
                            font: {{ size: 11 }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: {max_y:.0f},
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }},
                            font: {{ size: 10 }}
                        }},
                        grid: {{
                            color: '#e5e7eb'
                        }}
                    }},
                    x: {{
                        ticks: {{
                            font: {{ size: 10, weight: '500' }},
                            maxRotation: 0
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
    }})();
    </script>
    """
```

Note: Chart.js is already loaded via `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>` in the HTML head (html_generator.py line 266), so no additional script tag needed. The IIFE pattern `(function() { ... })();` matches the style used in projection_chart_generator.py.

Add `import json` at the top of the file if not already imported.
  </action>
  <verify>
    <automated>cd "C:\Users\Lenovo\OneDrive - theblankinc.com\IA Consulting\DyM\aa_v3_dym_wsr_proyecto_2209_sia(ultimo en produccion dym)" && python -c "import pandas as pd; from core.html_generator import HTMLGenerator; from datetime import datetime; g=HTMLGenerator(datetime(2026,3,17)); df=pd.DataFrame({'mes':['ENE','FEB','MAR'],'hit_rate':[75.0,78.0,80.0],'eficiencia':[85.0,87.0,89.0],'tendencia_hitrate':[0,3.0,2.0]}); html=g._generate_hitrate_chart(df); assert 'hitRateEficienciaChart' in html; assert 'Chart(ctx' in html or 'new Chart' in html; assert 'Hit Rate' in html; print('OK: Line chart generated')"</automated>
  </verify>
  <done>
    - Hit Rate vs Eficiencia section renders a Chart.js line chart with two series
    - X-axis shows month labels, Y-axis shows percentage
    - Blue line for Hit Rate, green line for Eficiencia, with dots at each data point
    - Tooltips show percentage values
    - CSS horizontal bars code is removed
  </done>
</task>

</tasks>

<verification>
After both tasks are complete:
1. `python -c "from proyeccion_objetiva.visualizacion.projection_chart_generator import ProjectionChartGenerator; print('OK')"` — import succeeds
2. `python -c "from proyeccion_objetiva.visualizacion.projection_html_generator import ProjectionHTMLGenerator; print('OK')"` — import succeeds
3. `python -c "from core.html_generator import HTMLGenerator; print('OK')"` — import succeeds
4. If VPN is available: `python wsr_generator_main.py` generates HTML with both charts and expanded table
</verification>

<success_criteria>
- WSR HTML output contains two "Senales de Cierre" charts: one titled "(BOB)" and one "(C9L)"
- The C9L chart has 4 series: PY Sistema (Nowcast), Venta Real, PY Gerente, SOP — using C9L values
- The signals table "4.1. RESUMEN DE SENALES" has 5 columns including MONTO (C9L) and vs SOP (C9L)
- The Hit Rate section shows a Chart.js line chart (not horizontal bars) with Hit Rate and Eficiencia as two line series
- All imports succeed without errors
- No regressions in existing BOB chart or signals table BOB columns
</success_criteria>

<output>
After completion, create `.planning/quick/1-wsr-adjustments-c9l-chart-signals-table-/1-SUMMARY.md`
</output>
