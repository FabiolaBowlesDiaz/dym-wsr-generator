# CLAUDE.md — WSR Generator DYM

## Proyecto

Generador automático de Weekly Sales Report (WSR) para DYM, empresa boliviana de distribución de bebidas alcohólicas premium. Genera un HTML interactivo con tablas de performance por marca/ciudad/canal, gráficos de tendencia, proyecciones estadísticas (Holt-Winters), y narrativa IA.

**Ejecución**: `python wsr_generator_main.py` (requiere VPN a 192.168.80.85)
**Output**: `output/WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html`
**Tests**: `pytest proyeccion_objetiva/tests/test_projection_processor.py -v` (7 tests)

---

## Arquitectura

```
wsr_generator_main.py          ← Orquestador principal
├── core/
│   ├── database.py            ← Conexión PostgreSQL (DWH SAIV)
│   ├── data_processor.py      ← Consolidación marca/ciudad/canal + KPIs
│   ├── html_generator.py      ← Estructura HTML del reporte
│   └── trend_chart_generator.py ← Gráficos Chart.js interactivos
├── utils/
│   ├── html_tables.py         ← Tablas de performance (BOB/C9L) con drill-down
│   ├── llm_processor.py       ← Análisis de comentarios de gerentes (OpenRouter)
│   └── business_days.py       ← Días hábiles Bolivia + eventos móviles
├── proyeccion_objetiva/       ← Módulo de Proyección Objetiva
│   ├── config.py              ← Constantes HW, umbrales, colores, eventos
│   ├── data_fetcher.py        ← Queries al DWH (ventas 36m, cobertura, HR, DS)
│   ├── projection_processor.py ← Orquestador: HW + Operativa + merge + spread
│   ├── narrative_generator.py ← Narrativa IA (Claude via OpenRouter)
│   ├── pilar2_estadistica/
│   │   ├── statistical_engine.py  ← Holt-Winters (Triple/Double Exp Smoothing)
│   │   └── event_calendar.py      ← Ajuste por Carnaval/Semana Santa
│   ├── pilar3_operativa/
│   │   ├── drivers_engine.py      ← Motor: Cob × HR × DS desde fact_ventas_detallado
│   │   ├── drivers_narrative.py   ← Narrativa IA diagnostico operativo (Claude)
│   │   └── DRIVERS.md             ← Documentación completa del pilar
│   └── visualizacion/
│       ├── projection_chart_generator.py ← Gráfico comparativo Chart.js
│       └── projection_html_generator.py  ← Sección HTML de proyecciones
└── output/                    ← Reportes generados (.html)
```

---

## Base de datos

- **Tipo**: PostgreSQL (DWH SAIV)
- **Host**: 192.168.80.85:5432 (requiere VPN)
- **DB**: `dwh_saiv`, schema `dym_stg` (auto-detectado)
- **User**: `automatizacion` (read-only)
- **Credenciales**: en `.env` (NO versionar)

### Tablas principales
| Tabla | Uso |
|-------|-----|
| `td_ventas_bob_historico` | Ventas mensuales por marca/ciudad/canal (36m) — fuente HW |
| `FactVentas` | Ventas granulares por cliente (cobertura, drop size) |
| `fact_eficiencia_hitrate` | Hit rate y eficiencia por ciudad |
| `fact_proyecciones` | PY Gerente ingresada por gerentes comerciales |
| `fact_ventas_detallado` | Ventas item-level con cod_cliente + cuf_factura (schema `auto`) — fuente Drivers |

### Dato crítico del DWH
- `td_ventas_bob_historico` se actualiza durante el día (ETL incremental)
- **Los datos históricos pueden cambiar entre ejecuciones** (credit notes, ajustes)
- **DEBE tener todos los meses completos cargados** — meses faltantes (ej: Ene 2026 sin cargar) generan zeros que desestabilizan el modelo HW
- Si hay gaps, el log muestra: `WARNING: DWH: X mes(es) sin datos: [YYYY-MM]`

---

## Motor Estadístico (Holt-Winters)

