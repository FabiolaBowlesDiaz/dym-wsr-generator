"""
WSR Generator Principal - Orquestador
Sistema completo para generar Weekly Sales Report de DYM
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv
import webbrowser

# Añadir el directorio actual al path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos propios
from core.database import DatabaseManager
from core.data_processor import DataProcessor
from core.html_generator import HTMLGenerator
from core.trend_chart_generator import TrendChartGenerator
from utils.html_tables import HTMLTableGenerator

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsr_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WSRGeneratorSystem:
    """Sistema completo de generación del WSR"""
    
    def __init__(self):
        """Inicializar el sistema WSR"""
        logger.info("="*50)
        logger.info("WSR GENERATOR - DYM")
        logger.info("="*50)
        
        # Configuración de fecha
        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_month = self.current_date.month
        self.current_day = self.current_date.day
        self.previous_year = self.current_year - 1
        
        # Configuración de base de datos
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', 5432),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        self.schema = os.getenv('DB_SCHEMA', 'auto')
        
        # Inicializar componentes
        self.db_manager = DatabaseManager(self.db_config, self.schema)
        self.data_processor = DataProcessor(self.current_date)
        self.html_generator = HTMLGenerator(self.current_date)
        self.table_generator = HTMLTableGenerator(self.html_generator)
        self.trend_chart_generator = TrendChartGenerator(self.current_date)
        
        logger.info(f"📅 Fecha: {self.current_date.strftime('%d/%m/%Y')}")
        logger.info(f"📊 Período: Mes {self.current_month}/{self.current_year}")
        logger.info(f"📈 Análisis hasta el día: {self.current_day}")
    
    def generate(self):
        """Generar el reporte completo"""
        try:
            # 1. Conectar a la base de datos
            logger.info("\n🔗 Conectando a la base de datos...")
            if not self.db_manager.connect():
                logger.error("❌ No se pudo conectar a la base de datos")
                return False
            
            # 2. Obtener todos los datos
            logger.info("\n📥 Obteniendo datos...")
            data = self._fetch_all_data()
            
            # 3. Consolidar y procesar datos
            logger.info("\n🔄 Procesando datos...")
            # Consolidar datos con estructura jerárquica para marcas
            estructura_marca = self.data_processor.consolidate_marca_subfamilia_data(
                data['marca'], data['marca_subfamilia']
            )
            marcas_df = estructura_marca['marca_totales']

            # Consolidar datos con estructura jerárquica para ciudades
            estructura_ciudad = self.data_processor.consolidate_ciudad_marca_data(
                data['ciudad'], data['ciudad_marca']
            )
            ciudades_df = estructura_ciudad['ciudad_totales']

            canales_df = self.data_processor.consolidate_canal_data(data['canal'])
            
            # 4. Calcular resumen ejecutivo
            logger.info("\n📊 Calculando métricas del resumen ejecutivo...")
            summary_data = self.data_processor.calculate_executive_summary(
                marcas_df, ciudades_df, canales_df
            )
            
            # 5. Generar análisis de comentarios
            logger.info("\n💬 Analizando comentarios de gerentes...")
            comentarios_df = data['comentarios'] if 'comentarios' in data else None
            comentarios_analysis = ""

            if comentarios_df is not None and not comentarios_df.empty:
                comentarios_analysis = self.data_processor.generate_comentarios_analysis(comentarios_df)

            # 6. Generar gráfico de tendencia comparativa
            logger.info("\n📊 Generando gráfico de tendencia comparativa...")
            trend_chart_html = self._generate_trend_chart()

            # 7. Obtener y procesar datos de Hit Rate
            logger.info("\n📈 Obteniendo datos de Hit Rate y Eficiencia...")
            hitrate_data = self._fetch_hitrate_data()

            # 8. Generar HTML
            logger.info("\n📄 Generando reporte HTML...")
            html = self._generate_html_report(
                marcas_df, ciudades_df, canales_df,
                summary_data, comentarios_analysis, hitrate_data,
                estructura_marca=estructura_marca,
                estructura_ciudad=estructura_ciudad,
                trend_chart_html=trend_chart_html
            )

            # 8. Guardar archivo
            output_path = self._save_report(html)

            # 9. Cerrar conexión
            self.db_manager.disconnect()
            
            logger.info(f"\n✅ Reporte generado exitosamente: {output_path}")
            
            # 10. Abrir en navegador
            if os.path.exists(output_path):
                logger.info("🌐 Abriendo reporte en navegador...")
                webbrowser.open(f"file://{os.path.abspath(output_path)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}", exc_info=True)
            return False
    
    def _fetch_all_data(self):
        """Obtener todos los datos necesarios de la base de datos"""
        data = {'marca': {}, 'ciudad': {}, 'canal': {}, 'marca_subfamilia': {}, 'ciudad_marca': {}}

        # === DATOS POR MARCA ===
        logger.info("  • Obteniendo datos por marca...")

        data['marca']['ventas_historicas'] = self.db_manager.get_ventas_historicas_marca(
            self.previous_year, self.current_month
        )

        data['marca']['avance_actual'] = self.db_manager.get_avance_actual_marca(
            self.current_year, self.current_month, self.current_day
        )

        data['marca']['ppto_general'] = self.db_manager.get_presupuesto_general_marca(
            self.current_year, self.current_month
        )

        data['marca']['sop'] = self.db_manager.get_sop_marca(
            self.current_year, self.current_month
        )

        data['marca']['proyecciones'] = self.db_manager.get_proyecciones_marca(
            self.current_year, self.current_month, self.current_day
        )

        data['marca']['stock'] = self.db_manager.get_stock_marca()

        data['marca']['ventas_semanales'] = self.db_manager.get_ventas_semanales_marca(
            self.current_year, self.current_month, self.current_day
        )

        data['marca']['venta_promedio_diaria'] = self.db_manager.get_venta_promedio_diaria_marca(
            self.current_year, self.current_month, self.current_day
        )

        # === DATOS POR MARCA-SUBFAMILIA ===
        logger.info("  • Obteniendo datos por marca y subfamilia...")

        data['marca_subfamilia']['ventas_historicas_subfamilia'] = self.db_manager.get_ventas_historicas_marca_subfamilia(
            self.previous_year, self.current_month
        )

        data['marca_subfamilia']['avance_actual_subfamilia'] = self.db_manager.get_avance_actual_marca_subfamilia(
            self.current_year, self.current_month, self.current_day
        )

        data['marca_subfamilia']['ppto_general_subfamilia'] = self.db_manager.get_presupuesto_general_marca_subfamilia(
            self.current_year, self.current_month
        )

        data['marca_subfamilia']['sop_subfamilia'] = self.db_manager.get_sop_marca_subfamilia(
            self.current_year, self.current_month
        )

        data['marca_subfamilia']['stock_subfamilia'] = self.db_manager.get_stock_marca_subfamilia()

        data['marca_subfamilia']['venta_promedio_diaria_subfamilia'] = self.db_manager.get_venta_promedio_diaria_marca_subfamilia(
            self.current_year, self.current_month, self.current_day
        )
        
        # === DATOS POR CIUDAD ===
        logger.info("  • Obteniendo datos por ciudad...")
        
        data['ciudad']['ventas_historicas'] = self.db_manager.get_ventas_historicas_ciudad(
            self.previous_year, self.current_month
        )
        
        data['ciudad']['avance_actual'] = self.db_manager.get_avance_actual_ciudad(
            self.current_year, self.current_month, self.current_day
        )
        
        data['ciudad']['ppto_general'] = self.db_manager.get_presupuesto_general_ciudad(
            self.current_year, self.current_month
        )
        
        data['ciudad']['sop'] = self.db_manager.get_sop_ciudad(
            self.current_year, self.current_month
        )

        data['ciudad']['proyecciones'] = self.db_manager.get_proyecciones_ciudad_hibrido(
            self.current_year, self.current_month, self.current_day
        )

        data['ciudad']['ventas_semanales'] = self.db_manager.get_ventas_semanales_ciudad(
            self.current_year, self.current_month, self.current_day
        )

        # === DATOS POR CIUDAD Y MARCA DIRECTORIO ===
        logger.info("  • Obteniendo datos por ciudad y marca directorio...")

        data['ciudad_marca']['ventas_historicas_ciudad_marca'] = self.db_manager.get_ventas_historicas_ciudad_marca(
            self.previous_year, self.current_month
        )

        data['ciudad_marca']['avance_actual_ciudad_marca'] = self.db_manager.get_avance_actual_ciudad_marca(
            self.current_year, self.current_month, self.current_day
        )

        data['ciudad_marca']['ppto_general_ciudad_marca'] = self.db_manager.get_presupuesto_general_ciudad_marca(
            self.current_year, self.current_month
        )

        data['ciudad_marca']['sop_ciudad_marca'] = self.db_manager.get_sop_ciudad_marca(
            self.current_year, self.current_month
        )

        data['ciudad_marca']['proyecciones_ciudad_marca'] = self.db_manager.get_proyecciones_ciudad_marca_hibrido(
            self.current_year, self.current_month, self.current_day
        )

        data['ciudad_marca']['stock_ciudad_marca'] = self.db_manager.get_stock_ciudad_marca()

        data['ciudad_marca']['venta_promedio_diaria_ciudad_marca'] = self.db_manager.get_venta_promedio_diaria_ciudad_marca(
            self.current_year, self.current_month
        )

        # === DATOS POR CANAL ===
        logger.info("  • Obteniendo datos por canal...")
        
        data['canal']['ventas_historicas'] = self.db_manager.get_ventas_historicas_canal(
            self.previous_year, self.current_month
        )
        
        data['canal']['avance_actual'] = self.db_manager.get_avance_actual_canal(
            self.current_year, self.current_month, self.current_day
        )
        
        data['canal']['ppto_general'] = self.db_manager.get_presupuesto_general_canal(
            self.current_year, self.current_month
        )
        
        data['canal']['sop'] = self.db_manager.get_sop_canal(
            self.current_year, self.current_month
        )
        
        data['canal']['ventas_semanales'] = self.db_manager.get_ventas_semanales_canal(
            self.current_year, self.current_month, self.current_day
        )
        
        # Calcular proyecciones por canal con multiplicador
        logger.info("  • Calculando proyecciones por canal...")
        
        # Primero obtener el total de PY de marcas para usar en el cálculo
        total_py = 0
        if not data['marca']['proyecciones'].empty:
            py_col = f'py_{self.current_year}_bob'
            if py_col in data['marca']['proyecciones'].columns:
                total_py = data['marca']['proyecciones'][py_col].sum()
        
        data['canal']['proyecciones_canal'] = self.db_manager.calcular_py_canal(
            self.current_year, self.current_month, self.current_day, total_py
        )
        
        # === COMENTARIOS DE GERENTES ===
        logger.info("  • Obteniendo comentarios de gerentes...")
        data['comentarios'] = self.db_manager.get_comentarios_gerentes(
            self.current_year, self.current_month
        )
        
        return data

    def _fetch_hitrate_data(self):
        """Obtener todos los datos de Hit Rate y Eficiencia"""
        try:
            # Obtener datos de Hit Rate
            logger.info("  • Obteniendo Hit Rate mensual...")
            hitrate_mensual = self.db_manager.get_hitrate_mensual(self.current_year)

            logger.info("  • Obteniendo Hit Rate YTD...")
            hitrate_ytd = self.db_manager.get_hitrate_ytd(self.current_year, self.current_month)

            logger.info("  • Obteniendo Hit Rate por ciudad...")
            hitrate_ciudad = self.db_manager.get_hitrate_por_ciudad(self.current_year, self.current_month)

            logger.info("  • Obteniendo Hit Rate histórico por ciudad...")
            hitrate_ciudad_historico = self.db_manager.get_hitrate_historico_por_ciudad(
                self.current_year, self.current_month
            )

            # Procesar los datos
            hitrate_data = self.data_processor.process_hitrate_data(
                hitrate_mensual, hitrate_ytd, hitrate_ciudad, hitrate_ciudad_historico
            )

            return hitrate_data

        except Exception as e:
            logger.error(f"Error obteniendo datos de Hit Rate: {e}")
            return None

    def _generate_html_report(self, marcas_df, ciudades_df, canales_df,
                             summary_data, comentarios_analysis, hitrate_data=None,
                             estructura_marca=None, estructura_ciudad=None, trend_chart_html=""):
        """Generar el reporte HTML completo"""

        # Extender HTMLGenerator con métodos de tablas
        # Si tenemos estructura jerárquica, pasar a generate_marca_tables
        if estructura_marca:
            self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(
                df, estructura_jerarquica=estructura_marca
            )
        else:
            self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(df)

        # Si tenemos estructura jerárquica de ciudad, pasar a _generate_ciudad_tables
        if estructura_ciudad:
            self.html_generator._generate_ciudad_tables = lambda df: self._generate_ciudad_tables(
                df, estructura_jerarquica=estructura_ciudad
            )
        else:
            self.html_generator._generate_ciudad_tables = lambda df: self._generate_ciudad_tables(df)
        self.html_generator._generate_canal_tables = lambda df: self._generate_canal_tables(df)
        self.html_generator._generate_stock_analysis = lambda df: self._generate_stock_analysis(df)
        self.html_generator._generate_footer = lambda: self._generate_footer()
        
        # Generar HTML completo
        html = self.html_generator.generate_complete_report(
            marcas_df, ciudades_df, canales_df,
            summary_data, comentarios_analysis, hitrate_data,
            trend_chart_html
        )
        
        return html
    
    def _generate_ciudad_tables(self, df, estructura_jerarquica=None):
        """Generar tablas de ciudad"""
        if df.empty:
            return "<p>No hay datos disponibles para ciudades</p>"

        html = ""
        # Si tenemos estructura jerárquica, usar la tabla con desglose por marca
        if estructura_jerarquica:
            html += self.table_generator.generate_ciudad_performance_bob_drilldown(estructura_jerarquica)
        else:
            html += self.table_generator.generate_ciudad_performance_bob(df)

        html += self.table_generator.generate_ciudad_semanal_bob(df)
        html += self.table_generator.generate_ciudad_performance_c9l(df)
        html += self.table_generator.generate_ciudad_semanal_c9l(df)

        return html
    
    def _generate_canal_tables(self, df):
        """Generar tablas de canal"""
        if df.empty:
            return "<p>No hay datos disponibles para canales</p>"

        html = ""
        html += self.table_generator.generate_canal_performance_bob(df)
        html += self.table_generator.generate_canal_semanal_bob(df)
        html += self.table_generator.generate_canal_performance_c9l(df)
        html += self.table_generator.generate_canal_semanal_c9l(df)

        return html
    
    def _generate_stock_analysis(self, df):
        """Generar análisis de stock"""
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
        
        for idx, row in df.iterrows():
            stock = row.get('stock_c9l', 0)
            venta_diaria = row.get('venta_promedio_diaria_c9l', 0)
            cobertura = row.get('cobertura_dias', 0)
            
            estado, estado_text = self.html_generator.get_cobertura_status(cobertura)
            rec_text = self.html_generator.get_cobertura_recomendacion(cobertura)
            
            html += f"""
                <tr>
                    <td>{row['marcadir']}</td>
                    <td>{self.html_generator.format_number(stock, 0)}</td>
                    <td>{self.html_generator.format_number(venta_diaria, 2)}</td>
                    <td>{self.html_generator.format_number(cobertura, 0)}</td>
                    <td>{estado} {estado_text}</td>
                    <td>{rec_text}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        return html
    
    def _generate_footer(self):
        """Generar pie de página con notas metodológicas"""
        return f"""
        <div class="footer">
            <h4>NOTAS METODOLÓGICAS</h4>
            <ul>
                <li>Tipo de cambio aplicado: 6.96 BOB/USD para conversión de proyecciones</li>
                <li>Cobertura de stock: Calculada con base en venta promedio diaria últimos {self.current_day} días</li>
                <li>PY 2025 por canal: Calculado mediante multiplicador ponderado (80% peso en avance actual)</li>
                <li>Ciudades sin gerente: Oruro y Trinidad usan presupuesto mensual como proyección</li>
                <li>Exclusiones aplicadas: Ciudad/Canal Turismo y marcas "Ninguna"/"Sin marca asignada"</li>
                <li>Datos actualizados al: {self.current_date.strftime('%d/%m/%Y %H:%M')}</li>
            </ul>
            <p style="margin-top: 15px; font-style: italic;">
                Generado automáticamente por el sistema de Business Intelligence de DYM<br>
                Para consultas sobre este reporte, contactar al área de Análisis Comercial
            </p>
        </div>
        """
    
    def _save_report(self, html):
        """Guardar el reporte HTML en archivo"""
        # Crear directorio de salida si no existe
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = self.current_date.strftime("%Y%m%d_%H%M%S")
        filename = f"WSR_DYM_{self.current_year}_{self.current_month:02d}_{timestamp}.html"
        filepath = output_dir / filename
        
        # Guardar archivo
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"📁 Archivo guardado: {filepath}")
        
        return str(filepath)


    def _generate_trend_chart(self) -> str:
        """
        Generar gráfico de tendencia comparativa ventas vs proyecciones
        Incluye SOP distribuido de Oruro y Trinidad

        Returns:
            HTML del gráfico interactivo
        """
        try:
            # Obtener datos semanales de ventas
            ventas_semanales = self.db_manager.get_ventas_semanales_nacional(
                self.current_year, self.current_month, self.current_day
            )

            # Obtener proyecciones semanales de gerentes
            proyecciones_semanales = self.db_manager.get_proyecciones_semanales_nacional(
                self.current_year, self.current_month
            )

            # Obtener SOP mensual de Oruro y Trinidad
            sop_oruro_trinidad = self.db_manager.get_sop_oruro_trinidad(
                self.current_year, self.current_month
            )

            if ventas_semanales.empty or proyecciones_semanales.empty:
                logger.warning("No hay datos suficientes para generar el gráfico de tendencia")
                return ""

            # Obtener datos por ciudad para vista multi-ciudad
            logger.info("Obteniendo datos de ventas y proyecciones por ciudad...")
            ventas_por_ciudad = self.db_manager.get_ventas_semanales_por_ciudad_detalle(
                self.current_year, self.current_month, self.current_day
            )
            proyecciones_por_ciudad = self.db_manager.get_proyecciones_semanales_por_ciudad(
                self.current_year, self.current_month
            )

            # Procesar datos multi-ciudad (general + ciudades individuales)
            chart_data = self.trend_chart_generator.process_weekly_data_multi_city(
                ventas_semanales,
                proyecciones_semanales,
                ventas_por_ciudad,
                proyecciones_por_ciudad,
                sop_oruro_trinidad
            )

            # Generar HTML del gráfico con selector de ciudades
            chart_html = self.trend_chart_generator.generate_chart_html(chart_data)

            logger.info("Gráfico de tendencia multi-ciudad generado exitosamente")
            return chart_html

        except Exception as e:
            logger.error(f"Error generando gráfico de tendencia: {e}")
            return ""


def main():
    """Función principal para ejecutar el generador"""
    try:
        # Crear instancia del sistema
        generator = WSRGeneratorSystem()
        
        # Generar reporte
        success = generator.generate()
        
        if success:
            print("\n" + "="*50)
            print("✅ REPORTE GENERADO EXITOSAMENTE")
            print("="*50)
            return 0
        else:
            print("\n" + "="*50)
            print("❌ ERROR EN LA GENERACIÓN DEL REPORTE")
            print("Revisa el archivo wsr_generator.log para más detalles")
            print("="*50)
            return 1
            
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logger.error(f"Error crítico en main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())