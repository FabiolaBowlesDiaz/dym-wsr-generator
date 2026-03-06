"""
Configuración y constantes para el módulo de Proyección Objetiva
"""

# === TABLAS DEL DWH ===
TABLE_VENTAS_HISTORICO = "td_ventas_bob_historico"
TABLE_FACT_VENTAS = "FactVentas"
TABLE_HITRATE = "fact_eficiencia_hitrate"
TABLE_PROYECCIONES = "fact_proyecciones"

# === FILTROS ESTÁNDAR (consistentes con el WSR existente) ===
EXCLUDED_CITIES = ("TURISMO",)
EXCLUDED_CHANNELS = ("TURISMO",)
EXCLUDED_BRANDS = ("NINGUNA", "SIN MARCA ASIGNADA")

# === MOTOR ESTADÍSTICO (Holt-Winters) ===
# Mínimo de meses para cada tipo de modelo
MIN_MONTHS_TRIPLE = 25   # Holt-Winters con estacionalidad (ideal: 2+ ciclos)
MIN_MONTHS_DOUBLE = 12   # Suavizado con tendencia, sin estacionalidad
MIN_MONTHS_MINIMUM = 12  # Por debajo de esto, retorna None

# Umbral de ceros: si >70% de la serie son ceros, no se modela
ZERO_THRESHOLD = 0.70

# Limpieza de outliers
OUTLIER_WINDOW = 5       # Ventana rolling para detección
OUTLIER_Z_THRESH = 2.5   # Umbral Z-score para outliers bajos

# Estacionalidad
SEASONAL_PERIOD = 12     # Meses en un ciclo estacional

# === MOTOR DE DESCOMPOSICIÓN OPERATIVA ===
# Pesos del promedio móvil ponderado (WMA) de 3 meses
WMA_WEIGHTS = [0.5, 0.3, 0.2]  # [más reciente, medio, más antiguo]

# === DIAGNÓSTICO DE SPREAD ===
# Spread = (PY_Gerente / PY_Estadística) - 1
SPREAD_OPTIMISTA_THRESHOLD = 0.10    # >+10% = Gerente optimista
SPREAD_CONSERVADOR_THRESHOLD = -0.10  # <-10% = Gerente conservador
SPREAD_CONSENSO_THRESHOLD = 0.05     # |spread| < 5% = Alto consenso

# === SANIDAD DE PROYECCIONES ===
# Las proyecciones deben estar entre estos factores vs mismo-mes-año-anterior
SANITY_MIN_FACTOR = 0.50  # Mínimo 50% del año anterior
SANITY_MAX_FACTOR = 2.00  # Máximo 200% del año anterior

# === COLORES PARA VISUALIZACIÓN ===
COLOR_PY_GERENTE = "#94A3B8"      # Gris azulado
COLOR_PY_ESTADISTICA = "#3B82F6"  # Azul
COLOR_PY_OPERATIVA = "#10B981"    # Verde
COLOR_TREND_UP = "#059669"        # Verde oscuro
COLOR_TREND_DOWN = "#DC2626"      # Rojo
COLOR_CONSENSUS_HIGH = "#ECFDF5"  # Verde claro (fondo)
COLOR_CONSENSUS_LOW = "#FFF7ED"   # Naranja claro (fondo)

# === AJUSTE POR EVENTOS MÓVILES ===
# Impacto estimado de eventos móviles en ventas de bebidas
# Estos factores representan el % de incremento/decremento que un evento
# genera sobre la venta mensual normal
EVENT_IMPACTS = {
    'carnaval': 0.15,        # +15% en el mes que cae Carnaval (2-3 días de fiesta masiva)
    'viernes_santo': -0.02,  # -2% leve baja (viaje/religión, menos consumo en bares)
    'corpus_christi': 0.0,   # Sin impacto medible (1 día, no afecta patrón de bebidas)
}

# Mapeo de mobile_holidays del BusinessDaysCalculator a nuestros event_ids
# Esto conecta los comentarios del calendario existente con nuestros impact IDs
EVENT_KEYWORDS = {
    'carnaval': 'carnaval',
    'viernes santo': 'viernes_santo',
    'corpus christi': 'corpus_christi',
}

# Años de training del modelo: usados para determinar si un evento
# es "nuevo" en el mes target o si "se fue"
# Se usa automáticamente de los datos, pero se puede overridear aquí
TRAINING_YEARS_LOOKBACK = 2  # Mirar últimos 2 años para determinar patrón

# === TIPO DE CAMBIO ===
TIPO_CAMBIO = 6.96  # BOB/USD (consistente con WSR)
