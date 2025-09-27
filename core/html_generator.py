"""
Módulo Generador HTML para WSR
Genera el reporte HTML completo con estilos y formato
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime
import logging
from utils.business_days import BusinessDaysCalculator

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Generador de HTML para el WSR"""
    
    def __init__(self, current_date: datetime):
        """
        Inicializar el generador HTML
        
        Args:
            current_date: Fecha actual para el reporte
        """
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
        
        # Calcular semana actual
        self.current_week = self._calculate_week(self.current_day)
        
    def _calculate_week(self, day: int) -> int:
        """Calcular en qué semana del mes estamos"""
        if day <= 7:
            return 1
        elif day <= 14:
            return 2
        elif day <= 21:
            return 3
        elif day <= 28:
            return 4
        else:
            return 5
    
    def format_number(self, value, decimals=2, is_percentage=False, show_plus=False):
        """Formatear números para el reporte"""
        if pd.isna(value) or value is None:
            return "N/D"

        if np.isinf(value):
            return "N/D"

        if is_percentage:
            percent_value = value * 100
            sign = "+" if show_plus and percent_value > 0 else ""
            return f"{sign}{percent_value:.2f}%"

        # Para decimales = 1, mostrar en millones
        if decimals == 1 and value >= 1000000:
            millions = value / 1000000
            return f"{millions:.1f}"

        if decimals == 0:
            formatted = f"{value:,.0f}"
        else:
            formatted = f"{value:,.{decimals}f}"

        if show_plus and value > 0:
            formatted = "+" + formatted

        return formatted

    def _generate_comments_analysis(self, raw_comments: str) -> str:
        """
        Generar análisis profesional de comentarios usando LLM

        Args:
            raw_comments: Comentarios sin procesar de los gerentes

        Returns:
            HTML con análisis profesional de comentarios
        """
        try:
            from utils.llm_processor import CommentProcessor, CommentFormatter

            # Inicializar el procesador de comentarios
            processor = CommentProcessor()

            # Construir contexto adicional para el LLM
            data_context = {
                'mes': self.meses[self.current_month],
                'año': self.current_year,
                'semana': self.current_week
            }

            # Procesar comentarios con LLM
            processed_comments = processor.process_comments(raw_comments, data_context)

            # Extraer insights clave
            insights = processor.extract_key_insights(processed_comments, None)

            # Formatear para HTML
            formatted_html = CommentFormatter.format_html_comments(processed_comments, insights)

            return formatted_html

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error procesando comentarios con LLM: {e}")

            # Fallback a presentación básica mejorada
            return f'''
            <div class="comments-section">
                <h4 style="color: #1e3a8a; margin-bottom: 15px;">
                    <span style="font-size: 18px;">💬</span> COMENTARIOS CLAVE DE GERENTES
                </h4>
                <div style="background: #f8fafc; padding: 15px; border-radius: 6px; border-left: 4px solid #3b82f6;">
                    <p style="line-height: 1.6; color: #374151; margin: 0;">
                        {raw_comments if raw_comments else "No hay comentarios disponibles para este período."}
                    </p>
                </div>
            </div>
            '''

    def get_kpi_status(self, value):
        """Obtener estado del KPI (emoji)"""
        if pd.isna(value) or np.isinf(value):
            return ""
        
        if value >= 0.95:
            return "🟢"
        elif value >= 0.85:
            return "🟡"
        else:
            return "🔴"
    
    def get_cobertura_status(self, dias):
        """Obtener estado de cobertura de stock"""
        if pd.isna(dias):
            return ("⚠️", "Sin datos")
        
        dias = float(dias)
        
        if dias == 0:
            return ("🔴", "Sin stock")
        elif dias < 15:
            return ("🔴", "Crítico")
        elif dias <= 30:
            return ("✅", "Óptimo")
        elif dias <= 60:
            return ("🟡", "Alto")
        else:
            return ("⚠️", "Exceso")
    
    def get_cobertura_recomendacion(self, dias):
        """Obtener recomendación según cobertura"""
        if pd.isna(dias):
            return "Verificar disponibilidad"
        
        dias = float(dias)
        
        if dias == 0:
            return "Reabastecer urgente"
        elif dias < 15:
            return "Reabastecer pronto"
        elif dias <= 30:
            return "Mantener nivel actual"
        elif dias <= 60:
            return "Monitorear rotación"
        else:
            return "Reducir inventario"
    
    def generate_complete_report(self,
                                marcas_df: pd.DataFrame,
                                ciudades_df: pd.DataFrame,
                                canales_df: pd.DataFrame,
                                summary_data: Dict,
                                comentarios_analysis: str,
                                hitrate_data: Dict = None,
                                trend_chart_html: str = "") -> str:
        """
        Generar el reporte HTML completo
        
        Args:
            marcas_df: DataFrame consolidado de marcas
            ciudades_df: DataFrame consolidado de ciudades
            canales_df: DataFrame consolidado de canales
            summary_data: Datos del resumen ejecutivo
            comentarios_analysis: Análisis de comentarios de gerentes
            
        Returns:
            String con el HTML completo del reporte
        """
        mes_nombre = self.meses[self.current_month]
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Sales Report - DYM - {mes_nombre} {self.current_year}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <h1>WEEKLY SALES REPORT - DYM</h1>
        <h2>Período: Semana {self.current_week} de {mes_nombre} {self.current_year}</h2>
        <h3>Fecha de generación: {self.current_date.strftime('%d/%m/%Y')}</h3>
        
        <hr>
        
        {self._generate_resumen_ejecutivo(summary_data, comentarios_analysis)}
        
        <div class="section">
            <h2>1. PERFORMANCE POR MARCA</h2>
            {self._generate_marca_tables(marcas_df)}
        </div>
        
        <div class="section">
            <h2>2. PERFORMANCE POR CIUDAD</h2>
            {self._generate_ciudad_tables(ciudades_df)}
        </div>
        
        <div class="section">
            <h2>3. PERFORMANCE POR CANAL</h2>
            {self._generate_canal_tables(canales_df)}
        </div>

        {trend_chart_html}

        <div class="section">
            <h2>4. ANÁLISIS DE STOCK Y COBERTURA</h2>
            {self._generate_stock_analysis(marcas_df)}
        </div>

        <div class="section">
            <h2>5. HIT RATE Y EFICIENCIA</h2>
            {self._generate_hitrate_section(hitrate_data) if hitrate_data else '<p>No hay datos de Hit Rate disponibles</p>'}
        </div>

        {self._generate_footer()}
    </div>
