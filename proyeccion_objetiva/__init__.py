"""
Módulo de Proyección Objetiva para el WSR de DYM
Implementa tres pilares de proyección:
  1. PY Gerente (existente) - Juicio de gerentes regionales
  2. PY Estadística (nuevo) - Holt-Winters sobre ventas históricas
  3. PY Operativa (nuevo) - Cobertura × Hit Rate × Drop Size
"""

from .projection_processor import ProjectionProcessor

__all__ = ['ProjectionProcessor']
