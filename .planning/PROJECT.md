# WSR DYM — Ajustes Resumen Ejecutivo y Narrativa

## What This Is

Ajustes al Weekly Sales Report (WSR) de DYM, un reporte HTML interactivo que analiza el desempeno comercial semanal a nivel nacional. El WSR incluye tablas de performance por marca/ciudad/canal con proyecciones estadisticas (Holt-Winters + Nowcast), drivers operativos (cobertura, frecuencia, drop size), y narrativas IA generadas por Claude via OpenRouter.

## Core Value

Los numeros del reporte deben ser consistentes y confiables — si el chart y la tabla muestran datos diferentes, los gerentes pierden confianza en todo el reporte.

## Requirements

### Validated

- Seccion 1-3: Tablas de performance por marca, ciudad, canal con PY Sistema (Nowcast), drivers STD, VSLY
- Seccion 4: Grafica historica de lineas con 4 senales (Venta Real, SOP, PY Gerente, PY Sistema)
- Seccion 4: Tabla resumen con montos vs SOP
- Narrativas IA por marca, ciudad, canal (OpenRouter Claude)
- Analisis de comentarios regionales (IA)
- Accuracy de la proyeccion comercial (chart interactivo por ciudad)

### Active

- [ ] Fix: Alinear datos del chart historico con los de la tabla resumen (PY Gerente y SOP)
- [ ] Fix: Renderizar narrativa de comentarios regionales como HTML (no markdown crudo)
- [ ] Fix: Reemplazar terminologia tecnica (SKUs → productos, lenguas → referencias/presentaciones)
- [ ] Feature: Ocultar seccion de Accuracy de proyeccion comercial (preservar codigo)

### Out of Scope

- PY Sistema C9L nativo (plan existe pero es fase separada) — complejidad alta, no urgente
- Cambios en Secciones 1-3 — funcionan correctamente
- Nuevas fuentes de datos o queries DWH adicionales

## Context

- **DWH**: PostgreSQL SAIV (192.168.80.85:5432), schema auto/dym_stg, requiere VPN
- **Narrativas IA**: OpenRouter API, claude-opus-4.6 con claude-sonnet-4 fallback
- **Chart.js**: Para graficas interactivas en HTML output
- **Discrepancia raiz**: El chart Section 4 consulta `fact_proyecciones` y `factpresupuesto_mensual` directamente a nivel nacional, mientras la tabla suma desde `marca_totales` (pipeline de consolidacion por marca). Diferencia: ~5M BOB en PY Gerente, ~1.4M en SOP.
- **Narrativa**: La IA genera markdown (`**bold**`) pero se inserta en HTML sin conversion. Tambien usa terminologia tecnica (SKUs, lenguas) que no es natural para el equipo comercial.
- **Accuracy chart**: Seccion existente que compara Venta Real vs Proyeccion Gerentes por ciudad. No agrega valor aun — ocultar sin eliminar codigo.

## Constraints

- **No breaking changes**: El WSR debe seguir generandose correctamente para todas las secciones
- **Preservar codigo**: La seccion de Accuracy se oculta con flag, no se elimina
- **Fuente de verdad**: `marca_totales` (pipeline consolidado) es autoritativo sobre queries directas

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| marca_totales como fuente de verdad | Es el mismo pipeline usado en Secciones 1-3, ya validado | — Pending |
| Productos/presentaciones como terminologia | Es el lenguaje natural del equipo comercial DYM | — Pending |
| Ocultar accuracy con flag (no eliminar) | Puede reactivarse cuando agregue valor | — Pending |

---
*Last updated: 2026-03-09 after initialization*
