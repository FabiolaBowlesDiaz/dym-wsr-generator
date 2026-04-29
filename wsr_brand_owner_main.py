"""
WSR Brand Owner Generator — Pernod Ricard
Genera un reporte simplificado para Brand Owners en el exterior.

Ejecucion: python wsr_brand_owner_main.py
Requiere VPN a 192.168.80.85

Output: output/WSR_PERNOD_{YEAR}_{MONTH}_{TIMESTAMP}.html
"""

import os
import sys
import webbrowser
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Modules — shared
from core.database import DatabaseManager
from core.data_processor import DataProcessor

# Modules — brand owner
from brand_owner.config import (
    EXCLUDED_BRANDS, REPORT_FILENAME_PREFIX, SECTIONS
)
from brand_owner.html_generator import BrandOwnerHTMLGenerator
from brand_owner.html_tables import BrandOwnerTableGenerator
from brand_owner.summary_builder import build_summary_data
from brand_owner.data_filter import (
    filter_data_dict, exclude_inactive_brands,
    build_canal_from_canal_marca, build_ciudad_from_ciudad_marca,
    filter_dataframe
)
from brand_owner.canal_proyeccion import calcular_py_canal_pernod
from utils.business_days import BusinessDaysCalculator
import pandas as pd

# Projection module (optional)
try:
    from proyeccion_objetiva import ProjectionProcessor
    from proyeccion_objetiva.pilar3_operativa.drivers_engine import DriversEngine
    PROJECTION_AVAILABLE = True
except ImportError:
    PROJECTION_AVAILABLE = False