### Flujo de datos
```
td_ventas_bob_historico (36m)
  → data_fetcher.get_ventas_mensuales_historicas()
  → statistical_engine._df_to_monthly_series()  [excluye mes actual]
  → statistical_engine.forecast_single_series()  [HW triple/double]
  → py_estadistica_bob (benchmark fijo del mes)
```

### Reglas clave
- **Excluye el mes en curso** de la serie (data parcial contamina el modelo)
- `N ≥ 25 meses` → Triple Exp (tendencia + estacionalidad), confidence=high
- `12 ≤ N < 25` → Double Exp (solo tendencia), confidence=medium
- `N < 12` o `>70% ceros` → None (datos insuficientes)
- Ajuste post-forecast por eventos móviles (Carnaval ±15%, Viernes Santo -2%)
- `horizon=1` siempre (proyecta el mes siguiente al último dato completo)

### PY Estadística = benchmark FIJO
- Se calcula con meses completos solamente
- NO se actualiza intra-mes con data parcial
- Sirve como ancla para comparar contra PY Gerente
- Si se necesita estimación dinámica, implementar Nowcast como columna separada (Fase 2, no implementada)

---

## Narrativa IA

- **Modelo**: `anthropic/claude-opus-4.6` via OpenRouter (fallback: `claude-sonnet-4`)
- **Ubicación en WSR**: justo después de la tabla Performance por Marca BOB, antes de la tabla semanal
- **Inyección**: via `generate_marca_tables(df, estructura_jerarquica, narrative_html)` en `utils/html_tables.py`
- **Prompt**: análisis financiero ejecutivo comparando PY Gerente vs PY Estadística, foco en divergencia absoluta BOB
- **Fallback**: si OpenRouter falla, la tabla se muestra sin narrativa (graceful degradation)

---

## Orden de marcas en tablas

Las tablas de performance ordenan marcas por volumen descendente (multi-columna con fallback):
1. `avance_{year}_bob` (avance actual)
2. `py_{year}_bob` (PY Gerente — tiebreaker si avance=0 a inicio de mes)
3. `vendido_{prev_year}_bob` (vendido año anterior — último recurso)

Esto aplica a marca, ciudad, y canal (3 ocurrencias en `data_processor.py`).
Ciudades tienen un sort fijo adicional: Santa Cruz → Cochabamba → La Paz → ...

---

## Monkey-patch pattern en wsr_generator_main.py

`_generate_html_report()` inyecta funciones en `html_generator` via lambdas:
```python
self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(
    df, estructura_jerarquica=estructura_marca, narrative_html=narrative_html
)
```
Esto evita modificar `HTMLGenerator` (core) para features de proyección (extensión).

---

## Ejecución y troubleshooting

### Ejecutar
```bash
# Con VPN conectada
python wsr_generator_main.py
```

### Encoding en Windows
Los emojis en logger causan `UnicodeEncodeError` en consola cp1252 — es cosmético, no afecta el HTML. Para logs limpios: `PYTHONIOENCODING=utf-8 python wsr_generator_main.py`

### Gerentes no han ingresado PY
Normal en semana 1 del mes. PY Gerente ≈ $0, spread ≈ -100%. La narrativa IA detecta esto y lo reporta. Los gerentes ingresan proyecciones en la segunda semana.

### Forecast inestable entre ejecuciones
Verificar: `WARNING: DWH: X mes(es) sin datos`. Si hay meses faltantes en `td_ventas_bob_historico`, el zero desestabiliza HW. Reportar a sistemas para que carguen los datos faltantes.

---

## Configuración clave (.env)

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key para narrativa IA y análisis de comentarios |
| `DEFAULT_MODEL` | Modelo LLM (actual: `anthropic/claude-opus-4.6`) |
| `DB_HOST` | `192.168.80.85` (DWH SAIV, requiere VPN) |
| `DB_SCHEMA` | `auto` (detecta `dym_stg` automáticamente) |

---

## Exclusiones hardcodeadas

- **Ciudades/Canales**: "TURISMO"
- **Marcas**: "NINGUNA", "SIN MARCA ASIGNADA"
- Definidas en `proyeccion_objetiva/config.py` y `core/data_processor.py`
