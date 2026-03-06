"""
Pilar 3: PY Operativa — Revenue Tree
Proyecta ventas como: Venta = Cobertura x Hit Rate x Drop Size
Cada componente se proyecta independientemente con WMA + estacionalidad.
"""

from .decomposition_engine import RevenueTreeEngine

__all__ = ['RevenueTreeEngine']
