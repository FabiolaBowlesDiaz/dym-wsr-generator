"""
Pilar 2: PY Estadística — Holt-Winters
Forecast basado en 24-36 meses de ventas históricas.
Captura nivel, tendencia y estacionalidad.
Incluye ajuste post-forecast por eventos móviles (Carnaval, Semana Santa).
"""

from .statistical_engine import StatisticalEngine

__all__ = ['StatisticalEngine']
