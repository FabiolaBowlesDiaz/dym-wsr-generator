"""
Generador HTML para la sección de Proyección Objetiva del WSR.
Produce tablas comparativas triple pilar, tablas de descomposición
operativa (revenue tree), y estilos CSS asociados.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional

from .. import config as cfg

logger = logging.getLogger(__name__)


class ProjectionHTMLGenerator:
    """Genera HTML para la sección de Proyección Objetiva."""

    def __init__(self, format_number_fn=None):
        """
        Args:
            format_number_fn: Función de formateo de números del HTMLGenerator principal.
                              Si es None, usa un formateador básico.
        """
        self.format_number = format_number_fn or self._default_format

    def generate_full_section(self, projection_data: Dict, chart_html: str = "") -> str:
        """
        Genera la sección HTML completa de Proyección Objetiva.

        Args:
            projection_data: Dict retornado por ProjectionProcessor.generate_projections()
            chart_html: HTML del gráfico Chart.js (generado por projection_chart_generator)

        Returns:
            String HTML de la sección completa
        """
        if not projection_data:
            return ""

        html = '<div class="section">'
        html += '<h2>4. PROYECCIÓN OBJETIVA — COMPARATIVO TRIPLE PILAR</h2>'

        html += self._generate_methodology_note()

        # 4.1 Comparativo por Marca
        html += '<h3>4.1. COMPARATIVO TRIPLE PILAR POR MARCA</h3>'
        html += self._generate_comparativo_table(
            projection_data.get('by_marca', pd.DataFrame()),
            key_col='marcadir',
            key_label='MARCA'
        )

        # Gráfico de barras
        if chart_html:
            html += chart_html

        # 4.2 Descomposición Operativa por Ciudad
        html += '<h3>4.2. DESCOMPOSICIÓN OPERATIVA (REVENUE TREE) POR CIUDAD</h3>'
        html += self._generate_decomposition_table(
            projection_data.get('decomposition_ciudad', pd.DataFrame()),
            key_col='ciudad',
            key_label='CIUDAD'
        )

        # 4.3 Comparativo por Ciudad
        html += '<h3>4.3. COMPARATIVO TRIPLE PILAR POR CIUDAD</h3>'
        html += self._generate_comparativo_table(
            projection_data.get('by_ciudad', pd.DataFrame()),
            key_col='ciudad',
            key_label='CIUDAD'
        )

        # Resumen nacional
        resumen = projection_data.get('resumen_nacional', {})
        if resumen:
            html += self._generate_resumen_cards(resumen)

        html += '</div>'
        return html

    def _generate_methodology_note(self) -> str:
        """Nota metodológica breve sobre los tres pilares."""
        return """
        <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px;
                    padding: 15px; margin: 15px 0; font-size: 12px; color: #0c4a6e;">
            <strong>Metodología:</strong> Esta sección presenta tres perspectivas independientes
            de proyección para el mes en curso:
            <div style="display: flex; gap: 20px; margin-top: 8px;">
                <span><span style="display: inline-block; width: 12px; height: 12px;
                      background: {color_ger}; border-radius: 2px; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>PY Gerente</strong> — Juicio de gerentes regionales</span>
                <span><span style="display: inline-block; width: 12px; height: 12px;
                      background: {color_est}; border-radius: 2px; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>PY Estadística</strong> — Holt-Winters sobre historial 24+ meses</span>
                <span><span style="display: inline-block; width: 12px; height: 12px;
                      background: {color_op}; border-radius: 2px; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>PY Operativa</strong> — Cobertura × Hit Rate × Drop Size</span>
            </div>
        </div>
        """.format(
            color_ger=cfg.COLOR_PY_GERENTE,
            color_est=cfg.COLOR_PY_ESTADISTICA,
            color_op=cfg.COLOR_PY_OPERATIVA
        )

    def _generate_comparativo_table(
        self,
        df: pd.DataFrame,
        key_col: str,
        key_label: str
    ) -> str:
        """
        Genera tabla comparativa triple pilar.

        Columnas: Entidad | PY Gerente | PY Estadística | PY Operativa | Spread | Diagnóstico
        """
        if df.empty:
            return '<p style="color: #6b7280;">No hay datos disponibles para esta vista.</p>'

        html = """
        <div class="table-container">
            <table style="min-width: 900px;">
                <thead>
                    <tr>
                        <th style="text-align: left;">{label}</th>
                        <th style="background: {c_ger};">PY GERENTE 🧑‍💼</th>
                        <th style="background: #2563eb;">PY ESTADÍSTICA 📊</th>
                        <th style="background: #059669;">PY OPERATIVA 🎯</th>
                        <th>SPREAD</th>
                        <th>MODELO</th>
                        <th>DIAGNÓSTICO</th>
                    </tr>
                </thead>
                <tbody>
        """.format(
            label=key_label,
            c_ger='#64748b'
        )

        # Filas de datos
        for _, row in df.iterrows():
            entity = row.get(key_col, 'N/D')
            py_ger = row.get('py_gerente_bob')
            py_est = row.get('py_estadistica_bob')
            py_op = row.get('py_operativa_bob')
            spread = row.get('spread')
            diag = row.get('diagnostico', '')
            model = row.get('model_type', '')

            # Formatear spread
            spread_str = 'N/D'
            spread_class = ''
            if spread is not None and not pd.isna(spread):
                spread_val = float(spread)
                spread_str = f"{spread_val:+.1%}"
                if abs(spread_val) < cfg.SPREAD_CONSENSO_THRESHOLD:
                    spread_class = 'style="background: #ecfdf5; color: #059669; font-weight: bold;"'
                elif spread_val > cfg.SPREAD_OPTIMISTA_THRESHOLD:
                    spread_class = 'style="background: #fef3c7; color: #92400e; font-weight: bold;"'
                elif spread_val < cfg.SPREAD_CONSERVADOR_THRESHOLD:
                    spread_class = 'style="background: #fef3c7; color: #92400e; font-weight: bold;"'

            # Diagnóstico color
            diag_style = ''
            if 'consenso' in str(diag).lower():
                diag_style = 'style="color: #059669; font-weight: bold;"'
            elif 'optimista' in str(diag).lower() or 'conservador' in str(diag).lower():
                diag_style = 'style="color: #d97706; font-weight: bold;"'

            # Modelo label
            model_label = ''
            if model == 'triple':
                model_label = '<span style="color: #059669; font-size: 10px;">HW-3</span>'
            elif model == 'double':
                model_label = '<span style="color: #d97706; font-size: 10px;">HW-2</span>'

            html += f"""
                <tr>
                    <td style="text-align: left; font-weight: 600;">{entity}</td>
                    <td>{self._fmt_bob(py_ger)}</td>
                    <td>{self._fmt_bob(py_est)}</td>
                    <td>{self._fmt_bob(py_op)}</td>
                    <td {spread_class}>{spread_str}</td>
                    <td style="text-align: center;">{model_label}</td>
                    <td {diag_style}>{diag}</td>
                </tr>
            """

        # Fila de totales
        total_ger = df['py_gerente_bob'].dropna().sum() if 'py_gerente_bob' in df else 0
        total_est = df['py_estadistica_bob'].dropna().sum() if 'py_estadistica_bob' in df else 0
        total_op = df['py_operativa_bob'].dropna().sum() if 'py_operativa_bob' in df else 0

        total_spread = ((total_ger / total_est) - 1) if total_est > 0 and total_ger > 0 else None
        total_spread_str = f"{total_spread:+.1%}" if total_spread is not None else 'N/D'

        html += f"""
                <tr class="total-row">
                    <td style="text-align: left;">TOTAL NACIONAL</td>
                    <td>{self._fmt_bob(total_ger)}</td>
                    <td>{self._fmt_bob(total_est)}</td>
                    <td>{self._fmt_bob(total_op)}</td>
                    <td style="font-weight: bold;">{total_spread_str}</td>
                    <td></td>
                    <td></td>
                </tr>
        """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def _generate_decomposition_table(
        self,
        df: pd.DataFrame,
        key_col: str,
        key_label: str
    ) -> str:
        """
        Genera tabla de descomposición operativa (revenue tree).

        Columnas: Entidad | Cobertura | Tend. | Hit Rate | Tend. | Drop Size | Tend. | PY Operativa
        """
        if df.empty:
            return '<p style="color: #6b7280;">No hay datos de descomposición disponibles.</p>'

        html = """
        <div class="table-container">
            <table style="min-width: 1000px;">
                <thead>
                    <tr>
                        <th style="text-align: left;">{label}</th>
                        <th>COBERTURA (clientes)</th>
                        <th>TEND.</th>
                        <th>HIT RATE (%)</th>
                        <th>TEND.</th>
                        <th>DROP SIZE (BOB)</th>
                        <th>TEND.</th>
                        <th style="background: #059669;">PY OPERATIVA</th>
                    </tr>
                </thead>
                <tbody>
        """.format(label=key_label)

        for _, row in df.iterrows():
            entity = row.get(key_col, 'N/D')
            sufficient = row.get('sufficient_data', False)

            if not sufficient:
                html += f"""
                <tr>
                    <td style="text-align: left;">{entity}</td>
                    <td colspan="7" style="text-align: center; color: #9ca3af;">
                        Datos insuficientes para descomposición
                    </td>
                </tr>
                """
                continue

            cob = row.get('cobertura_proj')
            cob_t = row.get('cobertura_trend')
            hr = row.get('hitrate_proj')
            hr_t = row.get('hitrate_trend')
            ds = row.get('dropsize_proj')
            ds_t = row.get('dropsize_trend')
            py_op = row.get('py_operativa_bob')

            html += f"""
                <tr>
                    <td style="text-align: left; font-weight: 500;">{entity}</td>
                    <td>{self._fmt_num(cob, 0)}</td>
                    <td>{self._fmt_trend(cob_t)}</td>
                    <td>{self._fmt_num(hr, 1)}%</td>
                    <td>{self._fmt_trend(hr_t)}</td>
                    <td>{self._fmt_num(ds, 0)}</td>
                    <td>{self._fmt_trend(ds_t)}</td>
                    <td style="font-weight: bold;">{self._fmt_bob(py_op)}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def _generate_resumen_cards(self, resumen: Dict) -> str:
        """Genera cards de resumen nacional del triple pilar."""
        marca = resumen.get('by_marca', {})

        py_ger = marca.get('py_gerente', 0)
        py_est = marca.get('py_estadistica', 0)
        py_op = marca.get('py_operativa', 0)
        spread = marca.get('spread')
        diag = marca.get('diagnostico', '')

        spread_str = f"{spread:+.1%}" if spread is not None else 'N/D'

        # Color del diagnóstico
        diag_bg = cfg.COLOR_CONSENSUS_HIGH if 'consenso' in str(diag).lower() else cfg.COLOR_CONSENSUS_LOW

        return f"""
        <div style="background: {diag_bg}; border: 1px solid #e5e7eb;
                    border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h4 style="margin-bottom: 15px; color: #1e3a8a;">RESUMEN NACIONAL — TRIPLE PILAR</h4>
            <div class="kpi-grid">
                <div class="kpi-card" style="border-left: 4px solid {cfg.COLOR_PY_GERENTE};">
                    <div class="kpi-title">PY GERENTE 🧑‍💼</div>
                    <div class="kpi-value">{self._fmt_millions(py_ger)}M</div>
                    <div class="kpi-subtitle">Proyección de gerentes</div>
                </div>
                <div class="kpi-card" style="border-left: 4px solid {cfg.COLOR_PY_ESTADISTICA};">
                    <div class="kpi-title">PY ESTADÍSTICA 📊</div>
                    <div class="kpi-value">{self._fmt_millions(py_est)}M</div>
                    <div class="kpi-subtitle">Holt-Winters histórico</div>
                </div>
                <div class="kpi-card" style="border-left: 4px solid {cfg.COLOR_PY_OPERATIVA};">
                    <div class="kpi-title">PY OPERATIVA 🎯</div>
                    <div class="kpi-value">{self._fmt_millions(py_op)}M</div>
                    <div class="kpi-subtitle">Cob × HR × DropSize</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">SPREAD / DIAGNÓSTICO</div>
                    <div class="kpi-value" style="font-size: 18px;">{spread_str}</div>
                    <div class="kpi-subtitle">{diag}</div>
                </div>
            </div>
        </div>
        """

    # ------------------------------------------------------------------
    # Helpers de formateo
    # ------------------------------------------------------------------

    def _fmt_bob(self, value) -> str:
        """Formatea valor en BOB con separador de miles."""
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return '<span style="color: #9ca3af;">N/D</span>'
        return f"{value:,.0f}"

    def _fmt_num(self, value, decimals: int = 0) -> str:
        """Formatea número genérico."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return 'N/D'
        return f"{value:,.{decimals}f}"

    def _fmt_millions(self, value) -> str:
        """Formatea en millones con 1 decimal."""
        if value is None or value == 0:
            return '0.0'
        return f"{value / 1_000_000:.1f}"

    def _fmt_trend(self, trend_pct) -> str:
        """Formatea tendencia con flecha y color."""
        if trend_pct is None or (isinstance(trend_pct, float) and np.isnan(trend_pct)):
            return '<span style="color: #9ca3af;">—</span>'

        trend_pct = float(trend_pct)
        if trend_pct > 1:
            return f'<span style="color: {cfg.COLOR_TREND_UP}; font-weight: bold;">↑{trend_pct:+.1f}%</span>'
        elif trend_pct < -1:
            return f'<span style="color: {cfg.COLOR_TREND_DOWN}; font-weight: bold;">↓{trend_pct:+.1f}%</span>'
        else:
            return f'<span style="color: #6b7280;">→{trend_pct:+.1f}%</span>'

    @staticmethod
    def _default_format(value, decimals=2, is_percentage=False, show_plus=False):
        """Formateador de respaldo si no se pasa el del HTMLGenerator."""
        if pd.isna(value):
            return "N/D"
        if is_percentage:
            return f"{value * 100:.2f}%"
        return f"{value:,.{decimals}f}"


def get_projection_css() -> str:
    """
    Retorna CSS adicional para la sección de Proyección Objetiva.
    Debe agregarse al CSS del HTMLGenerator principal.
    """
    return f"""
    /* === Proyección Objetiva === */
    .projection-card {{
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }}

    .projection-card.gerente {{
        border-left: 4px solid {cfg.COLOR_PY_GERENTE};
    }}

    .projection-card.estadistica {{
        border-left: 4px solid {cfg.COLOR_PY_ESTADISTICA};
    }}

    .projection-card.operativa {{
        border-left: 4px solid {cfg.COLOR_PY_OPERATIVA};
    }}

    .trend-up {{
        color: {cfg.COLOR_TREND_UP};
        font-weight: bold;
    }}

    .trend-down {{
        color: {cfg.COLOR_TREND_DOWN};
        font-weight: bold;
    }}

    .consensus-high {{
        background: {cfg.COLOR_CONSENSUS_HIGH};
    }}

    .consensus-low {{
        background: {cfg.COLOR_CONSENSUS_LOW};
    }}
    """
