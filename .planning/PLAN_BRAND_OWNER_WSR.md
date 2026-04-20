# Plan de Implementacion: WSR Brand Owner (Pernod)

**Fecha**: 2026-04-14
**Objetivo**: Crear un reporte WSR paralelo, simplificado, destinado a Brand Owners en el exterior (Pernod Ricard), que reutilice la infraestructura del WSR actual sin modificarlo.
**Solicitante**: Miguel A. Rengel E. (con copia a Gonzalo Abastoflor - Brand Manager D&M)

---

## 0. Arquitectura General

```
aa_v3_dym_wsr_proyecto_2209_sia/
├── wsr_generator_main.py              ← INTOCADO (produccion)
├── wsr_brand_owner_main.py            ← NUEVO: orquestador Brand Owner
├── core/                              ← COMPARTIDO (cambio minimo)
│   ├── database.py                    ← +3 metodos nuevos (canal_marca)
│   ├── data_processor.py              ← sin cambios
│   ├── html_generator.py              ← sin cambios
│   └── trend_chart_generator.py       ← sin cambios
├── brand_owner/                       ← NUEVO modulo completo
│   ├── __init__.py
│   ├── config.py                      ← Marcas Pernod, mapeo columnas, secciones
│   ├── data_filter.py                 ← Filtrado + re-agregacion de DataFrames
│   ├── html_generator.py              ← Estructura HTML simplificada
│   ├── html_tables.py                 ← Tablas C9L con nombres Brand Owner
│   └── summary_builder.py            ← Resumen ejecutivo C9L
├── utils/                             ← COMPARTIDO (sin cambios)
├── proyeccion_objetiva/               ← COMPARTIDO (cambio minimo en drivers)
└── output/                            ← Ambos reportes escriben aqui
```

### Principio: Proteger produccion

| Componente | Estrategia |
|------------|-----------|
| database.py | Solo AGREGAR metodos nuevos. Nunca modificar existentes |
| data_processor.py | Reusar tal cual. Filtrar ANTES de pasar datos |
| html_tables.py (existente) | No tocar. Crear version simplificada en brand_owner/ |
| html_generator.py (existente) | No tocar. Crear version nueva en brand_owner/ |
| proyeccion_objetiva/ | Solo agregar param `brand_filter` al DriversEngine |

---

## Decisiones confirmadas (2026-04-14)

| Pregunta | Decision | Razon |
|----------|---------|-------|
| Narrativa IA vs crudos | **Narrativa IA siempre** | Reporte externo requiere presentacion profesional |
| DimArticulo vs config | **DimArticulo obligatorio** | Miguel lo pide explicitamente. Query dinamica al DWH |
| Idioma headers columnas | **Tal cual pide Miguel** | LY, MTD, PY GRCs, Auto PY, etc. (mezcla ingles/espanol) |
| Idioma resto del reporte | **Espanol** (como WSR actual) | Ajustable despues si lo piden |
| Performance por Ciudad | **TBD** — preguntar a Miguel | No mencionada en el correo |
| Trend Chart | **TBD** — preguntar a Miguel | No mencionado en el correo |

---

## 1. Filtro de marcas: DimArticulo.brandmanager = 'Pernod'

La tabla `DimArticulo` NO es referenciada en ningun query actual (51 metodos en database.py).
Las queries actuales solo usan `marcadir` / `marcadirectorio` / `nombre_marca` como columna de marca.

### Solucion: Query obligatoria a DimArticulo + fallback de emergencia

**Paso 1**: Ejecutar query exploratoria en el DWH para verificar esquema de DimArticulo:
```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'dym_stg'
  AND (table_name ILIKE '%dim%articulo%' OR column_name ILIKE '%brandmanager%')
ORDER BY table_name, ordinal_position;
```

**Paso 2**: Agregar metodo `get_pernod_brands()` a database.py:
```sql
SELECT DISTINCT UPPER(marcadirectorio) as marcadir
FROM {schema}.DimArticulo
WHERE UPPER(brandmanager) = 'PERNOD'
  AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
```
Esto garantiza que la lista de marcas siempre este actualizada con el DWH.

