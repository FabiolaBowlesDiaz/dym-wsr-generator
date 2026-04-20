"""
Tablas HTML para el WSR Brand Owner (Pernod Ricard).

Solo unidades C9L. Columnas renombradas a nomenclatura Brand Owner:
LY, Mensual, MTD, PY GRCs, Auto PY, Spread, GRCs/Mensual, MTD/Mensual, GRCs VS LY, Stock, Cobertura.

Sin BOB, sin Ppto General, sin IngNeto/Precio, sin KPIs de gestion.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BrandOwnerTableGenerator:
    """Generador de tablas HTML para el WSR Brand Owner"""

    def __init__(self, html_generator):
        """
        Args:
            html_generator: Instancia con format_number(), current_year, etc.
        """
        self.gen = html_generator
        self.current_year = html_generator.current_year
        self.current_day = html_generator.current_day
        self.current_week = html_generator.current_week
        self.previous_year = html_generator.previous_year
        self.yy = str(self.current_year)[2:]    # '26'
        self.yy_prev = str(self.previous_year)[2:]  # '25'

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _kpi_class(self, value):
        """Clase CSS para colorear KPIs (>5% verde, <-5% rojo, neutro)"""
        if pd.isna(value) or (isinstance(value, float) and np.isinf(value)):
            return "neutral"
        if value > 0.05:
            return "positive"
        elif value < -0.05:
            return "negative"
        return "neutral"

    def _fmt(self, value, decimals=2, pct=False, plus=False):
        """Shortcut para format_number"""
        return self.gen.format_number(value, decimals=decimals,
                                       is_percentage=pct, show_plus=plus)

    def _calc_py_c9l(self, row):
        """Calcular PY C9L: (Avance_C9L * PY_BOB) / Avance_BOB"""
        avance_c9l = row.get(f'avance_{self.current_year}_c9l', 0)
        avance_bob = row.get(f'avance_{self.current_year}_bob', 0)
        py_bob = row.get(f'py_{self.current_year}_bob', 0)
        if avance_bob > 0:
            return (avance_c9l * py_bob) / avance_bob
        return 0

    # ------------------------------------------------------------------
    # MARCA TABLES — Entry Point
    # ------------------------------------------------------------------

    def generate_marca_tables(self, df: pd.DataFrame,
                               estructura_jerarquica: dict = None,
                               narrative_html: str = "",
                               drivers_data: dict = None,
                               drivers_narrative_html: str = "",
                               valid_marcas: list = None) -> str:
        """Generar tablas de marca para Brand Owner (solo C9L)"""
        if df.empty:
            return "<p>No hay datos disponibles para marcas</p>"

        html = ""

        # Tabla performance C9L con drilldown
        if estructura_jerarquica:
            html += self._generate_marca_performance_drilldown(estructura_jerarquica)
        else:
            html += self._generate_marca_performance(df)

        # Narrativa IA PY Sistema (si existe)
        if narrative_html:
            html += narrative_html

        # Drivers — solo Cobertura
        if drivers_data:
            html += self._generate_drivers_cobertura(
                drivers_data, drivers_narrative_html, valid_marcas)

        # Tabla semanal C9L
        html += self._generate_marca_semanal(df)

        return html

    # ------------------------------------------------------------------
    # PERFORMANCE POR MARCA (C9L, columnas Brand Owner)
    # ------------------------------------------------------------------

    def _generate_marca_performance_drilldown(self, estructura: dict) -> str:
        """Tabla C9L con drilldown por subfamilia, columnas Brand Owner"""

        html = f"""
        <h3>PERFORMANCE POR MARCA (Con desglose por Subfamilia)</h3>
        <div class="table-container">
        <table id="tabla-bo-marca">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Marca / Subfamilia</th>
                    <th>LY</th>
                    <th>Mensual</th>
                    <th>MTD</th>
                    <th>PY GRCs</th>
                    <th>Auto PY</th>
                    <th>Spread</th>
                    <th>GRCs/Mensual</th>
                    <th>MTD/Mensual</th>
                    <th>GRCs VS LY</th>
                    <th>Stock</th>
                    <th>Cobertura (días)</th>
                </tr>
            </thead>
            <tbody>
        """

        df_marca = estructura.get('marca_totales')
        df_subfamilia = estructura.get('marca_subfamilia')

        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'

        for idx, row in df_marca.iterrows():
            marca = row['marcadir']
            marca_id = marca.replace(' ', '_').replace('.', '')

            vendido = row.get(vendido_col, 0)
            sop = row.get('sop_c9l', 0)
            avance = row.get(avance_col, 0)
            py = self._calc_py_c9l(row)

            # KPIs
            py_sop = ((py / sop) - 1) if sop > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

            stock = row.get('stock_c9l', 0)
            cobertura = row.get('cobertura_dias', 0)
            py_sist = row.get('py_sistema_c9l', 0)
            # Spread = (PY_gerente_c9l / PY_sistema_c9l) - 1
            # Calculado on-the-fly porque py gerente C9L no existe como columna
            spread = ((py / py_sist) - 1) if py_sist > 0 and py > 0 else None

            # Subfamilias
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca] if not df_subfamilia.empty else pd.DataFrame()
            tiene_sub = not subfamilias.empty

            # CSS
            spread_class = self._kpi_class(spread) if spread is not None and spread == spread else ''
            spread_display = self._fmt(spread, pct=True) if spread is not None and spread == spread else '-'

            expand_btn = f'<span class="expand-icon" onclick="toggleBOMarca(\'{marca_id}\')">[+]</span>' if tiene_sub else ''

            html += f"""
                <tr class="marca-row" data-marca="{marca_id}">
                    <td class="expand-cell">{expand_btn}</td>
                    <td class="marca-nombre"><strong>{marca}</strong></td>
                    <td class="text-right">{self._fmt(vendido)}</td>
                    <td class="text-right">{self._fmt(sop)}</td>
                    <td class="text-right">{self._fmt(avance)}</td>
                    <td class="text-right">{self._fmt(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self._fmt(py_sist) if py_sist else '-'}</td>
                    <td class="text-right {spread_class}" style="font-weight: 600; background: #FFF7ED;">{spread_display}</td>
                    <td class="text-right {self._kpi_class(py_sop)}">{self._fmt(py_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(av_sop)}">{self._fmt(av_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(py_v)}">{self._fmt(py_v, pct=True)}</td>
                    <td class="text-right">{self._fmt(stock, 0)}</td>
                    <td class="text-right">{self._fmt(cobertura, 0)}</td>
                </tr>
            """

            # Subfamilias (ocultas)
            if tiene_sub:
                for _, sub in subfamilias.iterrows():
                    s_vendido = sub.get(vendido_col, 0)
                    s_sop = sub.get('sop_c9l', 0)
                    s_avance = sub.get(avance_col, 0)
                    s_av_sop = ((s_avance / s_sop) - 1) if s_sop > 0 else 0
                    s_stock = sub.get('stock_c9l', 0)
                    s_cob = sub.get('cobertura_dias', 0)

                    html += f"""
                    <tr class="subfamilia-row subfamilia-bo-{marca_id}" style="display: none;">
                        <td></td>
                        <td class="subfamilia-indent">\u251c\u2500 {sub.get('subfamilia', '')}</td>
                        <td class="text-right">{self._fmt(s_vendido)}</td>
                        <td class="text-right">{self._fmt(s_sop)}</td>
                        <td class="text-right">{self._fmt(s_avance)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right" style="color: #1d4ed8; background: #EFF6FF;">-</td>
                        <td class="text-right" style="background: #FFF7ED;">-</td>
                        <td class="text-right">-</td>
                        <td class="text-right {self._kpi_class(s_av_sop)}">{self._fmt(s_av_sop, pct=True)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right">{self._fmt(s_stock, 0)}</td>
                        <td class="text-right">{self._fmt(s_cob, 0)}</td>
                    </tr>
                    """

        # TOTAL row
        t_vendido = df_marca[vendido_col].sum() if vendido_col in df_marca.columns else 0
        t_sop = df_marca['sop_c9l'].sum() if 'sop_c9l' in df_marca.columns else 0
        t_avance = df_marca[avance_col].sum() if avance_col in df_marca.columns else 0

        t_avance_bob = df_marca[f'avance_{self.current_year}_bob'].sum() if f'avance_{self.current_year}_bob' in df_marca.columns else 0
        t_py_bob = df_marca[f'py_{self.current_year}_bob'].sum() if f'py_{self.current_year}_bob' in df_marca.columns else 0
        t_py = (t_avance * t_py_bob / t_avance_bob) if t_avance_bob > 0 else 0

        t_stock = df_marca['stock_c9l'].sum() if 'stock_c9l' in df_marca.columns else 0
        t_py_sist = df_marca['py_sistema_c9l'].sum() if 'py_sistema_c9l' in df_marca.columns else 0
        t_vpd = df_marca['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df_marca.columns else 0
        t_cob = (t_stock / t_vpd) if t_vpd > 0 else 0

        t_py_sop = ((t_py / t_sop) - 1) if t_sop > 0 else 0
        t_av_sop = ((t_avance / t_sop) - 1) if t_sop > 0 else 0
        t_py_v = ((t_py / t_vendido) - 1) if t_vendido > 0 else 0
        t_spread = ((t_py / t_py_sist) - 1) if t_py_sist > 0 else None
        t_spread_display = self._fmt(t_spread, pct=True) if t_spread is not None else '-'
        t_spread_class = self._kpi_class(t_spread) if t_spread is not None else ''

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_vendido)}</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_sop)}</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_avance)}</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_py)}</strong></td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self._fmt(t_py_sist) if t_py_sist else '-'}</strong></td>
                    <td class="text-right {t_spread_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{t_spread_display}</strong></td>
                    <td class="text-right {self._kpi_class(t_py_sop)}"><strong>{self._fmt(t_py_sop, pct=True)}</strong></td>
                    <td class="text-right {self._kpi_class(t_av_sop)}"><strong>{self._fmt(t_av_sop, pct=True)}</strong></td>
                    <td class="text-right {self._kpi_class(t_py_v)}"><strong>{self._fmt(t_py_v, pct=True)}</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_stock, 0)}</strong></td>
                    <td class="text-right"><strong>{self._fmt(t_cob, 0)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        <script>
        function toggleBOMarca(marca) {{
            const rows = document.querySelectorAll('.subfamilia-bo-' + marca);
            const icon = event.target;
            const isExpanded = icon.textContent === '[-]';
            rows.forEach(row => {{ row.style.display = isExpanded ? 'none' : ''; }});
            icon.textContent = isExpanded ? '[+]' : '[-]';
        }}
        </script>
        """
        return html

    def _generate_marca_performance(self, df: pd.DataFrame) -> str:
        """Tabla C9L plana (sin drilldown) — fallback si no hay estructura"""

        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'

        html = f"""
        <h3>PERFORMANCE POR MARCA</h3>
        <div class="table-container">
        <table>
            <thead><tr>
                <th>Marca</th><th>LY</th><th>Mensual</th><th>MTD</th>
                <th>PY GRCs</th><th>Auto PY</th><th>Spread</th>
                <th>GRCs/Mensual</th><th>MTD/Mensual</th><th>GRCs VS LY</th>
                <th>Stock</th><th>Cobertura (días)</th>
            </tr></thead>
            <tbody>
        """

        for _, row in df.iterrows():
            vendido = row.get(vendido_col, 0)
            sop = row.get('sop_c9l', 0)
            avance = row.get(avance_col, 0)
            py = self._calc_py_c9l(row)

            py_sop = ((py / sop) - 1) if sop > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

            py_sist = row.get('py_sistema_c9l', 0)
            spread = ((py / py_sist) - 1) if py_sist > 0 and py > 0 else None
            spread_display = self._fmt(spread, pct=True) if spread is not None and spread == spread else '-'

            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td class="text-right">{self._fmt(vendido)}</td>
                    <td class="text-right">{self._fmt(sop)}</td>
                    <td class="text-right">{self._fmt(avance)}</td>
                    <td class="text-right">{self._fmt(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self._fmt(py_sist) if py_sist else '-'}</td>
                    <td class="text-right" style="font-weight: 600; background: #FFF7ED;">{spread_display}</td>
                    <td class="text-right {self._kpi_class(py_sop)}">{self._fmt(py_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(av_sop)}">{self._fmt(av_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(py_v)}">{self._fmt(py_v, pct=True)}</td>
                    <td class="text-right">{self._fmt(row.get('stock_c9l', 0), 0)}</td>
                    <td class="text-right">{self._fmt(row.get('cobertura_dias', 0), 0)}</td>
                </tr>
            """

        html += "</tbody></table></div>"
        return html

    # ------------------------------------------------------------------
    # SEMANAL POR MARCA (C9L)
    # ------------------------------------------------------------------

    def _generate_marca_semanal(self, df: pd.DataFrame) -> str:
        """Tabla semanal de ventas por marca (solo C9L)"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR MARCA</h3>
        <div class="table-container">
        <table><thead><tr>
            <th>Marca</th><th>Semana 1</th><th>Semana 2</th>
            <th>Semana 3</th><th>Semana 4</th><th>Semana 5</th><th>Total Mes</th>
        </tr></thead><tbody>
        """

        for _, row in df.iterrows():
            s = [row.get(f'semana{i}_c9l', 0) if self.current_week >= i else 0 for i in range(1, 6)]
            total = sum(s)
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self._fmt(s[0])}</td>
                    <td>{self._fmt(s[1]) if self.current_week >= 2 else ''}</td>
                    <td>{self._fmt(s[2]) if self.current_week >= 3 else ''}</td>
                    <td>{self._fmt(s[3]) if self.current_week >= 4 else ''}</td>
                    <td>{self._fmt(s[4]) if self.current_week >= 5 else ''}</td>
                    <td>{self._fmt(total)}</td>
                </tr>
            """

        # Totals
        totals = [df[f'semana{i}_c9l'].sum() if f'semana{i}_c9l' in df.columns and self.current_week >= i else 0
                  for i in range(1, 6)]
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self._fmt(totals[0])}</strong></td>
                    <td><strong>{self._fmt(totals[1]) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self._fmt(totals[2]) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self._fmt(totals[3]) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self._fmt(totals[4]) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self._fmt(sum(totals))}</strong></td>
                </tr>
            </tbody></table></div>
        """
        return html

    # ------------------------------------------------------------------
    # CANAL TABLES (C9L, columnas Brand Owner)
    # ------------------------------------------------------------------

    def generate_canal_tables(self, df: pd.DataFrame,
                               estructura_canal: dict = None,
                               drivers_data: dict = None,
                               drivers_narrative_html: str = "") -> str:
        """Generar tablas de canal para Brand Owner (solo C9L con apertura por marca)"""
        if df.empty:
            return "<p>No hay datos disponibles para canales</p>"

        html = ""

        # Tabla performance canal con drilldown por marca
        if estructura_canal:
            html += self._generate_canal_performance_drilldown(estructura_canal)
        else:
            html += self._generate_canal_performance(df)

        # Drivers — solo Cobertura por canal
        if drivers_data:
            html += self._generate_drivers_cobertura(
                drivers_data, drivers_narrative_html, level='canal')

        # Tabla semanal canal
        html += self._generate_canal_semanal(df)

        return html

    def _generate_canal_performance(self, df: pd.DataFrame) -> str:
        """Tabla C9L performance por canal (sin drilldown)"""

        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'

        html = f"""
        <h3>PERFORMANCE POR CANAL</h3>
        <div class="table-container">
        <table><thead><tr>
            <th>Canal</th><th>LY</th><th>Mensual</th><th>MTD</th>
            <th>PY GRCs</th><th>GRCs/Mensual</th><th>MTD/Mensual</th><th>GRCs VS LY</th>
        </tr></thead><tbody>
        """

        for _, row in df.iterrows():
            vendido = row.get(vendido_col, 0)
            sop = row.get('sop_c9l', 0)
            avance = row.get(avance_col, 0)

            # Canal C9L PY: misma formula proporcional
            avance_bob = row.get(f'avance_{self.current_year}_bob', 0)
            py_bob = row.get(f'py_{self.current_year}_bob', 0)
            py = (avance * py_bob / avance_bob) if avance_bob > 0 else 0

            py_sop = ((py / sop) - 1) if sop > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td class="text-right">{self._fmt(vendido)}</td>
                    <td class="text-right">{self._fmt(sop)}</td>
                    <td class="text-right">{self._fmt(avance)}</td>
                    <td class="text-right">{self._fmt(py)}</td>
                    <td class="text-right {self._kpi_class(py_sop)}">{self._fmt(py_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(av_sop)}">{self._fmt(av_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(py_v)}">{self._fmt(py_v, pct=True)}</td>
                </tr>
            """

        html += "</tbody></table></div>"
        return html

    def _generate_canal_performance_drilldown(self, estructura_canal: dict) -> str:
        """Tabla C9L canal con drilldown por marca"""

        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'

        html = f"""
        <h3>PERFORMANCE POR CANAL (Con desglose por Marca)</h3>
        <div class="table-container">
        <table id="tabla-bo-canal">
            <thead><tr>
                <th style="width: 30px;"></th>
                <th>Canal / Marca</th><th>LY</th><th>Mensual</th><th>MTD</th>
                <th>PY GRCs</th><th>GRCs/Mensual</th><th>MTD/Mensual</th><th>GRCs VS LY</th>
            </tr></thead>
            <tbody>
        """

        df_canal = estructura_canal.get('canal_totales')
        df_canal_marca = estructura_canal.get('canal_marca')

        for _, canal_row in df_canal.iterrows():
            canal = canal_row['canal']
            canal_id = canal.replace(' ', '_').replace('.', '')

            vendido = canal_row.get(vendido_col, 0)
            sop = canal_row.get('sop_c9l', 0)
            avance = canal_row.get(avance_col, 0)
            avance_bob = canal_row.get(f'avance_{self.current_year}_bob', 0)
            py_bob = canal_row.get(f'py_{self.current_year}_bob', 0)
            py = (avance * py_bob / avance_bob) if avance_bob > 0 else 0

            py_sop = ((py / sop) - 1) if sop > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

            # Check for marca detail
            marcas = df_canal_marca[df_canal_marca['canal'] == canal] if df_canal_marca is not None and not df_canal_marca.empty else pd.DataFrame()
            tiene_marcas = not marcas.empty

            expand_btn = f'<span class="expand-icon" onclick="toggleBOCanal(\'{canal_id}\')">[+]</span>' if tiene_marcas else ''

            html += f"""
                <tr class="marca-row">
                    <td class="expand-cell">{expand_btn}</td>
                    <td class="marca-nombre"><strong>{canal}</strong></td>
                    <td class="text-right">{self._fmt(vendido)}</td>
                    <td class="text-right">{self._fmt(sop)}</td>
                    <td class="text-right">{self._fmt(avance)}</td>
                    <td class="text-right">{self._fmt(py)}</td>
                    <td class="text-right {self._kpi_class(py_sop)}">{self._fmt(py_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(av_sop)}">{self._fmt(av_sop, pct=True)}</td>
                    <td class="text-right {self._kpi_class(py_v)}">{self._fmt(py_v, pct=True)}</td>
                </tr>
            """

            # Marca rows (hidden)
            if tiene_marcas:
                for _, m_row in marcas.iterrows():
                    m_vendido = m_row.get(vendido_col, 0)
                    m_sop = m_row.get('sop_c9l', 0)
                    m_avance = m_row.get(avance_col, 0)
                    m_av_sop = ((m_avance / m_sop) - 1) if m_sop > 0 else 0

                    html += f"""
                    <tr class="subfamilia-row canal-bo-{canal_id}" style="display: none;">
                        <td></td>
                        <td class="subfamilia-indent">\u251c\u2500 {m_row.get('marcadir', '')}</td>
                        <td class="text-right">{self._fmt(m_vendido)}</td>
                        <td class="text-right">{self._fmt(m_sop)}</td>
                        <td class="text-right">{self._fmt(m_avance)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right">-</td>
                        <td class="text-right {self._kpi_class(m_av_sop)}">{self._fmt(m_av_sop, pct=True)}</td>
                        <td class="text-right">-</td>
                    </tr>
                    """

        html += """
            </tbody></table></div>
        <script>
        function toggleBOCanal(canal) {
            const rows = document.querySelectorAll('.canal-bo-' + canal);
            const icon = event.target;
            const isExpanded = icon.textContent === '[-]';
            rows.forEach(row => { row.style.display = isExpanded ? 'none' : ''; });
            icon.textContent = isExpanded ? '[+]' : '[-]';
        }
        </script>
        """
        return html

    def _generate_canal_semanal(self, df: pd.DataFrame) -> str:
        """Tabla semanal de ventas por canal (solo C9L)"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR CANAL</h3>
        <div class="table-container">
        <table><thead><tr>
            <th>Canal</th><th>Semana 1</th><th>Semana 2</th>
            <th>Semana 3</th><th>Semana 4</th><th>Semana 5</th><th>Total Mes</th>
        </tr></thead><tbody>
        """

        for _, row in df.iterrows():
            s = [row.get(f'semana{i}_c9l', 0) if self.current_week >= i else 0 for i in range(1, 6)]
            total = sum(s)
            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self._fmt(s[0])}</td>
                    <td>{self._fmt(s[1]) if self.current_week >= 2 else ''}</td>
                    <td>{self._fmt(s[2]) if self.current_week >= 3 else ''}</td>
                    <td>{self._fmt(s[3]) if self.current_week >= 4 else ''}</td>
                    <td>{self._fmt(s[4]) if self.current_week >= 5 else ''}</td>
                    <td>{self._fmt(total)}</td>
                </tr>
            """

        html += "</tbody></table></div>"
        return html

    # ------------------------------------------------------------------
    # DRIVERS — Solo Cobertura
    # ------------------------------------------------------------------

    def _generate_drivers_cobertura(self, drivers_data: dict,
                                     narrative_html: str = "",
                                     valid_marcas: list = None,
                                     level: str = 'marca') -> str:
        """
        Genera tabla de drivers mostrando SOLO Cobertura (clientes padre unicos).
        Sin Efectividad, Hit Rate, ni Drop Size.
        """

        if level == 'marca':
            df = drivers_data.get('by_marca')
            title = "DRIVERS DE PERFORMANCE POR MARCA"
            entity_col = 'marca'
        elif level == 'canal':
            df = drivers_data.get('by_canal')
            title = "DRIVERS DE PERFORMANCE POR CANAL"
            entity_col = 'canal'
        else:
            return ""

        if df is None or df.empty:
            return ""

        # Filter to valid brands if provided
        if valid_marcas and entity_col == 'marca':
            valid_upper = {m.upper() for m in valid_marcas}
            df = df[df[entity_col].str.upper().isin(valid_upper)].copy()

        # Parse narratives
        narratives = {}
        if narrative_html:
            narratives = self._parse_narrative_per_marca(narrative_html)

        html = f"""
        <div style="margin: 25px 0; padding: 20px; background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0 0 4px 0; color: #1e293b; font-size: 15px;">
                {title}
            </h3>
            <p style="margin: 0 0 6px 0; color: #64748b; font-size: 11px;">
                Periodo: <strong>Actual (al dia {self.current_day})</strong> &nbsp;|&nbsp;
                vs <strong>Mismo periodo ano anterior</strong>
            </p>
            <p style="margin: 0 0 15px 0; color: #94a3b8; font-size: 10px;">
                <strong>Cobertura (cli)</strong> = clientes padre unicos (Distinctcount Cod. Cliente Padre)
                &nbsp;|&nbsp; <em>Same-to-Date</em>
            </p>
            <div style="overflow-x: auto;">
            <table style="font-size: 11px; width: 100%; border-collapse: collapse; min-width: 600px;">
                <colgroup>
                    <col style="width: 140px;">
                    <col style="width: 90px;">
                    <col style="width: 90px;">
                    <col>
                </colgroup>
                <thead>
                    <tr>
                        <th style="text-align: left;">{entity_col.title()}</th>
                        <th>Cobertura<br>(cli padre)</th>
                        <th>&Delta; VS LY</th>
                        <th style="text-align: left;">Comentario</th>
                    </tr>
                </thead>
                <tbody>
        """

        for _, row in df.iterrows():
            entity = row.get(entity_col, '')
            # Usar cobertura (cod_cliente = clientes reales), no cobertura_real (items padre)
            cob = row.get('cobertura', row.get('cobertura_real', 0))
            cob_trend = row.get('cobertura_trend', row.get('cobertura_real_trend', None))

            # Format trend
            if cob_trend is not None and not (isinstance(cob_trend, float) and np.isnan(cob_trend)):
                pct = cob_trend * 100
                if pct > 2:
                    arrow = f'<span style="color: #059669;">\u25b2 {pct:+.1f}%</span>'
                elif pct < -2:
                    arrow = f'<span style="color: #dc2626;">\u25bc {pct:+.1f}%</span>'
                else:
                    arrow = f'<span style="color: #6b7280;">\u25b6 {pct:+.1f}%</span>'
            else:
                arrow = '-'

            # Get narrative for this entity
            comment = narratives.get(entity.upper(), '')
            if not comment:
                # Simple programmatic fallback
                if cob_trend is not None and not np.isnan(cob_trend):
                    if cob_trend > 0.05:
                        comment = 'Crecimiento en cobertura vs periodo anterior'
                    elif cob_trend < -0.05:
                        comment = 'Contraccion en cobertura — revisar alcance'
                    else:
                        comment = 'Cobertura estable'

            html += f"""
                    <tr style="border-bottom: 1px solid #e5e7eb;">
                        <td style="padding: 8px 6px; font-weight: 600;">{entity}</td>
                        <td style="padding: 8px 6px; text-align: right;">{int(cob):,}</td>
                        <td style="padding: 8px 6px; text-align: center;">{arrow}</td>
                        <td style="padding: 8px 10px; font-size: 10.5px; line-height: 1.5; color: #374151;">{comment}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
            </div>
        </div>
        """
        return html

    @staticmethod
    def _parse_narrative_per_marca(narrative_html: str) -> dict:
        """Parsea narrativa HTML en {MARCA_UPPER: texto_limpio}."""
        result = {}
        if not narrative_html:
            return result
        for li_match in re.finditer(r'<li[^>]*>(.*?)</li>', narrative_html, re.DOTALL):
            li_content = li_match.group(1)
            strong_match = re.search(r'<strong>\s*([^<]+?)\s*[—–\-]\s*', li_content)
            if strong_match:
                marca = strong_match.group(1).strip().upper()
                clean = re.sub(r'<[^>]+>', '', li_content).strip()
                dash_pos = clean.find('—')
                if dash_pos == -1:
                    dash_pos = clean.find('–')
                if dash_pos > 0:
                    clean = clean[dash_pos + 1:].strip()
                result[marca] = clean
        return result

    # ------------------------------------------------------------------
    # STOCK Y COBERTURA
    # ------------------------------------------------------------------

    def generate_stock_table(self, df: pd.DataFrame) -> str:
        """Tabla de stock y cobertura por marca"""

        html = """
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Stock Total (C9L)</th>
                    <th>Venta Promedio Diaria</th>
                    <th>Cobertura (días)</th>
                    <th>Estado</th>
                    <th>Recomendación</th>
                </tr>
            </thead>
            <tbody>
        """

        for _, row in df.iterrows():
            stock = row.get('stock_c9l', 0)
            vpd = row.get('venta_promedio_diaria_c9l', 0)
            cobertura = row.get('cobertura_dias', 0)

            # Estado y recomendacion
            if cobertura <= 15:
                estado = '\U0001f534 Critico'
                recomendacion = 'Reabastecer pronto'
            elif cobertura <= 30:
                estado = '\U0001f7e1 Normal'
                recomendacion = 'Monitorear'
            elif cobertura <= 90:
                estado = '\U0001f7e2 Bien'
                recomendacion = 'Stock saludable'
            else:
                estado = '\u26a0\ufe0f Exceso'
                recomendacion = 'Reducir inventario'

            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self._fmt(stock, 0)}</td>
                    <td>{self._fmt(vpd)}</td>
                    <td>{self._fmt(cobertura, 0)}</td>
                    <td>{estado}</td>
                    <td>{recomendacion}</td>
                </tr>
            """

        html += "</tbody></table>"
        return html
