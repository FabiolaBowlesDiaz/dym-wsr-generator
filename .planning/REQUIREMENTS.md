# Requirements: WSR DYM Ajustes

**Defined:** 2026-03-09
**Core Value:** Numeros consistentes y confiables entre chart y tabla del Resumen Ejecutivo

## v1 Requirements

### Data Integrity

- [x] **DATA-01**: Chart historical line for PY Gerente current month uses same value as the summary table (from marca_totales pipeline)
- [x] **DATA-02**: Chart historical line for SOP current month uses same value as the summary table (from marca_totales pipeline)

### Narrative Quality

- [x] **NARR-01**: Regional comments analysis renders bold text as HTML `<strong>` tags (not raw `**markdown**` asterisks)
- [x] **NARR-02**: AI narrative uses "productos" instead of "SKUs" and "referencias/presentaciones" instead of "lenguas" in its output

### Section Visibility

- [x] **VIS-01**: Accuracy de la proyeccion comercial section is hidden via config flag (code preserved, not deleted)

### Driver Data Verification

- [ ] **DRV-01**: Cobertura (distinct client count) per brand matches a direct COUNT(DISTINCT cod_cliente) query against the DWH for the same period
- [ ] **DRV-02**: Frecuencia (hit_rate = pedidos/clientes) per brand matches a direct calculation from the DWH
- [ ] **DRV-03**: Drop Size BOB (SUM(ingreso_neto_bob)/pedidos) per brand matches a direct calculation from the DWH
- [ ] **DRV-04**: Delta VSLY percentages are correctly computed as (current / prior) - 1

## v2 Requirements

### Projection Enhancement

- **PROJ-01**: PY Sistema C9L nativo (Holt-Winters entrenado sobre series C9L, no derivado de BOB)
- **PROJ-02**: Columnas PY Sistema + Spread en tablas C9L por marca y ciudad

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cambios en Secciones 1-3 | Funcionan correctamente, no requieren ajuste |
| Nuevas queries al DWH | Solo se reutilizan datos existentes del pipeline |
| Narrativa IA para C9L | Solo aplica a BOB en esta iteracion |
| Rediseno visual completo | Solo ajustes puntuales de formato |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| NARR-01 | Phase 2 | Complete |
| NARR-02 | Phase 2 | Complete |
| VIS-01 | Phase 2 | Complete |
| DRV-01 | Phase 3 | Planned |
| DRV-02 | Phase 3 | Planned |
| DRV-03 | Phase 3 | Planned |
| DRV-04 | Phase 3 | Planned |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-10 after Phase 3 planning*