**Paso 3**: Filtro adicional — excluir marcas sin ventas en los ultimos 12 meses:
```python
# En data_filter.py
marcas_con_venta = df_ventas_historicas[
    df_ventas_historicas[f'vendido_{prev_year}_c9l'] > 0
]['marcadir'].unique()
pernod_activas = [m for m in pernod_brands if m in marcas_con_venta]
```

**Fallback de emergencia**: Si DimArticulo no responde o no tiene datos,
el sistema logea un WARNING y aborta (no genera reporte con marcas incorrectas).

---

## 2. Problema de Datos: Ciudad y Canal requieren re-agregacion

### Situacion actual
- `get_ventas_historicas_ciudad()` suma TODAS las marcas por ciudad
- `get_ventas_historicas_canal()` suma TODAS las marcas por canal
- Para Brand Owner, necesitamos totales de SOLO marcas Pernod

### Solucion por dimension

| Dimension | Datos existentes en DB | Estrategia Brand Owner |
|-----------|----------------------|----------------------|
| **Marca** | get_*_marca() → filtrar por Pernod | DataFrame filter directo |
| **Subfamilia** | get_*_marca_subfamilia() → filtrar | DataFrame filter directo |
| **Ciudad** | get_*_ciudad_marca() existe (7 metodos) | Filtrar ciudad_marca → agregar por ciudad |
| **Canal** | get_*_canal_marca() **NO EXISTE** | **Agregar 5 metodos nuevos a database.py** |

### Metodos nuevos necesarios en database.py

```python
# ---- CANAL × MARCA (5 metodos nuevos) ----
def get_ventas_historicas_canal_marca(self, year, month):
    """Ventas por canal+marca. Fuente: td_ventas_bob_historico"""

def get_avance_actual_canal_marca(self, year, month, day):
    """Avance por canal+marca. Fuente: td_ventas_bob_historico"""

def get_presupuesto_general_canal_marca(self, year, month):
    """Ppto por canal+marca. Fuente: factpresupuesto_general"""

def get_sop_canal_marca(self, year, month):
    """SOP por canal+marca. Fuente: factpresupuesto_mensual"""

def get_stock_canal_marca(self):
    """Stock por canal+marca. Fuente: td_stock_sap"""
    # NOTA: td_stock_sap tiene columna 'canal'? Verificar.
    # Si no, omitir stock en canal drilldown.
```

**Patron SQL**: Identico a los metodos ciudad_marca existentes (lineas 1152-1257),
reemplazando `ciudad` por `canal` en GROUP BY.

---

## 3. Mapeo de Columnas (config.py)

### Tabla Performance por Marca

| Columna interna (DataFrame) | Header actual WSR | Header Brand Owner | Incluir? |
|----------------------------|-------------------|-------------------|----------|
| `vendido_{prev_year}_c9l` | Vendido {PREV_YEAR} (C9L) | **LY** | SI |
| `ppto_general_c9l` | Ppto General (C9L) | — | **NO** (quitar) |
| `sop_c9l` | SOP (C9L) | **Mensual** | SI |
| `avance_{year}_c9l` | Avance {CURR_YEAR} (C9L) | **MTD** | SI |
| `py_{year}_c9l` | PY {CURR_YEAR} (C9L) | **PY GRCs** | SI |
| `py_sistema_c9l` | PY Sistema | **Auto PY** | SI |
| `spread_sistema_c9l` | Spread | **Spread** | SI (mantener) |
| — | AV/PG | — | **NO** (quitar — PG es internal) |
| calc: `(py/sop)-1` | PY/SOP | **GRCs/Mensual** | SI |
| calc: `(av/sop)-1` | AV/SOP | **MTD/Mensual** | SI |
| calc: `(py/vendido)-1` | PY/V | **GRCs VS LY** | SI |
| `stock_c9l` | Stock (C9L) | **Stock** | SI |
| calc: `stock/vpd` | Cobertura (dias) | **Cobertura (dias)** | SI |

