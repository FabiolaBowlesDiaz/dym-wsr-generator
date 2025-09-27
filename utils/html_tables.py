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
        self.previous_year = html_generator.previous_year
    
    def generate_marca_tables(self, df: pd.DataFrame, estructura_jerarquica: dict = None) -> str:
        """Generar todas las tablas de marca"""
        if df.empty:
            return "<p>No hay datos disponibles para marcas</p>"

        html = ""
        # Si tenemos estructura jerárquica, usar las nuevas tablas con drill-down
        if estructura_jerarquica:
            html += self.generate_marca_performance_bob_drilldown(estructura_jerarquica)
        else:
            html += self.generate_marca_performance_bob(df)

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

        html = """
        <h3>PERFORMANCE POR MARCA - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Vendido 2024 (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance 2025 (BOB)</th>
                    <th>PY 2025 (BOB)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
                    <th>Precio 2024 (BOB/C9L)</th>
                    <th>Precio 2025 (BOB/C9L)</th>
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

        html = """
        <h3>PERFORMANCE POR MARCA - BOB (Con desglose por Subfamilia)</h3>
        <div class="table-container">
        <table id="tabla-performance-marca">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Marca / Subfamilia</th>
                    <th>Vendido 2024</th>
                    <th>Ppto General</th>
                    <th>SOP</th>
                    <th>Avance 2025</th>
                    <th>PY 2025</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
                    <th>Precio 2024</th>
                    <th>Precio 2025</th>
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
            av_pg = marca_row.get('AV_PG', 0)
            av_sop = marca_row.get('AV_SOP', 0)
            py_v = marca_row.get('PY_V', 0)
            precio_24 = marca_row.get(precio_prev, 0)
            precio_25 = marca_row.get(precio_curr, 0)
            inc_precio = marca_row.get('inc_precio', 0)
            stock = marca_row.get('stock_c9l', 0)
            cobertura = marca_row.get('cobertura_dias', 0)

            # Verificar si tiene subfamilias
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca] if not df_subfamilia.empty else pd.DataFrame()
            tiene_subfamilias = not subfamilias.empty

            # Clases CSS para KPIs
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)
            inc_precio_class = self._get_kpi_class(inc_precio)

            # Fila de marca
            expand_button = f'<span class="expand-icon" onclick="toggleSubfamilia(\'{marca_id}\')">[+]</span>' if tiene_subfamilias else ''
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

        # KPIs totales
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

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(precio_total_24)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(precio_total_25)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(inc_precio_total, is_percentage=True)}</strong></td>
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

        html = """
        <h3>PERFORMANCE POR MARCA - Unidades C9L (Con desglose por Subfamilia)</h3>
        <div class="table-container">
        <table id="tabla-performance-marca-c9l">
            <thead>
                <tr>
                    <th style="width: 30px;"></th>
                    <th>Marca / Subfamilia</th>
                    <th>Vendido 2024</th>
                    <th>Ppto General</th>
                    <th>SOP</th>
                    <th>Avance 2025</th>
                    <th>PY 2025</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
            py = sop  # Para C9L usar SOP como proyección

            # KPIs para C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

            stock = marca_row.get('stock_c9l', 0)
            cobertura = marca_row.get('cobertura_dias', 0)

            # Verificar si tiene subfamilias
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca] if not df_subfamilia.empty else pd.DataFrame()
            tiene_subfamilias = not subfamilias.empty

            # Clases CSS para KPIs
            av_pg_class = self._get_kpi_class(av_pg)
            av_sop_class = self._get_kpi_class(av_sop)
            py_v_class = self._get_kpi_class(py_v)

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

                    html += f"""
                    <tr class="subfamilia-row subfamilia-c9l-{marca_id}" style="display: none;">
                        <td></td>
                        <td class="subfamilia-indent">├─ {subfam}</td>
                        <td class="text-right">{self.gen.format_number(sub_vendido)}</td>
                        <td class="text-right">{self.gen.format_number(sub_ppto)}</td>
                        <td class="text-right">{self.gen.format_number(sub_sop)}</td>
                        <td class="text-right">{self.gen.format_number(sub_avance)}</td>
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
        total_py = total_sop  # Para C9L usar SOP
        total_stock = df_marca['stock_c9l'].sum() if 'stock_c9l' in df_marca.columns else 0

        # KPIs totales
        av_pg_total = ((total_avance / total_ppto) - 1) if total_ppto > 0 else 0
        av_sop_total = ((total_avance / total_sop) - 1) if total_sop > 0 else 0
        py_v_total = ((total_py / total_vendido) - 1) if total_vendido > 0 else 0

        # Cobertura promedio
        total_venta_diaria = df_marca['venta_promedio_diaria_c9l'].sum() if 'venta_promedio_diaria_c9l' in df_marca.columns else 0
        cobertura_total = (total_stock / total_venta_diaria) if total_venta_diaria > 0 else 0

        html += f"""
                <tr class="total-row">
                    <td></td>
                    <td><strong>TOTAL</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_vendido)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_ppto)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_sop)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_avance)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(total_py)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(av_pg_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(av_sop_total, is_percentage=True)}</strong></td>
                    <td class="text-right"><strong>{self.gen.format_number(py_v_total, is_percentage=True)}</strong></td>
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
        
        # Procesar cada marca
        for idx, row in df.iterrows():
            s1 = row.get('semana1_bob', 0)
            s2 = row.get('semana2_bob', 0)
            s3 = row.get('semana3_bob', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_bob', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_bob', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """
        
        # Totales
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5
        
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        """
        
        return html
    
    def generate_marca_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por marca en C9L"""
        
        html = """
        <h3>PERFORMANCE POR MARCA - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Marca</th>
                    <th>Vendido 2024 (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance 2025 (C9L)</th>
                    <th>PY 2025 (C9L)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
            py = row.get('sop_c9l', 0)  # Para C9L usar SOP como proyección
            
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
        total_py = total_sop  # Para C9L usar SOP
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
            s3 = row.get('semana3_c9l', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """
        
        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5
        
        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
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

    # === MÉTODOS PARA TABLAS DE CIUDAD ===

    def generate_ciudad_performance_bob(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por ciudad en BOB"""

        html = """
        <h3>PERFORMANCE POR CIUDAD - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Vendido 2024 (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance 2025 (BOB)</th>
                    <th>PY 2025 (BOB)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
            s3 = row.get('semana3_bob', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_bob', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_bob', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_ciudad_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por ciudad en C9L"""

        html = """
        <h3>PERFORMANCE POR CIUDAD - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Ciudad</th>
                    <th>Vendido 2024 (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance 2025 (C9L)</th>
                    <th>PY 2025 (C9L)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
            py = row.get('sop_c9l', 0)  # Para C9L usar SOP como proyección


            # KPIs C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

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

        # Totales
        total_vendido = df[vendido_col].sum() if vendido_col in df.columns else 0
        total_ppto = df['ppto_general_c9l'].sum() if 'ppto_general_c9l' in df.columns else 0
        total_sop = df['sop_c9l'].sum() if 'sop_c9l' in df.columns else 0
        total_avance = df[avance_col].sum() if avance_col in df.columns else 0
        total_py = total_sop  # Para C9L usar SOP

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
            s3 = row.get('semana3_c9l', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['ciudad']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
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

        html = """
        <h3>PERFORMANCE POR CANAL - BOB</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Vendido 2024 (BOB)</th>
                    <th>Ppto General (BOB)</th>
                    <th>SOP (BOB)</th>
                    <th>Avance 2025 (BOB)</th>
                    <th>PY 2025 (BOB)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
                    <td>{row['canal']}</td>
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
            s3 = row.get('semana3_bob', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_bob', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_bob', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_bob'].sum() if 'semana1_bob' in df.columns else 0
        total_s2 = df['semana2_bob'].sum() if 'semana2_bob' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_bob'].sum() if 'semana3_bob' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_bob'].sum() if 'semana4_bob' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_bob'].sum() if 'semana5_bob' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html

    def generate_canal_performance_c9l(self, df: pd.DataFrame) -> str:
        """Generar tabla de performance por canal en C9L"""

        html = """
        <h3>PERFORMANCE POR CANAL - Unidades C9L</h3>
        <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Canal</th>
                    <th>Vendido 2024 (C9L)</th>
                    <th>Ppto General (C9L)</th>
                    <th>SOP (C9L)</th>
                    <th>Avance 2025 (C9L)</th>
                    <th>PY 2025 (C9L)</th>
                    <th>AV25/PG</th>
                    <th>AV25/SOP</th>
                    <th>PY25/V24</th>
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
            py = row.get('sop_c9l', 0)  # Para C9L usar SOP como proyección

            # KPIs C9L
            av_pg = ((avance / ppto) - 1) if ppto > 0 else 0
            av_sop = ((avance / sop) - 1) if sop > 0 else 0
            py_v = ((py / vendido) - 1) if vendido > 0 else 0

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
        total_py = total_sop  # Para C9L usar SOP

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
            s3 = row.get('semana3_c9l', 0) if self.current_day > 14 else 0
            s4 = row.get('semana4_c9l', 0) if self.current_day > 21 else 0
            s5 = row.get('semana5_c9l', 0) if self.current_day > 28 else 0
            total = s1 + s2 + s3 + s4 + s5

            html += f"""
                <tr>
                    <td>{row['canal']}</td>
                    <td>{self.gen.format_number(s1)}</td>
                    <td>{self.gen.format_number(s2) if self.current_day > 7 else ''}</td>
                    <td>{self.gen.format_number(s3) if self.current_day > 14 else ''}</td>
                    <td>{self.gen.format_number(s4) if self.current_day > 21 else ''}</td>
                    <td>{self.gen.format_number(s5) if self.current_day > 28 else ''}</td>
                    <td>{self.gen.format_number(total)}</td>
                </tr>
            """

        # Totales
        total_s1 = df['semana1_c9l'].sum() if 'semana1_c9l' in df.columns else 0
        total_s2 = df['semana2_c9l'].sum() if 'semana2_c9l' in df.columns and self.current_day > 7 else 0
        total_s3 = df['semana3_c9l'].sum() if 'semana3_c9l' in df.columns and self.current_day > 14 else 0
        total_s4 = df['semana4_c9l'].sum() if 'semana4_c9l' in df.columns and self.current_day > 21 else 0
        total_s5 = df['semana5_c9l'].sum() if 'semana5_c9l' in df.columns and self.current_day > 28 else 0
        total_total = total_s1 + total_s2 + total_s3 + total_s4 + total_s5

        html += f"""
                <tr class="total-row">
                    <td><strong>TOTAL</strong></td>
                    <td><strong>{self.gen.format_number(total_s1)}</strong></td>
                    <td><strong>{self.gen.format_number(total_s2) if self.current_day > 7 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s3) if self.current_day > 14 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s4) if self.current_day > 21 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_s5) if self.current_day > 28 else ''}</strong></td>
                    <td><strong>{self.gen.format_number(total_total)}</strong></td>
                </tr>
            </tbody>
        </table>
        </div>
        """

        return html