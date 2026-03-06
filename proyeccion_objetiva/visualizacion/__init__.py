"""
Visualización: Generación de HTML y gráficos para la sección
de Proyección Objetiva del WSR.
"""

from .projection_html_generator import ProjectionHTMLGenerator, get_projection_css
from .projection_chart_generator import ProjectionChartGenerator

__all__ = ['ProjectionHTMLGenerator', 'ProjectionChartGenerator', 'get_projection_css']