### Columnas ELIMINADAS (KPIs internos / BOB)

- Toda tabla BOB completa (no se genera)
- Ppto General (presupuesto anual es concepto interno)
- AV/PG (ratio vs presupuesto anual — interno)
- IngNeto/C9L, %Inc/Dec Precio (analisis de precio — interno)
- Eficiencia, Hit Rate, Base de clientes, Portafolio (KPIs de gestion)

### Config en Python

```python
# brand_owner/config.py

COLUMN_MAP = {
    # DataFrame column → Display header
    'vendido_prev_c9l': 'LY',
    'sop_c9l': 'Mensual',
    'avance_c9l': 'MTD',
    'py_c9l': 'PY GRCs',
    'py_sistema_c9l': 'Auto PY',
    'spread_c9l': 'Spread',
    'py_vs_sop': 'GRCs/Mensual',
    'av_vs_sop': 'MTD/Mensual',
    'py_vs_ly': 'GRCs VS LY',
    'stock_c9l': 'Stock',
    'cobertura_dias': 'Cobertura (dias)',
}

# Columnas en orden de aparicion en la tabla
MARCA_TABLE_COLUMNS = [
    'marca', 'vendido_prev_c9l', 'sop_c9l', 'avance_c9l',
    'py_c9l', 'py_sistema_c9l', 'spread_c9l',
    'py_vs_sop', 'av_vs_sop', 'py_vs_ly',
    'stock_c9l', 'cobertura_dias',
]

# Secciones del reporte
SECTIONS = {
    'resumen_ejecutivo': True,
    'performance_marca': True,
    'comentarios_py': True,
    'drivers_cobertura': True,   # Solo cobertura, no HR/DS/Efectividad
    'performance_canal': True,    # Con apertura por marca
    'stock_cobertura': True,
    # Secciones EXCLUIDAS:
    'performance_ciudad': False,  # No mencionada por Miguel → incluir? TBD
    'trend_chart': False,         # No mencionado
    'proyeccion_objetiva': False, # No mencionado
    'hitrate_eficiencia': False,  # Explicitamente excluido (KPI gestion)
}
```

---

## 4. Fases de Implementacion

### FASE 1: Fundacion y Configuracion
**Archivos**: `brand_owner/__init__.py`, `brand_owner/config.py`
**Dependencias**: Ninguna
**Riesgo**: Bajo

Tareas:
1. Crear directorio `brand_owner/`
2. Crear `brand_owner/__init__.py`
3. Crear `brand_owner/config.py` con:
   - Query de descubrimiento DimArticulo (ejecutar manualmente primero)
   - Lista PERNOD_BRANDS (hardcoded como fallback)
   - COLUMN_MAP (mapeo completo de columnas)
   - SECTIONS dict (toggles de secciones)
   - Constantes: titulo reporte, version, formato output

### FASE 2: Capa de Datos
**Archivos**: `brand_owner/data_filter.py`, `core/database.py` (+3-5 metodos)
**Dependencias**: Fase 1
**Riesgo**: Medio (toca database.py, pero solo agrega)

Tareas:
1. Verificar existencia de DimArticulo en DWH (query exploratoria)
2. Agregar a `database.py`:
   - `get_pernod_brands()` — si DimArticulo existe
   - `get_ventas_historicas_canal_marca()` — ventas canal×marca
   - `get_avance_actual_canal_marca()` — avance canal×marca
   - `get_sop_canal_marca()` — SOP canal×marca
   - (Ppto General y Stock canal×marca solo si las tablas lo soportan)
3. Crear `brand_owner/data_filter.py`:
   - `filter_by_pernod(df, brand_col='marcadir')` — filtro generico
   - `exclude_inactive_brands(df, ventas_df, prev_year)` — sin ventas 12m
   - `reaggregate_by_dimension(df_detail, group_col)` — re-agregar ciudad_marca→ciudad
   - `build_ciudad_from_ciudad_marca(data_ciudad_marca, pernod_brands)` — pipeline completo
   - `build_canal_from_canal_marca(data_canal_marca, pernod_brands)` — pipeline completo

