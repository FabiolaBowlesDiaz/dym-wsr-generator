"""
Generador de gráficos Chart.js para la sección de Proyección Objetiva.
Produce un gráfico de barras agrupadas comparando los tres pilares por marca.
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, Optional

from .. import config as cfg

logger = logging.getLogger(__name__)


class ProjectionChartGenerator:
    """Genera gráficos Chart.js para la Proyección Objetiva."""

    def generate_comparison_chart(
        self,
        comparativo_marca: pd.DataFrame,
        chart_id: str = "projectionChart"
    ) -> str:
        """
        Genera gráfico de barras agrupadas con los tres pilares por marca.

        Args:
            comparativo_marca: DataFrame con columnas:
                marcadir, py_gerente_bob, py_estadistica_bob, py_operativa_bob
            chart_id: ID del canvas HTML

        Returns:
            HTML con canvas + script Chart.js
        """
        if comparativo_marca.empty:
            return ""

        # Filtrar marcas con al menos un dato
        df = comparativo_marca.dropna(
            subset=['py_estadistica_bob'], how='all'
        ).copy()

        if df.empty:
            return ""

        # Preparar datos para Chart.js
        labels = df['marcadir'].tolist()

        def safe_list(col):
            """Convierte columna a lista, reemplazando NaN/None con null para JSON."""
            return [
                round(float(v), 0) if v is not None and not pd.isna(v) else None
                for v in df[col]
            ] if col in df.columns else [None] * len(df)

        data_gerente = safe_list('py_gerente_bob')
        data_estadistica = safe_list('py_estadistica_bob')
        data_operativa = safe_list('py_operativa_bob')

        # Calcular max para escala Y
        all_values = [v for v in data_gerente + data_estadistica + data_operativa if v is not None]
        max_value = max(all_values) * 1.15 if all_values else 1000000

        labels_json = json.dumps(labels, ensure_ascii=False)
        data_ger_json = json.dumps(data_gerente)
        data_est_json = json.dumps(data_estadistica)
        data_op_json = json.dumps(data_operativa)

        return f"""
        <div style="margin: 25px 0; background: #f9fafb; padding: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 15px; color: #1e3a8a;">
                Comparativo Visual — Triple Pilar por Marca
            </h4>
            <div style="position: relative; height: 350px; width: 100%;">
                <canvas id="{chart_id}"></canvas>
            </div>
        </div>
        <script>
        (function() {{
            var ctx = document.getElementById('{chart_id}');
            if (!ctx) return;

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {labels_json},
                    datasets: [
                        {{
                            label: 'PY Gerente',
                            data: {data_ger_json},
                            backgroundColor: '{cfg.COLOR_PY_GERENTE}',
                            borderColor: '{cfg.COLOR_PY_GERENTE}',
                            borderWidth: 1,
                            borderRadius: 3,
                            order: 3
                        }},
                        {{
                            label: 'PY Estadística',
                            data: {data_est_json},
                            backgroundColor: '{cfg.COLOR_PY_ESTADISTICA}',
                            borderColor: '{cfg.COLOR_PY_ESTADISTICA}',
                            borderWidth: 1,
                            borderRadius: 3,
                            order: 2
                        }},
                        {{
                            label: 'PY Operativa',
                            data: {data_op_json},
                            backgroundColor: '{cfg.COLOR_PY_OPERATIVA}',
                            borderColor: '{cfg.COLOR_PY_OPERATIVA}',
                            borderWidth: 1,
                            borderRadius: 3,
                            order: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'top',
                            labels: {{
                                usePointStyle: true,
                                pointStyle: 'rectRounded',
                                padding: 20,
                                font: {{ size: 12 }}
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    var value = context.parsed.y;
                                    if (value === null || value === undefined) return context.dataset.label + ': N/D';
                                    return context.dataset.label + ': BOB ' + value.toLocaleString('es-BO', {{
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                    }});
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: {max_value:.0f},
                            ticks: {{
                                callback: function(value) {{
                                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                    return value;
                                }},
                                font: {{ size: 11 }}
                            }},
                            grid: {{
                                color: '#e5e7eb'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                font: {{ size: 11, weight: '500' }},
                                maxRotation: 45,
                                minRotation: 0
                            }},
                            grid: {{
                                display: false
                            }}
                        }}
                    }},
                    barPercentage: 0.85,
                    categoryPercentage: 0.75
                }}
            }});
        }})();
        </script>
        """

    def generate_decomposition_chart(
        self,
        decomposition_ciudad: pd.DataFrame,
        chart_id: str = "decompChart"
    ) -> str:
        """
        Genera gráfico horizontal de barras apiladas mostrando la contribución
        de cada componente (Cob × HR × DS) por ciudad.

        Args:
            decomposition_ciudad: DataFrame con cobertura_proj, hitrate_proj, dropsize_proj
            chart_id: ID del canvas

        Returns:
            HTML con gráfico de descomposición
        """
        if decomposition_ciudad.empty:
            return ""

        df = decomposition_ciudad[
            decomposition_ciudad['sufficient_data'] == True
        ].copy()

        if df.empty:
            return ""

        labels = df['ciudad'].tolist()

        # Para visualización proporcional, normalizar cada componente
        cob_vals = [round(float(v), 0) if v is not None else 0
                    for v in df['cobertura_proj']]
        hr_vals = [round(float(v), 1) if v is not None else 0
                   for v in df['hitrate_proj']]
        ds_vals = [round(float(v), 0) if v is not None else 0
                   for v in df['dropsize_proj']]
        py_vals = [round(float(v), 0) if v is not None else 0
                   for v in df['py_operativa_bob']]

        labels_json = json.dumps(labels, ensure_ascii=False)
        py_json = json.dumps(py_vals)

        return f"""
        <div style="margin: 15px 0; background: #f9fafb; padding: 15px; border-radius: 8px;">
            <h4 style="margin-bottom: 10px; color: #1e3a8a;">
                PY Operativa por Ciudad (Cob × HR × DS)
            </h4>
            <div style="position: relative; height: 280px; width: 100%;">
                <canvas id="{chart_id}"></canvas>
            </div>
        </div>
        <script>
        (function() {{
            var ctx = document.getElementById('{chart_id}');
            if (!ctx) return;

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {labels_json},
                    datasets: [{{
                        label: 'PY Operativa (BOB)',
                        data: {py_json},
                        backgroundColor: '{cfg.COLOR_PY_OPERATIVA}',
                        borderColor: '#059669',
                        borderWidth: 1,
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(ctx) {{
                                    return 'BOB ' + ctx.parsed.x.toLocaleString('es-BO');
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: function(v) {{
                                    if (v >= 1000000) return (v/1000000).toFixed(1) + 'M';
                                    if (v >= 1000) return (v/1000).toFixed(0) + 'K';
                                    return v;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }})();
        </script>
        """
