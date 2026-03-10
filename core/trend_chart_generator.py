"""
Módulo para generar gráficos de tendencia comparativa
Compara ventas reales vs proyecciones de gerentes (BOB)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
import calendar
import logging
import json

logger = logging.getLogger(__name__)


class TrendChartGenerator:
    """Generador de gráficos de tendencia comparativa ventas vs proyecciones"""

    def __init__(self, current_date: datetime):
        """
        Inicializar el generador de gráficos

        Args:
            current_date: Fecha actual para el reporte
        """
        self.current_date = current_date
        self.current_year = current_date.year
        self.current_month = current_date.month
        self.current_day = current_date.day

        # Determinar semana actual
        self.current_week = self._get_current_week()

        # Colores para el gráfico
        self.colors = {
            'venta_real': '#3B82F6',  # Azul
            'proyeccion': '#94A3B8',   # Gris azulado
            'cumplimiento_alto': '#10B981',  # Verde
            'cumplimiento_medio': '#F59E0B',  # Amarillo
            'cumplimiento_bajo': '#EF4444'    # Rojo
        }

    def _get_calendar_week_ranges(self) -> List[Tuple[int, int]]:
        """
        Calcula los rangos de días para cada semana CALENDARIO del mes.
        Las semanas van de Lunes a Domingo.

        Returns:
            Lista de tuplas (día_inicio, día_fin) para cada semana del mes
        """
        year = self.current_year
        month = self.current_month

        first_day = date(year, month, 1)
        last_day_num = calendar.monthrange(year, month)[1]

        weeks = []
        current_day = 1

        # Primera semana: desde día 1 hasta el primer domingo
        first_weekday = first_day.weekday()  # 0=Lunes, 6=Domingo

        if first_weekday == 6:  # Si empieza en domingo
            weeks.append((1, 1))
            current_day = 2
        else:
            # Días hasta el domingo
            days_to_sunday = 6 - first_weekday
            end_first_week = min(1 + days_to_sunday, last_day_num)
            weeks.append((1, end_first_week))
            current_day = end_first_week + 1

        # Semanas siguientes: lunes a domingo (7 días cada una)
        while current_day <= last_day_num:
            week_end = min(current_day + 6, last_day_num)
            weeks.append((current_day, week_end))
            current_day = week_end + 1

        # Asegurar que siempre tengamos 5 semanas (algunas pueden estar vacías)
        while len(weeks) < 5:
            weeks.append((last_day_num + 1, last_day_num + 1))  # Semana vacía

        return weeks[:5]  # Máximo 5 semanas

    def _get_current_week(self) -> int:
        """
        Determina en qué semana CALENDARIO del mes estamos.
        Usa semanas reales (Lunes-Domingo) en lugar de rangos fijos.

        Returns:
            Número de semana actual (1-5)
        """
        weeks = self._get_calendar_week_ranges()

        for i, (start, end) in enumerate(weeks, 1):
            if start <= self.current_day <= end:
                return i

        # Si estamos más allá del último día del mes, retornar semana 5
        return 5

    def process_weekly_data(self,
                           ventas_df: pd.DataFrame,
                           proyecciones_df: pd.DataFrame,
                           sop_oruro_trinidad_df: pd.DataFrame = None,
                           override_py_gerente_total: float = None,
                           override_sop_total: float = None) -> Dict:
        """
        Procesar datos semanales de ventas y proyecciones (solo BOB)
        Incluye distribución semanal del SOP de Oruro y Trinidad

        Args:
            ventas_df: DataFrame con ventas semanales
            proyecciones_df: DataFrame con proyecciones de gerentes
            sop_oruro_trinidad_df: DataFrame con SOP mensual de Oruro y Trinidad
            override_py_gerente_total: Total PY Gerente mensual desde marca_totales (override)
            override_sop_total: Total SOP mensual desde marca_totales (override)

        Returns:
            Diccionario con datos procesados para el gráfico
        """
        try:
            # Inicializar estructura de datos (solo BOB)
            data = {
                'semanas': [],
                'ventas_bob': [],
                'proyecciones_bob': [],
                'cumplimiento_bob': [],
                'totales': {}
            }

            # Procesar cada semana (siempre todas las 5 semanas para proyecciones)
            # First pass: collect raw weekly projection values for shape
            raw_weekly_projections = []
            for week in range(1, 6):
                proy_bob_gerentes = self._get_proyeccion_semana(proyecciones_df, week)
                proy_bob_sop = self._get_sop_distribuido_semana(sop_oruro_trinidad_df, week, include_future=True)
                raw_weekly_projections.append(proy_bob_gerentes + proy_bob_sop)

            # Apply marca_totales override if provided (scale weekly shape to match override totals)
            if override_py_gerente_total is not None and override_sop_total is not None:
                combined_total = override_py_gerente_total + override_sop_total
                raw_total = sum(raw_weekly_projections)
                if raw_total > 0:
                    scale_factor = combined_total / raw_total
                    weekly_projections = [v * scale_factor for v in raw_weekly_projections]
                else:
                    # No weekly shape available, distribute evenly
                    weekly_projections = [combined_total / 5.0] * 5
                logger.info(f"PY Gerente override: {override_py_gerente_total:,.0f} (from marca_totales)")
                logger.info(f"SOP override: {override_sop_total:,.0f} (from marca_totales)")
                logger.info(f"Combined override: {combined_total:,.0f}, scale factor: {scale_factor if raw_total > 0 else 'even distribution'}")
            else:
                weekly_projections = raw_weekly_projections

            for week in range(1, 6):
                semana_label = f"Semana {week}"
                data['semanas'].append(semana_label)

                # Ventas BOB (solo hasta semana actual, resto = 0)
                if week <= self.current_week:
                    venta_bob_col = f'semana{week}_bob'
                    venta_bob = ventas_df[venta_bob_col].sum() if venta_bob_col in ventas_df.columns else 0
                else:
                    venta_bob = 0  # Semanas futuras = 0

                data['ventas_bob'].append(float(venta_bob))

                # Proyecciones BOB - use override-scaled values if available
                proy_bob_total = weekly_projections[week - 1]
                data['proyecciones_bob'].append(float(proy_bob_total))

                # Calcular cumplimiento (solo para semanas transcurridas)
                if week <= self.current_week and proy_bob_total > 0:
                    cumpl_bob = (venta_bob / proy_bob_total * 100)
                else:
                    cumpl_bob = 0  # Semanas futuras no tienen cumplimiento

                data['cumplimiento_bob'].append(round(cumpl_bob, 1))

            # Calcular totales
            # Ventas: solo hasta semana actual
            total_ventas_actual = sum(data['ventas_bob'][:self.current_week])

            # Proyecciones: mes completo para mostrar total, pero solo actual para cumplimiento
            total_proyecciones_mes = sum(data['proyecciones_bob'])
            total_proyecciones_actual = sum(data['proyecciones_bob'][:self.current_week])

            data['totales'] = {
                'venta_bob': total_ventas_actual,
                'proyeccion_bob': total_proyecciones_mes,  # Mostrar proyección completa del mes
                'cumplimiento_bob': (total_ventas_actual / total_proyecciones_actual * 100)
                                    if total_proyecciones_actual > 0 else 0  # Cumplimiento solo vs semanas actuales
            }

            logger.info(f"Datos semanales procesados: {len(data['semanas'])} semanas")
            return data

        except Exception as e:
            logger.error(f"Error procesando datos semanales: {e}")
            raise

    def _get_proyeccion_semana(self, df: pd.DataFrame, week: int) -> float:
        """
        Obtener proyección BOB para una semana específica

        Args:
            df: DataFrame con proyecciones
            week: Número de semana (1-5)

        Returns:
            Valor de proyección en BOB para la semana
        """
        try:
            col_name = f'total_semana{week}'
            if col_name in df.columns and not df.empty:
                return float(df[col_name].iloc[0]) if len(df) > 0 else 0
            return 0
        except Exception as e:
            logger.error(f"Error obteniendo proyección semana {week}: {e}")
            return 0

    def _get_sop_distribuido_semana(self, sop_df: pd.DataFrame, week: int, include_future: bool = False) -> float:
        """
        Distribuir SOP mensual de Oruro y Trinidad por semana según patrones históricos

        Args:
            sop_df: DataFrame con SOP mensual por ciudad
            week: Número de semana (1-5)
            include_future: Si incluir semanas futuras (para proyecciones completas)

        Returns:
            Valor de SOP distribuido para la semana
        """
        if sop_df is None or sop_df.empty:
            return 0

        # Si no incluimos futuras, solo hasta semana actual
        if not include_future and week > self.current_week:
            return 0

        try:
            # Patrones de distribución semanal
            distribution_patterns = {
                'ORURO': {
                    1: 0.08,   # 8%
                    2: 0.12,   # 12%
                    3: 0.20,   # 20%
                    4: 0.28,   # 28%
                    5: 0.32    # 32%
                },
                'TRINIDAD': {
                    1: 0.25,   # 25%
                    2: 0.45,   # 45%
                    3: 0.20,   # 20%
                    4: 0.10,   # 10%
                    5: 0.00    # 0%
                }
            }

            total_sop_week = 0

            for _, row in sop_df.iterrows():
                ciudad = row['ciudad'].upper()
                sop_mensual = float(row['sop_mensual'])

                if ciudad in distribution_patterns:
                    percentage = distribution_patterns[ciudad].get(week, 0)
                    sop_semana = sop_mensual * percentage
                    total_sop_week += sop_semana

                    logger.debug(f"SOP {ciudad} semana {week}: {sop_semana:,.2f} ({percentage:.1%} de {sop_mensual:,.2f})")

            return total_sop_week

        except Exception as e:
            logger.error(f"Error distribuyendo SOP para semana {week}: {e}")
            return 0

    def generate_chart_html(self, data: Dict) -> str:
        """
        Generar HTML con gráfico interactivo usando Chart.js (solo BOB)

        Args:
            data: Datos procesados para el gráfico (puede ser simple o multi-ciudad)

        Returns:
            String con HTML del gráfico
        """
        # Detectar si es multi-ciudad o simple
        is_multi_city = 'general' in data

        if is_multi_city:
            # Convertir datos multi-ciudad a JSON
            chart_data_json = json.dumps(data)
        else:
            # Mantener compatibilidad con formato simple
            chart_data_json = json.dumps({'general': data})

        # Generar HTML con o sin selector de ciudades
        city_selector_html = ''
        if is_multi_city:
            city_selector_html = '''
            <!-- Selector de ciudades -->
            <div class="city-tabs" style="display: flex; gap: 8px; margin-bottom: 25px; border-bottom: 2px solid #e5e7eb; padding-bottom: 0; flex-wrap: wrap;">
                <button class="city-tab active" data-city="general" style="padding: 12px 20px; background: #f0f9ff; border: none; border-bottom: 3px solid #3b82f6; cursor: pointer; font-size: 14px; font-weight: 500; color: #3b82f6; transition: all 0.2s ease; margin-bottom: -2px;">
                    🇧🇴 GENERAL-NACIONAL
                </button>
                <button class="city-tab" data-city="santa_cruz" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 SANTA CRUZ
                </button>
                <button class="city-tab" data-city="cochabamba" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 COCHABAMBA
                </button>
                <button class="city-tab" data-city="la_paz" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 LA PAZ
                </button>
                <button class="city-tab" data-city="el_alto" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 EL ALTO
                </button>
                <button class="city-tab" data-city="tarija" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 TARIJA
                </button>
                <button class="city-tab" data-city="sucre" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 SUCRE
                </button>
                <button class="city-tab" data-city="potosi" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 POTOSÍ
                </button>
                <button class="city-tab" data-city="oruro" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 ORURO
                </button>
                <button class="city-tab" data-city="trinidad" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 3px solid transparent; cursor: pointer; font-size: 14px; font-weight: 500; color: #64748b; transition: all 0.2s ease; margin-bottom: -2px;">
                    📍 TRINIDAD
                </button>
            </div>
            '''

        html = f'''
        <div class="trend-chart-section" style="margin: 40px 0; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #1e3a8a; margin-bottom: 20px; font-size: 24px;">
                🎯 Accuracy de la proyección comercial - Ing. Neto (BOB)
            </h2>

            {city_selector_html}

            <!-- Contenedor del gráfico -->
            <div style="position: relative; height: 400px; margin-bottom: 20px;">
                <canvas id="trendChart"></canvas>
            </div>

            <!-- Tabla resumen -->
            <div class="summary-table" style="overflow-x: auto;">
                <h3 style="color: #1e3a8a; margin: 20px 0 10px 0;">📈 Indicadores de Cumplimiento Semanal</h3>
                <table id="summaryTable" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #F3F4F6;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #E5E7EB;">Semana</th>
                            <th style="padding: 12px; text-align: right; border: 1px solid #E5E7EB;">Venta Real (BOB)</th>
                            <th style="padding: 12px; text-align: right; border: 1px solid #E5E7EB;">Proyección Gerentes (BOB)</th>
                            <th style="padding: 12px; text-align: right; border: 1px solid #E5E7EB;">Cumplimiento</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid #E5E7EB;">Estado</th>
                        </tr>
                    </thead>
                    <tbody id="summaryTableBody">
                        <!-- Se llenará dinámicamente con JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            // Datos del gráfico
            const allChartData = {chart_data_json};
            const isMultiCity = {'true' if is_multi_city else 'false'};
            let chartData = isMultiCity ? allChartData['general'] : allChartData['general'];
            let currentCity = 'general';
            let myChart = null;

            // Función para formatear números
            function formatNumber(value) {{
                return value.toLocaleString('es-BO', {{
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }});
            }}

            // Función para formatear números abreviados (para el gráfico)
            function formatAbbreviated(value) {{
                if (value >= 1000000) {{
                    return (value / 1000000).toFixed(1) + 'M';
                }}
                if (value >= 1000) {{
                    return (value / 1000).toFixed(1) + 'K';
                }}
                return value.toFixed(0);
            }}

            // Función para obtener color según cumplimiento
            function getStatusColor(cumplimiento) {{
                if (cumplimiento >= 95) return '#10B981';
                if (cumplimiento >= 85) return '#F59E0B';
                return '#EF4444';
            }}

            // Función para obtener emoji de estado
            function getStatusEmoji(cumplimiento) {{
                if (cumplimiento >= 95) return '🟢';
                if (cumplimiento >= 85) return '🟡';
                return '🔴';
            }}

            // Inicializar el gráfico
            function initChart() {{
                const ctx = document.getElementById('trendChart').getContext('2d');

                const ventas = chartData.ventas_bob;
                const proyecciones = chartData.proyecciones_bob;

                if (myChart) {{
                    myChart.destroy();
                }}

                myChart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: chartData.semanas,
                        datasets: [
                            {{
                                label: 'Venta Real',
                                data: ventas,
                                backgroundColor: '#3B82F6',
                                borderColor: '#2563EB',
                                borderWidth: 1,
                                borderRadius: 4
                            }},
                            {{
                                label: 'Proyección Gerentes',
                                data: proyecciones,
                                backgroundColor: '#94A3B8',
                                borderColor: '#64748B',
                                borderWidth: 1,
                                borderRadius: 4
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                position: 'top',
                                labels: {{
                                    padding: 20,
                                    font: {{
                                        size: 14
                                    }}
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        let label = context.dataset.label || '';
                                        if (label) {{
                                            label += ': ';
                                        }}
                                        label += formatNumber(context.parsed.y) + ' BOB';
                                        return label;
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: function(value) {{
                                        return formatAbbreviated(value);
                                    }}
                                }}
                            }}
                        }}
                    }},
                    plugins: [{{
                        afterDatasetsDraw: function(chart) {{
                            const ctx = chart.ctx;
                            chart.data.datasets.forEach((dataset, i) => {{
                                const meta = chart.getDatasetMeta(i);
                                meta.data.forEach((bar, index) => {{
                                    const data = dataset.data[index];
                                    ctx.fillStyle = '#374151';
                                    ctx.font = 'bold 11px Arial';
                                    ctx.textAlign = 'center';
                                    ctx.textBaseline = 'bottom';
                                    ctx.fillText(formatAbbreviated(data), bar.x, bar.y - 5);
                                }});
                            }});
                        }}
                    }}]
                }});

                updateSummaryTable();
            }}

            // Actualizar tabla resumen
            function updateSummaryTable() {{
                const tbody = document.getElementById('summaryTableBody');
                const ventas = chartData.ventas_bob;
                const proyecciones = chartData.proyecciones_bob;
                const cumplimientos = chartData.cumplimiento_bob;

                let html = '';

                // Filas de semanas
                chartData.semanas.forEach((semana, index) => {{
                    const cumplimiento = cumplimientos[index];
                    const ventaValue = ventas[index];
                    const proyeccionValue = proyecciones[index];

                    // Determinar si es semana futura
                    const weekNumber = index + 1;
                    const isFutureWeek = ventaValue === 0 && proyeccionValue > 0;

                    let cumplimientoText = cumplimiento.toFixed(1) + '%';
                    let estadoEmoji = getStatusEmoji(cumplimiento);

                    if (isFutureWeek) {{
                        cumplimientoText = 'Pendiente';
                        estadoEmoji = '⏳';
                    }}

                    html += `
                        <tr style="${{isFutureWeek ? 'opacity: 0.7; font-style: italic;' : ''}}">
                            <td style="padding: 10px; border: 1px solid #E5E7EB;">${{semana}} ${{isFutureWeek ? '(Proyección)' : ''}}</td>
                            <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">${{isFutureWeek ? '-' : formatNumber(ventaValue)}}</td>
                            <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">${{formatNumber(proyeccionValue)}}</td>
                            <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB; color: ${{isFutureWeek ? '#6B7280' : getStatusColor(cumplimiento)}}; font-weight: bold;">${{cumplimientoText}}</td>
                            <td style="padding: 10px; text-align: center; border: 1px solid #E5E7EB;">${{estadoEmoji}}</td>
                        </tr>
                    `;
                }});

                // Fila de totales
                const totalVenta = chartData.totales.venta_bob;
                const totalProyeccion = chartData.totales.proyeccion_bob;
                const totalCumplimiento = chartData.totales.cumplimiento_bob;

                html += `
                    <tr style="background: #F3F4F6; font-weight: bold;">
                        <td style="padding: 10px; border: 1px solid #E5E7EB;">TOTAL MES</td>
                        <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">${{formatNumber(totalVenta)}}</td>
                        <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">${{formatNumber(totalProyeccion)}}</td>
                        <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB; color: ${{getStatusColor(totalCumplimiento)}};">${{totalCumplimiento.toFixed(1)}}%</td>
                        <td style="padding: 10px; text-align: center; border: 1px solid #E5E7EB;">${{getStatusEmoji(totalCumplimiento)}}</td>
                    </tr>
                `;

                tbody.innerHTML = html;
            }}

            // Función para cambiar de ciudad
            function changeCity(cityKey) {{
                if (isMultiCity) {{
                    // Actualizar datos actuales
                    chartData = allChartData[cityKey];
                    currentCity = cityKey;

                    // Actualizar UI
                    document.querySelectorAll('.city-tab').forEach(tab => {{
                        tab.classList.remove('active');
                        tab.style.background = 'transparent';
                        tab.style.borderBottomColor = 'transparent';
                        tab.style.color = '#64748b';
                    }});

                    const activeTab = document.querySelector(`[data-city="${{cityKey}}"]`);
                    if (activeTab) {{
                        activeTab.classList.add('active');
                        activeTab.style.background = '#f0f9ff';
                        activeTab.style.borderBottomColor = '#3b82f6';
                        activeTab.style.color = '#3b82f6';
                    }}

                    // Reinicializar gráfico y tabla
                    initChart();
                }}
            }}

            // Event listener para tabs de ciudad
            if (isMultiCity) {{
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelectorAll('.city-tab').forEach(tab => {{
                        tab.addEventListener('click', function() {{
                            changeCity(this.dataset.city);
                        }});

                        // Agregar efectos hover
                        tab.addEventListener('mouseenter', function() {{
                            if (!this.classList.contains('active')) {{
                                this.style.background = '#f0f9ff';
                                this.style.color = '#3b82f6';
                            }}
                        }});

                        tab.addEventListener('mouseleave', function() {{
                            if (!this.classList.contains('active')) {{
                                this.style.background = 'transparent';
                                this.style.color = '#64748b';
                            }}
                        }});
                    }});

                    initChart();
                }});
            }} else {{
                // Inicializar normalmente si no es multi-ciudad
                document.addEventListener('DOMContentLoaded', function() {{
                    initChart();
                }});
            }}
        </script>
        '''

        return html

    def process_weekly_data_multi_city(self,
                                      ventas_df: pd.DataFrame,
                                      proyecciones_df: pd.DataFrame,
                                      ventas_por_ciudad_df: pd.DataFrame,
                                      proyecciones_por_ciudad_df: pd.DataFrame,
                                      sop_oruro_trinidad_df: pd.DataFrame = None,
                                      override_py_gerente_total: float = None,
                                      override_sop_total: float = None) -> Dict:
        """
        Procesar datos semanales para vista general y por ciudad (solo BOB)

        Args:
            ventas_df: DataFrame con ventas semanales totales
            proyecciones_df: DataFrame con proyecciones totales de gerentes
            ventas_por_ciudad_df: DataFrame con ventas semanales por ciudad
            proyecciones_por_ciudad_df: DataFrame con proyecciones por ciudad
            sop_oruro_trinidad_df: DataFrame con SOP mensual de Oruro y Trinidad
            override_py_gerente_total: Total PY Gerente mensual desde marca_totales (override, solo general)
            override_sop_total: Total SOP mensual desde marca_totales (override, solo general)

        Returns:
            Diccionario con datos procesados para todas las ciudades
        """
        try:
            result = {}

            # 1. Procesar datos generales (vista actual) con overrides de marca_totales
            general_data = self.process_weekly_data(
                ventas_df, proyecciones_df, sop_oruro_trinidad_df,
                override_py_gerente_total=override_py_gerente_total,
                override_sop_total=override_sop_total
            )
            result['general'] = general_data

            # 2. Procesar datos por cada ciudad
            ciudades_incluidas = ['SANTA CRUZ', 'COCHABAMBA', 'LA PAZ', 'EL ALTO',
                                 'TARIJA', 'SUCRE', 'ORURO', 'POTOSI', 'TRINIDAD']

            for ciudad in ciudades_incluidas:
                ciudad_data = {
                    'semanas': [],
                    'ventas_bob': [],
                    'proyecciones_bob': [],
                    'cumplimiento_bob': [],
                    'totales': {}
                }

                # Filtrar datos de la ciudad
                ventas_ciudad = ventas_por_ciudad_df[
                    ventas_por_ciudad_df['ciudad'].str.upper() == ciudad
                ] if not ventas_por_ciudad_df.empty else pd.DataFrame()

                proyecciones_ciudad = proyecciones_por_ciudad_df[
                    proyecciones_por_ciudad_df['ciudad'].str.upper() == ciudad
                ] if not proyecciones_por_ciudad_df.empty else pd.DataFrame()

                # Procesar cada semana
                for week in range(1, 6):
                    semana_label = f"Semana {week}"
                    ciudad_data['semanas'].append(semana_label)

                    # Ventas BOB (solo hasta semana actual, resto = 0)
                    if week <= self.current_week:
                        venta_col = f'semana{week}_bob'
                        if not ventas_ciudad.empty and venta_col in ventas_ciudad.columns:
                            venta_bob = float(ventas_ciudad[venta_col].iloc[0])
                        else:
                            venta_bob = 0
                    else:
                        venta_bob = 0

                    ciudad_data['ventas_bob'].append(venta_bob)

                    # Proyecciones BOB (todas las semanas)
                    proy_col = f'total_semana{week}'
                    if not proyecciones_ciudad.empty and proy_col in proyecciones_ciudad.columns:
                        proy_bob = float(proyecciones_ciudad[proy_col].iloc[0])
                    else:
                        proy_bob = 0

                    # Si es ciudad sin gerente Y proy_bob = 0, usar SOP distribuido
                    # 2025 y antes: Oruro y Trinidad | 2026+: Solo Trinidad
                    ciudades_sin_gerente = ['TRINIDAD'] if self.current_year >= 2026 else ['ORURO', 'TRINIDAD']
                    if ciudad in ciudades_sin_gerente and proy_bob == 0 and sop_oruro_trinidad_df is not None:
                        try:
                            sop_ciudad = sop_oruro_trinidad_df[
                                sop_oruro_trinidad_df['ciudad'].str.upper() == ciudad
                            ]
                            if not sop_ciudad.empty:
                                sop_mensual = float(sop_ciudad['sop_mensual'].iloc[0])

                                # Patrones de distribución semanal
                                distribution = {
                                    'ORURO': {1: 0.08, 2: 0.12, 3: 0.20, 4: 0.28, 5: 0.32},
                                    'TRINIDAD': {1: 0.25, 2: 0.18, 3: 0.22, 4: 0.20, 5: 0.15}
                                }

                                if ciudad in distribution:
                                    percentage = distribution[ciudad].get(week, 0)
                                    proy_bob = sop_mensual * percentage
                        except Exception as e:
                            logger.warning(f"Error calculando SOP para {ciudad} semana {week}: {e}")
                            proy_bob = 0

                    ciudad_data['proyecciones_bob'].append(proy_bob)

                    # Calcular cumplimiento
                    if week <= self.current_week and proy_bob > 0:
                        cumpl_bob = (venta_bob / proy_bob * 100)
                    else:
                        cumpl_bob = 0

                    ciudad_data['cumplimiento_bob'].append(round(cumpl_bob, 1))

                # Calcular totales
                total_ventas_actual = sum(ciudad_data['ventas_bob'][:self.current_week])
                total_proyecciones_mes = sum(ciudad_data['proyecciones_bob'])
                total_proyecciones_actual = sum(ciudad_data['proyecciones_bob'][:self.current_week])

                ciudad_data['totales'] = {
                    'venta_bob': total_ventas_actual,
                    'proyeccion_bob': total_proyecciones_mes,
                    'cumplimiento_bob': (total_ventas_actual / total_proyecciones_actual * 100)
                                        if total_proyecciones_actual > 0 else 0
                }

                # Guardar con key normalizado
                ciudad_key = ciudad.lower().replace(' ', '_')
                result[ciudad_key] = ciudad_data

            logger.info(f"Datos procesados para {len(result)} vistas (general + {len(result)-1} ciudades)")
            return result

        except Exception as e:
            logger.error(f"Error procesando datos multi-ciudad: {e}")
            raise

    def get_status_emoji(self, cumplimiento: float) -> str:
        """
        Obtener emoji de estado según cumplimiento

        Args:
            cumplimiento: Porcentaje de cumplimiento

        Returns:
            Emoji correspondiente
        """
        if cumplimiento >= 95:
            return "🟢"
        elif cumplimiento >= 85:
            return "🟡"
        else:
            return "🔴"