### FASE 3: Presentacion — Tablas C9L
**Archivos**: `brand_owner/html_tables.py`
**Dependencias**: Fase 1 (config), Fase 2 (datos filtrados)
**Riesgo**: Bajo (archivo nuevo, no toca nada existente)

Tareas:
1. Crear `brand_owner/html_tables.py` con clase `BrandOwnerTableGenerator`:
   - `generate_marca_tables(df, estructura, narrative_html, drivers_data)` — entry point
   - `_generate_marca_performance(df)` — tabla C9L con headers renombrados
   - `_generate_marca_performance_drilldown(estructura)` — con subfamilias
   - `_generate_marca_semanal(df)` — tabla semanal (solo C9L)
   - `_generate_canal_performance(df)` — tabla canal con headers Brand Owner
   - `_generate_canal_marca_drilldown(estructura_canal)` — canal→marca drilldown
   - `_generate_canal_semanal(df)` — semanal por canal
   - `_generate_drivers_cobertura(drivers_data, narrative_html)` — SOLO cobertura
   - `_generate_stock_table(df)` — stock y cobertura simplificado

2. Cada metodo:
   - Usa COLUMN_MAP para headers
   - Solo columnas C9L (nunca BOB)
   - Formato numerico: enteros para C9L, 1 decimal para ratios
   - Colores consistentes con WSR actual (#1e3a8a, etc.)

### Detalle: Tabla Performance por Marca (C9L renombrada)

```
┌──────────┬──────┬─────────┬───────┬──────────┬─────────┬────────┬──────────────┬──────────────┬────────────┬───────┬──────────────────┐
│ Marca    │  LY  │ Mensual │  MTD  │ PY GRCs  │ Auto PY │ Spread │ GRCs/Mensual │ MTD/Mensual  │ GRCs VS LY │ Stock │ Cobertura (dias) │
├──────────┼──────┼─────────┼───────┼──────────┼─────────┼────────┼──────────────┼──────────────┼────────────┼───────┼──────────────────┤
│ ABSOLUT  │ 450  │   520   │  380  │   510    │   495   │  +3%   │    -1.9%     │   -26.9%     │   +13.3%   │  620  │       22         │
│ ├ 750ml  │ 300  │   340   │  250  │   335    │    —    │   —    │     —        │   -26.5%     │   +11.7%   │  410  │       23         │
│ └ 1000ml │ 150  │   180   │  130  │   175    │    —    │   —    │     —        │   -27.8%     │   +16.7%   │  210  │       21         │
├──────────┼──────┼─────────┼───────┼──────────┼─────────┼────────┼──────────────┼──────────────┼────────────┼───────┼──────────────────┤
│ TOTAL    │ 2100 │  2400   │ 1750  │   2350   │  2300   │  +2%   │    -2.1%     │   -27.1%     │   +11.9%   │ 3200  │       25         │
└──────────┴──────┴─────────┴───────┴──────────┴─────────┴────────┴──────────────┴──────────────┴────────────┴───────┴──────────────────┘
```

### Detalle: Tabla Drivers (Solo Cobertura)

```
┌──────────┬──────────────┬──────────┬─────────────────────────────────────┐
│ Marca    │ Cobertura    │ Δ VS LY  │ Comentario                          │
│          │ (cli padre)  │          │                                     │
├──────────┼──────────────┼──────────┼─────────────────────────────────────┤
│ ABSOLUT  │     850      │  +12.3%  │ Crecimiento sostenido en cobertura  │
│ CHIVAS   │     620      │   -4.2%  │ Contraccion en ciudades secundarias │
│ ...      │              │          │                                     │
└──────────┴──────────────┴──────────┴─────────────────────────────────────┘
```

### FASE 4: Presentacion — Estructura HTML
**Archivos**: `brand_owner/html_generator.py`, `brand_owner/summary_builder.py`
**Dependencias**: Fase 3
**Riesgo**: Bajo (archivos nuevos)

Tareas:
1. Crear `brand_owner/summary_builder.py`:
   - `build_summary_data(marcas_df, canales_df)` — KPIs en C9L
   - KPIs del Resumen Ejecutivo Brand Owner:
     - **MTD** (avance C9L total)
     - **% vs Mensual** (cumplimiento vs SOP en C9L)
     - **PY GRCs** (proyeccion cierre C9L)
     - **GRCs VS LY** (proyeccion vs ano anterior)
     - **Dias laborales** (avance del mes)
     - Quitar: PY VS AVANCE, PY VS PG (conceptos internos)

2. Crear `brand_owner/html_generator.py` con clase `BrandOwnerHTMLGenerator`:
   - `generate_complete_report(...)` — estructura simplificada:
     ```
     TITLE: "WEEKLY SALES REPORT - DYM | PERNOD RICARD"
     HEADER: Periodo, Fecha generacion
     
     RESUMEN EJECUTIVO
       - KPI grid (5-6 cards, C9L)
       - Comentarios gerentes (solo marcas Pernod)
     
     1. PERFORMANCE POR MARCA
       - Tabla C9L renombrada con drilldown subfamilia
       - Columnas: LY, Mensual, MTD, PY GRCs, Auto PY, Spread, GRCs/Mensual, MTD/Mensual, GRCs VS LY, Stock, Cobertura (dias)
       - Narrativa IA (PY Sistema / Señales) limitada a marcas Pernod
       - Drivers integrados: SOLO Cobertura (cli padre) + trend + comentario
       - Tabla semanal C9L
     
     2. COMENTARIOS PY SISTEMA
       - Mantener limitado a marcas Pernod
     
     3. PERFORMANCE POR CANAL
       - Tabla C9L renombrada con drilldown por marca (NUEVO)
       - Headers Brand Owner (mismos que Performance Marca)
       - Drivers integrados: SOLO Cobertura
       - Tabla semanal C9L
     
     4. ANALISIS DE STOCK Y COBERTURA
       - Tabla stock solo marcas Pernod
     
     FOOTER (notas metodologicas simplificadas)
     ```
   - `_get_css_styles()` — reutilizar CSS del WSR actual (copiar, no importar)
   - `_generate_resumen_ejecutivo(summary_data, comentarios)` — version C9L
   - `_generate_footer()` — notas metodologicas para Brand Owner

### FASE 5: Orquestador
**Archivos**: `wsr_brand_owner_main.py`
**Dependencias**: Fases 1-4
**Riesgo**: Bajo (archivo nuevo)

Tareas:
1. Crear clase `BrandOwnerWSRGenerator`:
   - `__init__()` — misma config DB, fecha, etc. que WSRGeneratorSystem
   - `run()` — pipeline completo:

```python
def run(self):
    # 1. Conectar a DB
    self.db_manager.connect()

    # 2. Obtener lista de marcas Pernod
    pernod_brands = self._get_pernod_brands()  # DimArticulo o config

    # 3. Fetch datos MARCA (reutiliza metodos existentes)
    marca_data = self._fetch_marca_data()
    marca_subfamilia_data = self._fetch_marca_subfamilia_data()

    # 4. FILTRAR por Pernod + excluir inactivas
    marca_data = filter_by_pernod(marca_data, pernod_brands)
    marca_subfamilia_data = filter_by_pernod(marca_subfamilia_data, pernod_brands)

    # 5. Fetch datos CIUDAD×MARCA → filtrar → re-agregar
    ciudad_marca_data = self._fetch_ciudad_marca_data()
    ciudad_data = build_ciudad_from_ciudad_marca(ciudad_marca_data, pernod_brands)

    # 6. Fetch datos CANAL×MARCA → filtrar → re-agregar
    canal_marca_data = self._fetch_canal_marca_data()
    canal_data = build_canal_from_canal_marca(canal_marca_data, pernod_brands)

    # 7. Consolidar via DataProcessor existente
    estructura_marca = self.data_processor.consolidate_marca_subfamilia_data(
        marca_data, marca_subfamilia_data)
    canales_df = self.data_processor.consolidate_canal_data(canal_data)

    # 8. Construir estructura canal→marca para drilldown
    estructura_canal = self._build_canal_marca_estructura(canal_marca_data, pernod_brands)

    # 9. Resumen ejecutivo (C9L)
    summary_data = build_summary_data(estructura_marca['marca_totales'], canales_df)

    # 10. Comentarios gerentes (filtrados)
    comentarios = self._fetch_and_filter_comentarios(pernod_brands)

    # 11. Drivers (solo cobertura)
    drivers_data = self._fetch_drivers(pernod_brands)

    # 12. Narrativa IA (opcional)
    narrative_html = self._generate_narrative(drivers_data, pernod_brands)

    # 13. Generar HTML
    html = self.html_generator.generate_complete_report(
        marcas_df=estructura_marca['marca_totales'],
        canales_df=canales_df,
        summary_data=summary_data,
        comentarios_analysis=comentarios,
        estructura_marca=estructura_marca,
        estructura_canal=estructura_canal,
        drivers_data=drivers_data,
        narrative_html=narrative_html,
    )

    # 14. Guardar
    self._save_report(html)  # WSR_PERNOD_2026_04_TIMESTAMP.html
```

### FASE 6: Integracion Drivers (Cobertura)
**Archivos**: `proyeccion_objetiva/pilar3_operativa/drivers_engine.py` (cambio minimo)
**Dependencias**: Fase 5
**Riesgo**: Bajo-Medio (modifica modulo compartido, pero solo agrega parametro)

Tareas:
1. Agregar parametro `brand_filter: List[str] = None` a `DriversEngine.calculate_all()`
2. Si `brand_filter` no es None, agregar WHERE clause:
   ```sql
   AND UPPER(marca) IN ({','.join(f"'{b}'" for b in brand_filter)})
   ```
3. En `brand_owner/html_tables.py`, `_generate_drivers_cobertura()`:
   - Recibir drivers_data del DriversEngine
   - Mostrar SOLO columna Cobertura + Trend + Comentario
   - Ignorar Efectividad, Hit Rate, Drop Size

### FASE 7: Testing y Polish
**Dependencias**: Fases 1-6
**Riesgo**: Bajo

Tareas:
1. Test end-to-end: `python wsr_brand_owner_main.py`
2. Verificar:
   - Solo marcas Pernod aparecen
   - Todas las columnas tienen nombres Brand Owner
   - No hay columnas BOB
   - Drivers solo muestra Cobertura
   - Canal tiene apertura por marca
   - Stock filtrado a Pernod
3. Verificar que `python wsr_generator_main.py` sigue funcionando (regresion)
4. Ajustar CSS/formato segun feedback del Brand Manager
5. Output: `output/WSR_PERNOD_{YEAR}_{MONTH}_{TIMESTAMP}.html`

---

## 5. Dependencias entre fases

```
FASE 1 (Config)
  │
  ├──→ FASE 2 (Data Layer)
  │      │
  │      ├──→ FASE 3 (Tablas HTML)
  │      │      │
  │      │      └──→ FASE 4 (HTML Generator)
  │      │             │
  │      │             └──→ FASE 5 (Orquestador)
  │      │                    │
  │      │                    └──→ FASE 6 (Drivers)
  │      │                           │
  │      │                           └──→ FASE 7 (Testing)
  │      │
  │      └──→ FASE 6 (Drivers — puede empezar en paralelo con Fase 3)
  │
  └──→ FASE 3 (puede empezar en paralelo con Fase 2 usando datos mock)
```

**Camino critico**: Fase 1 → Fase 2 → Fase 5 → Fase 7
**Fases paralelizables**: Fase 3 + Fase 4 pueden avanzar con datos mock mientras Fase 2 se completa

---

## 6. Estimacion de complejidad por archivo

| Archivo | Lineas estimadas | Complejidad | Notas |
|---------|-----------------|-------------|-------|
| `brand_owner/config.py` | ~80 | Baja | Constantes y mapeos |
| `brand_owner/data_filter.py` | ~150 | Media | Logica de filtrado y re-agregacion |
| `brand_owner/html_tables.py` | ~800 | Alta | Adaptado de html_tables.py (2300 → 800) |
| `brand_owner/html_generator.py` | ~400 | Media | Adaptado de html_generator.py (1169 → 400) |
| `brand_owner/summary_builder.py` | ~100 | Baja | KPIs C9L |
| `wsr_brand_owner_main.py` | ~500 | Media | Pipeline completo, similar a wsr_generator_main.py |
| `core/database.py` (cambios) | +~150 | Media | 3-5 metodos nuevos canal×marca |
| `drivers_engine.py` (cambios) | +~20 | Baja | Solo agregar parametro brand_filter |
| **Total nuevo** | **~2,200** | | vs 8,800 del WSR actual = 75% ahorro |

---

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| DimArticulo no existe en DWH | Media | Bajo | Fallback a lista hardcoded en config.py |
| td_stock_sap no tiene columna `canal` | Media | Bajo | Omitir stock en drilldown canal→marca |
| fact_ventas_detallado no tiene `brandmanager` | Alta | Bajo | Filtrar drivers por lista de marcas Pernod |
| Re-agregacion ciudad/canal pierde precision | Baja | Medio | Verificar que SUM(ciudad_marca) = ciudad original para marcas comunes |
| CSS del WSR actual cambia | Baja | Bajo | CSS copiado (no importado), evoluciona independientemente |
| DriversEngine brand_filter rompe WSR actual | Baja | Alto | Parametro opcional con default None = comportamiento actual |

---

## 8. Preguntas abiertas (para Miguel/Gonzalo)

### RESUELTAS
- ~~Narrativa IA vs crudos~~ → **Narrativa IA siempre** (reporte externo)
- ~~DimArticulo vs config~~ → **DimArticulo obligatorio** (query dinamica al DWH)
- ~~Idioma headers~~ → **Tal cual pide Miguel** (LY, MTD, GRCs = mezcla ingles/espanol)
- ~~Idioma resto~~ → **Espanol** (titulos, narrativas, notas = como WSR actual)
- ~~Trend Chart~~ → **No aplica** (ya fue removido del WSR actual)

### ESTADO REAL DEL WSR (verificado 14-abr-2026)
Secciones actuales: Resumen Ejecutivo, 1.Marca (con drivers integrados), 2.Ciudad (con drivers), 
3.Canal (con drivers), 4.Señales de Cierre (Nowcast/Proyeccion), 5.Stock, 6.Hit Rate.
Drivers estan DENTRO de cada seccion de Performance, no como seccion separada.
PY Sistema + Spread son columnas estandar en tablas BOB y C9L.

### PENDIENTES
1. **Performance por Ciudad**: Miguel no la menciona explicitamente. Se incluye?
2. **Seccion "Señales de Cierre"**: Es la proyeccion Nowcast con narrativa IA detallada. Auto PY ya aparece como columna — se necesita la seccion completa ademas?
3. **Frecuencia de generacion**: Semanal como el WSR actual?

---

## 9. Criterios de aceptacion (Definition of Done)

- [ ] `python wsr_brand_owner_main.py` genera HTML sin errores
- [ ] Solo aparecen marcas Pernod (verificable visualmente)
- [ ] No aparecen marcas sin ventas en 12 meses
- [ ] Todas las columnas usan nomenclatura Brand Owner (LY, MTD, GRCs, etc.)
- [ ] No hay columnas BOB en ninguna tabla
- [ ] No hay KPIs de gestion (eficiencia, hit rate, portafolio, base clientes)
- [ ] Drivers solo muestra Cobertura (cli padre) + tendencia + comentario
- [ ] Performance por Canal tiene apertura (drilldown) por Marca
- [ ] Stock limitado a marcas Pernod
- [ ] Comentarios de gerentes filtrados a marcas Pernod
- [ ] `python wsr_generator_main.py` sigue funcionando sin cambios (regresion)
- [ ] Output: `output/WSR_PERNOD_{YEAR}_{MONTH}_{TIMESTAMP}.html`
- [ ] Reporte se abre correctamente en navegador
