"""
Módulo de generación de tablas HTML para WSR
Contiene todas las funciones para generar tablas específicas
"""

import pandas as pd
import numpy as np
from typing import Optional


class HTMLTableGenerator:
    """Generador de tablas HTML para el WSR"""
    
    def __init__(self, html_generator):
        """
        Inicializar con referencia al generador HTML principal
        
        Args:
            html_generator: Instancia del HTMLGenerator
        """
        self.gen = html_generator
        self.current_year = html_generator.current_year
        self.current_day = html_generator.current_day
        self.current_week = html_generator.current_week
        self.previous_year = html_generator.previous_year
    
    def generate_marca_tables(self, df: pd.DataFrame, estructura_jerarquica: dict = None,
                              narrative_html: str = "", drivers_data: dict = None,
                              drivers_narrative_html: str = "",
                              valid_marcas: list = None) -> str:
        """Generar todas las tablas de marca"""
        if df.empty:
            return "<p>No hay datos disponibles para marcas</p>"

        html = ""
        # Si tenemos estructura jerárquica, usar las nuevas tablas con drill-down
        if estructura_jerarquica:
            html += self.generate_marca_performance_bob_drilldown(estructura_jerarquica)
        else:
            html += self.generate_marca_performance_bob(df)

        # Insertar narrativa IA de PY Sistema justo después de la tabla BOB performance
        if narrative_html:
            html += narrative_html

        # Insertar Drivers de Performance (Pilar 3) después de la narrativa, antes de semanal
        if drivers_data:
            html += self.generate_drivers_section(
                drivers_data, drivers_narrative_html, level="marca",
                valid_marcas=valid_marcas
            )

        html += self.generate_marca_semanal_bob(df)

        # Tabla C9L con drill-down si disponible
        if estructura_jerarquica:
            html += self.generate_marca_performance_c9l_drilldown(estructura_jerarquica)
        else:
            html += self.generate_marca_performance_c9l(df)

        html += self.generate_marca_semanal_c9l(df)

        return html
    
    def generate_marca_performance_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por marca en BOB"""

        html = f"""
        <h3>PERFORMANCE POR MARCA - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Vendido {self.previous_year} (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance {self.current_year} (BOB)</th>
                    <th>Proyección de Cierre {self.current_year} (BOB)</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                    <th>IngNeto/C9L {self.previous_year}</th>
                    <th>IngNeto/C9L {self.current_year}</th>
                    <th>%Inc/Dec Precio</th>
                    <th>Stock (C9L)</th>
                    <th>Cobertura (días)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'
        precio_prev = f'precio_{self.previous_year}'
        precio_curr = f'precio_{self.current_year}'
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_bob', 0)
            sop = row.get('sop_bob', 0)
            avance = row[avance_col] if avance_col in df.columns else 0
            py = row[py_col] if py_col in df.columns else 0
            av_pg = row.get('AV_PG', 0)
            av_sop = row.get('AV_SOP', 0)
            py_v = row.get('PY_V', 0)
            precio_24 = row[precio_prev] if precio_prev in df.columns else 0
            precio_25 = row[precio_curr] if precio_curr in df.columns else 0
            inc_precio = row.get('inc_precio', 0)
            stock = row.get('stock_c9l', 0)
            cobertura = row.get('cobertura_dias', 0)
            
            # Determinar clases CSS para KPIs
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            inc_precio_class = self._get_kpi_class(inc_precio)
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                    <td>{self.gen.format_number(precio_24)}</td>
                    <td>{self.gen.format_number(precio_25)}</td>
                    <td class="{inc_precio_class}">{self.gen.format_number(inc_precio, is_percentage=True)}</td>
                    <td>{self.gen.format_number(stock, 0)}</td>
                    <td>{self.gen.format_number(cobertura, 0)}</td>
                </tr>
            """
        
        # Fila de totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_bob'].sum() if 'ppto_general_bob' in df.columns else 0
        total_sop = df['sop_bob'].sum() if 'sop_bob' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = df[py_col].sum() if py_col in df.columns else 0
        total_stock = df['stock_c9l'].sum() if 'stock_c9l' in df.columns else 0
        
        # KPIs totales
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0
        
        # Precios promedio totales
        total_vendido_c9l = df[f'vendido_{self.previous_year}_c9l'].sum() if f'vendido_{self.previous_year}_c9l' in df.columns else 0
        total_avance_c9l = df[f'avance_{self.current_year}_c9l'].sum() if f'avance_{self.current_year}_c9l' in df.columns else 0
        
        precio_total_24 = (total_vendido / total_vendido_c9l) if total_vendido_c9l > 0 else 0
        precio_total_25 = (total_avance / total_avance_c9l) if total_avance_c9l > 0 else 0
        inc_precio_total = ((precio_total_25 / precio_total_24) - 1) if precio_total_24 > 0 else 0
        
        # Cobertura promedio
        total_venta_diaria = df['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df.columns else 0
        cobertura_total = (total_stock / total_venta_diaria) if total_venta_diaria > 0 else 0
        
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(precio_total_24)}</strong></td>
                    <td><strong>{self.gen.format_number(precio_total_25)}</strong></td>
                    <td><strong>{self.gen.format_number(inc_precio_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(total_stock, 0)}</strong></td>
                    <td><strong>{self.gen.format_number(cobertura_total, 0)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_marca_performance_bob_drilldown(self, estructura: dict) -> str:
        """Generar tabla de performance por marca con drill-down por subfamilia"""

        html = f"""
        <h3>PERFORMANCE POR MARCA - BOB (Con desglose por Subfamilia)</h3>
        <div class="table-container">
        <table id="tabla-performance-marca">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Marca / Subfamilia</th>
                    <th>Vendido {self.previous_year}</th>
                    <th>Ppto General</th>
                    <th>SOP</th>
                    <th>Avance {self.current_year}</th>
                    <th>Proyección de Cierre {self.current_year}</th>
                    <th>PY Sistema</th>
                    <th>Spread</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                    <th>IngNeto/C9L {self.previous_year}</th>
                    <th>IngNeto/C9L {self.current_year}</th>
                    <th>%Inc Precio</th>
                    <th>Stock C9L</th>
                    <th>Cobertura</th>
                </tr>
            </thead>
            <tbody>
        """

        # Obtener DataFrames de la estructura
        df_marca = estructura.get('marca_totales')
        df_subfamilia = estructura.get('marca_subfamilia')
        estructura_jerarquica = estructura.get('estructura_jerarquica', {})

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'
        precio_prev = f'precio_{self.previous_year}'
        precio_curr = f'precio_{self.current_year}'

        # Procesar cada marca
        for idx, marca_row in df_marca.iterrows():
            marca = marca_row['marcadir']
            marca_id = marca.replace(' ', '_').replace('.', '')

            # Datos de la marca
            vendido = marca_row.get(vendido_col, 0)
            ppto = marca_row.get('ppto_general_bob', 0)
            sop = marca_row.get('sop_bob', 0)
            avance = marca_row.get(avance_col, 0)
            py = marca_row.get(py_col, 0)
            py_sop = marca_row.get('PY_SOP', 0)
            av_pg = marca_row.get('AV_PG', 0)
            av_sop = marca_row.get('AV_SOP', 0)
            py_v = marca_row.get('PY_V', 0)
            precio_24 = marca_row.get(precio_prev, 0)
            precio_25 = marca_row.get(precio_curr, 0)
            inc_precio = marca_row.get('inc_precio', 0)
            stock = marca_row.get('stock_c9l', 0)
            cobertura = marca_row.get('cobertura_dias', 0)
            py_sist = marca_row.get('py_sistema_bob', 0)
            spread_sist = marca_row.get('spread_sistema', None)

            # Verificar si tiene subfamilias
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca] if not df_subfamilia.empty else pd.DataFrame()
            tiene_subfamilias = not subfamilias.empty

            # Clases CSS para KPIs
            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            inc_precio_class = self._get_kpi_class(inc_precio)

            # Fila de marca
            expand_button = f'<span class="expand-icon" onclick="toggleSubfamilia(\'{marca_id}\')">[+]</span>' if tiene_subfamilias else ''
            # Spread CSS class
            spread_class = self._get_kpi_class(spread_sist) if spread_sist is not None and spread_sist == spread_sist else ''
            spread_display = self.gen.format_number(spread_sist, is_percentage=True) if spread_sist is not None and spread_sist == spread_sist else '-'

            html += f"""
                <tr class="marca-row" data-marca="{marca_id}">
                    <td class="expand-cell">
                        {expand_button}
                    </td>
                    <td class="marca-nombre"><strong>{marca}</strong></td>
                    <td class="text-right">{self.gen.format_number(vendido)}</td>
                    <td class="text-right">{self.gen.format_number(ppto)}</td>
                    <td class="text-right">{self.gen.format_number(sop)}</td>
                    <td class="text-right">{self.gen.format_number(avance)}</td>
                    <td class="text-right">{self.gen.format_number(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self.gen.format_number(py_sist) if py_sist else '-'}</td>
                    <td class="text-right {spread_class}" style="font-weight: 600; background: #FFF7ED;">{spread_display}</td>
                    <td class="text-right {py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="text-right {av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="text-right {av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="text-right {py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                    <td class="text-right">{self.gen.format_number(precio_24)}</td>
                    <td class="text-right">{self.gen.format_number(precio_25)}</td>
                    <td class="text-right {inc_precio_class}">{self.gen.format_number(inc_precio, is_percentage=True)}</td>
                    <td class="text-right">{self.gen.format_number(stock, 0)}</td>
                    <td class="text-right">{self.gen.format_number(cobertura, 0)}</td>
                </tr>
            """

            # Filas de subfamilias (inicialmente ocultas)
            if tiene_subfamilias:
                for _, sub_row in subfamilias.iterrows():
                    subfam = sub_row.get('subfamilia', '')

                    # Datos de la subfamilia
                    sub_vendido = sub_row.get(vendido_col, 0)
                    sub_ppto = sub_row.get('ppto_general_bob', 0)
                    sub_sop = sub_row.get('sop_bob', 0)
                    sub_avance = sub_row.get(avance_col, 0)
                    # NO hay proyección para subfamilia
                    sub_av_pg = sub_row.get('AV_PG', 0)
                    sub_av_sop = sub_row.get('AV_SOP', 0)
                    sub_precio_24 = sub_row.get(precio_prev, 0)
                    sub_precio_25 = sub_row.get(precio_curr, 0)
                    sub_inc_precio = sub_row.get('inc_precio', 0)
                    sub_stock = sub_row.get('stock_c9l', 0)
                    sub_cobertura = sub_row.get('cobertura_dias', 0)
                    sub_py_sist = sub_row.get('py_sistema_bob', 0)
                    sub_py_sist_display = self.gen.format_number(sub_py_sist) if sub_py_sist and sub_py_sist > 0 else '-'

                    # Clases CSS para KPIs de subfamilia
                    sub_av_pg_class = self._get_kpi_class(sub_av_pg)
                    sub_av_sop_class = self._get_kpi_class(sub_av_sop)
                    sub_inc_precio_class = self._get_kpi_class(sub_inc_precio)

                    html += f"""
                    <tr class="subfamilia-row subfamilia-{marca_id}" style="display: none;">
                        <td></td>
                        <td class="subfamilia-indent">├─ {subfam}</td>
                        <td class="text-right">{self.gen.format_number(sub_vendido)}</td>
                        <td class="text-right">{self.gen.format_number(sub_ppto)}</td>
                        <td class="text-right">{self.gen.format_number(sub_sop)}</td>
                        <td class="text-right">{self.gen.format_number(sub_avance)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right" style="color: #1d4ed8; background: #EFF6FF;">{sub_py_sist_display}</td>
                        <td class="text-right" style="background: #FFF7ED;">-</td>
                        <td class="text-right">-</td>
                        <td class="text-right {sub_av_pg_class}">{self.gen.format_number(sub_av_pg, is_percentage=True)}</td>
                        <td class="text-right {sub_av_sop_class}">{self.gen.format_number(sub_av_sop, is_percentage=True)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right">{self.gen.format_number(sub_precio_24)}</td>
                        <td class="text-right">{self.gen.format_number(sub_precio_25)}</td>
                        <td class="text-right {sub_inc_precio_class}">{self.gen.format_number(sub_inc_precio, is_percentage=True)}</td>
                        <td class="text-right">{self.gen.format_number(sub_stock, 0)}</td>
                        <td class="text-right">{self.gen.format_number(sub_cobertura, 0)}</td>
                    </tr>
                    """

        # Fila de totales
        total_vendido = df_marca[vendido_col].sum() if vendido_col in df_marca.columns else 0
        total_ppto = df_marca['ppto_general_bob'].sum() if 'ppto_general_bob' in df_marca.columns else 0
        total_sop = df_marca['sop_bob'].sum() if 'sop_bob' in df_marca.columns else 0
        total_avance = df_marca[avance_col].sum() if avance_col in df_marca.columns else 0
        total_py = df_marca[py_col].sum() if py_col in df_marca.columns else 0
        total_stock = df_marca['stock_c9l'].sum() if 'stock_c9l' in df_marca.columns else 0
        total_py_sist = df_marca['py_sistema_bob'].sum() if 'py_sistema_bob' in df_marca.columns else 0
        total_spread_sist = ((total_py / total_py_sist) - 1) if total_py_sist > 0 else None

        # KPIs totales
        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Precios promedio totales
        total_vendido_c9l = df_marca[f'vendido_{self.previous_year}_c9l'].sum() if f'vendido_{self.previous_year}_c9l' in df_marca.columns else 0
        total_avance_c9l = df_marca[f'avance_{self.current_year}_c9l'].sum() if f'avance_{self.current_year}_c9l' in df_marca.columns else 0

        precio_total_24 = (total_vendido / total_vendido_c9l) if total_vendido_c9l > 0 else 0
        precio_total_25 = (total_avance / total_avance_c9l) if total_avance_c9l > 0 else 0
        inc_precio_total = ((precio_total_25 / precio_total_24) - 1) if precio_total_24 > 0 else 0

        # Cobertura promedio
        total_venta_diaria = df_marca['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df_marca.columns else 0
        cobertura_total = (total_stock / total_venta_diaria) if total_venta_diaria > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)
        inc_precio_total_class = self._get_kpi_class(inc_precio_total)

        total_spread_class = self._get_kpi_class(total_spread_sist) if total_spread_sist is not None else ''
        total_spread_display = self.gen.format_number(total_spread_sist, is_percentage=True) if total_spread_sist is not None else '-'

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self.gen.format_number(total_py_sist) if total_py_sist else '-'}</strong></td>
                    <td class="text-right {total_spread_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{total_spread_display}</strong></td>
                    <td class="text-right {py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(precio_total_24)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(precio_total_25)}</strong></td>
                    <td class="text-right {inc_precio_total_class}"><strong>{self.gen.format_number(inc_precio_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_stock, 0)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(cobertura_total, 0)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        # Agregar JavaScript y CSS
        html += """
        <script>
        function toggleSubfamilia(marca) {
            const rows = document.querySelectorAll('.subfamilia-' + marca);
            const icon = event.target;
            const isExpanded = icon.textContent === '[-]';

            rows.forEach(row => {
                row.style.display = isExpanded ? 'none' : '';
            });

            icon.textContent = isExpanded ? '[+]' : '[-]';
        }
        </script>

        <style>
        .expand-icon {
            cursor: pointer;
            color: #007bff;
            font-weight: bold;
            user-select: none;
        }
        .expand-icon:hover {
            color: #0056b3;
        }
        .subfamilia-row {
            background-color: #f8f9fa;
            font-size: 0.95em;
        }
        .subfamilia-indent {
            padding-left: 30px !important;
        }
        .marca-row {
            font-weight: 500;
        }
        .text-right {
            text-align: right;
        }
        .expand-cell {
            text-align: center;
            width: 30px;
        }
        </style>
        """

        return html

    def generate_marca_performance_c9l_drilldown(self, estructura: dict) -> str:
        """Generar tabla de performance por marca en C9L con drill-down por subfamilia"""

        html = f"""
        <h3>PERFORMANCE POR MARCA - Unidades C9L (Con desglose por Subfamilia)</h3>
        <div class="table-container">
        <table id="tabla-performance-marca-c9l">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Marca / Subfamilia</th>
                    <th>Vendido {self.previous_year}</th>
                    <th>Ppto General</th>
                    <th>SOP</th>
                    <th>Avance {self.current_year}</th>
                    <th>Proyección Cierre {self.current_year} (C9L)</th>
                    <th>PY Sistema</th>
                    <th>Spread</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                    <th>Stock C9L</th>
                    <th>Cobertura</th>
                </tr>
            </thead>
            <tbody>
        """

        # Obtener DataFrames de la estructura
        df_marca = estructura.get('marca_totales')
        df_subfamilia = estructura.get('marca_subfamilia')

        # Columnas esperadas para C9L
        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'

        # Procesar cada marca
        for idx, marca_row in df_marca.iterrows():
            marca = marca_row['marcadir']
            marca_id = marca.replace(' ', '_').replace('.', '')

            # Datos de la marca para C9L
            vendido = marca_row.get(vendido_col, 0)
            ppto = marca_row.get('ppto_general_c9l', 0)
            sop = marca_row.get('sop_c9l', 0)
            avance = marca_row.get(avance_col, 0)

            # Nueva fórmula para PY2025 en C9L: (Avance 2025 C9L * PY2025 BOB) / Avance 2025 BOB
            avance_bob_col = f'avance_{self.current_year}_bob'
            py_bob_col = f'py_{self.current_year}_bob'
            avance_c9l = marca_row.get(avance_col, 0)
            avance_bob = marca_row.get(avance_bob_col, 0)
            py_bob = marca_row.get(py_bob_col, 0)

            # Calcular PY para C9L con manejo de división por cero
            if avance_bob > 0:
                py = (avance_c9l * py_bob) / avance_bob
            else:
                py = 0

            # KPIs para C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0
            py_sop = ((py / sop) - 1) if sop > 0 else 0

            stock = marca_row.get('stock_c9l', 0)
            cobertura = marca_row.get('cobertura_dias', 0)
            py_sist_c9l = marca_row.get('py_sistema_c9l', 0)
            spread_sist_c9l = marca_row.get('spread_sistema_c9l', None)

            # Verificar si tiene subfamilias
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca] if not df_subfamilia.empty else pd.DataFrame()
            tiene_subfamilias = not subfamilias.empty

            # Clases CSS para KPIs
            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            spread_c9l_class = self._get_kpi_class(spread_sist_c9l) if spread_sist_c9l is not None and spread_sist_c9l == spread_sist_c9l else ''
            spread_c9l_display = self.gen.format_number(spread_sist_c9l, is_percentage=True) if spread_sist_c9l is not None and spread_sist_c9l == spread_sist_c9l else '-'

            # Fila de marca
            expand_button = f'<span class="expand-icon" onclick="toggleSubfamiliaC9L(\'{marca_id}\')">[+]</span>' if tiene_subfamilias else ''
            html += f"""
                <tr class="marca-row" data-marca="{marca_id}">
                    <td class="expand-cell">
                        {expand_button}
                    </td>
                    <td class="marca-nombre"><strong>{marca}</strong></td>
                    <td class="text-right">{self.gen.format_number(vendido)}</td>
                    <td class="text-right">{self.gen.format_number(ppto)}</td>
                    <td class="text-right">{self.gen.format_number(sop)}</td>
                    <td class="text-right">{self.gen.format_number(avance)}</td>
                    <td class="text-right">{self.gen.format_number(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self.gen.format_number(py_sist_c9l) if py_sist_c9l else '-'}</td>
                    <td class="text-right {spread_c9l_class}" style="font-weight: 600; background: #FFF7ED;">{spread_c9l_display}</td>
                    <td class="text-right {py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="text-right {av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="text-right {av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="text-right {py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                    <td class="text-right">{self.gen.format_number(stock, 0)}</td>
                    <td class="text-right">{self.gen.format_number(cobertura, 0)}</td>
                </tr>
            """

            # Filas de subfamilias (inicialmente ocultas)
            if tiene_subfamilias:
                for _, sub_row in subfamilias.iterrows():
                    subfam = sub_row.get('subfamilia', '')

                    # Datos de la subfamilia para C9L
                    sub_vendido = sub_row.get(vendido_col, 0)
                    sub_ppto = sub_row.get('ppto_general_c9l', 0)
                    sub_sop = sub_row.get('sop_c9l', 0)
                    sub_avance = sub_row.get(avance_col, 0)
                    # NO hay proyección para subfamilia

                    # KPIs para subfamilia C9L
                    sub_av_pg = ((sub_avance / sub_ppto) - 1) if sub_ppto > 0 else 0
                    sub_av_sop = ((sub_avance / sub_sop) - 1) if sub_sop > 0 else 0

                    sub_stock = sub_row.get('stock_c9l', 0)
                    sub_cobertura = sub_row.get('cobertura_dias', 0)

                    # Clases CSS para KPIs de subfamilia
                    sub_av_pg_class = self._get_kpi_class(sub_av_pg)
                    sub_av_sop_class = self._get_kpi_class(sub_av_sop)

                    sub_py_sist_c9l = sub_row.get('py_sistema_c9l', 0)
                    sub_py_sist_c9l_display = self.gen.format_number(sub_py_sist_c9l) if sub_py_sist_c9l and sub_py_sist_c9l > 0 else '-'

                    html += f"""
                    <tr class="subfamilia-row subfamilia-c9l-{marca_id}" style="display: none;">
                        <td></td>
                        <td class="subfamilia-indent">├─ {subfam}</td>
                        <td class="text-right">{self.gen.format_number(sub_vendido)}</td>
                        <td class="text-right">{self.gen.format_number(sub_ppto)}</td>
                        <td class="text-right">{self.gen.format_number(sub_sop)}</td>
                        <td class="text-right">{self.gen.format_number(sub_avance)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right" style="color: #1d4ed8; background: #EFF6FF;">{sub_py_sist_c9l_display}</td>
                        <td class="text-right" style="background: #FFF7ED;">-</td>
                        <td class="text-right">-</td>
                        <td class="text-right {sub_av_pg_class}">{self.gen.format_number(sub_av_pg, is_percentage=True)}</td>
                        <td class="text-right {sub_av_sop_class}">{self.gen.format_number(sub_av_sop, is_percentage=True)}</td>
                        <td class="text-right">-</td>
                        <td class="text-right">{self.gen.format_number(sub_stock, 0)}</td>
                        <td class="text-right">{self.gen.format_number(sub_cobertura, 0)}</td>
                    </tr>
                    """

        # Fila de totales
        total_vendido = df_marca[vendido_col].sum() if vendido_col in df_marca.columns else 0
        total_ppto = df_marca['ppto_general_c9l'].sum() if 'ppto_general_c9l' in df_marca.columns else 0
        total_sop = df_marca['sop_c9l'].sum() if 'sop_c9l' in df_marca.columns else 0
        total_avance = df_marca[avance_col].sum() if avance_col in df_marca.columns else 0

        # Calcular total PY usando la nueva fórmula
        avance_bob_col = f'avance_{self.current_year}_bob'
        py_bob_col = f'py_{self.current_year}_bob'
        total_avance_c9l = df_marca[avance_col].sum() if avance_col in df_marca.columns else 0
        total_avance_bob = df_marca[avance_bob_col].sum() if avance_bob_col in df_marca.columns else 0
        total_py_bob = df_marca[py_bob_col].sum() if py_bob_col in df_marca.columns else 0

        # Aplicar fórmula con manejo de división por cero
        if total_avance_bob > 0:
            total_py = (total_avance_c9l * total_py_bob) / total_avance_bob
        else:
            total_py = 0

        total_stock = df_marca['stock_c9l'].sum() if 'stock_c9l' in df_marca.columns else 0
        total_py_sist_c9l = df_marca['py_sistema_c9l'].sum() if 'py_sistema_c9l' in df_marca.columns else 0
        total_spread_c9l = ((total_py / total_py_sist_c9l) - 1) if total_py_sist_c9l > 0 else None

        # KPIs totales
        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Cobertura promedio
        total_venta_diaria = df_marca['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df_marca.columns else 0
        cobertura_total = (total_stock / total_venta_diaria) if total_venta_diaria > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)
        total_spread_c9l_class = self._get_kpi_class(total_spread_c9l) if total_spread_c9l is not None else ''
        total_spread_c9l_display = self.gen.format_number(total_spread_c9l, is_percentage=True) if total_spread_c9l is not None else '-'

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self.gen.format_number(total_py_sist_c9l) if total_py_sist_c9l else '-'}</strong></td>
                    <td class="text-right {total_spread_c9l_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{total_spread_c9l_display}</strong></td>
                    <td class="text-right {py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_stock, 0)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(cobertura_total, 0)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        # Agregar JavaScript específico para tabla C9L
        html += """
        <script>
        function toggleSubfamiliaC9L(marca) {
            const rows = document.querySelectorAll('.subfamilia-c9l-' + marca);
            const icon = event.target;
            const isExpanded = icon.textContent === '[-]';

            rows.forEach(row => {
                row.style.display = isExpanded ? 'none' : '';
            });

            icon.textContent = isExpanded ? '[+]' : '[-]';
        }
        </script>
        """

        return html

    def generate_marca_semanal_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de marcas en BOB"""
        
        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR MARCA (BOB)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Procesar cada marca - usar semana calendario actual
        for idx, row in df.iterrows():
            s1 = row.get('semana1_bob', 0) if self.current_week >= 1 else 0
            s2 = row.get('semana2_bob', 0) if self.current_week >= 2 else 0
            s3 = row.get('semana3_bob', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_bob', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_bob', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales - usar semana calendario actual
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns and self.current_week >= 1 else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        """
        
        return html
    
    def generate_marca_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por marca en C9L"""
        
        html = f"""
        <h3>PERFORMANCE POR MARCA - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Vendido {self.previous_year} (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance {self.current_year} (C9L)</th>
                    <th>PY {self.current_year} (C9L)</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                    <th>Stock (C9L)</th>
                    <th>Cobertura (días)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Similar a BOB pero con columnas C9L
        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'
        py_col = f'py_{self.current_year}_c9l'

        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_c9l', 0)
            sop = row.get('sop_c9l', 0)
            avance = row[avance_col] if avance_col in df.columns else 0

            # Nueva fórmula para PY2025 en C9L: (Avance 2025 C9L * PY2025 BOB) / Avance 2025 BOB
            avance_bob_col = f'avance_{self.current_year}_bob'
            py_bob_col = f'py_{self.current_year}_bob'
            avance_c9l = row[avance_col] if avance_col in df.columns else 0
            avance_bob = row[avance_bob_col] if avance_bob_col in df.columns else 0
            py_bob = row[py_bob_col] if py_bob_col in df.columns else 0

            # Calcular PY para C9L con manejo de división por cero
            if avance_bob > 0:
                py = (avance_c9l * py_bob) / avance_bob
            else:
                py = 0
            
            # KPIs C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0
            
            stock = row.get('stock_c9l', 0)
            cobertura = row.get('cobertura_dias', 0)
            
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                    <td>{self.gen.format_number(stock, 0)}</td>
                    <td>{self.gen.format_number(cobertura, 0)}</td>
                </tr>
            """
        
        # Totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_c9l'].sum() if 'ppto_general_c9l' in df.columns else 0
        total_sop = df['sop_c9l'].sum() if 'sop_c9l' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0

        # Calcular total PY usando la nueva fórmula
        avance_bob_col = f'avance_{self.current_year}_bob'
        py_bob_col = f'py_{self.current_year}_bob'
        total_avance_c9l = df[avance_col].sum() if avance_col in df.columns else 0
        total_avance_bob = df[avance_bob_col].sum() if avance_bob_col in df.columns else 0
        total_py_bob = df[py_bob_col].sum() if py_bob_col in df.columns else 0

        # Aplicar fórmula con manejo de división por cero
        if total_avance_bob > 0:
            total_py = (total_avance_c9l * total_py_bob) / total_avance_bob
        else:
            total_py = 0

        total_stock = df['stock_c9l'].sum() if 'stock_c9l' in df.columns else 0

        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0
        
        total_venta_diaria = df['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df.columns else 0
        cobertura_total = (total_stock / total_venta_diaria) if total_venta_diaria > 0 else 0
        
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(total_stock, 0)}</strong></td>
                    <td><strong>{self.gen.format_number(cobertura_total, 0)}</strong></td>
                </tr>
            </tbody>
        </table>
        """
        
        return html
    
    def generate_marca_semanal_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de marcas en C9L"""
        
        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR MARCA (C9L)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for idx, row in df.iterrows():
            s1 = row.get('semana1_c9l', 0)
            s2 = row.get('semana2_c9l', 0)
            s3 = row.get('semana3_c9l', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """
        
        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5
        
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        """
        
        return html
    
    def _get_kpi_class(self, value):
        """Determinar clase CSS para KPI"""
        if pd.isna(value) or np.isinf(value):
            return "neutral"

        if value > 0.05:
            return "positive"
        elif value < -0.05:
            return "negative"
        else:
            return "neutral"

    # === MÉTODOS PARA DRIVERS DE PERFORMANCE ===

    def generate_drivers_section(self, drivers_data: dict, narrative_html: str = "",
                                level: str = "marca", valid_marcas: list = None) -> str:
        """
        Genera la sección completa de Drivers de Performance (tabla con narrativa inline).

        Args:
            drivers_data: Dict con DataFrames de DriversEngine.calculate_all()
            narrative_html: HTML de narrativa IA generada por DriversNarrativeGenerator
            level: "marca", "ciudad" o "canal" — determina qué tabla(s) mostrar
            valid_marcas: Lista de marcas válidas del WSR (para filtrar micro-marcas)
        """
        html = ""

        if level == "marca":
            by_marca = drivers_data.get('by_marca')
            if by_marca is not None and not by_marca.empty:
                # Filtrar a marcas del WSR si se proporciona lista
                if valid_marcas:
                    valid_upper = {m.upper() for m in valid_marcas}
                    by_marca = by_marca[by_marca['marca'].str.upper().isin(valid_upper)].copy()
                # Parsear narrativa IA por marca para insertar inline
                marca_narratives = self._parse_narrative_per_marca(narrative_html) if narrative_html else {}
                html += self._generate_drivers_table(
                    by_marca, "DRIVERS DE PERFORMANCE POR MARCA", "Marca", "marca",
                    marca_narratives=marca_narratives
                )
        elif level == "ciudad":
            by_ciudad = drivers_data.get('by_ciudad')
            if by_ciudad is not None and not by_ciudad.empty:
                ciudad_narratives = self._parse_narrative_per_marca(narrative_html) if narrative_html else {}
                html += self._generate_drivers_table(
                    by_ciudad, "DRIVERS DE PERFORMANCE POR CIUDAD", "Ciudad", "ciudad",
                    marca_narratives=ciudad_narratives
                )
        elif level == "canal":
            by_canal = drivers_data.get('by_canal')
            if by_canal is not None and not by_canal.empty:
                canal_narratives = self._parse_narrative_per_marca(narrative_html) if narrative_html else {}
                html += self._generate_drivers_table(
                    by_canal, "DRIVERS DE PERFORMANCE POR CANAL", "Canal", "canal",
                    marca_narratives=canal_narratives
                )

        return html

    @staticmethod
    def _parse_narrative_per_marca(narrative_html: str) -> dict:
        """Parsea narrativa HTML en {MARCA_UPPER: texto_limpio}."""
        import re
        result = {}
        if not narrative_html:
            return result
        # Extraer cada <li>
        for li_match in re.finditer(r'<li[^>]*>(.*?)</li>', narrative_html, re.DOTALL):
            li_content = li_match.group(1)
            # Buscar marca en <strong>MARCA — ...
            strong_match = re.search(r'<strong>\s*([^<]+?)\s*[—–\-]\s*', li_content)
            if strong_match:
                marca = strong_match.group(1).strip().upper()
                # Limpiar tags HTML para texto plano
                clean = re.sub(r'<[^>]+>', '', li_content).strip()
                # Quitar el nombre de marca del inicio (ya está en la columna Marca)
                dash_pos = clean.find('—')
                if dash_pos == -1:
                    dash_pos = clean.find('–')
                if dash_pos > 0:
                    clean = clean[dash_pos + 1:].strip()
                result[marca] = clean
        return result

    @staticmethod
    def _generate_driver_insight(row) -> str:
        """Genera insight programático basado en datos para una marca/ciudad."""
        cob_t = row.get('cobertura_trend')
        hr_t = row.get('hitrate_trend')
        ds_t = row.get('dropsize_trend')
        cob = row.get('cobertura', 0)
        hr = row.get('hit_rate', 0)
        ds = row.get('drop_size', 0)
        sufficient = row.get('sufficient_data', False)

        if not sufficient:
            venta_est = cob * hr * ds if cob and hr and ds else 0
            venta_str = f"Bs{venta_est:,.0f}" if venta_est else "-"
            return (f"Perfil: {int(cob)} clientes, frecuencia {hr:.2f} ped/cli, "
                    f"ticket Bs{ds:,.0f}/ped. Venta implicita: {venta_str}. "
                    f"Sin dato VSLY para comparacion interanual.")

        def classify(t):
            if t is None: return 'nd'
            if t > 0.05: return 'sube_f'
            if t > 0.02: return 'sube'
            if t < -0.05: return 'baja_f'
            if t < -0.02: return 'baja'
            return 'estable'

        c, h, d = classify(cob_t), classify(hr_t), classify(ds_t)

        parts = []
        # Cobertura
        if c == 'nd':
            parts.append(f"Cob {int(cob)} cli (sin dato VSLY)")
        elif 'sube' in c:
            parts.append(f"Cob crece VSLY ({cob_t:+.1%}, {int(cob)} cli)")
        elif 'baja' in c:
            parts.append(f"Cob cae VSLY ({cob_t:+.1%}, {int(cob)} cli)")
        else:
            parts.append(f"Cob estable VSLY ({int(cob)} cli)")
        # Hit Rate
        if h == 'nd':
            parts.append(f"HR {hr:.2f} (sin dato VSLY)")
        elif 'sube' in h:
            parts.append(f"frecuencia mejora VSLY ({hr_t:+.1%})")
        elif 'baja' in h:
            parts.append(f"frecuencia cae VSLY ({hr_t:+.1%})")
        else:
            parts.append(f"frecuencia estable VSLY")
        # Drop Size
        if d == 'nd':
            parts.append(f"DS Bs{ds:,.0f}/ped (sin dato VSLY)")
        elif 'sube' in d:
            parts.append(f"ticket crece VSLY ({ds_t:+.1%}, Bs{ds:,.0f}/ped)")
        elif 'baja' in d:
            parts.append(f"ticket cae VSLY ({ds_t:+.1%}, Bs{ds:,.0f}/ped)")
        else:
            parts.append(f"ticket estable VSLY (Bs{ds:,.0f}/ped)")

        line1 = "; ".join(parts) + "."

        neg = sum(1 for x in [c, h, d] if 'baja' in x)
        pos = sum(1 for x in [c, h, d] if 'sube' in x)

        if neg >= 3:
            line2 = "Alerta: deterioro sistémico en las 3 palancas."
        elif neg >= 2:
            line2 = "Alerta: deterioro en múltiples palancas."
        elif 'baja' in h and 'sube' in c:
            line2 = "Expansión sin retención — más puertas, menos recurrencia."
        elif 'baja' in d and 'sube' in c:
            line2 = "Más clientes con menor ticket — posible dilución de mix."
        elif 'baja_f' in c:
            line2 = "Prioridad: recuperar clientes perdidos."
        elif 'baja_f' in h:
            line2 = "Prioridad: reactivar frecuencia de compra."
        elif 'baja_f' in d:
            line2 = "Prioridad: revisar mix/precio por pedido."
        elif neg == 1 and pos >= 1:
            line2 = "Señal mixta — monitorear palanca débil."
        elif pos >= 2:
            line2 = "Dinámica positiva — mantener ritmo."
        elif pos == 1:
            line2 = "Estable con mejora marginal."
        else:
            line2 = "Sin señales de alerta."

        return f"{line1} {line2}"

    def _generate_drivers_table(self, df, title: str, key_label: str, key_col: str,
                                marca_narratives: dict = None) -> str:
        """Genera tabla HTML de drivers con tendencias YoY y resumen ejecutivo inline."""

        # Extraer periodo de referencia del DataFrame
        meses_nombre = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        is_std = False
        ref_dia = None
        if 'ref_mes' in df.columns and not df.empty:
            ref_mes = int(df.iloc[0]['ref_mes'])
            ref_anio = int(df.iloc[0]['ref_anio'])
            is_std = bool(df.iloc[0].get('is_std', False))
            ref_dia = df.iloc[0].get('ref_dia')
            if is_std and ref_dia:
                ref_dia = int(ref_dia)
                periodo_str = f"{meses_nombre[ref_mes]} {ref_anio} (al dia {ref_dia})"
                periodo_yoy = f"{meses_nombre[ref_mes]} {ref_anio - 1} (al dia {ref_dia})"
                metodo_str = "Same-to-Date: mismos dias del mes, año actual vs año anterior"
            else:
                periodo_str = f"{meses_nombre[ref_mes]} {ref_anio} (mes completo)"
                periodo_yoy = f"{meses_nombre[ref_mes]} {ref_anio - 1} (mes completo)"
                metodo_str = "Ultimo mes completo disponible vs mismo mes año anterior"
        else:
            periodo_str = "Ultimo mes"
            periodo_yoy = "Mismo mes año anterior"
            metodo_str = ""

        html = f"""
        <div style="margin: 25px 0; padding: 20px; background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0 0 4px 0; color: #1e293b; font-size: 15px;">
                {title}
            </h3>
            <p style="margin: 0 0 6px 0; color: #64748b; font-size: 11px;">
                Venta = Cobertura &times; Frecuencia &times; Drop Size &nbsp;|&nbsp;
                Periodo: <strong>{periodo_str}</strong> &nbsp;|&nbsp; vs <strong>{periodo_yoy}</strong>
            </p>
            <p style="margin: 0 0 15px 0; color: #94a3b8; font-size: 10px; line-height: 1.5;">
                <strong>Cob (cli)</strong> = COUNT(DISTINCT clientes) que compraron en el periodo &nbsp;|&nbsp;
                <strong>Freq.</strong> = pedidos / clientes — frecuencia de compra &nbsp;|&nbsp;
                <strong>DS (BOB)</strong> = SUM(venta) / pedidos — ticket promedio por pedido &nbsp;|&nbsp;
                <strong>&Delta; VSLY</strong> = variacion % vs mismo periodo año anterior (Versus Last Year)
                {f'&nbsp;|&nbsp; <em>{metodo_str}</em>' if metodo_str else ''}
            </p>
            <div style="overflow-x: auto;">
            <table style="font-size: 11px; table-layout: fixed; width: 100%;">
                <colgroup>
                    <col style="width: 95px;">
                    <col style="width: 52px;">
                    <col style="width: 62px;">
                    <col style="width: 40px;">
                    <col style="width: 62px;">
                    <col style="width: 62px;">
                    <col style="width: 62px;">
                    <col>
                </colgroup>
                <thead>
                    <tr>
                        <th>{key_label}</th>
                        <th>Cob (cli)</th>
                        <th>&Delta; VSLY</th>
                        <th>Freq.</th>
                        <th>&Delta; VSLY</th>
                        <th>DS (BOB)</th>
                        <th>&Delta; VSLY</th>
                        <th>Resumen Ejecutivo</th>
                    </tr>
                </thead>
                <tbody>
        """

        if not marca_narratives:
            marca_narratives = {}

        for _, row in df.iterrows():
            key_value = row.get(key_col, '?')
            display_name = str(key_value).title() if str(key_value).isupper() else str(key_value)

            cob = row.get('cobertura', 0)
            hr = row.get('hit_rate', 0)
            ds = row.get('drop_size', 0)
            cob_t = row.get('cobertura_trend', None)
            hr_t = row.get('hitrate_trend', None)
            ds_t = row.get('dropsize_trend', None)

            cob_str = f"{int(cob):,}" if cob else "-"
            hr_str = f"{hr:.2f}" if hr else "-"
            ds_str = self.gen.format_number(ds) if ds else "-"

            cob_t_str = self._format_trend(cob_t)
            hr_t_str = self._format_trend(hr_t)
            ds_t_str = self._format_trend(ds_t)

            # Resumen: IA narrative si existe, sino insight programático
            # Fuzzy match: exact → startswith → contains (LLM puede escribir "Beefeater" pero DB tiene "BEEFEATEAR")
            marca_upper = str(key_value).upper()
            ai_text = marca_narratives.get(marca_upper, '')
            if not ai_text:
                for narr_key, narr_val in marca_narratives.items():
                    if marca_upper.startswith(narr_key[:5]) or narr_key.startswith(marca_upper[:5]):
                        ai_text = narr_val
                        break
                    if narr_key in marca_upper or marca_upper in narr_key:
                        ai_text = narr_val
                        break
            if ai_text:
                resumen = ai_text
            else:
                resumen = self._generate_driver_insight(row)

            html += f"""
                <tr>
                    <td><strong>{display_name}</strong></td>
                    <td class="text-right">{cob_str}</td>
                    <td class="text-right">{cob_t_str}</td>
                    <td class="text-right">{hr_str}</td>
                    <td class="text-right">{hr_t_str}</td>
                    <td class="text-right">{ds_str}</td>
                    <td class="text-right">{ds_t_str}</td>
                    <td style="font-size: 10.5px; line-height: 1.5; color: #374151; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; padding: 8px 10px;">{resumen}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
            </div>
        </div>
        """
        return html

    def _format_trend(self, trend_value) -> str:
        """Formatea un valor de tendencia con color y flecha."""
        if trend_value is None or (isinstance(trend_value, float) and np.isnan(trend_value)):
            return '<span style="color: #94a3b8;">-</span>'

        pct = trend_value * 100
        if trend_value > 0.02:
            color = "#16a34a"
            arrow = "&#9650;"  # ▲
        elif trend_value < -0.02:
            color = "#dc2626"
            arrow = "&#9660;"  # ▼
        else:
            color = "#64748b"
            arrow = "&#9654;"  # ▶ (stable)

        return f'<span style="color: {color}; font-weight: 600;">{arrow} {pct:+.1f}%</span>'

    def _get_diag_color(self, diag: str) -> str:
        """Color para el texto de diagnostico."""
        if "sistemico" in diag.lower():
            return "#dc2626"  # red
        elif "problema" in diag.lower():
            return "#ea580c"  # orange
        elif "estable" in diag.lower():
            return "#16a34a"  # green
        else:
            return "#64748b"  # gray (insuficiente)

    # === MÉTODOS PARA TABLAS DE CIUDAD ===

    def generate_ciudad_performance_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por ciudad en BOB"""

        html = f"""
        <h3>PERFORMANCE POR CIUDAD - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Vendido {self.previous_year} (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance {self.current_year} (BOB)</th>
                    <th>PY {self.current_year} (BOB)</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                </tr>
            </thead>
            <tbody>
        """

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'

        # Procesar cada fila
        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_bob', 0)
            sop = row.get('sop_bob', 0)
            avance = row[avance_col] if avance_col in df.columns else 0
            py = row[py_col] if py_col in df.columns else 0
            av_pg = row.get('AV_PG', 0)
            av_sop = row.get('AV_SOP', 0)
            py_v = row.get('PY_V', 0)


            # Determinar clases CSS para KPIs
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                </tr>
            """

        # Fila de totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_bob'].sum() if 'ppto_general_bob' in df.columns else 0
        total_sop = df['sop_bob'].sum() if 'sop_bob' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = df[py_col].sum() if py_col in df.columns else 0

        # KPIs totales
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td><strong>-</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_ciudad_performance_bob_drilldown(self, estructura: dict) -> str:
        """Generar tabla de performance por ciudad con drill-down por marca directorio"""

        html = f"""
        <h3>PERFORMANCE POR CIUDAD - BOB (Con desglose por Marca Directorio)</h3>
        <div class="table-container">
        <table id="tabla-performance-ciudad">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Ciudad / Marca</th>
                    <th>Vendido {self.previous_year} (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance {self.current_year} (BOB)</th>
                    <th>Proyección de Cierre {self.current_year} (BOB)</th>
                    <th>PY Sistema</th>
                    <th>Spread</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                </tr>
            </thead>
            <tbody>
        """

        # Obtener DataFrames de la estructura
        df_ciudad = estructura.get('ciudad_totales')
        df_ciudad_marca = estructura.get('ciudad_marca')
        estructura_jerarquica = estructura.get('estructura_jerarquica', {})
        marca_order = estructura.get('marca_order', [])

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'

        # Procesar cada ciudad
        for idx, ciudad_row in df_ciudad.iterrows():
            ciudad = ciudad_row['ciudad']
            ciudad_id = ciudad.replace(' ', '_').replace('.', '')

            # Datos de la ciudad
            vendido = ciudad_row.get(vendido_col, 0)
            ppto = ciudad_row.get('ppto_general_bob', 0)
            sop = ciudad_row.get('sop_bob', 0)
            avance = ciudad_row.get(avance_col, 0)
            py = ciudad_row.get(py_col, 0)
            py_sop = ciudad_row.get('PY_SOP', 0)
            av_pg = ciudad_row.get('AV_PG', 0)
            av_sop = ciudad_row.get('AV_SOP', 0)
            py_v = ciudad_row.get('PY_V', 0)
            ciudad_py_sist = ciudad_row.get('py_sistema_bob', 0)
            ciudad_spread_sist = ciudad_row.get('spread_sistema', None)

            # Verificar si tiene marcas — ordenar igual que la tabla principal de marcas (orden nacional)
            marcas = df_ciudad_marca[df_ciudad_marca['ciudad'] == ciudad] if not df_ciudad_marca.empty else pd.DataFrame()
            if not marcas.empty and marca_order:
                # Usar el mismo orden que la tabla Performance por Marca (nacional)
                order_map = {m: i for i, m in enumerate(marca_order)}
                marcas = marcas.copy()
                marcas['_sort_order'] = marcas['marcadir'].map(order_map).fillna(len(marca_order))
                marcas = marcas.sort_values('_sort_order').drop(columns='_sort_order')
            elif not marcas.empty:
                sort_cols = [c for c in [vendido_col, avance_col, py_col] if c in marcas.columns]
                if sort_cols:
                    marcas = marcas.sort_values(sort_cols, ascending=False)
            tiene_marcas = not marcas.empty

            # Clases CSS para KPIs
            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            ciudad_spread_class = self._get_kpi_class(ciudad_spread_sist) if ciudad_spread_sist is not None and ciudad_spread_sist == ciudad_spread_sist else ''
            ciudad_spread_display = self.gen.format_number(ciudad_spread_sist, is_percentage=True) if ciudad_spread_sist is not None and ciudad_spread_sist == ciudad_spread_sist else '-'

            # Fila de ciudad
            expand_button = f'<span class="expand-icon" onclick="toggleMarca(\'{ciudad_id}\')">[+]</span>' if tiene_marcas else ''
            html += f"""
                <tr class="ciudad-row" data-ciudad="{ciudad_id}">
                    <td class="expand-cell">
                        {expand_button}
                    </td>
                    <td class="ciudad-nombre"><strong>{ciudad}</strong></td>
                    <td class="text-right">{self.gen.format_number(vendido)}</td>
                    <td class="text-right">{self.gen.format_number(ppto)}</td>
                    <td class="text-right">{self.gen.format_number(sop)}</td>
                    <td class="text-right">{self.gen.format_number(avance)}</td>
                    <td class="text-right">{self.gen.format_number(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self.gen.format_number(ciudad_py_sist) if ciudad_py_sist else '-'}</td>
                    <td class="text-right {ciudad_spread_class}" style="font-weight: 600; background: #FFF7ED;">{ciudad_spread_display}</td>
                    <td class="text-right {py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="text-right {av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="text-right {av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="text-right {py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                </tr>
            """

            # Filas de marcas (inicialmente ocultas)
            if tiene_marcas:
                for _, marca_row in marcas.iterrows():
                    marca = marca_row.get('marcadir', '')

                    # Datos de la marca
                    marca_vendido = marca_row.get(vendido_col, 0)
                    marca_ppto = marca_row.get('ppto_general_bob', 0)
                    marca_sop = marca_row.get('sop_bob', 0)
                    marca_avance = marca_row.get(avance_col, 0)
                    marca_py = marca_row.get(py_col, 0)  # Proyección híbrida por ciudad-marca
                    marca_py_sop = marca_row.get('PY_SOP', 0)
                    marca_av_pg = marca_row.get('AV_PG', 0)
                    marca_av_sop = marca_row.get('AV_SOP', 0)
                    marca_py_v = marca_row.get('PY_V', 0)
                    marca_py_sist = marca_row.get('py_sistema_bob', 0)

                    # Clases CSS para KPIs de marca
                    marca_py_sop_class = self._get_kpi_class(marca_py_sop)
                    marca_av_pg_class = self._get_kpi_class(marca_av_pg)
                    marca_av_sop_class = self._get_kpi_class(marca_av_sop)
                    marca_py_v_class = self._get_kpi_class(marca_py_v)

                    html += f"""
                    <tr class="marca-row marca-{ciudad_id}" style="display: none;">
                        <td></td>
                        <td class="marca-indent">├─ {marca}</td>
                        <td class="text-right">{self.gen.format_number(marca_vendido)}</td>
                        <td class="text-right">{self.gen.format_number(marca_ppto)}</td>
                        <td class="text-right">{self.gen.format_number(marca_sop)}</td>
                        <td class="text-right">{self.gen.format_number(marca_avance)}</td>
                        <td class="text-right">{self.gen.format_number(marca_py)}</td>
                        <td class="text-right" style="color: #1d4ed8; background: #EFF6FF;">{self.gen.format_number(marca_py_sist) if marca_py_sist else '-'}</td>
                        <td class="text-right" style="background: #FFF7ED;">-</td>
                        <td class="text-right {marca_py_sop_class}">{self.gen.format_number(marca_py_sop, is_percentage=True)}</td>
                        <td class="text-right {marca_av_pg_class}">{self.gen.format_number(marca_av_pg, is_percentage=True)}</td>
                        <td class="text-right {marca_av_sop_class}">{self.gen.format_number(marca_av_sop, is_percentage=True)}</td>
                        <td class="text-right {marca_py_v_class}">{self.gen.format_number(marca_py_v, is_percentage=True)}</td>
                    </tr>
                    """

        # Fila de totales
        total_vendido = df_ciudad[vendido_col].sum() if vendido_col in df_ciudad.columns else 0
        total_ppto = df_ciudad['ppto_general_bob'].sum() if 'ppto_general_bob' in df_ciudad.columns else 0
        total_sop = df_ciudad['sop_bob'].sum() if 'sop_bob' in df_ciudad.columns else 0
        total_avance = df_ciudad[avance_col].sum() if avance_col in df_ciudad.columns else 0
        total_py = df_ciudad[py_col].sum() if py_col in df_ciudad.columns else 0
        total_py_sist_ciudad = df_ciudad['py_sistema_bob'].sum() if 'py_sistema_bob' in df_ciudad.columns else 0
        total_spread_ciudad = ((total_py / total_py_sist_ciudad) - 1) if total_py_sist_ciudad > 0 else None

        # KPIs totales
        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)
        total_spread_ciudad_class = self._get_kpi_class(total_spread_ciudad) if total_spread_ciudad is not None else ''
        total_spread_ciudad_display = self.gen.format_number(total_spread_ciudad, is_percentage=True) if total_spread_ciudad is not None else '-'

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self.gen.format_number(total_py_sist_ciudad) if total_py_sist_ciudad else '-'}</strong></td>
                    <td class="text-right {total_spread_ciudad_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{total_spread_ciudad_display}</strong></td>
                    <td class="text-right {py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="text-right {av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right {py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        # Agregar JavaScript y CSS
        html += """
        <script>
        function toggleMarca(ciudad) {
            const rows = document.querySelectorAll('.marca-' + ciudad);
            const icon = event.target;
            const isExpanded = icon.textContent === '[-]';

            rows.forEach(row => {
                row.style.display = isExpanded ? 'none' : 'table-row';
            });

            icon.textContent = isExpanded ? '[+]' : '[-]';
        }
        </script>

        <style>
        #tabla-performance-ciudad .expand-cell {
            text-align: center;
            cursor: pointer;
            user-select: none;
        }

        #tabla-performance-ciudad .expand-icon {
            display: inline-block;
            width: 20px;
            font-weight: bold;
            color: #2563eb;
        }

        #tabla-performance-ciudad .expand-icon:hover {
            color: #1d4ed8;
        }

        #tabla-performance-ciudad .ciudad-row {
            background-color: #f8fafc;
            font-weight: 600;
        }

        #tabla-performance-ciudad .marca-row {
            background-color: #ffffff;
        }

        #tabla-performance-ciudad .marca-indent {
            padding-left: 30px;
            color: #64748b;
        }

        #tabla-performance-ciudad .text-right {
            text-align: right;
        }
        </style>
        """

        return html

    def generate_ciudad_semanal_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de ciudades en BOB"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR CIUDAD (BOB)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """

        # Procesar cada ciudad
        for idx, row in df.iterrows():
            s1 = row.get('semana1_bob', 0)
            s2 = row.get('semana2_bob', 0)
            s3 = row.get('semana3_bob', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_bob', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_bob', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_ciudad_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por ciudad en C9L"""

        html = f"""
        <h3>PERFORMANCE POR CIUDAD - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Vendido {self.previous_year} (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance {self.current_year} (C9L)</th>
                    <th>Proyección Cierre {self.current_year} (C9L)</th>
                    <th>PY Sistema</th>
                    <th>Spread</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                </tr>
            </thead>
            <tbody>
        """

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'
        py_col = f'py_{self.current_year}_c9l'

        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_c9l', 0)
            sop = row.get('sop_c9l', 0)
            avance = row[avance_col] if avance_col in df.columns else 0
            py = row[py_col] if py_col in df.columns else 0
            ciudad_py_sist_c9l = row.get('py_sistema_c9l', 0)
            ciudad_spread_sist_c9l = row.get('spread_sistema_c9l', None)

            # KPIs C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0
            py_sop = ((py / sop) - 1) if sop > 0 else 0

            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            ciudad_spread_c9l_class = self._get_kpi_class(ciudad_spread_sist_c9l) if ciudad_spread_sist_c9l is not None and ciudad_spread_sist_c9l == ciudad_spread_sist_c9l else ''
            ciudad_spread_c9l_display = self.gen.format_number(ciudad_spread_sist_c9l, is_percentage=True) if ciudad_spread_sist_c9l is not None and ciudad_spread_sist_c9l == ciudad_spread_sist_c9l else '-'

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self.gen.format_number(ciudad_py_sist_c9l) if ciudad_py_sist_c9l else '-'}</td>
                    <td class="{ciudad_spread_c9l_class}" style="font-weight: 600; background: #FFF7ED;">{ciudad_spread_c9l_display}</td>
                    <td class="{py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                </tr>
            """

        # Totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_c9l'].sum() if 'ppto_general_c9l' in df.columns else 0
        total_sop = df['sop_c9l'].sum() if 'sop_c9l' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = df[py_col].sum() if py_col in df.columns else 0
        total_py_sist_c9l_ciudad = df['py_sistema_c9l'].sum() if 'py_sistema_c9l' in df.columns else 0
        total_spread_c9l_ciudad = ((total_py / total_py_sist_c9l_ciudad) - 1) if total_py_sist_c9l_ciudad > 0 else None

        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)
        total_spread_c9l_ciudad_class = self._get_kpi_class(total_spread_c9l_ciudad) if total_spread_c9l_ciudad is not None else ''
        total_spread_c9l_ciudad_display = self.gen.format_number(total_spread_c9l_ciudad, is_percentage=True) if total_spread_c9l_ciudad is not None else '-'

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self.gen.format_number(total_py_sist_c9l_ciudad) if total_py_sist_c9l_ciudad else '-'}</strong></td>
                    <td class="{total_spread_c9l_ciudad_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{total_spread_c9l_ciudad_display}</strong></td>
                    <td class="{py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="{av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="{av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="{py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_ciudad_semanal_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de ciudades en C9L"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR CIUDAD (C9L)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """

        for idx, row in df.iterrows():
            s1 = row.get('semana1_c9l', 0)
            s2 = row.get('semana2_c9l', 0)
            s3 = row.get('semana3_c9l', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    # === MÉTODOS PARA TABLAS DE CANAL ===

    def generate_canal_performance_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por canal en BOB"""

        html = f"""
        <h3>PERFORMANCE POR CANAL - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Vendido {self.previous_year} (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance {self.current_year} (BOB)</th>
                    <th>PY {self.current_year} (BOB)</th>
                    <th>PY Sistema</th>
                    <th>Spread</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                </tr>
            </thead>
            <tbody>
        """

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'

        # Procesar cada fila
        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_bob', 0)
            sop = row.get('sop_bob', 0)
            avance = row[avance_col] if avance_col in df.columns else 0
            py = row[py_col] if py_col in df.columns else 0
            py_sop = row.get('PY_SOP', 0)
            av_pg = row.get('AV_PG', 0)
            av_sop = row.get('AV_SOP', 0)
            py_v = row.get('PY_V', 0)

            # Determinar clases CSS para KPIs
            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)

            canal_py_sist = row.get('py_sistema_bob', 0)
            canal_spread_sist = row.get('spread_sistema', None)
            canal_spread_class = self._get_kpi_class(canal_spread_sist) if canal_spread_sist is not None and canal_spread_sist == canal_spread_sist else ''
            canal_spread_display = self.gen.format_number(canal_spread_sist, is_percentage=True) if canal_spread_sist is not None and canal_spread_sist == canal_spread_sist else '-'

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td class="text-right" style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;">{self.gen.format_number(canal_py_sist) if canal_py_sist else '-'}</td>
                    <td class="text-right {canal_spread_class}" style="font-weight: 600; background: #FFF7ED;">{canal_spread_display}</td>
                    <td class="{py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                </tr>
            """

        # Fila de totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_bob'].sum() if 'ppto_general_bob' in df.columns else 0
        total_sop = df['sop_bob'].sum() if 'sop_bob' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = df[py_col].sum() if py_col in df.columns else 0
        total_py_sist_canal = df['py_sistema_bob'].sum() if 'py_sistema_bob' in df.columns else 0
        total_spread_canal = ((total_py / total_py_sist_canal) - 1) if total_py_sist_canal > 0 else None

        # KPIs totales
        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)
        total_spread_canal_class = self._get_kpi_class(total_spread_canal) if total_spread_canal is not None else ''
        total_spread_canal_display = self.gen.format_number(total_spread_canal, is_percentage=True) if total_spread_canal is not None else '-'

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td style="color: #1d4ed8; font-weight: 600; background: #EFF6FF;"><strong>{self.gen.format_number(total_py_sist_canal) if total_py_sist_canal else '-'}</strong></td>
                    <td class="{total_spread_canal_class}" style="font-weight: 600; background: #FFF7ED;"><strong>{total_spread_canal_display}</strong></td>
                    <td class="{py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="{av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="{av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="{py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_canal_semanal_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de canales en BOB"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR CANAL (BOB)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """

        # Procesar cada canal
        for idx, row in df.iterrows():
            s1 = row.get('semana1_bob', 0)
            s2 = row.get('semana2_bob', 0)
            s3 = row.get('semana3_bob', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_bob', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_bob', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_canal_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por canal en C9L"""

        html = f"""
        <h3>PERFORMANCE POR CANAL - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Vendido {self.previous_year} (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance {self.current_year} (C9L)</th>
                    <th>Proyección Cierre {self.current_year} (C9L)</th>
                    <th>PY/SOP</th>
                    <th>AV{str(self.current_year)[2:]}/PG</th>
                    <th>AV{str(self.current_year)[2:]}/SOP</th>
                    <th>PY{str(self.current_year)[2:]}/V{str(self.previous_year)[2:]}</th>
                </tr>
            </thead>
            <tbody>
        """

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_c9l'
        avance_col = f'avance_{self.current_year}_c9l'
        py_col = f'py_{self.current_year}_c9l'

        for idx, row in df.iterrows():
            vendido = row[vendido_col] if vendido_col in df.columns else 0
            ppto = row.get('ppto_general_c9l', 0)
            sop = row.get('sop_c9l', 0)
            avance = row[avance_col] if avance_col in df.columns else 0
            py = row[py_col] if py_col in df.columns else 0  # Usar proyección calculada proporcional

            # KPIs C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0
            py_sop = ((py / sop) - 1) if sop > 0 else 0

            py_sop_class = self._get_kpi_class(py_sop)
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(vendido)}</td>
                    <td>{self.gen.format_number(ppto)}</td>
                    <td>{self.gen.format_number(sop)}</td>
                    <td>{self.gen.format_number(avance)}</td>
                    <td>{self.gen.format_number(py)}</td>
                    <td class="{py_sop_class}">{self.gen.format_number(py_sop, is_percentage=True)}</td>
                    <td class="{av_pg_class}">{self.gen.format_number(av_pg, is_percentage=True)}</td>
                    <td class="{ av_sop_class}">{self.gen.format_number(av_sop, is_percentage=True)}</td>
                    <td class="{py_v_class}">{self.gen.format_number(py_v, is_percentage=True)}</td>
                </tr>
            """

        # Totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_c9l'].sum() if 'ppto_general_c9l' in df.columns else 0
        total_sop = df['sop_c9l'].sum() if 'sop_c9l' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = df[py_col].sum() if py_col in df.columns else 0  # Sumar proyección calculada

        py_sop_total = ((total_py / total_sop) - 1) if total_sop > 0 else 0
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Clases CSS para KPIs totales
        py_sop_total_class = self._get_kpi_class(py_sop_total)
        av_pg_total_class = self._get_kpi_class(av_pg_total)
        av_sop_total_class = self._get_kpi_class(av_sop_total)
        py_v_total_class = self._get_kpi_class(py_v_total)

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="{py_sop_total_class}"><strong>{self.gen.format_number(py_sop_total, is_percentage=True)}</strong></td>
                    <td class="{av_pg_total_class}"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="{av_sop_total_class}"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="{py_v_total_class}"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_canal_semanal_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla semanal de canales en C9L"""

        html = """
        <h3>DETALLE SEMANAL DE VENTAS - POR CANAL (C9L)</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Semana 1</th>
                    <th>Semana 2</th>
                    <th>Semana 3</th>
                    <th>Semana 4</th>
                    <th>Semana 5</th>
                    <th>Total Mes</th>
                </tr>
            </thead>
            <tbody>
        """

        for idx, row in df.iterrows():
            s1 = row.get('semana1_c9l', 0)
            s2 = row.get('semana2_c9l', 0)
            s3 = row.get('semana3_c9l', 0) if self.current_week >= 3 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_week >= 4 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_week >= 5 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_week >= 2 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_week >= 3 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_week >= 4 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_week >= 5 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_week >= 2 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_week >= 3 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_week >= 4 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_week >= 5 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_week >= 2 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_week >= 3 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_week >= 4 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_week >= 5 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html