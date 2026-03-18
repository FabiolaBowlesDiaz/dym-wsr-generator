"""
Generador HTML para la Sección 4: Resumen Ejecutivo — Señales de Cierre.
Produce una gráfica de líneas histórica + tabla resumen con 4 señales.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional

from .. import config as cfg

logger = logging.getLogger(__name__)


class ProjectionHTMLGenerator:
    """Genera HTML para la Sección 4: Resumen Ejecutivo."""

    def __init__(self, format_number_fn=None):
        self.format_number = format_number_fn or self._default_format

    def generate_full_section(
        self,
        chart_html: str,
        sop_nacional: float,
        py_gerente_nacional: float,
        py_sistema_nacional: float,
        avance_nacional: float,
        narrative_html: str = "",
        chart_html_c9l: str = "",
        sop_nacional_c9l: float = 0,
        py_gerente_nacional_c9l: float = 0,
        py_sistema_nacional_c9l: float = 0,
        avance_nacional_c9l: float = 0
    ) -> str:
        """
        Genera la seccion HTML completa del Resumen Ejecutivo.

        Args:
            chart_html: HTML de la grafica de lineas BOB (del chart generator)
            sop_nacional: SOP total del mes actual (BOB)
            py_gerente_nacional: PY Gerente total del mes actual (BOB)
            py_sistema_nacional: PY Sistema (Nowcast) total del mes actual (BOB)
            avance_nacional: Avance acumulado del mes actual (BOB)
            narrative_html: Narrativa IA ejecutiva (opcional)
            chart_html_c9l: HTML de la grafica de lineas C9L
            sop_nacional_c9l: SOP total del mes actual (C9L)
            py_gerente_nacional_c9l: PY Gerente total del mes actual (C9L)
            py_sistema_nacional_c9l: PY Sistema (Nowcast) total del mes actual (C9L)
            avance_nacional_c9l: Avance acumulado del mes actual (C9L)
        """
        html = '<div class="section">'
        html += '<h2>4. RESUMEN EJECUTIVO — SENALES DE CIERRE</h2>'

        # Nota metodologica
        html += self._generate_methodology_note()

        # Grafica historica BOB
        if chart_html:
            html += chart_html

        # Grafica historica C9L
        if chart_html_c9l:
            html += chart_html_c9l

        # Tabla resumen (5 columnas: BOB + C9L)
        html += '<h3 style="margin-top: 20px;">4.1. RESUMEN DE SENALES — MES ACTUAL</h3>'
        html += self._generate_resumen_table(
            sop_nacional, py_gerente_nacional,
            py_sistema_nacional, avance_nacional,
            sop_c9l=sop_nacional_c9l,
            py_gerente_c9l=py_gerente_nacional_c9l,
            py_sistema_c9l=py_sistema_nacional_c9l,
            avance_c9l=avance_nacional_c9l
        )

        # Narrativa IA
        if narrative_html:
            html += narrative_html

        html += '</div>'
        return html

    def _generate_methodology_note(self) -> str:
        """Nota metodológica breve sobre las señales."""
        return """
        <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px;
                    padding: 12px 16px; margin: 12px 0; font-size: 11px; color: #0c4a6e;">
            <strong>Senales de cierre:</strong> Cuatro perspectivas independientes para proyectar
            el cierre del mes.
            <div style="display: flex; gap: 16px; margin-top: 6px; flex-wrap: wrap;">
                <span><span style="display: inline-block; width: 18px; height: 2px;
                      background: {c_vr}; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>Venta Real</strong> — acumulado a la fecha</span>
                <span><span style="display: inline-block; width: 18px; height: 0;
                      border-top: 2px dashed {c_sop}; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>SOP</strong> — presupuesto mensual</span>
                <span><span style="display: inline-block; width: 8px; height: 8px;
                      background: #F59E0B; border-radius: 50%; margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>PY Gerente</strong> — proyeccion de gerentes regionales</span>
                <span><span style="display: inline-block; width: 9px; height: 9px;
                      background: {c_ps}; transform: rotate(45deg); margin-right: 4px;
                      vertical-align: middle;"></span>
                      <strong>PY Sistema</strong> — Nowcast (HW + Run Rate)</span>
            </div>
        </div>
        """.format(
            c_vr=cfg.COLOR_VENTA_REAL,
            c_sop=cfg.COLOR_SOP,
            c_ps=cfg.COLOR_PY_SISTEMA
        )

    def _generate_resumen_table(
        self,
        sop: float,
        py_gerente: float,
        py_sistema: float,
        avance: float,
        sop_c9l: float = 0,
        py_gerente_c9l: float = 0,
        py_sistema_c9l: float = 0,
        avance_c9l: float = 0
    ) -> str:
        """Genera tabla resumen con las 4 senales nacionales (BOB + C9L)."""

        def vs_sop_bob(val):
            if not sop or sop == 0 or not val or val == 0:
                return '—'
            pct = (val / sop) - 1
            color = '#059669' if pct >= 0 else '#DC2626'
            return f'<span style="color: {color}; font-weight: 600;">{pct:+.1%}</span>'

        def pct_sop_bob(val):
            if not sop or sop == 0 or not val:
                return '—'
            pct = val / sop
            return f'{pct:.1%}'

        def vs_sop_c9l(val):
            if not sop_c9l or sop_c9l == 0 or not val or val == 0:
                return '—'
            pct = (val / sop_c9l) - 1
            color = '#059669' if pct >= 0 else '#DC2626'
            return f'<span style="color: {color}; font-weight: 600;">{pct:+.1%}</span>'

        def pct_sop_c9l(val):
            if not sop_c9l or sop_c9l == 0 or not val:
                return '—'
            pct = val / sop_c9l
            return f'{pct:.1%}'

        html = """
        <div class="table-container">
            <table style="min-width: 600px; max-width: 900px;">
                <thead>
                    <tr>
                        <th style="text-align: left;">SENAL</th>
                        <th>MONTO (BOB)</th>
                        <th>vs SOP</th>
                        <th>MONTO (C9L)</th>
                        <th>vs SOP (C9L)</th>
                    </tr>
                </thead>
                <tbody>
        """

        rows = [
            ('SOP (Presupuesto)', sop, '—', sop_c9l, '—'),
            ('PY Gerente', py_gerente, vs_sop_bob(py_gerente), py_gerente_c9l, vs_sop_c9l(py_gerente_c9l)),
            ('PY Sistema (Nowcast)', py_sistema, vs_sop_bob(py_sistema), py_sistema_c9l, vs_sop_c9l(py_sistema_c9l)),
            ('Avance actual', avance, pct_sop_bob(avance) + ' del SOP', avance_c9l, pct_sop_c9l(avance_c9l) + ' del SOP'),
        ]

        styles = [
            f'border-left: 3px solid {cfg.COLOR_SOP};',
            'border-left: 3px solid #F59E0B;',
            f'border-left: 3px solid {cfg.COLOR_PY_SISTEMA};',
            f'border-left: 3px solid {cfg.COLOR_VENTA_REAL};',
        ]

        for i, (label, val_bob, vs_bob, val_c9l, vs_c9l) in enumerate(rows):
            bob_fmt = self._fmt_bob(val_bob) if val_bob and val_bob > 0 else '<span style="color:#9ca3af;">Sin datos</span>'
            c9l_fmt = self._fmt_bob(val_c9l) if val_c9l and val_c9l > 0 else '<span style="color:#9ca3af;">Sin datos</span>'
            html += f"""
                <tr>
                    <td style="text-align: left; font-weight: 600; {styles[i]} padding-left: 10px;">
                        {label}
                    </td>
                    <td style="font-weight: 500;">{bob_fmt}</td>
                    <td>{vs_bob}</td>
                    <td style="font-weight: 500;">{c9l_fmt}</td>
                    <td>{vs_c9l}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fmt_bob(self, value) -> str:
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return '<span style="color: #9ca3af;">N/D</span>'
        return f"{value:,.0f}"

    @staticmethod
    def _default_format(value, decimals=2, is_percentage=False, show_plus=False):
        if pd.isna(value):
            return "N/D"
        if is_percentage:
            return f"{value * 100:.2f}%"
        return f"{value:,.{decimals}f}"


def get_projection_css() -> str:
    """CSS adicional para la sección de Resumen Ejecutivo."""
    return f"""
    /* === Resumen Ejecutivo === */
    .signal-card {{
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }}
    """
