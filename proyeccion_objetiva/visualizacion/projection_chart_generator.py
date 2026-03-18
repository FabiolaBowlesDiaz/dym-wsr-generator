"""
Generador de gráficos Chart.js para la sección de Resumen Ejecutivo.
Produce un gráfico de líneas mostrando Venta Real vs SOP vs PY Gerente (histórico)
con PY Sistema como punto del mes actual.
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict

from .. import config as cfg

logger = logging.getLogger(__name__)

MESES_CORTO = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
}


class ProjectionChartGenerator:
    """Genera gráfico de líneas histórico para el Resumen Ejecutivo."""

    def generate_historical_chart(
        self,
        historico_nacional: Dict,
        py_sistema_nacional: float = 0,
        avance_nacional: float = 0,
        current_year: int = 2026,
        current_month: int = 3,
        chart_id: str = "resumenEjecutivoChart"
    ) -> str:
        """
        Genera gráfico de líneas con 4 series: Venta Real, SOP, PY Gerente, PY Sistema.

        Args:
            historico_nacional: Dict con DataFrames 'ventas_nacionales', 'sop_nacional', 'py_gerente_nacional'
            py_sistema_nacional: Total PY Sistema (Nowcast) para el mes actual
            avance_nacional: Avance acumulado del mes actual
            current_year, current_month: Mes actual del reporte
            chart_id: ID del canvas HTML
        """
        ventas_df = historico_nacional.get('ventas_nacionales', pd.DataFrame())
        sop_df = historico_nacional.get('sop_nacional', pd.DataFrame())
        py_ger_df = historico_nacional.get('py_gerente_nacional', pd.DataFrame())

        if ventas_df.empty:
            return ""

        # Build unified month index (last 12 months)
        all_months = []
        for _, row in ventas_df.iterrows():
            anio, mes = int(row['anio']), int(row['mes'])
            all_months.append((anio, mes))

        if not all_months:
            return ""

        # Labels
        labels = [f"{MESES_CORTO.get(m, m)}'{str(a)[-2:]}" for a, m in all_months]

        # Venta Real series
        venta_map = {(int(r['anio']), int(r['mes'])): float(r['venta_bob'])
                     for _, r in ventas_df.iterrows()}

        # For current month, use avance (partial) instead of full month
        is_current = [(a == current_year and m == current_month) for a, m in all_months]
        venta_data = []
        for i, (a, m) in enumerate(all_months):
            val = venta_map.get((a, m), None)
            if is_current[i] and avance_nacional > 0:
                val = avance_nacional
            venta_data.append(round(val, 0) if val is not None else None)

        # SOP series
        sop_map = {(int(r['anio']), int(r['mes'])): float(r['sop_bob'])
                   for _, r in sop_df.iterrows()} if not sop_df.empty else {}
        sop_data = [round(sop_map.get((a, m), None) or 0, 0) if sop_map.get((a, m)) else None
                    for a, m in all_months]

        # PY Gerente series (sparse — only months with data)
        py_ger_map = {(int(r['anio']), int(r['mes'])): float(r['py_gerente_bob'])
                      for _, r in py_ger_df.iterrows()} if not py_ger_df.empty else {}
        py_ger_data = [round(py_ger_map.get((a, m), None) or 0, 0) if py_ger_map.get((a, m)) else None
                       for a, m in all_months]

        # PY Sistema: only current month point
        py_sistema_data = [None] * len(all_months)
        for i, (a, m) in enumerate(all_months):
            if a == current_year and m == current_month and py_sistema_nacional > 0:
                py_sistema_data[i] = round(py_sistema_nacional, 0)

        # Calculate max for Y scale
        all_vals = [v for v in venta_data + sop_data + py_ger_data + py_sistema_data if v is not None and v > 0]
        max_value = max(all_vals) * 1.12 if all_vals else 1000000

        # Current month index for annotation
        current_idx = None
        for i, (a, m) in enumerate(all_months):
            if a == current_year and m == current_month:
                current_idx = i
                break

        labels_json = json.dumps(labels, ensure_ascii=False)
        venta_json = json.dumps(venta_data)
        sop_json = json.dumps(sop_data)
        py_ger_json = json.dumps(py_ger_data)
        py_sis_json = json.dumps(py_sistema_data)

        current_label = f"{MESES_CORTO.get(current_month, current_month)}'{str(current_year)[-2:]}"

        return f"""
        <div style="margin: 20px 0; background: #f9fafb; padding: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 4px; color: #1e3a8a; font-size: 13px;">
                Senales de Cierre — Evolucion Mensual Nacional (BOB)
            </h4>
            <p style="margin: 0 0 15px 0; font-size: 10.5px; color: #6b7280;">
                {current_label}: avance parcial (linea solida) + proyecciones de cierre (puntos)
            </p>
            <div style="position: relative; height: 320px; width: 100%;">
                <canvas id="{chart_id}"></canvas>
            </div>
        </div>
        <script>
        (function() {{
            var ctx = document.getElementById('{chart_id}');
            if (!ctx) return;

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {labels_json},
                    datasets: [
                        {{
                            label: 'Venta Real',
                            data: {venta_json},
                            borderColor: '{cfg.COLOR_VENTA_REAL}',
                            backgroundColor: '{cfg.COLOR_VENTA_REAL}',
                            borderWidth: 2.5,
                            tension: 0.3,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            fill: false,
                            spanGaps: false,
                            order: 1
                        }},
                        {{
                            label: 'SOP (Presupuesto)',
                            data: {sop_json},
                            borderColor: '{cfg.COLOR_SOP}',
                            backgroundColor: '{cfg.COLOR_SOP}',
                            borderWidth: 1.5,
                            borderDash: [6, 4],
                            tension: 0.3,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            fill: false,
                            spanGaps: true,
                            order: 3
                        }},
                        {{
                            label: 'PY Gerente',
                            data: {py_ger_json},
                            borderColor: '#F59E0B',
                            backgroundColor: '#F59E0B',
                            borderWidth: 1.5,
                            tension: 0.3,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointStyle: 'circle',
                            fill: false,
                            showLine: true,
                            spanGaps: true,
                            order: 2
                        }},
                        {{
                            label: 'PY Sistema (Nowcast)',
                            data: {py_sis_json},
                            borderColor: '{cfg.COLOR_PY_SISTEMA}',
                            backgroundColor: '{cfg.COLOR_PY_SISTEMA}',
                            borderWidth: 0,
                            pointRadius: 7,
                            pointHoverRadius: 9,
                            pointStyle: 'rectRot',
                            fill: false,
                            showLine: false,
                            spanGaps: false,
                            order: 0
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                usePointStyle: true,
                                padding: 15,
                                font: {{ size: 11 }}
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    var value = context.parsed.y;
                                    if (value === null || value === undefined) return null;
                                    return context.dataset.label + ': BOB ' + value.toLocaleString('es-BO', {{
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                    }});
                                }}
                            }},
                            filter: function(item) {{
                                return item.parsed.y !== null;
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            min: 0,
                            max: {max_value:.0f},
                            ticks: {{
                                callback: function(value) {{
                                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                    return value;
                                }},
                                font: {{ size: 10 }}
                            }},
                            grid: {{
                                color: '#e5e7eb'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{ size: 10, weight: '500' }},
                                maxRotation: 0
                            }},
                            grid: {{
                                display: false
                            }}
                        }}
                    }}
                }}
            }});
        }})();
        </script>
        """

    def generate_historical_chart_c9l(
        self,
        historico_nacional: Dict,
        py_sistema_c9l: float = 0,
        avance_c9l: float = 0,
        py_gerente_c9l: float = 0,
        sop_c9l: float = 0,
        current_year: int = 2026,
        current_month: int = 3,
        chart_id: str = "resumenEjecutivoChartC9L"
    ) -> str:
        """
        Genera grafico de lineas C9L con 4 series: Venta Real, SOP, PY Gerente, PY Sistema.
        Identical structure to generate_historical_chart() but uses C9L data.

        For C9L, historical SOP and PY Gerente may not be available from the DB queries.
        - Venta Real C9L: full historical from venta_c9l column in ventas_nacionales
        - SOP C9L: only current month (single point from sop_c9l parameter)
        - PY Gerente C9L: only current month (single point from py_gerente_c9l parameter)
        - PY Sistema C9L: only current month (single point from py_sistema_c9l parameter)
        """
        ventas_df = historico_nacional.get('ventas_nacionales', pd.DataFrame())

        if ventas_df.empty or 'venta_c9l' not in ventas_df.columns:
            return ""

        # Build unified month index (last 12 months)
        all_months = []
        for _, row in ventas_df.iterrows():
            anio, mes = int(row['anio']), int(row['mes'])
            all_months.append((anio, mes))

        if not all_months:
            return ""

        # Labels
        labels = [f"{MESES_CORTO.get(m, m)}'{str(a)[-2:]}" for a, m in all_months]

        # Venta Real C9L series
        venta_map = {(int(r['anio']), int(r['mes'])): float(r['venta_c9l'])
                     for _, r in ventas_df.iterrows()
                     if pd.notna(r.get('venta_c9l'))}

        # For current month, use avance C9L (partial) instead of full month
        is_current = [(a == current_year and m == current_month) for a, m in all_months]
        venta_data = []
        for i, (a, m) in enumerate(all_months):
            val = venta_map.get((a, m), None)
            if is_current[i] and avance_c9l > 0:
                val = avance_c9l
            venta_data.append(round(val, 0) if val is not None else None)

        # SOP C9L: only current month point
        sop_data = [None] * len(all_months)
        for i, (a, m) in enumerate(all_months):
            if a == current_year and m == current_month and sop_c9l > 0:
                sop_data[i] = round(sop_c9l, 0)

        # PY Gerente C9L: only current month point
        py_ger_data = [None] * len(all_months)
        for i, (a, m) in enumerate(all_months):
            if a == current_year and m == current_month and py_gerente_c9l > 0:
                py_ger_data[i] = round(py_gerente_c9l, 0)

        # PY Sistema C9L: only current month point
        py_sistema_data = [None] * len(all_months)
        for i, (a, m) in enumerate(all_months):
            if a == current_year and m == current_month and py_sistema_c9l > 0:
                py_sistema_data[i] = round(py_sistema_c9l, 0)

        # Calculate max for Y scale
        all_vals = [v for v in venta_data + sop_data + py_ger_data + py_sistema_data if v is not None and v > 0]
        max_value = max(all_vals) * 1.12 if all_vals else 1000000

        labels_json = json.dumps(labels, ensure_ascii=False)
        venta_json = json.dumps(venta_data)
        sop_json = json.dumps(sop_data)
        py_ger_json = json.dumps(py_ger_data)
        py_sis_json = json.dumps(py_sistema_data)

        current_label = f"{MESES_CORTO.get(current_month, current_month)}'{str(current_year)[-2:]}"

        return f"""
        <div style="margin: 20px 0; background: #f9fafb; padding: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 4px; color: #1e3a8a; font-size: 13px;">
                Senales de Cierre — Evolucion Mensual Nacional (C9L)
            </h4>
            <p style="margin: 0 0 15px 0; font-size: 10.5px; color: #6b7280;">
                {current_label}: avance parcial (linea solida) + proyecciones de cierre (puntos)
            </p>
            <div style="position: relative; height: 320px; width: 100%;">
                <canvas id="{chart_id}"></canvas>
            </div>
        </div>
        <script>
        (function() {{
            var ctx = document.getElementById('{chart_id}');
            if (!ctx) return;

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {labels_json},
                    datasets: [
                        {{
                            label: 'Venta Real',
                            data: {venta_json},
                            borderColor: '{cfg.COLOR_VENTA_REAL}',
                            backgroundColor: '{cfg.COLOR_VENTA_REAL}',
                            borderWidth: 2.5,
                            tension: 0.3,
                            pointRadius: 3,
                            pointHoverRadius: 6,
                            fill: false,
                            spanGaps: false,
                            order: 1
                        }},
                        {{
                            label: 'SOP (Presupuesto)',
                            data: {sop_json},
                            borderColor: '{cfg.COLOR_SOP}',
                            backgroundColor: '{cfg.COLOR_SOP}',
                            borderWidth: 0,
                            pointRadius: 7,
                            pointHoverRadius: 9,
                            pointStyle: 'triangle',
                            fill: false,
                            showLine: false,
                            spanGaps: false,
                            order: 3
                        }},
                        {{
                            label: 'PY Gerente',
                            data: {py_ger_json},
                            borderColor: '#F59E0B',
                            backgroundColor: '#F59E0B',
                            borderWidth: 0,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            pointStyle: 'circle',
                            fill: false,
                            showLine: false,
                            spanGaps: false,
                            order: 2
                        }},
                        {{
                            label: 'PY Sistema (Nowcast)',
                            data: {py_sis_json},
                            borderColor: '{cfg.COLOR_PY_SISTEMA}',
                            backgroundColor: '{cfg.COLOR_PY_SISTEMA}',
                            borderWidth: 0,
                            pointRadius: 7,
                            pointHoverRadius: 9,
                            pointStyle: 'rectRot',
                            fill: false,
                            showLine: false,
                            spanGaps: false,
                            order: 0
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                usePointStyle: true,
                                padding: 15,
                                font: {{ size: 11 }}
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    var value = context.parsed.y;
                                    if (value === null || value === undefined) return null;
                                    return context.dataset.label + ': C9L ' + value.toLocaleString('es-BO', {{
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                    }});
                                }}
                            }},
                            filter: function(item) {{
                                return item.parsed.y !== null;
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            min: 0,
                            max: {max_value:.0f},
                            ticks: {{
                                callback: function(value) {{
                                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                    return value;
                                }},
                                font: {{ size: 10 }}
                            }},
                            grid: {{
                                color: '#e5e7eb'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{ size: 10, weight: '500' }},
                                maxRotation: 0
                            }},
                            grid: {{
                                display: false
                            }}
                        }}
                    }}
                }}
            }});
        }})();
        </script>
        """
