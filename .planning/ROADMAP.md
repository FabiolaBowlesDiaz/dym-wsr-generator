# Roadmap: WSR DYM Ajustes

## Overview

Fix data integrity issues in the Section 4 chart (PY Gerente and SOP values diverge from the summary table), then clean up narrative rendering and hide the accuracy section. Two phases: trust the numbers first, then polish the presentation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2): Planned milestone work
- Decimal phases (1.1, etc.): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Data Integrity** - Chart Section 4 matches summary table for PY Gerente and SOP (source: marca_totales)
- [ ] **Phase 2: Narrative and Visibility** - Regional comments render as HTML, terminology is commercial-friendly, accuracy section hidden

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
  2. The narrative text uses "productos" instead of "SKUs" and "referencias/presentaciones" instead of "lenguas"
  3. The Accuracy de la proyeccion comercial section does not appear in the generated HTML output
  4. The accuracy section code remains in the codebase (not deleted), controllable via a config flag
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md -- Fix bold rendering, add terminology rules to LLM prompts, hide accuracy section via config flag

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Integrity | 1/1 | Complete | 2026-03-10 |
| 2. Narrative and Visibility | 0/1 | Not started | - |
