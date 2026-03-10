# Roadmap: WSR DYM Ajustes

## Overview

Fix data integrity issues in the Section 4 chart (PY Gerente and SOP values diverge from the summary table), then clean up narrative rendering and hide the accuracy section. Two phases: trust the numbers first, then polish the presentation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2): Planned milestone work
- Decimal phases (1.1, etc.): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Data Integrity** - Chart Section 4 matches summary table for PY Gerente and SOP (source: marca_totales)
- [x] **Phase 2: Narrative and Visibility** - Regional comments render as HTML, terminology is commercial-friendly, accuracy section hidden
- [ ] **Phase 3: Driver Data Verification** - Validate cobertura, frecuencia and dropsize calculations in drivers performance table

## Phase Details

### Phase 1: Data Integrity
**Goal**: The Section 4 historical chart shows the same PY Gerente and SOP values as the summary table for the current month
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. PY Gerente value displayed in the chart line for the current month equals the PY Gerente value shown in the summary table (both sourced from marca_totales)
  2. SOP value displayed in the chart line for the current month equals the SOP value shown in the summary table (both sourced from marca_totales)
  3. The WSR generates without errors for all sections (no breaking changes)
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md -- Align chart PY Gerente and SOP with marca_totales (override national totals, preserve weekly distribution)

### Phase 2: Narrative and Visibility
**Goal**: Regional narrative renders cleanly as HTML with commercial terminology, and the accuracy section is hidden without deleting code
**Depends on**: Phase 1
**Requirements**: NARR-01, NARR-02, VIS-01
**Success Criteria** (what must be TRUE):
  1. Bold text in the regional comments analysis displays as rendered HTML bold (no visible `**asterisks**` in the browser)
  2. The narrative text uses "productos" instead of "SKUs" and "referencias/presentaciones" instead of "lenguas" in its output
  3. The Accuracy de la proyeccion comercial section does not appear in the generated HTML output
  4. The accuracy section code remains in the codebase (not deleted), controllable via a config flag
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md -- Fix bold rendering, add terminology rules to LLM prompts, hide accuracy section via config flag

### Phase 3: Driver Data Verification
**Goal**: Cobertura, frecuencia and drop size values in the Drivers de Performance por Marca table are correct -- cross-validated against direct DWH queries
**Depends on**: Phase 2
**Requirements**: DRV-01, DRV-02, DRV-03, DRV-04
**Success Criteria** (what must be TRUE):
  1. Cobertura (distinct client count) per brand matches a direct COUNT(DISTINCT) query against the DWH for the same period
  2. Frecuencia (pedidos/clientes) per brand matches a direct calculation from the DWH
  3. Drop Size BOB (SUM(venta)/pedidos) per brand matches a direct calculation from the DWH
  4. Delta VSLY percentages are correctly computed as (current - prior) / prior x 100
**Plans**: 1 plan

Plans:
- [ ] 03-01-PLAN.md -- Standalone validation script comparing DriversEngine output vs direct DWH queries with PASS/FAIL per brand

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Integrity | 1/1 | Complete | 2026-03-10 |
| 2. Narrative and Visibility | 1/1 | Complete | 2026-03-10 |
| 3. Driver Data Verification | 0/1 | Not started | - |
