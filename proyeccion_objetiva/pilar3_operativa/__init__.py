"""
Pilar 3: PY Operativa — Drivers de Performance (Revenue Tree)
Descompone ventas en: Venta = Cobertura x Hit Rate x Drop Size
Fuente: fact_ventas_detallado (DWH)
"""

from .drivers_engine import DriversEngine
from .drivers_narrative import DriversNarrativeGenerator

__all__ = ['DriversEngine', 'DriversNarrativeGenerator']
