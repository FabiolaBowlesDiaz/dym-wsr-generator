# WSR DYM — Ajustes Resumen Ejecutivo y Narrativa

## What This Is

Ajustes al Weekly Sales Report (WSR) de DYM, un reporte HTML interactivo que analiza el desempeno comercial semanal a nivel nacional. El WSR incluye tablas de performance por marca/ciudad/canal con proyecciones estadisticas (Holt-Winters + Nowcast), drivers operativos (cobertura, frecuencia, drop size), y narrativas IA generadas por Claude via OpenRouter.

## Core Value

Los numeros del reporte deben ser consistentes y confiables — si el chart y la tabla muestran datos diferentes, los gerentes pierden confianza en todo el reporte.

## Requirements

### Validated

- ✓ Chart PY Gerente y SOP alineados con tabla resumen (marca_totales como fuente) — v1.0
- ✓ Narrativa regional renderiza bold como HTML strong tags — v1.0
- ✓ Terminologia comercial en narrativas IA (productos, referencias/presentaciones) — v1.0
- ✓ Seccion Accuracy oculta via config flag (codigo preservado) — v1.0
- ✓ Drivers (cobertura, frecuencia, drop size) validados contra DWH directo — v1.0

### Active

(None — define in next milestone)

### Out of Scope

- PY Sistema C9L nativo (plan existe pero es fase separada) — complejidad alta, no urgente
- Cambios en Secciones 1-3 — funcionan correctamente
- Nuevas fuentes de datos o queries DWH adicionales

## Context

- **DWH**: PostgreSQL SAIV (192.168.80.85:5432), schema auto/dym_stg, requiere VPN
- **Narrativas IA**: OpenRouter API, claude-opus-4.6 con claude-sonnet-4 fallback
- **Chart.js**: Para graficas interactivas en HTML output
- **v1.0 shipped**: 3 phases, 3 plans, 9 requirements satisfied. Validation script at `scripts/validate_drivers.py`.

## Constraints

- **No breaking changes**: El WSR debe seguir generandose correctamente para todas las secciones
- **Preservar codigo**: La seccion de Accuracy se oculta con flag, no se elimina
- **Fuente de verdad**: `marca_totales` (pipeline consolidado) es autoritativo sobre queries directas

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| marca_totales como fuente de verdad | Es el mismo pipeline usado en Secciones 1-3, ya validado | ✓ Good — eliminated ~5M BOB discrepancy |
| Productos/presentaciones como terminologia | Es el lenguaje natural del equipo comercial DYM | ✓ Good — enforced in both LLM prompts |
| Ocultar accuracy con flag (no eliminar) | Puede reactivarse cuando agregue valor | ✓ Good — SHOW_ACCURACY_SECTION=False, reversible |
| Proportional weekly scaling for chart | Preserves week-over-week selling pattern while correcting totals | ✓ Good — no visual regression |
| Config flag pattern (early return + try/except) | Graceful degradation if config module unavailable | ✓ Good — reusable pattern |

---
*Last updated: 2026-03-10 after v1.0 milestone*
