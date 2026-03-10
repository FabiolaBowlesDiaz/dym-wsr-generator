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
import pandas as pd

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

# Módulo de Proyección Objetiva (nuevo)
try:
    from proyeccion_objetiva import ProjectionProcessor
    from proyeccion_objetiva.nowcast_engine import NowcastEngine
    from proyeccion_objetiva.visualizacion.projection_html_generator import ProjectionHTMLGenerator, get_projection_css
    from proyeccion_objetiva.visualizacion.projection_chart_generator import ProjectionChartGenerator
    from utils.business_days import BusinessDaysCalculator
    PROJECTION_MODULE_AVAILABLE = True
except ImportError as e:
    PROJECTION_MODULE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"Módulo de Proyección Objetiva no disponible: {e}")

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
            # Pasar orden nacional de marcas para que el drilldown de ciudad use el mismo orden
            estructura_ciudad['marca_order'] = marcas_df['marcadir'].tolist()

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
            # Compute marca_totales-derived totals for chart alignment
            py_col = f'py_{self.current_year}_bob'
            chart_py_gerente = float(marcas_df[py_col].sum()) if py_col in marcas_df.columns else None
            chart_sop = float(marcas_df['ppto_general_bob'].sum()) if 'ppto_general_bob' in marcas_df.columns else None
            if chart_py_gerente is not None and chart_sop is not None:
                logger.info(f"Chart alignment: PY Gerente={chart_py_gerente:,.0f}, SOP={chart_sop:,.0f} (from marca_totales)")
            trend_chart_html = self._generate_trend_chart(
                py_gerente_total=chart_py_gerente,
                sop_total=chart_sop
            )

            # 7. Obtener y procesar datos de Hit Rate
            logger.info("\n📈 Obteniendo datos de Hit Rate y Eficiencia...")
            hitrate_data = self._fetch_hitrate_data()

            # 7.5. Generar Proyecciones Objetivas (nuevo módulo)
            projection_data = None
            if PROJECTION_MODULE_AVAILABLE:
                try:
                    logger.info("\n📊 Generando proyecciones objetivas...")
                    proj_processor = ProjectionProcessor(
                        self.db_manager, self.current_date, self.schema
                    )
                    projection_data = proj_processor.generate_projections(
                        py_gerente_marca=data['marca'].get('proyecciones'),
                        py_gerente_ciudad=data['ciudad'].get('proyecciones')
                    )
                    logger.info("✅ Proyecciones objetivas generadas exitosamente")

                    # 7.6 Merge PY Estadística en DataFrames existentes
                    # Nota: WSR usa Title Case (Branca), DWH usa UPPER (BRANCA).
                    # Se normaliza a UPPER antes del merge y se restaura después.
                    logger.info("\n🔗 Embebiendo PY Estadística en tablas de performance...")
                    try:
                        def _merge_py_est(target_df, source_df, key_cols, value_col='py_estadistica_bob'):
                            """Merge case-insensitive usando columnas temporales UPPER."""
                            if source_df.empty or value_col not in source_df.columns:
                                return target_df
                            # Crear columnas temporales UPPER para merge
                            tmp_cols = [f'_tmp_{c}' for c in key_cols]
                            src = source_df[key_cols + [value_col]].copy()
                            for c, tc in zip(key_cols, tmp_cols):
                                src[tc] = src[c].astype(str).str.upper()
                            src = src[tmp_cols + [value_col]]
                            # Deduplicar source por keys (promediar si hay duplicados)
                            src = src.groupby(tmp_cols, as_index=False)[value_col].sum()

                            tgt = target_df.copy()
                            for c, tc in zip(key_cols, tmp_cols):
                                tgt[tc] = tgt[c].astype(str).str.upper()
                            tgt = tgt.merge(src, on=tmp_cols, how='left')
                            tgt[value_col] = tgt[value_col].fillna(0)
                            # Eliminar columnas temporales
                            tgt.drop(columns=tmp_cols, inplace=True)
                            return tgt

                        # Merge en marca_totales
                        est_marca = projection_data.get('est_by_marca', pd.DataFrame())
                        estructura_marca['marca_totales'] = _merge_py_est(
                            estructura_marca['marca_totales'], est_marca, ['marcadir']
                        )

                        # Merge en marca_subfamilia
                        est_subfam = projection_data.get('est_by_subfamilia', pd.DataFrame())
                        estructura_marca['marca_subfamilia'] = _merge_py_est(
                            estructura_marca['marca_subfamilia'], est_subfam, ['marcadir', 'subfamilia']
                        )

                        # Merge en ciudad_totales
                        est_ciudad = projection_data.get('est_by_ciudad', pd.DataFrame())
                        estructura_ciudad['ciudad_totales'] = _merge_py_est(
                            estructura_ciudad['ciudad_totales'], est_ciudad, ['ciudad']
                        )

                        # Merge en ciudad_marca
                        est_ciudad_marca = projection_data.get('est_by_ciudad_marca', pd.DataFrame())
                        estructura_ciudad['ciudad_marca'] = _merge_py_est(
                            estructura_ciudad['ciudad_marca'], est_ciudad_marca, ['ciudad', 'marcadir']
                        )

                        # Merge en canales_df
                        est_canal = projection_data.get('est_by_canal', pd.DataFrame())
                        canales_df = _merge_py_est(canales_df, est_canal, ['canal'])

                        # Reconciliación top-down: escalar HW de ciudad/canal para coincidir con marca total
                        total_hw_marca = estructura_marca['marca_totales']['py_estadistica_bob'].sum() if 'py_estadistica_bob' in estructura_marca['marca_totales'].columns else 0
                        if total_hw_marca > 0:
                            for tgt_df in [estructura_ciudad['ciudad_totales'], estructura_ciudad['ciudad_marca'], canales_df]:
                                if 'py_estadistica_bob' in tgt_df.columns:
                                    total_hw = tgt_df['py_estadistica_bob'].sum()
                                    if total_hw > 0:
                                        tgt_df['py_estadistica_bob'] *= (total_hw_marca / total_hw)

                        # Merge PY Estadística C9L
                        est_marca_c9l = projection_data.get('est_by_marca_c9l', pd.DataFrame())
                        estructura_marca['marca_totales'] = _merge_py_est(
                            estructura_marca['marca_totales'], est_marca_c9l, ['marcadir'], value_col='py_estadistica_c9l'
                        )
                        est_subfam_c9l = projection_data.get('est_by_subfamilia_c9l', pd.DataFrame())
                        estructura_marca['marca_subfamilia'] = _merge_py_est(
                            estructura_marca['marca_subfamilia'], est_subfam_c9l, ['marcadir', 'subfamilia'], value_col='py_estadistica_c9l'
                        )
                        est_ciudad_c9l = projection_data.get('est_by_ciudad_c9l', pd.DataFrame())
                        estructura_ciudad['ciudad_totales'] = _merge_py_est(
                            estructura_ciudad['ciudad_totales'], est_ciudad_c9l, ['ciudad'], value_col='py_estadistica_c9l'
                        )
                        est_ciudad_marca_c9l = projection_data.get('est_by_ciudad_marca_c9l', pd.DataFrame())
                        estructura_ciudad['ciudad_marca'] = _merge_py_est(
                            estructura_ciudad['ciudad_marca'], est_ciudad_marca_c9l, ['ciudad', 'marcadir'], value_col='py_estadistica_c9l'
                        )
                        est_canal_c9l = projection_data.get('est_by_canal_c9l', pd.DataFrame())
                        canales_df = _merge_py_est(canales_df, est_canal_c9l, ['canal'], value_col='py_estadistica_c9l')

                        # Reconciliación top-down C9L
                        total_hw_marca_c9l = estructura_marca['marca_totales']['py_estadistica_c9l'].sum() if 'py_estadistica_c9l' in estructura_marca['marca_totales'].columns else 0
                        if total_hw_marca_c9l > 0:
                            for tgt_df in [estructura_ciudad['ciudad_totales'], estructura_ciudad['ciudad_marca'], canales_df]:
                                if 'py_estadistica_c9l' in tgt_df.columns:
                                    total_hw = tgt_df['py_estadistica_c9l'].sum()
                                    if total_hw > 0:
                                        tgt_df['py_estadistica_c9l'] *= (total_hw_marca_c9l / total_hw)

                        logger.info("✅ PY Estadística embebida en tablas de performance (BOB + C9L)")
                    except Exception as e:
                        logger.warning(f"⚠️ Error embebiendo PY Estadística (tablas se generan sin esta columna): {e}")

                    # 7.6.5 Calcular PY Sistema (Nowcast = blend HW + Run Rate)
                    nowcast_meta = {}
                    try:
                        biz_calc = BusinessDaysCalculator()
                        dias_mes, dias_avance, pct_avance = biz_calc.calculate_business_days(self.current_date)
                        nowcast = NowcastEngine(self.current_date, dias_mes, dias_avance)
                        nowcast_meta = nowcast.get_metadata()
                        avance_col = f'avance_{self.current_year}_bob'

                        # Calcular PY Sistema en cada DataFrame
                        estructura_marca['marca_totales'] = nowcast.calculate(
                            estructura_marca['marca_totales'], avance_col
                        )
                        estructura_marca['marca_subfamilia'] = nowcast.calculate(
                            estructura_marca['marca_subfamilia'], avance_col
                        )
                        estructura_ciudad['ciudad_totales'] = nowcast.calculate(
                            estructura_ciudad['ciudad_totales'], avance_col
                        )
                        estructura_ciudad['ciudad_marca'] = nowcast.calculate(
                            estructura_ciudad['ciudad_marca'], avance_col
                        )
                        canales_df = nowcast.calculate(canales_df, avance_col)

                        # Nowcast C9L
                        avance_col_c9l = f'avance_{self.current_year}_c9l'
                        estructura_marca['marca_totales'] = nowcast.calculate(
                            estructura_marca['marca_totales'], avance_col_c9l,
                            hw_col='py_estadistica_c9l', value_suffix='c9l'
                        )
                        estructura_marca['marca_subfamilia'] = nowcast.calculate(
                            estructura_marca['marca_subfamilia'], avance_col_c9l,
                            hw_col='py_estadistica_c9l', value_suffix='c9l'
                        )
                        estructura_ciudad['ciudad_totales'] = nowcast.calculate(
                            estructura_ciudad['ciudad_totales'], avance_col_c9l,
                            hw_col='py_estadistica_c9l', value_suffix='c9l'
                        )
                        estructura_ciudad['ciudad_marca'] = nowcast.calculate(
                            estructura_ciudad['ciudad_marca'], avance_col_c9l,
                            hw_col='py_estadistica_c9l', value_suffix='c9l'
                        )
                        canales_df = nowcast.calculate(canales_df, avance_col_c9l,
                            hw_col='py_estadistica_c9l', value_suffix='c9l'
                        )

                        logger.info(f"✅ PY Sistema calculado BOB + C9L (w={nowcast_meta['w']:.2%} credibilidad)")
                    except Exception as e:
                        logger.warning(f"⚠️ Error calculando PY Sistema (se usa PY Estadística como fallback): {e}")

                    # 7.7 Generar narrativa IA de proyecciones (PY Sistema)
                    try:
                        from proyeccion_objetiva.narrative_generator import ProjectionNarrativeGenerator
                        narr_gen = ProjectionNarrativeGenerator()
                        projection_data['narrative_html'] = narr_gen.generate_narrative(
                            projection_data, estructura_marca.get('marca_totales', pd.DataFrame()),
                            self.current_date, nowcast_meta=nowcast_meta
                        )
                    except Exception as e:
                        logger.warning(f"Narrativa IA PY Sistema no generada: {e}")

                    # 7.8 Generar narrativa IA de Drivers de Performance (Pilar 3)
                    try:
                        drivers_data = projection_data.get('drivers_data', {})
                        drivers_by_marca = drivers_data.get('by_marca', pd.DataFrame())
                        if not drivers_by_marca.empty:
                            from proyeccion_objetiva.pilar3_operativa.drivers_narrative import DriversNarrativeGenerator
                            drivers_narr_gen = DriversNarrativeGenerator()
                            drivers_by_marca_sub = drivers_data.get('by_marca_submarca', pd.DataFrame())
                            projection_data['drivers_narrative_html'] = drivers_narr_gen.generate_diagnostic(
                                drivers_by_marca, self.current_date, level="marca",
                                detail_df=drivers_by_marca_sub
                            )
                            logger.info("[Drivers] Narrativa IA de drivers por marca generada")

                            # Narrativa IA para ciudades (con detalle marca×ciudad)
                            drivers_by_ciudad = drivers_data.get('by_ciudad', pd.DataFrame())
                            drivers_by_ciudad_marca = drivers_data.get('by_ciudad_marca', pd.DataFrame())
                            if not drivers_by_ciudad.empty:
                                projection_data['drivers_ciudad_narrative_html'] = drivers_narr_gen.generate_diagnostic(
                                    drivers_by_ciudad, self.current_date, level="ciudad",
                                    detail_df=drivers_by_ciudad_marca
                                )
                                logger.info("[Drivers] Narrativa IA de drivers por ciudad generada")

                            # Narrativa IA para canales (con detalle subcanal)
                            drivers_by_canal = drivers_data.get('by_canal', pd.DataFrame())
                            drivers_by_canal_sub = drivers_data.get('by_canal_subcanal', pd.DataFrame())
                            if not drivers_by_canal.empty:
                                projection_data['drivers_canal_narrative_html'] = drivers_narr_gen.generate_diagnostic(
                                    drivers_by_canal, self.current_date, level="canal",
                                    detail_df=drivers_by_canal_sub
                                )
                                logger.info("[Drivers] Narrativa IA de drivers por canal generada")
                        else:
                            logger.info("[Drivers] Sin datos de drivers por marca (tabla vacia)")
                    except Exception as e:
                        logger.warning(f"Narrativa IA de Drivers no generada: {e}")

                except Exception as e:
                    logger.warning(f"⚠️ Módulo de Proyección Objetiva falló (WSR se genera sin esta sección): {e}")
                    projection_data = None

            # 8. Generar HTML
            logger.info("\n📄 Generando reporte HTML...")
            html = self._generate_html_report(
                marcas_df, ciudades_df, canales_df,
                summary_data, comentarios_analysis, hitrate_data,
                estructura_marca=estructura_marca,
                estructura_ciudad=estructura_ciudad,
                trend_chart_html=trend_chart_html,
                projection_data=projection_data
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
                             estructura_marca=None, estructura_ciudad=None,
                             trend_chart_html="", projection_data=None):
        """Generar el reporte HTML completo"""

        # Extender HTMLGenerator con métodos de tablas
        # Si tenemos estructura jerárquica, pasar a generate_marca_tables
        narrative_html = projection_data.get('narrative_html', '') if projection_data else ''
        drivers_data = projection_data.get('drivers_data', {}) if projection_data else {}
        drivers_narrative_html = projection_data.get('drivers_narrative_html', '') if projection_data else ''

        # Obtener lista de marcas válidas del WSR para filtrar drivers
        valid_marcas = None
        if estructura_marca and 'marca_totales' in estructura_marca:
            valid_marcas = estructura_marca['marca_totales']['marcadir'].tolist()

        if estructura_marca:
            self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(
                df, estructura_jerarquica=estructura_marca, narrative_html=narrative_html,
                drivers_data=drivers_data, drivers_narrative_html=drivers_narrative_html,
                valid_marcas=valid_marcas
            )
        else:
            self.html_generator._generate_marca_tables = lambda df: self.table_generator.generate_marca_tables(
                df, narrative_html=narrative_html,
                drivers_data=drivers_data, drivers_narrative_html=drivers_narrative_html,
                valid_marcas=valid_marcas
            )

        # Si tenemos estructura jerárquica de ciudad, pasar a _generate_ciudad_tables
        drivers_ciudad_narr = projection_data.get('drivers_ciudad_narrative_html', '') if projection_data else ''
        if estructura_ciudad:
            self.html_generator._generate_ciudad_tables = lambda df: self._generate_ciudad_tables(
                df, estructura_jerarquica=estructura_ciudad, drivers_data=drivers_data,
                drivers_ciudad_narrative=drivers_ciudad_narr
            )
        else:
            self.html_generator._generate_ciudad_tables = lambda df: self._generate_ciudad_tables(
                df, drivers_data=drivers_data, drivers_ciudad_narrative=drivers_ciudad_narr
            )
        drivers_canal_narr = projection_data.get('drivers_canal_narrative_html', '') if projection_data else ''
        self.html_generator._generate_canal_tables = lambda df: self._generate_canal_tables(
            df, drivers_data=drivers_data, drivers_canal_narrative=drivers_canal_narr
        )
        self.html_generator._generate_stock_analysis = lambda df: self._generate_stock_analysis(df)
        self.html_generator._generate_footer = lambda: self._generate_footer()
        
        # Generar Sección 4: Resumen Ejecutivo — Señales de Cierre
        projection_html = ""
        if projection_data and PROJECTION_MODULE_AVAILABLE:
            try:
                proj_html_gen = ProjectionHTMLGenerator(self.html_generator.format_number)
                proj_chart_gen = ProjectionChartGenerator()

                # Calcular totales nacionales del mes actual
                # Nota: py_sistema_bob vive en estructura_marca (calculado por Nowcast), no en marcas_df
                marca_totales = estructura_marca.get('marca_totales', marcas_df) if estructura_marca else marcas_df
                avance_col = f'avance_{self.current_year}_bob'
                py_col = f'py_{self.current_year}_bob'
                avance_nacional = marca_totales[avance_col].sum() if avance_col in marca_totales.columns else 0
                sop_nacional = marca_totales['ppto_general_bob'].sum() if 'ppto_general_bob' in marca_totales.columns else 0
                py_gerente_nacional = marca_totales[py_col].sum() if py_col in marca_totales.columns else 0
                py_sistema_nacional = marca_totales['py_sistema_bob'].sum() if 'py_sistema_bob' in marca_totales.columns else 0

                # Gráfica histórica
                historico_nacional = projection_data.get('historico_nacional', {})

                # Override current month PY Gerente and SOP with marca_totales values
                # historico_nacional queries fact_proyecciones/factpresupuesto directly,
                # which produces different totals than marca_totales (the authoritative source)
                py_ger_hist = historico_nacional.get('py_gerente_nacional', pd.DataFrame())
                if not py_ger_hist.empty and py_gerente_nacional > 0:
                    mask = (py_ger_hist['anio'].astype(int) == self.current_year) & \
                           (py_ger_hist['mes'].astype(int) == self.current_month)
                    if mask.any():
                        old_val = float(py_ger_hist.loc[mask, 'py_gerente_bob'].iloc[0])
                        py_ger_hist.loc[mask, 'py_gerente_bob'] = py_gerente_nacional
                        logger.info(f"Chart PY Gerente override: {old_val:,.0f} -> {py_gerente_nacional:,.0f} (marca_totales)")

                sop_hist = historico_nacional.get('sop_nacional', pd.DataFrame())
                if not sop_hist.empty and sop_nacional > 0:
                    mask = (sop_hist['anio'].astype(int) == self.current_year) & \
                           (sop_hist['mes'].astype(int) == self.current_month)
                    if mask.any():
                        old_val = float(sop_hist.loc[mask, 'sop_bob'].iloc[0])
                        sop_hist.loc[mask, 'sop_bob'] = sop_nacional
                        logger.info(f"Chart SOP override: {old_val:,.0f} -> {sop_nacional:,.0f} (marca_totales)")

                chart_html = proj_chart_gen.generate_historical_chart(
                    historico_nacional,
                    py_sistema_nacional=py_sistema_nacional,
                    avance_nacional=avance_nacional,
                    current_year=self.current_year,
                    current_month=self.current_month
                )

                # Sección completa
                projection_html = proj_html_gen.generate_full_section(
                    chart_html=chart_html,
                    sop_nacional=sop_nacional,
                    py_gerente_nacional=py_gerente_nacional,
                    py_sistema_nacional=py_sistema_nacional,
                    avance_nacional=avance_nacional
                )
            except Exception as e:
                logger.warning(f"Error generando HTML de Resumen Ejecutivo: {e}")
                import traceback
                logger.warning(traceback.format_exc())
                projection_html = ""

        # Generar HTML completo
        html = self.html_generator.generate_complete_report(
            marcas_df, ciudades_df, canales_df,
            summary_data, comentarios_analysis, hitrate_data,
            trend_chart_html, projection_html
        )

        return html
    
    def _generate_ciudad_tables(self, df, estructura_jerarquica=None, drivers_data=None,
                                drivers_ciudad_narrative: str = ""):
        """Generar tablas de ciudad"""
        if df.empty:
            return "<p>No hay datos disponibles para ciudades</p>"

        html = ""
        # Si tenemos estructura jerárquica, usar la tabla con desglose por marca
        if estructura_jerarquica:
            html += self.table_generator.generate_ciudad_performance_bob_drilldown(estructura_jerarquica)
        else:
            html += self.table_generator.generate_ciudad_performance_bob(df)

        # Insertar Drivers de Performance por Ciudad después de la tabla BOB
        if drivers_data:
            html += self.table_generator.generate_drivers_section(
                drivers_data, narrative_html=drivers_ciudad_narrative, level="ciudad"
            )

        html += self.table_generator.generate_ciudad_semanal_bob(df)

        # Para C9L, usar ciudad_totales de estructura (tiene columnas nowcast C9L)
        ciudad_c9l_df = estructura_jerarquica.get('ciudad_totales', df) if estructura_jerarquica else df
        html += self.table_generator.generate_ciudad_performance_c9l(ciudad_c9l_df)
        html += self.table_generator.generate_ciudad_semanal_c9l(df)

        return html
    
    def _generate_canal_tables(self, df, drivers_data=None, drivers_canal_narrative: str = ""):
        """Generar tablas de canal con drivers operativos"""
        if df.empty:
            return "<p>No hay datos disponibles para canales</p>"

        html = ""
        html += self.table_generator.generate_canal_performance_bob(df)

        # Insertar Drivers de Performance por Canal después de la tabla BOB
        if drivers_data:
            html += self.table_generator.generate_drivers_section(
                drivers_data, narrative_html=drivers_canal_narrative, level="canal"
            )

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
            <h4>NOTAS METODOLOGICAS</h4>
            <ul>
                <li><strong>PY Sistema (Nowcast)</strong>: Proyeccion hibrida que combina el Modelo Historico Holt-Winters
                    (entrenado sobre 24-36 meses de ventas reales, captura tendencia y estacionalidad) con el Ritmo Actual
                    de ventas del mes extrapolado al cierre. El peso se ajusta diariamente: al inicio de mes domina el modelo
                    historico; conforme avanzan las ventas reales, el ritmo actual gana protagonismo.</li>
                <li><strong>Drivers de Performance</strong>: Venta = Cobertura x Frecuencia x Drop Size.
                    Comparacion Same-to-Date (STD): mismos dias del mes actual vs mismos dias del ano anterior.
                    Fuente: tabla <em>fact_ventas_detallado</em> del DWH (nivel item con cliente y factura unicos).
                    <br><strong>Formulas exactas:</strong>
                    <br>1. <strong>Cobertura</strong> (cli) = COUNT(DISTINCT cod_cliente) — clientes unicos que compraron en el periodo.
                    <br>2. <strong>Frecuencia</strong> (ped/cli) = COUNT(DISTINCT cuf_factura) / COUNT(DISTINCT cod_cliente) — pedidos unicos por cliente.
                    <br>3. <strong>Drop Size</strong> (BOB/ped) = SUM(ingreso_neto_bob) / COUNT(DISTINCT cuf_factura) — ingreso neto promedio por pedido.
                    <br><strong>Check multiplicativo:</strong> Cobertura x Frecuencia x Drop Size = SUM(ingreso_neto_bob) (identidad exacta, diferencias menores por redondeo).
                    <br><strong>Delta VSLY:</strong> (valor periodo actual / valor mismo periodo ano anterior) - 1.</li>
                <li><strong>Narrativa IA</strong>: Los resumenes ejecutivos en Drivers (marca, ciudad, canal) y PY Sistema
                    son generados por IA (Claude, Anthropic) basandose exclusivamente en los datos del reporte.
                    No reemplazan el criterio del equipo comercial.</li>
                <li><strong>PY {self.current_year} por canal</strong>: Calculado mediante multiplicador ponderado (80% peso en avance actual).</li>
                <li><strong>Tipo de cambio</strong>: 6.96 BOB/USD para conversion de proyecciones.</li>
                <li><strong>Cobertura de stock</strong>: Calculada con base en venta promedio diaria ultimos {self.current_day} dias.</li>
                <li><strong>Ciudades sin gerente</strong>: {"Trinidad usa" if self.current_year >= 2026 else "Oruro y Trinidad usan"} presupuesto mensual como proyeccion.</li>
                <li><strong>Exclusiones</strong>: Ciudad/Canal Turismo y marcas "Ninguna"/"Sin marca asignada".</li>
                <li><strong>Datos actualizados al</strong>: {self.current_date.strftime('%d/%m/%Y %H:%M')}.</li>
            </ul>
            <p style="margin-top: 15px; font-style: italic;">
                Generado automaticamente por el sistema de Business Intelligence de DYM<br>
                Para consultas sobre este reporte, contactar al area de Analisis Comercial
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


    def _generate_trend_chart(self, py_gerente_total: float = None, sop_total: float = None) -> str:
        """
        Generar gráfico de tendencia comparativa ventas vs proyecciones
        Incluye SOP distribuido de Oruro y Trinidad

        Args:
            py_gerente_total: Total PY Gerente mensual desde marca_totales (override para vista general)
            sop_total: Total SOP mensual desde marca_totales (override para vista general)

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
                sop_oruro_trinidad,
                override_py_gerente_total=py_gerente_total,
                override_sop_total=sop_total
            )

            # Generar HTML del gráfico con selector de ciudades
            chart_html = self.trend_chart_generator.generate_chart_html(chart_data)

            # Log chart general totals for verification against summary table
            if 'general' in chart_data:
                gen_total = chart_data['general'].get('totales', {})
                logger.info(f"Chart general total proyeccion: {gen_total.get('proyeccion_bob', 0):,.0f} BOB")

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