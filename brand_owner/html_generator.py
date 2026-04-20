"""
Generador HTML para el WSR Brand Owner (Pernod Ricard).

Estructura simplificada: solo C9L, sin BOB, sin KPIs de gestion.
Reutiliza el CSS del WSR principal con ajustes menores para tablas Brand Owner.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from utils.business_days import BusinessDaysCalculator

logger = logging.getLogger(__name__)


class BrandOwnerHTMLGenerator:
    """Generador HTML para el reporte Brand Owner"""

    def __init__(self, current_date: datetime):
        self.current_date = current_date
        self.current_year = current_date.year
        self.current_month = current_date.month
        self.current_day = current_date.day
        self.previous_year = self.current_year - 1

        self.meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }

        # Semana calendario (Lunes-Domingo)
        from calendar import monthrange
        from datetime import date
        first_day = date(self.current_year, self.current_month, 1)
        first_weekday = first_day.weekday()
        if first_weekday == 6:
            end_first = 1
        else:
            end_first = min(1 + (6 - first_weekday), monthrange(self.current_year, self.current_month)[1])

        week = 1
        if self.current_day > end_first:
            week = 2 + (self.current_day - end_first - 1) // 7
        self.current_week = min(week, 5)

    def format_number(self, value, decimals=2, is_percentage=False, show_plus=False):
        """Formatear numeros para el reporte"""
        import pandas as pd
        import numpy as np

        if pd.isna(value) or value is None:
            return "N/D"
        if np.isinf(value):
            return "N/D"
        if is_percentage:
            pct = value * 100
            sign = "+" if show_plus and pct > 0 else ""
            return f"{sign}{pct:.2f}%"
        if decimals == 0:
            return f"{int(round(value)):,}"
        return f"{value:,.{decimals}f}"

    def generate_complete_report(self,
                                  marcas_df,
                                  canales_df,
                                  summary_data: Dict,
                                  comentarios_analysis: str,
                                  marca_tables_html: str,
                                  canal_tables_html: str,
                                  stock_html: str,
                                  comentarios_py_html: str = "") -> str:
        """Generar el HTML completo del reporte Brand Owner"""

        mes = self.meses[self.current_month]

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Sales Report - DYM | Pernod Ricard - {mes} {self.current_year}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <h1>WEEKLY SALES REPORT - DYM</h1>
        <p style="text-align: center; color: #1e3a8a; font-size: 1.1em; font-weight: 600; margin-top: -5px;">PERNOD RICARD</p>
        <p style="text-align: center; color: #666; font-size: 0.9em; margin-top: -5px;">Version 1.0</p>
        <h2>Periodo: Semana {self.current_week} de {mes} {self.current_year}</h2>
        <h3>Fecha de generacion: {self.current_date.strftime('%d/%m/%Y')}</h3>

        <hr>

        {self._generate_resumen_ejecutivo(summary_data, comentarios_analysis)}

        <div class="section">
            <h2>1. PERFORMANCE POR MARCA</h2>
            {marca_tables_html}
        </div>

        {self._wrap_section("2. COMENTARIOS PY SISTEMA", comentarios_py_html) if comentarios_py_html else ""}

        <div class="section">
            <h2>3. PERFORMANCE POR CANAL</h2>
            {canal_tables_html}
        </div>

        <div class="section">
            <h2>4. ANALISIS DE STOCK Y COBERTURA</h2>
            {stock_html}
        </div>

        {self._generate_footer()}
    </div>
</body>
</html>"""
        return html

    def _wrap_section(self, title: str, content: str) -> str:
        """Envolver contenido en una seccion con titulo"""
        if not content:
            return ""
        return f"""
        <div class="section">
            <h2>{title}</h2>
            {content}
        </div>
        """

    def _generate_resumen_ejecutivo(self, summary_data: Dict, comentarios: str) -> str:
        """Generar resumen ejecutivo con KPIs en C9L"""

        d = summary_data
        avance = d.get('total_avance_c9l', 0)
        sop = d.get('total_sop_c9l', 0)
        py = d.get('total_py_c9l', 0)
        cumpl = d.get('cumpl_mensual', 0)
        py_mensual = d.get('py_vs_mensual', 0)
        py_ly = d.get('py_vs_ly', 0)
        dias_mes = d.get('dias_laborales_mes', 0)
        dias_av = d.get('dias_laborales_avance', 0)

        html = f"""
        <div class="executive-summary">
            <h2 style="text-align: center; margin-bottom: 30px;">RESUMEN EJECUTIVO</h2>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-title">MTD (AVANCE ACTUAL)</div>
                    <div class="kpi-value">{avance:,.0f}</div>
                    <div class="kpi-subtitle">C9L vendidos a la fecha</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-title">% VS MENSUAL</div>
                    <div class="kpi-value">{cumpl*100:.1f}%</div>
                    <div class="kpi-subtitle">{sop:,.0f} C9L objetivo mensual</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-title">PY GRCs (PROYECCION)</div>
                    <div class="kpi-value">{py:,.0f}</div>
                    <div class="kpi-subtitle">C9L estimados {self.meses[self.current_month].lower()}</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-title">GRCs VS LY</div>
                    <div class="kpi-value" style="color: {'#059669' if py_ly > 0 else '#dc2626' if py_ly < 0 else '#6b7280'};">{py_ly*100:+.1f}%</div>
                    <div class="kpi-subtitle">Proyeccion vs {self.previous_year}</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-title">GRCs/MENSUAL</div>
                    <div class="kpi-value" style="color: {'#059669' if py_mensual > 0 else '#dc2626' if py_mensual < 0 else '#6b7280'};">{py_mensual*100:+.1f}%</div>
                    <div class="kpi-subtitle">Proyeccion vs objetivo mensual</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-title">AVANCE MENSUAL</div>
                    <div class="kpi-value">{dias_av} dias</div>
                    <div class="kpi-subtitle">De {dias_mes} dias laborales</div>
                </div>
            </div>
        """

        # Comentarios de gerentes (narrativa IA)
        if comentarios:
            html += f"""
            <div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px; padding: 15px; margin: 20px 0;">
                <h4 style="color: #1e3a8a; margin-bottom: 15px;">
                    ANALISIS DE COMENTARIOS REGIONALES
                </h4>
                <div style="line-height: 1.6; color: #374151; font-size: 12px;">
                    {comentarios}
                </div>
            </div>
            """

        html += """
        </div>
        """
        return html

    def _generate_footer(self) -> str:
        """Notas metodologicas para Brand Owner"""
        return f"""
        <div class="footer">
            <h4>NOTAS METODOLOGICAS</h4>
            <ul>
                <li><strong>Alcance:</strong> Este reporte incluye exclusivamente marcas del portafolio Pernod Ricard distribuidas por DyM en Bolivia.</li>
                <li><strong>Unidades:</strong> Todas las cifras estan expresadas en C9L (Cajas de 9 Litros equivalentes).</li>
                <li><strong>LY:</strong> Ventas del mismo mes en {self.previous_year}.</li>
                <li><strong>Mensual:</strong> Objetivo mensual (SOP - Sales Operating Plan).</li>
                <li><strong>MTD:</strong> Month-to-Date — ventas acumuladas del mes hasta la fecha de corte.</li>
                <li><strong>PY GRCs:</strong> Proyeccion de cierre del mes en Gross Cases (C9L), basada en proyecciones de gerentes regionales + ventas reales cerradas.</li>
                <li><strong>Auto PY:</strong> Proyeccion automatica del sistema (Nowcast: modelo estadistico + ritmo actual de ventas).</li>
                <li><strong>Spread:</strong> Diferencia porcentual entre PY GRCs (gerente) y Auto PY (sistema).</li>
                <li><strong>Cobertura (cli padre):</strong> Cantidad de clientes padre unicos que compraron en el periodo (Distinctcount Cod. Cliente Padre).</li>
                <li><strong>Cobertura (dias):</strong> Dias de stock disponible = Stock / Venta Promedio Diaria.</li>
                <li><strong>Fecha de corte:</strong> {self.current_date.strftime('%d/%m/%Y')}. Los datos pueden actualizarse intra-dia.</li>
            </ul>
            <p style="margin-top: 10px; color: #9ca3af; font-size: 10px;">
                Generado automaticamente | WSR Brand Owner v1.0 | DyM Bolivia
            </p>
        </div>
        """

    def _get_css_styles(self) -> str:
        """CSS para el reporte Brand Owner — basado en el WSR principal"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; color: #333; background: #f5f5f5;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        h1 { color: #1e3a8a; text-align: center; font-size: 28px; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 3px solid #1e3a8a; }
        h2 { color: #1e3a8a; text-align: center; font-size: 18px; margin-bottom: 5px; }
        h3 { color: #666; text-align: center; font-size: 14px; margin-bottom: 20px; }
        hr { border: none; border-top: 2px solid #e5e7eb; margin: 20px 0; }
        .section { margin: 30px 0; }
        .section h2 { background: #f0f9ff; padding: 10px; margin-bottom: 20px; text-align: left; border-left: 4px solid #1e3a8a; }
        .section h3 { color: #1e3a8a; font-size: 16px; margin: 20px 0 10px 0; text-align: left; }
        .executive-summary { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }
        .kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px; text-align: center; }
        .kpi-title { font-size: 10px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
        .kpi-value { font-size: 20px; font-weight: bold; color: #1e3a8a; margin-bottom: 4px; line-height: 1; }
        .kpi-subtitle { font-size: 10px; color: #9ca3af; line-height: 1.2; }
        .table-container { overflow-x: auto; margin: 15px 0; border: 1px solid #e5e7eb; border-radius: 6px; background: white; }
        table { width: 100%; min-width: 900px; border-collapse: collapse; margin: 0; font-size: 12px; }
        th { background: #1e3a8a; color: white; padding: 8px 6px; text-align: right; font-weight: 500; white-space: nowrap; min-width: 75px; font-size: 11px; border-right: 1px solid #2563eb; }
        th:first-child { text-align: left; position: sticky; left: 0; z-index: 10; min-width: 120px; max-width: 150px; }
        td { padding: 6px 6px; border-bottom: 1px solid #e5e7eb; border-right: 1px solid #f3f4f6; text-align: right; white-space: nowrap; min-width: 75px; }
        td:first-child { text-align: left; font-weight: 500; position: sticky; left: 0; background: #f8fafc; z-index: 9; min-width: 120px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; }
        tr:hover { background: #f9fafb; }
        tr.total-row { background: #f0f9ff !important; font-weight: bold; border-top: 2px solid #1e3a8a; }
        tr.total-row td { padding: 8px 5px; border-bottom: 2px solid #1e3a8a; }

        /* Frozen columns for drilldown tables */
        #tabla-bo-marca th:nth-child(1), #tabla-bo-canal th:nth-child(1) {
            position: sticky; left: 0; z-index: 11; background: #1e3a8a; width: 30px; min-width: 30px; max-width: 30px; text-align: center; border-right: 2px solid #2563eb;
        }
        #tabla-bo-marca th:nth-child(2), #tabla-bo-canal th:nth-child(2) {
            position: sticky; left: 30px; z-index: 11; background: #1e3a8a; text-align: left; min-width: 160px; max-width: 200px; border-right: 2px solid #2563eb;
        }
        #tabla-bo-marca td:nth-child(1), #tabla-bo-canal td:nth-child(1) {
            position: sticky; left: 0; z-index: 10; background: white; width: 30px; min-width: 30px; max-width: 30px; text-align: center; border-right: 1px solid #e5e7eb;
        }
        #tabla-bo-marca td:nth-child(2), #tabla-bo-canal td:nth-child(2) {
            position: sticky; left: 30px; z-index: 10; background: white; text-align: left; font-weight: 500; min-width: 160px; max-width: 200px; border-right: 1px solid #e5e7eb;
        }
        #tabla-bo-marca tr.subfamilia-row td:nth-child(1), #tabla-bo-marca tr.subfamilia-row td:nth-child(2),
        #tabla-bo-canal tr.subfamilia-row td:nth-child(1), #tabla-bo-canal tr.subfamilia-row td:nth-child(2) { background: #f8fafc; }
        #tabla-bo-marca tr.total-row td:nth-child(1), #tabla-bo-marca tr.total-row td:nth-child(2),
        #tabla-bo-canal tr.total-row td:nth-child(1), #tabla-bo-canal tr.total-row td:nth-child(2) { background: #f0f9ff; }

        .positive { color: #059669; }
        .negative { color: #dc2626; }
        .neutral { color: #6b7280; }
        .expand-cell { cursor: pointer; text-align: center !important; }
        .expand-icon { font-family: monospace; font-size: 14px; color: #1e3a8a; cursor: pointer; user-select: none; }
        .subfamilia-indent { color: #6b7280; font-size: 11px; padding-left: 8px !important; }
        .marca-nombre { font-weight: 600 !important; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 2px solid #e5e7eb; font-size: 11px; color: #6b7280; }
        .footer h4 { color: #4b5563; margin-bottom: 10px; }
        .footer ul { margin-left: 20px; }
        .footer li { margin: 5px 0; }
        @media print {
            body { background: white; }
            .container { box-shadow: none; max-width: 100%; }
            .section { page-break-inside: avoid; }
            table { font-size: 10px; }
        }
        """