</body>
</html>"""
        
        return html
    
    def _get_css_styles(self) -> str:
        """Obtener estilos CSS para el reporte"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #1e3a8a;
            text-align: center;
            font-size: 28px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 3px solid #1e3a8a;
        }
        
        h2 {
            color: #1e3a8a;
            text-align: center;
            font-size: 18px;
            margin-bottom: 5px;
        }
        
        h3 {
            color: #666;
            text-align: center;
            font-size: 14px;
            margin-bottom: 20px;
        }
        
        hr {
            border: none;
            border-top: 2px solid #e5e7eb;
            margin: 20px 0;
        }
        
        .section {
            margin: 30px 0;
        }
        
        .section h2 {
            background: #f0f9ff;
            padding: 10px;
            margin-bottom: 20px;
            text-align: left;
            border-left: 4px solid #1e3a8a;
        }
        
        .section h3 {
            color: #1e3a8a;
            font-size: 16px;
            margin: 20px 0 10px 0;
            text-align: left;
        }
        
        .executive-summary {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin: 20px 0;
        }

        .kpi-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }
        
        .kpi-card .label {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
        }
        
        .kpi-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #1e3a8a;
        }
        
        .kpi-card .status {
            font-size: 14px;
            margin-top: 5px;
        }

        .kpi-icon {
            font-size: 18px;
            margin-bottom: 5px;
        }

        .kpi-title {
            font-size: 10px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }

        .kpi-value {
            font-size: 20px;
            font-weight: bold;
            color: #1e3a8a;
            margin-bottom: 4px;
            line-height: 1;
        }

        .kpi-subtitle {
            font-size: 10px;
            color: #9ca3af;
            line-height: 1.2;
        }
        
        .comments-section {
            background: #fffbeb;
            border: 1px solid #fcd34d;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }
        
        .comments-section h4 {
            color: #92400e;
            margin-bottom: 10px;
        }
        
        .table-container {
            overflow-x: auto;
            margin: 15px 0;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: white;
        }

        table {
            width: 100%;
            min-width: 1200px;
            border-collapse: collapse;
            margin: 0;
            font-size: 12px;
        }
        
        th {
            background: #1e3a8a;
            color: white;
            padding: 8px 6px;
            text-align: right;
            font-weight: 500;
            white-space: nowrap;
            min-width: 85px;
            font-size: 11px;
            border-right: 1px solid #2563eb;
        }

        th:first-child {
            text-align: left;
            position: sticky;
            left: 0;
            z-index: 10;
            min-width: 120px;
            max-width: 150px;
        }

        td {
            padding: 6px 6px;
            border-bottom: 1px solid #e5e7eb;
            border-right: 1px solid #f3f4f6;
            text-align: right;
            white-space: nowrap;
            min-width: 85px;
        }

        td:first-child {
            text-align: left;
            font-weight: 500;
            position: sticky;
            left: 0;
            background: #f8fafc;
            z-index: 9;
            min-width: 120px;
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        tr:hover {
            background: #f9fafb;
        }
        
        tr.total-row {
            background: #f0f9ff !important;
            font-weight: bold;
            border-top: 2px solid #1e3a8a;
        }
        
        tr.total-row td {
            padding: 8px 5px;
            border-bottom: 2px solid #1e3a8a;
        }
        
        .positive {
            color: #059669;
        }
        
        .negative {
            color: #dc2626;
        }
        
        .neutral {
            color: #6b7280;
        }
        
        .metrics-table {
            background: #f9fafb;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            font-size: 11px;
            color: #6b7280;
        }
        
        .footer h4 {
            color: #4b5563;
            margin-bottom: 10px;
        }
        
        .footer ul {
            margin-left: 20px;
        }
        
        .footer li {
            margin: 5px 0;
        }
        
        @media print {
            body {
                background: white;
            }
            
            .container {
                box-shadow: none;
                max-width: 100%;
            }
            
            .section {
                page-break-inside: avoid;
            }
            
            h2 {
                page-break-after: avoid;
            }
            
            table {
                font-size: 10px;
            }
        }
        """
    
    def _generate_resumen_ejecutivo(self, summary_data: Dict, comentarios: str) -> str:
        """Generar sección de resumen ejecutivo"""

        # Calcular métricas de avance dinámicamente
        calculator = BusinessDaysCalculator()
        dias_laborales_mes, dias_laborales_avance, porcentaje_avance = calculator.calculate_business_days(self.current_date)
        
        total_avance = summary_data.get('total_avance', 0)
        total_sop = summary_data.get('total_sop', 0)
        total_ppto = summary_data.get('total_ppto_general', 0)
        total_py = summary_data.get('total_py', 0)
        
        av_sop = summary_data.get('av_sop', 0)
        av_pg = summary_data.get('av_pg', 0)
        
        # Calcular cumplimientos
        cumpl_sop = (total_avance / total_sop * 100) if total_sop > 0 else 0
        cumpl_pg = (total_avance / total_ppto * 100) if total_ppto > 0 else 0
        py_vs_avance = ((total_py / total_avance - 1) * 100) if total_avance > 0 else 0
        py_vs_sop = ((total_py / total_sop - 1) * 100) if total_sop > 0 else 0
        py_vs_pg = ((total_py / total_ppto - 1) * 100) if total_ppto > 0 else 0
        
        venta_diaria_promedio = total_avance / dias_laborales_avance if dias_laborales_avance > 0 else 0
        venta_diaria_objetivo = total_py / dias_laborales_mes if dias_laborales_mes > 0 else 0
        tendencia_lineal = venta_diaria_promedio * dias_laborales_mes
        
        html = f"""
        <div class="executive-summary">
            <h2 style="text-align: center; margin-bottom: 30px;">RESUMEN EJECUTIVO</h2>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-icon">💰</div>
                    <div class="kpi-title">AVANCE 2025 ACTUAL</div>
                    <div class="kpi-value">{self.format_number(total_avance, 1)}M</div>
                    <div class="kpi-subtitle">BOB vendidos a la fecha</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">📊</div>
                    <div class="kpi-title">PRESUPUESTO MENSUAL</div>
                    <div class="kpi-value">{self.format_number(cumpl_sop/100, is_percentage=True)}</div>
                    <div class="kpi-subtitle">{self.format_number(total_sop, 1)}M BOB objetivo SOP</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">🎯</div>
                    <div class="kpi-title">PRESUPUESTO GENERAL</div>
                    <div class="kpi-value">{self.format_number(cumpl_pg/100, is_percentage=True)}</div>
                    <div class="kpi-subtitle">{self.format_number(total_ppto, 1)}M BOB objetivo</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">🚀</div>
                    <div class="kpi-title">PROYECCION CIERRE</div>
                    <div class="kpi-value">{self.format_number(total_py, 1)}M</div>
                    <div class="kpi-subtitle">BOB estimados {self.meses[self.current_month].lower()}</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">📈</div>
                    <div class="kpi-title">PY VS AVANCE</div>
                    <div class="kpi-value">{self.format_number(py_vs_avance/100, is_percentage=True, show_plus=True)}</div>
                    <div class="kpi-subtitle">Proyección vs actual</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">📋</div>
                    <div class="kpi-title">PY VS SOP</div>
                    <div class="kpi-value">{self.format_number(py_vs_sop/100, is_percentage=True, show_plus=True)}</div>
                    <div class="kpi-subtitle">Proyección vs objetivo mensual</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">📌</div>
                    <div class="kpi-title">PY VS PPTO GENERAL</div>
                    <div class="kpi-value">{self.format_number(py_vs_pg/100, is_percentage=True, show_plus=True)}</div>
                    <div class="kpi-subtitle">Proyección vs presupuesto anual</div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon">⏰</div>
                    <div class="kpi-title">AVANCE MENSUAL</div>
                    <div class="kpi-value">{int(dias_laborales_avance)} días</div>
                    <div class="kpi-subtitle">De {dias_laborales_mes} días laborales</div>
                </div>
            </div>
            
            {self._generate_comments_analysis(comentarios)}
            
            <hr>
            
            <h3>MÉTRICAS DE AVANCE MENSUAL</h3>
            <ul style="list-style: none; padding: 0;">
                <li>• <strong>Días laborales del mes:</strong> {dias_laborales_mes} días</li>
                <li>• <strong>Días laborales de avance:</strong> {dias_laborales_avance} días</li>
                <li>• <strong>% Avance del mes:</strong> {self.format_number(porcentaje_avance/100, is_percentage=True)}</li>
                <li>• <strong>Venta diaria promedio actual:</strong> BOB {self.format_number(venta_diaria_promedio)}</li>
                <li>• <strong>Venta diaria objetivo:</strong> BOB {self.format_number(venta_diaria_objetivo)}</li>
                <li>• <strong>Tendencia lineal proyectada:</strong> BOB {self.format_number(tendencia_lineal)}</li>
            </ul>
        </div>
        """

        return html

    def _generate_hitrate_section(self, hitrate_data: Dict) -> str:
        """
        Generar sección completa de Hit Rate y Eficiencia

        Args:
            hitrate_data: Diccionario con datos procesados de Hit Rate

        Returns:
            HTML de la sección de Hit Rate
        """
        if not hitrate_data:
            return "<p>No hay datos de Hit Rate disponibles</p>"

        html = ""

        # Get data for cards
        summary = hitrate_data.get('summary_metrics', {})
        mensual_df = hitrate_data.get('mensual', pd.DataFrame())

        # Calculate YTD averages from monthly data (promedio)
        ytd_hitrate = summary.get('promedio_hitrate', 0)
        ytd_eficiencia = summary.get('promedio_eficiencia', 0)

        # Get current month metrics (último mes disponible)
        current_month_hr = 0
        current_month_ef = 0
        if not mensual_df.empty:
            current_month_hr = mensual_df.iloc[-1]['hit_rate']
            current_month_ef = mensual_df.iloc[-1]['eficiencia']
            current_month_name = mensual_df.iloc[-1]['mes']
        else:
            current_month_name = self.meses[self.current_month]

        html += f"""
        <div class="kpi-grid" style="margin-bottom: 30px;">
            <div class="kpi-card">
                <div class="label">HIT RATE YTD (PROMEDIO)</div>
                <div class="value" style="font-size: 24px; color: #1e3a8a;">{ytd_hitrate:.1f}%</div>
                <div class="label">Conversión promedio de visitas en ventas</div>
            </div>
            <div class="kpi-card">
                <div class="label">EFICIENCIA YTD (PROMEDIO)</div>
                <div class="value" style="font-size: 24px; color: #1e3a8a;">{ytd_eficiencia:.1f}%</div>
                <div class="label">Cobertura promedio de clientes</div>
            </div>
            <div class="kpi-card">
                <div class="label">HIT RATE {current_month_name.upper()}</div>
                <div class="value" style="font-size: 24px; color: #3b82f6;">{current_month_hr:.1f}%</div>
                <div class="label">Conversión del mes actual</div>
            </div>
            <div class="kpi-card">
                <div class="label">EFICIENCIA {current_month_name.upper()}</div>
                <div class="value" style="font-size: 24px; color: #059669;">{current_month_ef:.1f}%</div>
                <div class="label">Cobertura del mes actual</div>
            </div>
        </div>
        """

        # Tabla histórica mensual
        html += "<h3>5.1. EVOLUCIÓN MENSUAL - HIT RATE Y EFICIENCIA</h3>"
        html += self._generate_hitrate_mensual_table(hitrate_data.get('mensual', pd.DataFrame()))

        # Gráfico de barras (simulado con HTML/CSS)
        html += self._generate_hitrate_chart(hitrate_data.get('mensual', pd.DataFrame()))

        # Tabla de ciudades
        html += "<h3>5.2. HIT RATE Y EFICIENCIA POR CIUDAD - MES ACTUAL</h3>"
        html += self._generate_hitrate_ciudad_table(hitrate_data.get('ciudad_actual', pd.DataFrame()))

        # Matriz histórica por ciudad
        html += "<h3>5.3. EVOLUCIÓN HISTÓRICA POR CIUDAD</h3>"
        ciudad_historico = hitrate_data.get('ciudad_historico', {})
        if isinstance(ciudad_historico, dict) and 'hitrate_matrix' in ciudad_historico:
            html += self._generate_hitrate_ciudad_matrix(ciudad_historico['hitrate_matrix'], 'Hit Rate')
            html += self._generate_hitrate_ciudad_matrix(ciudad_historico['eficiencia_matrix'], 'Eficiencia')

        return html

    def _generate_hitrate_mensual_table(self, df: pd.DataFrame) -> str:
        """Generar tabla de Hit Rate mensual"""
        if df.empty:
            return "<p>No hay datos mensuales disponibles</p>"

        html = """
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>MES</th>
                        <th>CLIENTES TOTALES</th>
                        <th>CLIENTES CONTACTADOS</th>
                        <th>CLIENTES CON VENTA</th>
                        <th style="background: #059669;">EFICIENCIA (%)</th>
                        <th style="background: #3b82f6;">HIT RATE (%)</th>
                        <th>TENDENCIA HIT RATE</th>
                    </tr>
                </thead>
                <tbody>
        """

        for idx, row in df.iterrows():
            tendencia_hr = row.get('tendencia_hitrate', 0)
            tendencia_icon = "↑" if tendencia_hr > 0 else "↓" if tendencia_hr < 0 else "→"
            tendencia_color = "positive" if tendencia_hr > 0 else "negative" if tendencia_hr < 0 else "neutral"

            html += f"""
                <tr>
                    <td>{row['mes']}</td>
                    <td>{self.format_number(row['clientes_totales'], 0)}</td>
                    <td>{self.format_number(row['clientes_contactados'], 0)}</td>
                    <td>{self.format_number(row['clientes_con_venta'], 0)}</td>
                    <td style="background: #ecfdf5; font-weight: bold;">{row['eficiencia']:.1f}%</td>
                    <td style="background: #eff6ff; font-weight: bold;">{row['hit_rate']:.1f}%</td>
                    <td class="{tendencia_color}">{tendencia_icon} {abs(tendencia_hr):.1f}%</td>
                </tr>
            """

        # Fila de promedios
        html += f"""
                <tr class="total-row">
                    <td>PROMEDIO</td>
                    <td>{self.format_number(df['clientes_totales'].mean(), 0)}</td>
                    <td>{self.format_number(df['clientes_contactados'].mean(), 0)}</td>
                    <td>{self.format_number(df['clientes_con_venta'].mean(), 0)}</td>
                    <td style="background: #ecfdf5; font-weight: bold;">{df['eficiencia'].mean():.1f}%</td>
                    <td style="background: #eff6ff; font-weight: bold;">{df['hit_rate'].mean():.1f}%</td>
                    <td>-</td>
                </tr>
        """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def _generate_hitrate_chart(self, df: pd.DataFrame) -> str:
        """Generar gráfico de barras de Hit Rate y Eficiencia"""
        if df.empty:
            return ""

        max_value = max(df['hit_rate'].max(), df['eficiencia'].max(), 100)

        html = """
        <div style="margin: 30px 0; background: #f9fafb; padding: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 20px;">Evolución Hit Rate vs Eficiencia</h4>
            <div style="display: flex; gap: 20px; margin-bottom: 15px;">
                <span style="display: flex; align-items: center;"><span style="width: 20px; height: 12px; background: #3b82f6; margin-right: 5px; border-radius: 2px;"></span>Hit Rate</span>
                <span style="display: flex; align-items: center;"><span style="width: 20px; height: 12px; background: #10b981; margin-right: 5px; border-radius: 2px;"></span>Eficiencia</span>
            </div>
            <div style="display: flex;">
                <div style="width: 100px; display: flex; flex-direction: column; justify-content: space-between; padding-right: 10px;">
        """

        # Add month labels on Y-axis
        for idx, row in df.iterrows():
            html += f"""<div style="height: 40px; display: flex; align-items: center; font-size: 11px; font-weight: 500;">{row['mes'][:3]}</div>"""

        html += """
                </div>
                <div style="flex: 1; display: flex; flex-direction: column;">
        """

        for idx, row in df.iterrows():
            hr_width = (row['hit_rate'] / max_value) * 100
            ef_width = (row['eficiencia'] / max_value) * 100

            html += f"""
            <div style="height: 40px; display: flex; flex-direction: column; justify-content: center; gap: 2px; border-bottom: 1px solid #e5e7eb;">
                <div style="display: flex; align-items: center;">
                    <div style="background: #3b82f6; height: 15px; width: {hr_width}%; border-radius: 2px; position: relative; min-width: 45px;">
                        <span style="position: absolute; right: 3px; color: white; font-size: 10px; line-height: 15px; font-weight: 500;">{row['hit_rate']:.1f}%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="background: #10b981; height: 15px; width: {ef_width}%; border-radius: 2px; position: relative; min-width: 45px;">
                        <span style="position: absolute; right: 3px; color: white; font-size: 10px; line-height: 15px; font-weight: 500;">{row['eficiencia']:.1f}%</span>
                    </div>
                </div>
            </div>
            """

        html += """
                </div>
            </div>
            <div style="margin-top: 10px; display: flex; justify-content: space-between; padding-left: 110px; font-size: 10px; color: #6b7280;">
                <span>0%</span>
                <span>25%</span>
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
            </div>
        </div>
        """
        return html

    def _generate_hitrate_ciudad_table(self, df: pd.DataFrame) -> str:
        """Generar tabla de Hit Rate por ciudad"""
        if df.empty:
            return "<p>No hay datos por ciudad disponibles</p>"

        html = """
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>CIUDAD</th>
                        <th>CLIENTES TOTALES</th>
                        <th>CLIENTES CONTACTADOS</th>
                        <th>CLIENTES CON VENTA</th>
                        <th style="background: #059669;">EFICIENCIA (%)</th>
                        <th>PERFORMANCE</th>
                        <th style="background: #3b82f6;">HIT RATE (%)</th>
                        <th>PERFORMANCE</th>
                    </tr>
                </thead>
                <tbody>
        """

        for idx, row in df.iterrows():
            perf_hr = row.get('performance_hitrate', 'Regular')
            perf_ef = row.get('performance_eficiencia', 'Regular')

            color_hr = '#059669' if perf_hr == 'Excelente' else '#eab308' if perf_hr == 'Bueno' else '#f97316' if perf_hr == 'Regular' else '#dc2626'
            color_ef = '#059669' if perf_ef == 'Excelente' else '#eab308' if perf_ef == 'Bueno' else '#f97316' if perf_ef == 'Regular' else '#dc2626'

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.format_number(row['clientes_totales'], 0)}</td>
                    <td>{self.format_number(row['clientes_contactados'], 0)}</td>
                    <td>{self.format_number(row['clientes_con_venta'], 0)}</td>
                    <td style="background: #ecfdf5; font-weight: bold;">{row['eficiencia']:.1f}%</td>
                    <td style="color: {color_ef}; font-weight: bold;">{perf_ef}</td>
                    <td style="background: #eff6ff; font-weight: bold;">{row['hit_rate']:.1f}%</td>
                    <td style="color: {color_hr}; font-weight: bold;">{perf_hr}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def _generate_hitrate_ciudad_matrix(self, df: pd.DataFrame, metric_name: str) -> str:
        """Generar matriz de Hit Rate/Eficiencia por ciudad y mes"""
        if df.empty:
            return ""

        html = f"""
        <h4>{metric_name} por Ciudad - Evolución Mensual</h4>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>CIUDAD</th>
        """

        # Headers de meses
        meses_disponibles = sorted(df.columns.tolist())
        for mes in meses_disponibles:
            mes_nombre = self.meses.get(mes, f'Mes {mes}')
            html += f"<th>{mes_nombre[:3].upper()}</th>"

        html += """
                        <th>PROMEDIO</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Filas de ciudades
        for ciudad in df.index:
            html += f"<tr><td>{ciudad}</td>"

            valores = []
            for mes in meses_disponibles:
                valor = df.loc[ciudad, mes]
                valores.append(valor)

                # Color coding
                if metric_name == 'Hit Rate':
                    color = '#059669' if valor >= 80 else '#eab308' if valor >= 70 else '#f97316' if valor >= 60 else '#dc2626'
                else:  # Eficiencia
                    color = '#059669' if valor >= 90 else '#eab308' if valor >= 80 else '#f97316' if valor >= 70 else '#dc2626'

                html += f'<td style="color: {color}; font-weight: bold;">{valor:.1f}%</td>'

            promedio = sum(valores) / len(valores) if valores else 0
            html += f'<td style="font-weight: bold;">{promedio:.1f}%</td>'
            html += "</tr>"

        html += """
                </tbody>
            </table>
        </div>
        """
        return html