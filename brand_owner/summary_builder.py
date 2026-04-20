"""
Resumen Ejecutivo para el WSR Brand Owner.

KPIs en C9L (no BOB). Simplificado respecto al WSR interno:
sin Ppto General, sin PY vs PG, sin PY vs Avance.
"""

import logging
from typing import Dict
from utils.business_days import BusinessDaysCalculator

logger = logging.getLogger(__name__)


def build_summary_data(marcas_df, canales_df, current_date) -> Dict:
    """
    Construir datos del resumen ejecutivo para Brand Owner.

    Args:
        marcas_df: DataFrame consolidado de marcas Pernod (marca_totales)
        canales_df: DataFrame consolidado de canales (totales Pernod-only)
        current_date: datetime actual

    Returns:
        Dict con metricas para renderizar el resumen ejecutivo
    """
    year = current_date.year
    prev_year = year - 1
    month = current_date.month

    # Totales C9L
    avance_col = f'avance_{year}_c9l'
    vendido_col = f'vendido_{prev_year}_c9l'

    total_avance = marcas_df[avance_col].sum() if avance_col in marcas_df.columns else 0
    total_sop = marcas_df['sop_c9l'].sum() if 'sop_c9l' in marcas_df.columns else 0
    total_vendido = marcas_df[vendido_col].sum() if vendido_col in marcas_df.columns else 0

    # PY C9L: (avance_c9l * py_bob) / avance_bob
    avance_bob_col = f'avance_{year}_bob'
    py_bob_col = f'py_{year}_bob'
    total_avance_bob = marcas_df[avance_bob_col].sum() if avance_bob_col in marcas_df.columns else 0
    total_py_bob = marcas_df[py_bob_col].sum() if py_bob_col in marcas_df.columns else 0
    total_py = (total_avance * total_py_bob / total_avance_bob) if total_avance_bob > 0 else 0

    # Ratios
    cumpl_mensual = (total_avance / total_sop) if total_sop > 0 else 0
    py_vs_mensual = ((total_py / total_sop) - 1) if total_sop > 0 else 0
    py_vs_ly = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

    # Dias laborales
    calculator = BusinessDaysCalculator()
    dias_mes, dias_avance, pct_avance = calculator.calculate_business_days(current_date)

    # Venta diaria C9L
    vpd = (total_avance / dias_avance) if dias_avance > 0 else 0
    vpd_objetivo = (total_py / dias_mes) if dias_mes > 0 else 0

    return {
        'total_avance_c9l': total_avance,
        'total_sop_c9l': total_sop,
        'total_py_c9l': total_py,
        'total_vendido_ly_c9l': total_vendido,
        'cumpl_mensual': cumpl_mensual,
        'py_vs_mensual': py_vs_mensual,
        'py_vs_ly': py_vs_ly,
        'dias_laborales_mes': dias_mes,
        'dias_laborales_avance': dias_avance,
        'pct_avance': pct_avance,
        'vpd_c9l': vpd,
        'vpd_objetivo_c9l': vpd_objetivo,
    }