load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsr_brand_owner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BrandOwnerWSRGenerator:
    """Generador de WSR para Brand Owners (Pernod Ricard)"""

    def __init__(self):
        logger.info("=" * 50)
        logger.info("WSR BRAND OWNER GENERATOR - PERNOD RICARD")
        logger.info("=" * 50)

        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_month = self.current_date.month
        self.current_day = self.current_date.day
        self.previous_year = self.current_year - 1

        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', 5432),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        self.schema = os.getenv('DB_SCHEMA', 'auto')

        self.db_manager = DatabaseManager(self.db_config, self.schema)
        self.data_processor = DataProcessor(self.current_date)
        self.html_generator = BrandOwnerHTMLGenerator(self.current_date)
        self.table_generator = BrandOwnerTableGenerator(self.html_generator)

        logger.info(f"Fecha: {self.current_date.strftime('%d/%m/%Y')}")
        logger.info(f"Periodo: Mes {self.current_month}/{self.current_year}")

    def generate(self):
        """Generar el reporte Brand Owner completo"""
        try:
            # 1. Conectar a DB
            logger.info("Conectando a la base de datos...")
            if not self.db_manager.connect():
                logger.error("No se pudo conectar a la base de datos")
                return False

            # 2. Obtener marcas Pernod desde DimArticulo
            logger.info("Obteniendo marcas Pernod desde DimArticulo...")
            pernod_brands = self.db_manager.get_pernod_brands()
            if not pernod_brands:
                logger.error("No se encontraron marcas Pernod — abortando")
                return False
            logger.info(f"Marcas Pernod: {pernod_brands}")

            # 3. Fetch datos (reutiliza metodos existentes del DatabaseManager)
            logger.info("Obteniendo datos del DWH...")
            data = self._fetch_data()

            # 4. (Antes aqui se excluian marcas sin ventas en el ano anterior,
            #    pero ese filtro se quito por pedido del usuario — mostrar todas
            #    las marcas Pernod del DimArticulo aunque no hayan vendido en 2025)
            logger.info(f"Usando todas las marcas Pernod de DimArticulo: {pernod_brands}")

            if not pernod_brands:
                logger.error("No hay marcas Pernod en DimArticulo — abortando")
                return False

            # 5. Filtrar datos a marcas Pernod
            logger.info("Filtrando datos a marcas Pernod...")
            data['marca'] = filter_data_dict(data['marca'], pernod_brands)
            data['marca_subfamilia'] = filter_data_dict(
                data['marca_subfamilia'], pernod_brands)

            # 6. Canal: fetch canal×marca, filtrar Pernod, re-agregar
            logger.info("Procesando datos de canal (solo Pernod)...")
            data_canal = build_canal_from_canal_marca(
                data['canal_marca'], pernod_brands)
            for key, df in data_canal.items():
                data['canal'][key] = df

            # 6b. Ciudad: fetch ciudad×marca, filtrar Pernod, re-agregar
            logger.info("Procesando datos de ciudad (solo Pernod)...")
            data_ciudad = build_ciudad_from_ciudad_marca(
                data['ciudad_marca'], pernod_brands)
            # Renombrar keys (quitar sufijo _ciudad_marca) para consolidate_ciudad_data
            key_map = {
                'ventas_historicas_ciudad_marca': 'ventas_historicas',
                'avance_actual_ciudad_marca': 'avance_actual',
                'sop_ciudad_marca': 'sop',
                'proyecciones_ciudad_marca': 'proyecciones',
            }
            for old_key, df in data_ciudad.items():
                new_key = key_map.get(old_key, old_key)
                data['ciudad'][new_key] = df

            # 7. Consolidar datos via DataProcessor existente
            logger.info("Consolidando datos...")
            estructura_marca = self.data_processor.consolidate_marca_subfamilia_data(
                data['marca'], data['marca_subfamilia']
            )
            marcas_df = estructura_marca['marca_totales']

            # Merge proyecciones semanales en marcas_df (case-insensitive)
            proy_sem = data['marca'].get('proyecciones_semanales')
            if proy_sem is not None and not proy_sem.empty:
                py_cols = [c for c in proy_sem.columns if c.startswith('py_semana')]
                if py_cols:
                    merged = marcas_df.copy()
                    merged['_tmp_marca_up'] = merged['marcadir'].str.upper()
                    src = proy_sem.copy()
                    src['_tmp_marca_up'] = src['marcadir'].str.upper()
                    src = src[['_tmp_marca_up'] + py_cols].drop_duplicates('_tmp_marca_up')
                    merged = merged.merge(src, on='_tmp_marca_up', how='left').drop(columns=['_tmp_marca_up'])
                    for c in py_cols:
                        merged[c] = merged[c].fillna(0)
                    marcas_df = merged
                    estructura_marca['marca_totales'] = marcas_df

            # 7b. Calcular proyeccion por canal para Pernod
            #     Replica formula ponderada del WSR principal (R, S, T redistribuidos sin Q)
            py_col = f'py_{self.current_year}_bob'
            total_py_pernod_bob = float(marcas_df[py_col].sum()) if py_col in marcas_df.columns else 0

            if total_py_pernod_bob > 0:
                proy_canal = calcular_py_canal_pernod(
                    canal_data=data['canal'],
                    total_py_pernod_bob=total_py_pernod_bob,
                    current_year=self.current_year,
                    previous_year=self.previous_year
                )
                if not proy_canal.empty:
                    data['canal']['proyecciones_canal'] = proy_canal

            canales_df = self.data_processor.consolidate_canal_data(data['canal'])

            # 8. Preparar estructura canal→marca para drilldown
            estructura_canal = self._build_canal_marca_estructura(
                data['canal_marca'], pernod_brands)

            # 8b. Enriquecer canal_totales con PY desde canales_df (para drilldown)
            if estructura_canal.get('canal_totales') is not None and not estructura_canal['canal_totales'].empty:
                py_cols_to_merge = [f'py_{self.current_year}_bob', f'py_{self.current_year}_c9l']
                available_py_cols = [c for c in py_cols_to_merge if c in canales_df.columns]
                if available_py_cols:
                    ct = estructura_canal['canal_totales'].copy()
                    ct['_canal_upper'] = ct['canal'].str.upper()
                    cf = canales_df[['canal'] + available_py_cols].copy()
                    cf['_canal_upper'] = cf['canal'].str.upper()
                    cf = cf.drop(columns=['canal'])
                    merged = pd.merge(ct, cf, on='_canal_upper', how='left').drop(columns=['_canal_upper'])
                    estructura_canal['canal_totales'] = merged.fillna(0)

            # 8c. Ciudad: consolidar + estructura para drilldown marca
            ciudades_df = self.data_processor.consolidate_ciudad_marca_data(
                data['ciudad'], data['ciudad_marca']
            )
            # ciudades_df es un dict con ciudad_totales y ciudad_marca
            # Filtrar ciudad_marca a Pernod (para drilldown)
            if isinstance(ciudades_df, dict) and 'ciudad_marca' in ciudades_df:
                ciudades_df['ciudad_marca'] = filter_dataframe(
                    ciudades_df['ciudad_marca'], pernod_brands)
            estructura_ciudad = ciudades_df
            ciudades_totales_df = estructura_ciudad.get('ciudad_totales', pd.DataFrame())

            # 9. Resumen ejecutivo (C9L)
            logger.info("Calculando resumen ejecutivo...")
            summary_data = build_summary_data(
                marcas_df, canales_df, self.current_date)

            # 10. Comentarios de gerentes (filtrados a Pernod)
            logger.info("Procesando comentarios de gerentes...")
            comentarios_analysis = ""
            comentarios_df = data.get('comentarios')
            if comentarios_df is not None and not comentarios_df.empty:
                # Filtrar a marcas Pernod
                pernod_upper = {b.upper() for b in pernod_brands}
                comentarios_filtered = comentarios_df[
                    comentarios_df['nombre_marca'].str.upper().isin(pernod_upper)
                ]
                if not comentarios_filtered.empty:
                    comentarios_analysis = self.data_processor.generate_comentarios_analysis(
                        comentarios_filtered)

            # 11. Proyeccion Objetiva + Drivers — usa ProyeccionObjetiva si disponible
            projection_data = None
            drivers_data = {}
            drivers_narrative = ""
            drivers_canal_narrative = ""
            if PROJECTION_AVAILABLE:
                try:
                    logger.info("Calculando proyecciones objetivas + drivers (filtrado a Pernod)...")
                    proj_processor = ProjectionProcessor(
                        self.db_manager, self.current_date, self.schema,
                        brand_filter=pernod_brands)
                    projection_data = proj_processor.generate_projections(
                        py_gerente_marca=data['marca'].get('proyecciones'),
                        py_gerente_ciudad=None
                    )
                    drivers_data = projection_data.get('drivers_data', {})

                    # 11a. Merge PY Estadistica (HW) en marca_totales
                    self._merge_hw_into_estructura(estructura_marca, projection_data)

                    # 11b. Calcular PY Sistema (Nowcast = blend HW + Run Rate)
                    self._calculate_nowcast(estructura_marca)

                    # 11a2. Tambien merge HW + Nowcast para ciudad
                    self._merge_hw_into_ciudad(estructura_ciudad, projection_data)
                    self._calculate_nowcast_ciudad(estructura_ciudad)

                    # 11c. Generar narrativa IA de Drivers (marca + canal)
                    try:
                        from proyeccion_objetiva.pilar3_operativa.drivers_narrative import DriversNarrativeGenerator
                        narr_gen = DriversNarrativeGenerator()

                        drivers_by_marca = drivers_data.get('by_marca', pd.DataFrame())
                        if not drivers_by_marca.empty:
                            drivers_narrative = narr_gen.generate_diagnostic(
                                drivers_by_marca, self.current_date, level="marca",
                                detail_df=drivers_data.get('by_marca_submarca', pd.DataFrame())
                            )
                            logger.info("Narrativa IA de drivers marca generada")

                        drivers_by_canal = drivers_data.get('by_canal', pd.DataFrame())
                        if not drivers_by_canal.empty:
                            drivers_canal_narrative = narr_gen.generate_diagnostic(
                                drivers_by_canal, self.current_date, level="canal",
                                detail_df=drivers_data.get('by_canal_subcanal', pd.DataFrame())
                            )
                            logger.info("Narrativa IA de drivers canal generada")
                    except Exception as e:
                        logger.warning(f"Narrativa IA drivers no generada: {e}")

                    marcas_df = estructura_marca['marca_totales']
                    logger.info("Proyecciones + Nowcast + Drivers completados")

                except Exception as e:
                    logger.warning(f"Drivers/Proyeccion no disponible: {e}", exc_info=True)

            # 12. Generar tablas HTML
            logger.info("Generando tablas HTML...")
            valid_marcas = marcas_df['marcadir'].tolist()

            marca_tables_html = self.table_generator.generate_marca_tables(
                marcas_df,
                estructura_jerarquica=estructura_marca,
                narrative_html="",  # PY narrative goes in comentarios_py section
                drivers_data=drivers_data,
                drivers_narrative_html=drivers_narrative,
                valid_marcas=valid_marcas
            )

            canal_tables_html = self.table_generator.generate_canal_tables(
                canales_df,
                estructura_canal=estructura_canal,
                drivers_data=drivers_data,
                drivers_narrative_html=drivers_canal_narrative
            )

            # Performance por Ciudad (con drilldown por marca)
            ciudad_tables_html = ""
            if SECTIONS.get('performance_ciudad', False):
                ciudad_tables_html = self.table_generator.generate_ciudad_tables(
                    estructura_ciudad)

            stock_html = self.table_generator.generate_stock_table(marcas_df)

            # PY Sistema narrative (Senales de Cierre) — as separate section
            comentarios_py_html = ""
            if PROJECTION_AVAILABLE and 'narrative_html' in (projection_data or {}):
                comentarios_py_html = projection_data.get('narrative_html', '')

            # 13. Generar HTML completo
            logger.info("Ensamblando reporte HTML...")
            html = self.html_generator.generate_complete_report(
                marcas_df=marcas_df,
                canales_df=canales_df,
                summary_data=summary_data,
                comentarios_analysis=comentarios_analysis,
                marca_tables_html=marca_tables_html,
                canal_tables_html=canal_tables_html,
                stock_html=stock_html,
                comentarios_py_html=comentarios_py_html,
                ciudad_tables_html=ciudad_tables_html
            )

            # 14. Guardar
            output_path = self._save_report(html)
            logger.info(f"Reporte guardado: {output_path}")

            # 15. Abrir en navegador
            webbrowser.open(f"file://{os.path.abspath(output_path)}")
            logger.info("Reporte abierto en navegador")

            return True

        except Exception as e:
            logger.error(f"Error generando reporte: {e}", exc_info=True)
            return False
        finally:
            self.db_manager.disconnect()

    def _fetch_data(self) -> dict:
        """Obtener todos los datos del DWH (mismos queries que WSR original)"""
        data = {
            'marca': {}, 'marca_subfamilia': {},
            'canal': {}, 'canal_marca': {},
            'ciudad': {}, 'ciudad_marca': {}
        }

        # === MARCA ===
        logger.info("  Marca...")
        data['marca']['ventas_historicas'] = self.db_manager.get_ventas_historicas_marca(
            self.previous_year, self.current_month)
        data['marca']['avance_actual'] = self.db_manager.get_avance_actual_marca(
            self.current_year, self.current_month, self.current_day)
        data['marca']['ppto_general'] = self.db_manager.get_presupuesto_general_marca(
            self.current_year, self.current_month)
        data['marca']['sop'] = self.db_manager.get_sop_marca(
            self.current_year, self.current_month)
        data['marca']['proyecciones'] = self.db_manager.get_proyecciones_marca(
            self.current_year, self.current_month, self.current_day)
        data['marca']['stock'] = self.db_manager.get_stock_marca()
        data['marca']['ventas_semanales'] = self.db_manager.get_ventas_semanales_marca(
            self.current_year, self.current_month, self.current_day)
        data['marca']['venta_promedio_diaria'] = self.db_manager.get_venta_promedio_diaria_marca(
            self.current_year, self.current_month, self.current_day)
        # Proyecciones semanales por marca (para rellenar semanas no cerradas)
        data['marca']['proyecciones_semanales'] = self.db_manager.get_proyecciones_semanales_marca(
            self.current_year, self.current_month)

        # === MARCA-SUBFAMILIA ===
        logger.info("  Marca-Subfamilia...")
        data['marca_subfamilia']['ventas_historicas_subfamilia'] = self.db_manager.get_ventas_historicas_marca_subfamilia(
            self.previous_year, self.current_month)
        data['marca_subfamilia']['avance_actual_subfamilia'] = self.db_manager.get_avance_actual_marca_subfamilia(
            self.current_year, self.current_month, self.current_day)
        data['marca_subfamilia']['ppto_general_subfamilia'] = self.db_manager.get_presupuesto_general_marca_subfamilia(
            self.current_year, self.current_month)
        data['marca_subfamilia']['sop_subfamilia'] = self.db_manager.get_sop_marca_subfamilia(
            self.current_year, self.current_month)
        data['marca_subfamilia']['stock_subfamilia'] = self.db_manager.get_stock_marca_subfamilia()
        data['marca_subfamilia']['venta_promedio_diaria_subfamilia'] = self.db_manager.get_venta_promedio_diaria_marca_subfamilia(
            self.current_year, self.current_month, self.current_day)

        # === CIUDAD × MARCA (para filtrado Pernod + drilldown) ===
        # Keys con sufijo _ciudad_marca para compatibilidad con DataProcessor
        logger.info("  Ciudad x Marca...")
        data['ciudad_marca']['ventas_historicas_ciudad_marca'] = self.db_manager.get_ventas_historicas_ciudad_marca(
            self.previous_year, self.current_month)
        data['ciudad_marca']['avance_actual_ciudad_marca'] = self.db_manager.get_avance_actual_ciudad_marca(
            self.current_year, self.current_month, self.current_day)
        data['ciudad_marca']['sop_ciudad_marca'] = self.db_manager.get_sop_ciudad_marca(
            self.current_year, self.current_month)
        data['ciudad_marca']['proyecciones_ciudad_marca'] = self.db_manager.get_proyecciones_ciudad_marca_hibrido(
            self.current_year, self.current_month, self.current_day)

        # === CANAL (totales — se re-agregan despues del filtrado) ===
        logger.info("  Canal...")
        data['canal']['ventas_historicas'] = self.db_manager.get_ventas_historicas_canal(
            self.previous_year, self.current_month)
        data['canal']['avance_actual'] = self.db_manager.get_avance_actual_canal(
            self.current_year, self.current_month, self.current_day)
        data['canal']['sop'] = self.db_manager.get_sop_canal(
            self.current_year, self.current_month)
        data['canal']['ventas_semanales'] = self.db_manager.get_ventas_semanales_canal(
            self.current_year, self.current_month, self.current_day)

        # === CANAL × MARCA (para filtrado Pernod + drilldown) ===
        logger.info("  Canal x Marca...")
        data['canal_marca']['ventas_historicas'] = self.db_manager.get_ventas_historicas_canal_marca(
            self.previous_year, self.current_month)
        data['canal_marca']['avance_actual'] = self.db_manager.get_avance_actual_canal_marca(
            self.current_year, self.current_month, self.current_day)
        data['canal_marca']['sop'] = self.db_manager.get_sop_canal_marca(
            self.current_year, self.current_month)
        data['canal_marca']['ventas_semanales'] = self.db_manager.get_ventas_semanales_canal_marca(
            self.current_year, self.current_month, self.current_day)

        # === COMENTARIOS ===
        logger.info("  Comentarios...")
        data['comentarios'] = self.db_manager.get_comentarios_gerentes(
            self.current_year, self.current_month)

        return data

    def _build_canal_marca_estructura(self, data_canal_marca: dict,
                                       pernod_brands: list) -> dict:
        """
        Construir estructura canal→marca para drilldown en tablas.
        Filtra canal_marca a Pernod y prepara la estructura.
        """
        import pandas as pd

        # Re-aggregate canal totals (Pernod only)
        canal_totales = build_canal_from_canal_marca(data_canal_marca, pernod_brands)

        # Merge canal totals into a single DataFrame
        df_canal = None
        for key, df in canal_totales.items():
            if df is not None and not df.empty and 'canal' in df.columns:
                if df_canal is None:
                    df_canal = df
                else:
                    df_canal = pd.merge(df_canal, df, on='canal', how='outer')

        # Filter canal_marca detail to Pernod
        df_detail = None
        avance_key = 'avance_actual'
        if avance_key in data_canal_marca:
            df_detail = filter_dataframe(
                data_canal_marca[avance_key], pernod_brands)

        # Merge ventas historicas and SOP into detail
        if df_detail is not None and not df_detail.empty:
            if 'ventas_historicas' in data_canal_marca:
                vh = filter_dataframe(data_canal_marca['ventas_historicas'], pernod_brands)
                if not vh.empty:
                    df_detail = pd.merge(df_detail, vh, on=['canal', 'marcadir'], how='outer')
            if 'sop' in data_canal_marca:
                sop = filter_dataframe(data_canal_marca['sop'], pernod_brands)
                if not sop.empty:
                    df_detail = pd.merge(df_detail, sop, on=['canal', 'marcadir'], how='outer')
            df_detail = df_detail.fillna(0)

        return {
            'canal_totales': df_canal if df_canal is not None else pd.DataFrame(),
            'canal_marca': df_detail if df_detail is not None else pd.DataFrame()
        }

    def _merge_hw_into_estructura(self, estructura_marca, projection_data):
        """Merge PY Estadistica (Holt-Winters) en estructura_marca — replica logica del WSR original"""
        import pandas as pd

        def _merge_py_est(target_df, source_df, key_cols, value_col='py_estadistica_bob'):
            """Merge case-insensitive usando columnas temporales UPPER."""
            if source_df is None or source_df.empty or value_col not in source_df.columns:
                return target_df
            tmp_cols = [f'_tmp_{c}' for c in key_cols]
            src = source_df[key_cols + [value_col]].copy()
            for c, tc in zip(key_cols, tmp_cols):
                src[tc] = src[c].astype(str).str.upper()
            src = src[tmp_cols + [value_col]]
            src = src.groupby(tmp_cols, as_index=False)[value_col].sum()
            tgt = target_df.copy()
            for c, tc in zip(key_cols, tmp_cols):
                tgt[tc] = tgt[c].astype(str).str.upper()
            tgt = tgt.merge(src, on=tmp_cols, how='left')
            tgt[value_col] = tgt[value_col].fillna(0)
            tgt.drop(columns=tmp_cols, inplace=True)
            return tgt

        # Merge HW BOB
        est_marca = projection_data.get('est_by_marca', pd.DataFrame())
        estructura_marca['marca_totales'] = _merge_py_est(
            estructura_marca['marca_totales'], est_marca, ['marcadir'])

        est_subfam = projection_data.get('est_by_subfamilia', pd.DataFrame())
        if estructura_marca.get('marca_subfamilia') is not None:
            estructura_marca['marca_subfamilia'] = _merge_py_est(
                estructura_marca['marca_subfamilia'], est_subfam, ['marcadir', 'subfamilia'])

        # Merge HW C9L
        est_marca_c9l = projection_data.get('est_by_marca_c9l', pd.DataFrame())
        estructura_marca['marca_totales'] = _merge_py_est(
            estructura_marca['marca_totales'], est_marca_c9l, ['marcadir'], value_col='py_estadistica_c9l')

        est_subfam_c9l = projection_data.get('est_by_subfamilia_c9l', pd.DataFrame())
        if estructura_marca.get('marca_subfamilia') is not None:
            estructura_marca['marca_subfamilia'] = _merge_py_est(
                estructura_marca['marca_subfamilia'], est_subfam_c9l, ['marcadir', 'subfamilia'], value_col='py_estadistica_c9l')

        logger.info("PY Estadistica (HW) embebida en marca_totales y marca_subfamilia")

    def _calculate_nowcast(self, estructura_marca):
        """Calcular PY Sistema (Nowcast = blend HW + Run Rate) — replica logica del WSR original"""
        try:
            from proyeccion_objetiva.nowcast_engine import NowcastEngine

            calculator = BusinessDaysCalculator()
            dias_mes, dias_avance, pct_avance = calculator.calculate_business_days(self.current_date)
            nowcast = NowcastEngine(self.current_date, dias_mes, dias_avance)
            meta = nowcast.get_metadata()

            avance_bob_col = f'avance_{self.current_year}_bob'
            avance_c9l_col = f'avance_{self.current_year}_c9l'

            # Nowcast BOB
            estructura_marca['marca_totales'] = nowcast.calculate(
                estructura_marca['marca_totales'], avance_bob_col)
            if estructura_marca.get('marca_subfamilia') is not None:
                estructura_marca['marca_subfamilia'] = nowcast.calculate(
                    estructura_marca['marca_subfamilia'], avance_bob_col)

            # Nowcast C9L
            estructura_marca['marca_totales'] = nowcast.calculate(
                estructura_marca['marca_totales'], avance_c9l_col,
                hw_col='py_estadistica_c9l', value_suffix='c9l')
            if estructura_marca.get('marca_subfamilia') is not None:
                estructura_marca['marca_subfamilia'] = nowcast.calculate(
                    estructura_marca['marca_subfamilia'], avance_c9l_col,
                    hw_col='py_estadistica_c9l', value_suffix='c9l')

            logger.info(f"PY Sistema (Nowcast) calculado — credibilidad: {meta['w']:.1%}")
        except Exception as e:
            logger.warning(f"Nowcast no disponible (Auto PY estara vacio): {e}")

    def _merge_hw_into_ciudad(self, estructura_ciudad, projection_data):
        """Merge HW por ciudad (BOB + C9L) en ciudad_totales"""
        import pandas as pd

        def _merge_py_est(target_df, source_df, key_cols, value_col='py_estadistica_bob'):
            if source_df is None or source_df.empty or value_col not in source_df.columns:
                return target_df
            tmp_cols = [f'_tmp_{c}' for c in key_cols]
            src = source_df[key_cols + [value_col]].copy()
            for c, tc in zip(key_cols, tmp_cols):
                src[tc] = src[c].astype(str).str.upper()
            src = src[tmp_cols + [value_col]]
            src = src.groupby(tmp_cols, as_index=False)[value_col].sum()
            tgt = target_df.copy()
            for c, tc in zip(key_cols, tmp_cols):
                tgt[tc] = tgt[c].astype(str).str.upper()
            tgt = tgt.merge(src, on=tmp_cols, how='left')
            tgt[value_col] = tgt[value_col].fillna(0)
            tgt.drop(columns=tmp_cols, inplace=True)
            return tgt

        est_ciudad = projection_data.get('est_by_ciudad', pd.DataFrame())
        estructura_ciudad['ciudad_totales'] = _merge_py_est(
            estructura_ciudad['ciudad_totales'], est_ciudad, ['ciudad'])

        est_ciudad_c9l = projection_data.get('est_by_ciudad_c9l', pd.DataFrame())
        estructura_ciudad['ciudad_totales'] = _merge_py_est(
            estructura_ciudad['ciudad_totales'], est_ciudad_c9l, ['ciudad'],
            value_col='py_estadistica_c9l')

        logger.info("PY Estadistica (HW) embebida en ciudad_totales")

    def _calculate_nowcast_ciudad(self, estructura_ciudad):
        """Calcular PY Sistema (Nowcast) para ciudad_totales"""
        try:
            from proyeccion_objetiva.nowcast_engine import NowcastEngine

            calculator = BusinessDaysCalculator()
            dias_mes, dias_avance, _ = calculator.calculate_business_days(self.current_date)
            nowcast = NowcastEngine(self.current_date, dias_mes, dias_avance)

            avance_bob_col = f'avance_{self.current_year}_bob'
            avance_c9l_col = f'avance_{self.current_year}_c9l'

            estructura_ciudad['ciudad_totales'] = nowcast.calculate(
                estructura_ciudad['ciudad_totales'], avance_bob_col)
            estructura_ciudad['ciudad_totales'] = nowcast.calculate(
                estructura_ciudad['ciudad_totales'], avance_c9l_col,
                hw_col='py_estadistica_c9l', value_suffix='c9l')

            logger.info("PY Sistema (Nowcast) calculado para ciudad_totales")
        except Exception as e:
            logger.warning(f"Nowcast ciudad no disponible: {e}")

    def _save_report(self, html: str) -> str:
        """Guardar reporte HTML"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        timestamp = self.current_date.strftime("%Y%m%d_%H%M%S")
        filename = f"{REPORT_FILENAME_PREFIX}_{self.current_year}_{self.current_month:02d}_{timestamp}.html"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)


def main():
    generator = BrandOwnerWSRGenerator()
    success = generator.generate()

    if success:
        print("\n" + "=" * 50)
        print("REPORTE BRAND OWNER GENERADO EXITOSAMENTE")
        print("=" * 50)
    else:
        print("\nError generando el reporte Brand Owner")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
