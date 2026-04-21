"""
Configuracion del WSR Brand Owner (Pernod Ricard)

Reporte simplificado para Brand Owners en el exterior.
Filtrado por brandmanager = 'Pernod' en auto.dimarticulo.
Solo unidades C9L, sin BOB. Columnas renombradas a nomenclatura Brand Owner.
"""

# =============================================================================
# FUENTE DE MARCAS
# =============================================================================

# DimArticulo en el DWH — fuente autoritativa de marcas Pernod
DIMARTICULO_TABLE = 'auto.dimarticulo'
DIMARTICULO_BRAND_COL = 'marcadir'       # columna de marca (no marcadirectorio)
DIMARTICULO_FILTER_COL = 'brandmanager'   # columna de filtro
DIMARTICULO_FILTER_VALUE = 'PERNOD'       # valor del filtro

# Marcas excluidas (genericas o catch-all)
EXCLUDED_BRANDS = ('NINGUNA', 'SIN MARCA ASIGNADA', 'RESTO')

# Schema donde estan las tablas de ventas (auto-detectado)
# El WSR actual usa 'auto' como schema en el DWH
VENTAS_SCHEMA = 'auto'


# =============================================================================
# MAPEO DE COLUMNAS — Performance por Marca / Canal
# =============================================================================

# Columnas DataFrame → Header Brand Owner
# Orden: como aparecen de izquierda a derecha en la tabla
COLUMN_MAP = {
    'vendido_prev_c9l':   'LY',
    'sop_c9l':            'Mensual',
    'avance_c9l':         'MTD',
    'py_c9l':             'PY GRCs',
    'py_sistema_c9l':     'Auto PY',
    'spread_c9l':         'Spread',
    'py_vs_sop':          'GRCs/Mensual',
    'av_vs_sop':          'MTD/Mensual',
    'py_vs_ly':           'GRCs VS LY',
    'stock_c9l':          'Stock',
    'cobertura_dias':     'Cobertura (días)',
}

# Columnas que aparecen en la tabla (en orden)
MARCA_TABLE_COLUMNS = [
    'marca',
    'vendido_prev_c9l',
    'sop_c9l',
    'avance_c9l',
    'py_c9l',
    'py_sistema_c9l',
    'spread_c9l',
    'py_vs_sop',
    'av_vs_sop',
    'py_vs_ly',
    'stock_c9l',
    'cobertura_dias',
]

# Columnas ELIMINADAS respecto al WSR original:
# - Ppto General (presupuesto anual = concepto interno)
# - AV/PG (ratio vs presupuesto anual = interno)
# - IngNeto/C9L, %Inc/Dec Precio (analisis de precio = interno)
# - Toda tabla BOB


# =============================================================================
# SECCIONES DEL REPORTE
# =============================================================================

SECTIONS = {
    'resumen_ejecutivo':     True,
    'performance_marca':     True,   # C9L con drilldown subfamilia
    'comentarios_py':        True,   # Narrativa IA limitada a marcas Pernod
    'drivers_cobertura':     True,   # Solo Cobertura (cli padre) + trend
    'performance_canal':     True,   # C9L con apertura por marca
    'stock_cobertura':       True,

    'performance_ciudad':    True,   # Activado (Miguel lo confirmo)

    # Secciones EXCLUIDAS (KPIs de gestion / internos):
    'senales_cierre':        False,  # Proyeccion Nowcast — pendiente confirmar
    'hitrate_eficiencia':    False,  # Explicitamente excluido
}


# =============================================================================
# REPORTE
# =============================================================================

REPORT_TITLE = 'WEEKLY SALES REPORT - DYM'
REPORT_SUBTITLE = 'PERNOD RICARD'
REPORT_VERSION = '1.0'
REPORT_FILENAME_PREFIX = 'WSR_PERNOD'  # WSR_PERNOD_2026_04_TIMESTAMP.html


# =============================================================================
# KPIs DEL RESUMEN EJECUTIVO (en C9L)
# =============================================================================

# KPIs que se muestran en el resumen ejecutivo del Brand Owner
# Todos en C9L, sin BOB
EXECUTIVE_KPIS = [
    'mtd_c9l',            # Avance actual en C9L
    'cumpl_mensual',      # % cumplimiento vs SOP (Mensual)
    'py_grcs',            # Proyeccion cierre en C9L
    'grcs_vs_ly',         # Proyeccion vs ano anterior
    'avance_mensual',     # Dias laborales avanzados
]

# KPIs ELIMINADOS respecto al WSR original:
# - PY VS AVANCE (concepto interno)
# - PY VS PPTO GENERAL (presupuesto anual = interno)
# - PRESUPUESTO GENERAL (interno)
