"""
Data Fetcher para Proyección Objetiva
Ejecuta queries SQL contra el DWH para obtener datos de cobertura,
hit rate, drop size y ventas históricas mensuales.
"""

import pandas as pd
import logging
from typing import Optional, Dict

from . import config as cfg

logger = logging.getLogger(__name__)


class ProjectionDataFetcher:
    """
    Obtiene datos del DWH necesarios para los motores de proyección.
    Reutiliza el DatabaseManager existente del WSR.
    """

    def __init__(self, db_manager, schema: str = 'auto'):
        """
        Args:
            db_manager: Instancia de DatabaseManager del WSR (ya conectada)
            schema: Schema del DWH (default 'auto')
        """
        self.db = db_manager
        self.schema = schema

    # ------------------------------------------------------------------
    # Query 0: Descubrimiento de esquema
    # ------------------------------------------------------------------
    def validate_factventas_schema(self) -> Dict:
        """
        Valida que FactVentas tenga las columnas esperadas.
        Retorna dict con las columnas encontradas y las faltantes.
        """
        expected_cols = {
            'cod_cliente_padre', 'total_venta', 'c9l',
            'marcadir', 'ciudad', 'canal', 'anio', 'mes'
        }

        query = f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE LOWER(table_schema) = LOWER('{self.schema}')
          AND LOWER(table_name) = LOWER('{cfg.TABLE_FACT_VENTAS}')
        ORDER BY ordinal_position
        """

        try:
            df = self.db.execute_query(query)
            if df.empty:
                logger.warning(f"Tabla {cfg.TABLE_FACT_VENTAS} no encontrada en schema {self.schema}")
                return {
                    'exists': False,
                    'found_columns': [],
                    'missing_columns': list(expected_cols)
                }

            found = set(df['column_name'].str.lower())
            missing = expected_cols - found

            result = {
                'exists': True,
                'found_columns': sorted(found),
                'missing_columns': sorted(missing),
                'all_expected_present': len(missing) == 0
            }

            if missing:
                logger.warning(
                    f"FactVentas: columnas faltantes: {missing}. "
                    f"Se usará td_ventas_bob_historico como fallback para cobertura."
                )
            else:
                logger.info("FactVentas: todas las columnas esperadas están presentes.")

            return result

        except Exception as e:
            logger.error(f"Error validando esquema de FactVentas: {e}")
            return {'exists': False, 'found_columns': [], 'missing_columns': list(expected_cols)}

    # ------------------------------------------------------------------
    # Query 1: Cobertura mensual (clientes únicos)
    # ------------------------------------------------------------------
    def get_cobertura_mensual(self, months_back: int = 24) -> pd.DataFrame:
        """
        Clientes únicos activos por marca/ciudad/mes.
        Intenta FactVentas primero; si no existe, usa td_ventas_bob_historico.

        Returns:
            DataFrame con columnas: marcadir, ciudad, anio, mes, clientes_unicos
        """
        # Intentar con FactVentas (tiene cod_cliente_padre)
        schema_info = self.validate_factventas_schema()

        if schema_info.get('all_expected_present'):
            return self._cobertura_from_factventas(months_back)
        else:
            logger.info("Usando td_ventas_bob_historico como proxy para cobertura")
            return self._cobertura_from_historico(months_back)

    def _cobertura_from_factventas(self, months_back: int) -> pd.DataFrame:
        """Cobertura desde FactVentas (datos granulares por cliente)"""
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            ciudad,
            anio,
            mes,
            COUNT(DISTINCT cod_cliente_padre) AS clientes_unicos
        FROM {self.schema}.{cfg.TABLE_FACT_VENTAS}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, ciudad, anio, mes
        ORDER BY anio, mes, marcadir, ciudad
        """
        return self.db.execute_query(query)

    def _cobertura_from_historico(self, months_back: int) -> pd.DataFrame:
        """
        Proxy de cobertura usando td_ventas_bob_historico.
        Sin cod_cliente_padre, usamos combinaciones únicas de subfamilia como proxy.
        """
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            ciudad,
            anio,
            mes,
            COUNT(DISTINCT subfamilia) AS clientes_unicos
        FROM {self.schema}.{cfg.TABLE_VENTAS_HISTORICO}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, ciudad, anio, mes
        ORDER BY anio, mes, marcadir, ciudad
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Query 2: Drop Size mensual (venta / cliente)
    # ------------------------------------------------------------------
    def get_dropsize_mensual(self, months_back: int = 24) -> pd.DataFrame:
        """
        Drop size mensual: venta promedio por cliente activo.

        Returns:
            DataFrame con: marcadir, ciudad, anio, mes,
                           total_venta, total_c9l, clientes,
                           dropsize_bob, dropsize_c9l
        """
        schema_info = self.validate_factventas_schema()

        if schema_info.get('all_expected_present'):
            return self._dropsize_from_factventas(months_back)
        else:
            return self._dropsize_from_historico(months_back)

    def _dropsize_from_factventas(self, months_back: int) -> pd.DataFrame:
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            ciudad,
            anio,
            mes,
            SUM(CAST(total_venta AS NUMERIC)) AS total_venta,
            SUM(CAST(c9l AS NUMERIC)) AS total_c9l,
            COUNT(DISTINCT cod_cliente_padre) AS clientes,
            CASE WHEN COUNT(DISTINCT cod_cliente_padre) > 0
                 THEN SUM(CAST(total_venta AS NUMERIC)) / COUNT(DISTINCT cod_cliente_padre)
                 ELSE 0 END AS dropsize_bob,
            CASE WHEN COUNT(DISTINCT cod_cliente_padre) > 0
                 THEN SUM(CAST(c9l AS NUMERIC)) / COUNT(DISTINCT cod_cliente_padre)
                 ELSE 0 END AS dropsize_c9l
        FROM {self.schema}.{cfg.TABLE_FACT_VENTAS}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, ciudad, anio, mes
        ORDER BY anio, mes, marcadir, ciudad
        """
        return self.db.execute_query(query)

    def _dropsize_from_historico(self, months_back: int) -> pd.DataFrame:
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            ciudad,
            anio,
            mes,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) AS total_venta,
            SUM(CAST(c9l AS NUMERIC)) AS total_c9l,
            COUNT(DISTINCT subfamilia) AS clientes,
            CASE WHEN COUNT(DISTINCT subfamilia) > 0
                 THEN SUM(CAST(fin_01_ingreso AS NUMERIC)) / COUNT(DISTINCT subfamilia)
                 ELSE 0 END AS dropsize_bob,
            CASE WHEN COUNT(DISTINCT subfamilia) > 0
                 THEN SUM(CAST(c9l AS NUMERIC)) / COUNT(DISTINCT subfamilia)
                 ELSE 0 END AS dropsize_c9l
        FROM {self.schema}.{cfg.TABLE_VENTAS_HISTORICO}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, ciudad, anio, mes
        ORDER BY anio, mes, marcadir, ciudad
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Query 3: Hit Rate mensual por ciudad (12+ meses)
    # ------------------------------------------------------------------
    def get_hitrate_mensual_historico(self, months_back: int = 24) -> pd.DataFrame:
        """
        Hit Rate y Eficiencia mensual por ciudad para los últimos N meses.
        Extiende el patrón de get_hitrate_mensual() de database.py.

        Nota: fact_eficiencia_hitrate NO tiene columna de marca,
        así que hit rate solo está disponible a nivel ciudad.

        Returns:
            DataFrame con: ciudad, anio, mes, clientes_totales,
                           clientes_contactados, clientes_con_venta,
                           eficiencia, hit_rate
        """
        query = f"""
        WITH per_cliente AS (
            SELECT
                anio_visita AS anio,
                mes_visita AS mes,
                ciudad_no_concrecion AS ciudad,
                codigo_cliente,
                MAX(CASE WHEN tipo_visita = 'Ventas' THEN 1 ELSE 0 END) AS tuvo_venta,
                MAX(CASE WHEN tipo_visita = 'Visita' THEN 1 ELSE 0 END) AS tuvo_visita
            FROM {self.schema}.{cfg.TABLE_HITRATE}
            WHERE (anio_visita * 12 + mes_visita) >= (
                    EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                    + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                    - {months_back}
                  )
            GROUP BY anio_visita, mes_visita, ciudad_no_concrecion, codigo_cliente
        )
        SELECT
            ciudad,
            anio,
            mes,
            COUNT(*) AS clientes_totales,
            SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) AS clientes_contactados,
            SUM(tuvo_venta) AS clientes_con_venta,
            ROUND(
                100.0 * SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0)
            , 2) AS eficiencia,
            ROUND(
                100.0 * SUM(tuvo_venta)
                / NULLIF(SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END), 0)
            , 2) AS hit_rate
        FROM per_cliente
        WHERE ciudad IS NOT NULL
        GROUP BY ciudad, anio, mes
        ORDER BY ciudad, anio, mes
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Query 4: Ventas mensuales históricas (24+ meses)
    # ------------------------------------------------------------------
    def get_ventas_mensuales_historicas(self, months_back: int = 36) -> pd.DataFrame:
        """
        Ventas mensuales históricas por marca y ciudad.
        Fuente principal para el motor estadístico Holt-Winters.

        Returns:
            DataFrame con: marcadir, ciudad, anio, mes,
                           venta_bob, venta_c9l
        """
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            ciudad,
            anio,
            mes,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) AS venta_bob,
            SUM(CAST(c9l AS NUMERIC)) AS venta_c9l
        FROM {self.schema}.{cfg.TABLE_VENTAS_HISTORICO}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, ciudad, anio, mes
        ORDER BY marcadir, ciudad, anio, mes
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Query 5: Ventas históricas por subfamilia (36m)
    # ------------------------------------------------------------------
    def get_ventas_historicas_subfamilia(self, months_back: int = 36) -> pd.DataFrame:
        """
        Ventas mensuales históricas por marca y subfamilia.
        Para forecast HW a nivel subfamilia.

        Returns:
            DataFrame con: marcadir, subfamilia, anio, mes, venta_bob, venta_c9l
        """
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            marcadir,
            subfamilia,
            anio,
            mes,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) AS venta_bob,
            SUM(CAST(c9l AS NUMERIC)) AS venta_c9l
        FROM {self.schema}.{cfg.TABLE_VENTAS_HISTORICO}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY marcadir, subfamilia, anio, mes
        ORDER BY marcadir, subfamilia, anio, mes
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Query 6: Ventas históricas por canal (36m)
    # ------------------------------------------------------------------
    def get_ventas_historicas_canal(self, months_back: int = 36) -> pd.DataFrame:
        """
        Ventas mensuales históricas por canal.
        Para forecast HW a nivel canal.

        Returns:
            DataFrame con: canal, anio, mes, venta_bob, venta_c9l
        """
        excluded_cities = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CITIES)
        excluded_channels = ", ".join(f"'{c}'" for c in cfg.EXCLUDED_CHANNELS)
        excluded_brands = ", ".join(f"'{b}'" for b in cfg.EXCLUDED_BRANDS)

        query = f"""
        SELECT
            canal,
            anio,
            mes,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) AS venta_bob,
            SUM(CAST(c9l AS NUMERIC)) AS venta_c9l
        FROM {self.schema}.{cfg.TABLE_VENTAS_HISTORICO}
        WHERE (anio * 12 + mes) >= (
                EXTRACT(YEAR FROM CURRENT_DATE)::INT * 12
                + EXTRACT(MONTH FROM CURRENT_DATE)::INT
                - {months_back}
              )
          AND UPPER(ciudad) NOT IN ({excluded_cities})
          AND UPPER(canal) NOT IN ({excluded_channels})
          AND UPPER(marcadir) NOT IN ({excluded_brands})
        GROUP BY canal, anio, mes
        ORDER BY canal, anio, mes
        """
        return self.db.execute_query(query)

    # ------------------------------------------------------------------
    # Método maestro: obtener todos los datos
    # ------------------------------------------------------------------
    def fetch_all(self, months_back_components: int = 24,
                  months_back_historico: int = 36) -> Dict[str, pd.DataFrame]:
        """
        Obtiene todos los datos necesarios para ambos motores de proyección.

        Returns:
            Dict con claves:
              - 'cobertura': Cobertura mensual por marca/ciudad
              - 'dropsize': Drop size mensual por marca/ciudad
              - 'hitrate': Hit rate mensual por ciudad
              - 'ventas_historicas': Ventas mensuales históricas
              - 'schema_validation': Resultado de validación de FactVentas
        """
        logger.info("Obteniendo datos para Proyección Objetiva...")

        schema_info = self.validate_factventas_schema()

        logger.info("  • Cobertura mensual...")
        cobertura = self.get_cobertura_mensual(months_back_components)
        logger.info(f"    → {len(cobertura)} registros de cobertura")

        logger.info("  • Drop Size mensual...")
        dropsize = self.get_dropsize_mensual(months_back_components)
        logger.info(f"    → {len(dropsize)} registros de drop size")

        logger.info("  • Hit Rate mensual histórico...")
        hitrate = self.get_hitrate_mensual_historico(months_back_components)
        logger.info(f"    → {len(hitrate)} registros de hit rate")

        logger.info("  • Ventas mensuales históricas...")
        ventas = self.get_ventas_mensuales_historicas(months_back_historico)
        logger.info(f"    → {len(ventas)} registros de ventas históricas")

        logger.info("  • Ventas históricas por subfamilia...")
        ventas_subfam = self.get_ventas_historicas_subfamilia(months_back_historico)
        logger.info(f"    → {len(ventas_subfam)} registros de ventas por subfamilia")

        logger.info("  • Ventas históricas por canal...")
        ventas_canal = self.get_ventas_historicas_canal(months_back_historico)
        logger.info(f"    → {len(ventas_canal)} registros de ventas por canal")

        return {
            'cobertura': cobertura,
            'dropsize': dropsize,
            'hitrate': hitrate,
            'ventas_historicas': ventas,
            'ventas_historicas_subfamilia': ventas_subfam,
            'ventas_historicas_canal': ventas_canal,
            'schema_validation': schema_info
        }
