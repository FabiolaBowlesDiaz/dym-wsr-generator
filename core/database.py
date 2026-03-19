"""
Módulo de Base de Datos para WSR Generator
Maneja todas las conexiones y queries a la base de datos
Configuración corregida para dwh_saiv con schema auto
"""

import psycopg2
import pandas as pd
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date
import calendar

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de base de datos para el WSR"""

    def __init__(self, config: dict, schema: str = 'auto'):
        """
        Inicializar el gestor de base de datos

        Args:
            config: Diccionario con configuración de conexión
            schema: Schema de base de datos a usar (default: 'auto')
        """
        self.config = config
        self.schema = schema  # Será 'auto' según tu configuración
        self.conn = None
        self.tipo_cambio = 6.96  # BOB/USD

    def _get_ciudades_sin_gerente(self, year: int) -> tuple:
        """
        Retorna tupla de ciudades sin gerente segun el ano.
        - 2025 y anteriores: Oruro y Trinidad usan SOP
        - 2026 en adelante: Solo Trinidad usa SOP (Oruro ya tiene gerente)
        """
        if year >= 2026:
            return ('TRINIDAD',)
        else:
            return ('ORURO', 'TRINIDAD')

    def _get_ciudades_sin_gerente_sql(self, year: int) -> str:
        """Retorna string SQL para usar en clausula IN"""
        ciudades = self._get_ciudades_sin_gerente(year)
        return ", ".join([f"'{c}'" for c in ciudades])

    def get_calendar_week_ranges(self, year: int, month: int) -> List[Tuple[int, int]]:
        """
        Calcula los rangos de días para cada semana CALENDARIO del mes.
        Las semanas van de Lunes a Domingo.

        Args:
            year: Año
            month: Mes (1-12)

        Returns:
            Lista de tuplas (día_inicio, día_fin) para cada semana del mes
            Ejemplo para Nov 2025: [(1,2), (3,9), (10,16), (17,23), (24,30)]
        """
        # Obtener el primer y último día del mes
        first_day = date(year, month, 1)
        last_day_num = calendar.monthrange(year, month)[1]

        weeks = []
        current_day = 1

        # Primera semana: desde día 1 hasta el próximo domingo
        first_weekday = first_day.weekday()  # 0=Lunes, 6=Domingo
        if first_weekday == 6:  # Si empieza en domingo
            weeks.append((1, 1))
            current_day = 2
        else:
            # Días hasta el domingo (6 - weekday)
            days_to_sunday = 6 - first_weekday
            end_first_week = min(1 + days_to_sunday, last_day_num)
            weeks.append((1, end_first_week))
            current_day = end_first_week + 1

        # Semanas intermedias (Lunes a Domingo completas)
        while current_day <= last_day_num:
            week_end = min(current_day + 6, last_day_num)
            weeks.append((current_day, week_end))
            current_day = week_end + 1

        # Asegurar que siempre tengamos 5 semanas (rellenar si es necesario)
        while len(weeks) < 5:
            weeks.append((last_day_num + 1, last_day_num + 1))  # Semana vacía

        logger.debug(f"Semanas calendario para {month}/{year}: {weeks}")
        return weeks[:5]  # Máximo 5 semanas

    def get_current_calendar_week(self, year: int, month: int, day: int) -> int:
        """
        Determina en qué semana calendario del mes estamos.

        Args:
            year: Año
            month: Mes
            day: Día del mes

        Returns:
            Número de semana (1-5)
        """
        weeks = self.get_calendar_week_ranges(year, month)
        for i, (start, end) in enumerate(weeks, 1):
            if start <= day <= end:
                return i
        return 5  # Por defecto última semana

    def connect(self) -> bool:
        """Establecer conexión con la base de datos"""
        try:
            # Conectar directamente a PostgreSQL con las credenciales del .env
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            logger.info(f"Conexión exitosa a la base de datos {self.config['database']}")
            logger.info(f"Usando schema: {self.schema}")
            return True
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            return False
    
    def disconnect(self):
        """Cerrar conexión con la base de datos"""
        if self.conn:
            self.conn.close()
            logger.info("Conexión cerrada")
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Ejecutar query y retornar DataFrame
        
        Args:
            query: Query SQL a ejecutar
            
        Returns:
            DataFrame con los resultados
        """
        try:
            df = pd.read_sql(query, self.conn)
            logger.debug(f"Query ejecutado exitosamente, {len(df)} filas retornadas")
            return df
        except Exception as e:
            logger.error(f"Error ejecutando query: {e}")
            logger.error(f"Query: {query[:500]}...")
            return pd.DataFrame()
    
    def get_ventas_historicas_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener ventas históricas por marca"""
        query = f"""
        SELECT 
            marcadir,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as vendido_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as vendido_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_avance_actual_marca(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener avance actual por marca"""
        query = f"""
        SELECT 
            marcadir,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as avance_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as avance_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_presupuesto_general_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener presupuesto general por marca"""
        query = f"""
        SELECT 
            marcadirectorio as marcadir,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general_bob,
            SUM(CAST(c9l AS NUMERIC)) as ppto_general_c9l
        FROM {self.schema}.factpresupuesto_general
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadirectorio
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_sop_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener SOP (presupuesto mensual) por marca"""
        query = f"""
        SELECT 
            marcadirectorio as marcadir,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob,
            SUM(CAST(c9l AS NUMERIC)) as sop_c9l
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadirectorio
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_proyecciones_marca(self, year: int, month: int, day: int) -> pd.DataFrame:
        """
        Obtener proyecciones híbridas por marca
        ENFOQUE HÍBRIDO: Combina ventas reales de semanas CALENDARIO pasadas + proyecciones de semanas futuras

        CORREGIDO: Usa semanas calendario (Lunes-Domingo) en lugar de rangos fijos de días.
        Ejemplo Nov 2025: S1=1-2, S2=3-9, S3=10-16, S4=17-23, S5=24-30

        Lógica por semana actual:
        - Semana 1: Proyección completa (S1+S2+S3+S4+S5)
        - Semana 2: Real_S1 + Proy_S2+S3+S4+S5
        - Semana 3: Real_S1+S2 + Proy_S3+S4+S5
        - Semana 4: Real_S1+S2+S3 + Proy_S4+S5
        - Semana 5: Real_S1+S2+S3+S4 + Proy_S5

        Para Oruro y Trinidad (sin gerente): Usa SOP COMPLETO (no prorrateado)
        """
        # Calcular rangos de semanas calendario
        weeks = self.get_calendar_week_ranges(year, month)
        current_week = self.get_current_calendar_week(year, month, day)

        # Extraer rangos de días para cada semana
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        logger.info(f"Semanas calendario: S1={s1_start}-{s1_end}, S2={s2_start}-{s2_end}, S3={s3_start}-{s3_end}, S4={s4_start}-{s4_end}, S5={s5_start}-{s5_end}")
        logger.info(f"Día actual: {day}, Semana actual: {current_week}")

        query = f"""
        WITH ventas_reales_semanales AS (
            -- Obtener ventas reales por marca, ciudad y semana CALENDARIO
            SELECT
                UPPER(marcadir) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
                SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
                SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
                SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s4,
                SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s5
            FROM {self.schema}.td_ventas_bob_historico
            WHERE anio = {year}
                AND mes = {month}
                AND dia <= {day}
                AND UPPER(ciudad) != 'TURISMO'
                AND UPPER(canal) != 'TURISMO'
                AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY UPPER(marcadir), UPPER(ciudad)
        ),
        proyecciones_gerentes_base AS (
            -- Obtener proyecciones de gerentes por semana (convertir USD a BOB, SUMAR y NORMALIZAR)
            SELECT
                UPPER(nombre_marca) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
                END) as proy_s1,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
                END) as proy_s2,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
                END) as proy_s3,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
                END) as proy_s4,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
                END) as proy_s5
            FROM {self.schema}.fact_proyecciones
            WHERE anio_proyeccion = {year}
                AND mes_proyeccion = {month}
                AND UPPER(ciudad) != 'TURISMO'
            GROUP BY UPPER(nombre_marca), UPPER(ciudad)
        ),
        ciudades_todas AS (
            -- Obtener todas las combinaciones únicas de marca-ciudad (de ventas reales y proyecciones)
            SELECT DISTINCT marcadir, ciudad FROM ventas_reales_semanales
            UNION
            SELECT DISTINCT marcadir, ciudad FROM proyecciones_gerentes_base
        ),
        proyecciones_gerentes AS (
            -- Aplicar lógica híbrida: Ventas reales de semanas CERRADAS + Proyecciones de semanas FUTURAS
            SELECT
                ct.marcadir,
                ct.ciudad,
                CASE
                    -- Semana 1: Proyección completa
                    WHEN {current_week} = 1 THEN
                        COALESCE(pg.proy_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana 2: Real S1 (cerrada) + Proy S2-S5
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana 3: Real S1-S2 (cerradas) + Proy S3-S5
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(pg.proy_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana 4: Real S1-S3 (cerradas) + Proy S4-S5
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana 5: Real S1-S4 (cerradas) + Proy S5
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) + COALESCE(pg.proy_s5, 0)
                END as total_bob
            FROM ciudades_todas ct
            LEFT JOIN proyecciones_gerentes_base pg
                ON ct.marcadir = pg.marcadir AND ct.ciudad = pg.ciudad
            LEFT JOIN ventas_reales_semanales vr
                ON ct.marcadir = vr.marcadir AND ct.ciudad = vr.ciudad
            WHERE ct.ciudad NOT IN ({self._get_ciudades_sin_gerente_sql(year)})
        ),
        sop_ciudades_sin_gerente_base AS (
            -- Obtener SOP COMPLETO de ciudades sin gerente (no prorrateado)
            SELECT
                UPPER(marcadirectorio) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
            FROM {self.schema}.factpresupuesto_mensual
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) IN ({self._get_ciudades_sin_gerente_sql(year)})
                AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY UPPER(marcadirectorio), UPPER(ciudad)
        ),
        oruro_trinidad_todas AS (
            -- Obtener todas las marcas con ventas reales O SOP en ciudades sin gerente
            SELECT DISTINCT marcadir, ciudad
            FROM ventas_reales_semanales
            WHERE ciudad IN ({self._get_ciudades_sin_gerente_sql(year)})
            UNION
            SELECT DISTINCT marcadir, ciudad
            FROM sop_ciudades_sin_gerente_base
        ),
        sop_ciudades_sin_gerente AS (
            -- Para Oruro/Trinidad: Ventas reales CERRADAS + SOP con PORCENTAJES PERSONALIZADOS
            -- ORURO: S1=8%, S2=12%, S3=20%, S4=28%, S5=32%
            -- TRINIDAD: S1=25%, S2=18%, S3=22%, S4=20%, S5=15%
            SELECT
                ot.marcadir,
                ot.ciudad,
                CASE
                    -- Semana 1: SOP completo (todas las semanas son proyección)
                    WHEN {current_week} = 1 THEN
                        COALESCE(sop.sop_total_mes, 0)

                    -- Semana 2: Real S1 + SOP porcentaje restante (S2+S3+S4+S5)
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.92, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.75, 0) END

                    -- Semana 3: Real S1-S2 + SOP porcentaje restante (S3+S4+S5)
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.80, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.57, 0) END

                    -- Semana 4: Real S1-S3 + SOP porcentaje restante (S4+S5)
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.60, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.35, 0) END

                    -- Semana 5: Real S1-S4 + SOP porcentaje restante (S5)
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.32, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.15, 0) END
                END as total_bob
            FROM oruro_trinidad_todas ot
            LEFT JOIN sop_ciudades_sin_gerente_base sop
                ON ot.marcadir = sop.marcadir AND ot.ciudad = sop.ciudad
            LEFT JOIN ventas_reales_semanales vr
                ON ot.marcadir = vr.marcadir AND ot.ciudad = vr.ciudad
        ),
        consolidado_marcas AS (
            SELECT
                marcadir,
                SUM(total_bob) as py_{year}_bob
            FROM (
                SELECT marcadir, total_bob FROM proyecciones_gerentes
                UNION ALL
                SELECT marcadir, total_bob FROM sop_ciudades_sin_gerente
            ) unificado
            WHERE UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY marcadir
        )
        SELECT * FROM consolidado_marcas
        ORDER BY py_{year}_bob DESC
        """
        return self.execute_query(query)
    
    def get_stock_marca(self) -> pd.DataFrame:
        """Obtener stock actual por marca usando marcadirectorio"""
        query = f"""
        SELECT
            marcadirectorio as marcadir,
            SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) as stock_c9l
        FROM {self.schema}.td_stock_sap
        WHERE UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            AND UPPER(ciudad) != 'TURISMO'
        GROUP BY marcadirectorio
        HAVING SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) > 0
        ORDER BY SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) DESC
        """
        return self.execute_query(query)
    
    def get_marcas_con_stock_en_almacenes(self, warehouse_column: str, warehouses: list, min_c9l: float = 1.0) -> set:
        """Obtener set de marcas con stock >= min_c9l en almacenes específicos.

        Returns set of brand names (uppercase) or empty set if query fails.
        """
        placeholders = ', '.join(f"'{w}'" for w in warehouses)
        query = f"""
        SELECT
            UPPER(marcadirectorio) as marca
        FROM {self.schema}.td_stock_sap
        WHERE {warehouse_column} IN ({placeholders})
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY UPPER(marcadirectorio)
        HAVING SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) >= {min_c9l}
        """
        df = self.execute_query(query)
        if df is None or df.empty:
            return set()
        return set(df['marca'].str.upper())

    def get_ventas_semanales_marca(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener ventas semanales por marca (SEMANAS CALENDARIO)"""
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            marcadir,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana1_c9l,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana2_c9l,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana3_c9l,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana4_c9l,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana5_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir
        """
        return self.execute_query(query)
    
    def get_venta_promedio_diaria_marca(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener venta promedio diaria para cálculo de cobertura"""
        query = f"""
        SELECT 
            marcadir,
            COUNT(DISTINCT fecha) as dias_con_venta,
            SUM(CAST(c9l AS NUMERIC)) as total_c9l,
            SUM(CAST(c9l AS NUMERIC)) / NULLIF(COUNT(DISTINCT fecha), 0) as venta_promedio_diaria_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir
        ORDER BY total_c9l DESC
        """
        return self.execute_query(query)
    
    def get_proyecciones_semanales_nacional(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener proyecciones semanales a nivel nacional (BOB y C9L)
        Para el gráfico de tendencia comparativa
        """
        query = f"""
        SELECT
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
            END) as total_semana1,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
            END) as total_semana2,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
            END) as total_semana3,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
            END) as total_semana4,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
            END) as total_semana5
        FROM {self.schema}.fact_proyecciones
        WHERE anio_proyeccion = {year}
            AND mes_proyeccion = {month}
            AND UPPER(ciudad) != 'TURISMO'
        """
        return self.execute_query(query)

    def get_ventas_semanales_nacional(self, year: int, month: int, day: int) -> pd.DataFrame:
        """
        Obtener ventas semanales a nivel nacional (BOB y C9L) - SEMANAS CALENDARIO
        Para el gráfico de tendencia comparativa
        """
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana1_c9l,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana2_c9l,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana3_c9l,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana4_c9l,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana5_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
        """
        return self.execute_query(query)

    def get_sop_oruro_trinidad(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener presupuesto mensual (SOP) de ciudades sin gerente
        Para distribuir semanalmente en el grafico de tendencia
        - 2025 y anteriores: Oruro y Trinidad
        - 2026 en adelante: Solo Trinidad (Oruro ya tiene gerente)
        """
        query = f"""
        SELECT
            ciudad,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_mensual
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) IN ({self._get_ciudades_sin_gerente_sql(year)})
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY ciudad
        """
        return self.execute_query(query)

    def get_comentarios_gerentes(self, year: int, month: int) -> pd.DataFrame:
        """Obtener comentarios de gerentes para resumen ejecutivo"""
        query = f"""
        SELECT
            usuario,
            ciudad,
            nombre_marca,
            COALESCE(comentario_semana1, '') as com_s1,
            COALESCE(comentario_semana2, '') as com_s2,
            COALESCE(comentario_semana3, '') as com_s3,
            COALESCE(comentario_semana4, '') as com_s4,
            COALESCE(comentario_semana5, '') as com_s5,
            CASE
                WHEN moneda = 'USD' THEN (
                    COALESCE(CAST(total_semana1 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana2 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana3 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana4 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana5 AS NUMERIC), 0)
                ) * {self.tipo_cambio}
                ELSE (
                    COALESCE(CAST(total_semana1 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana2 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana3 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana4 AS NUMERIC), 0) +
                    COALESCE(CAST(total_semana5 AS NUMERIC), 0)
                )
            END as proyeccion_total_bob
        FROM {self.schema}.fact_proyecciones
        WHERE anio_proyeccion = {year}
            AND mes_proyeccion = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND (comentario_semana1 IS NOT NULL 
                 OR comentario_semana2 IS NOT NULL 
                 OR comentario_semana3 IS NOT NULL 
                 OR comentario_semana4 IS NOT NULL 
                 OR comentario_semana5 IS NOT NULL)
        ORDER BY usuario, ciudad, proyeccion_total_bob DESC
        """
        return self.execute_query(query)
    
    # === QUERIES POR CIUDAD ===
    
    def get_ventas_historicas_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """Obtener ventas históricas por ciudad"""
        query = f"""
        SELECT 
            ciudad,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as vendido_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as vendido_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_avance_actual_ciudad(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener avance actual por ciudad"""
        query = f"""
        SELECT 
            ciudad,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as avance_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as avance_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_presupuesto_general_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """Obtener presupuesto general por ciudad"""
        query = f"""
        SELECT 
            ciudad,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general_bob,
            SUM(CAST(c9l AS NUMERIC)) as ppto_general_c9l
        FROM {self.schema}.factpresupuesto_general
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_sop_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """Obtener SOP por ciudad"""
        query = f"""
        SELECT 
            ciudad,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob,
            SUM(CAST(c9l AS NUMERIC)) as sop_c9l
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_proyecciones_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """Obtener proyecciones por ciudad (con lógica especial para Oruro y Trinidad)"""
        query = f"""
        WITH proyecciones_detalle AS (
            SELECT 
                ciudad,
                nombre_marca,
                moneda,
                COALESCE(CAST(total_semana1 AS NUMERIC), 0) +
                COALESCE(CAST(total_semana2 AS NUMERIC), 0) +
                COALESCE(CAST(total_semana3 AS NUMERIC), 0) +
                COALESCE(CAST(total_semana4 AS NUMERIC), 0) +
                COALESCE(CAST(total_semana5 AS NUMERIC), 0) as total_marca
            FROM {self.schema}.fact_proyecciones
            WHERE anio_proyeccion = {year}
                AND mes_proyeccion = {month}
                AND UPPER(ciudad) != 'TURISMO'
        ),
        proyecciones_por_ciudad AS (
            SELECT 
                ciudad,
                SUM(CASE 
                    WHEN moneda = 'USD' THEN total_marca * {self.tipo_cambio}
                    ELSE total_marca 
                END) as py_{year}_bob
            FROM proyecciones_detalle
            GROUP BY ciudad
        ),
        sop_por_ciudad AS (
            SELECT 
                ciudad,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob
            FROM {self.schema}.factpresupuesto_mensual
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) != 'TURISMO'
            GROUP BY ciudad
        )
        SELECT 
            s.ciudad,
            COALESCE(p.py_{year}_bob, s.sop_bob) as py_{year}_bob,
            s.sop_bob as py_{year}_c9l,
            CASE 
                WHEN p.py_{year}_bob IS NULL THEN 'SOP (sin proyección)'
                ELSE 'Proyección gerente'
            END as fuente
        FROM sop_por_ciudad s
        LEFT JOIN proyecciones_por_ciudad p ON UPPER(s.ciudad) = UPPER(p.ciudad)
        ORDER BY COALESCE(p.py_{year}_bob, s.sop_bob) DESC
        """
        return self.execute_query(query)

    def get_proyecciones_ciudad_hibrido(self, year: int, month: int, day: int) -> pd.DataFrame:
        """
        Obtener proyecciones híbridas por ciudad
        ENFOQUE HÍBRIDO: Combina ventas reales de semanas CALENDARIO pasadas + proyecciones de semanas futuras

        CORREGIDO: Usa semanas calendario (Lunes-Domingo) + SOP ponderado para Oruro/Trinidad
        """
        # Calcular rangos de semanas calendario
        weeks = self.get_calendar_week_ranges(year, month)
        current_week = self.get_current_calendar_week(year, month, day)

        # Extraer rangos de días para cada semana
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        WITH ventas_reales_semanales AS (
            -- Obtener ventas reales por ciudad y semana CALENDARIO
            SELECT
                UPPER(ciudad) as ciudad,
                SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
                SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
                SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
                SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s4,
                SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s5
            FROM {self.schema}.td_ventas_bob_historico
            WHERE anio = {year}
                AND mes = {month}
                AND dia <= {day}
                AND UPPER(ciudad) != 'TURISMO'
                AND UPPER(canal) != 'TURISMO'
                AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY UPPER(ciudad)
        ),
        proyecciones_gerentes_base AS (
            -- Proyecciones de gerentes (ciudades CON gerente)
            SELECT
                UPPER(ciudad) as ciudad,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
                END) as proy_s1,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
                END) as proy_s2,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
                END) as proy_s3,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
                END) as proy_s4,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
                END) as proy_s5
            FROM {self.schema}.fact_proyecciones
            WHERE anio_proyeccion = {year}
                AND mes_proyeccion = {month}
                AND UPPER(ciudad) != 'TURISMO'
            GROUP BY UPPER(ciudad)
        ),
        sop_ciudades_sin_gerente AS (
            -- SOP total para ciudades sin gerente
            SELECT
                UPPER(ciudad) as ciudad,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
            FROM {self.schema}.factpresupuesto_mensual
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) IN ({self._get_ciudades_sin_gerente_sql(year)})
            GROUP BY UPPER(ciudad)
        ),
        ciudades_con_gerente AS (
            -- Proyeccion hibrida para ciudades CON gerente
            SELECT
                pg.ciudad,
                CASE
                    WHEN {current_week} = 1 THEN
                        COALESCE(pg.proy_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(pg.proy_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) + COALESCE(pg.proy_s5, 0)
                END as total_bob
            FROM proyecciones_gerentes_base pg
            LEFT JOIN ventas_reales_semanales vr ON pg.ciudad = vr.ciudad
            WHERE pg.ciudad NOT IN ({self._get_ciudades_sin_gerente_sql(year)})
        ),
        ciudades_sin_gerente AS (
            -- Proyección híbrida para Oruro y Trinidad (SOP ponderado)
            -- ORURO: S1=8%, S2=12%, S3=20%, S4=28%, S5=32%
            -- TRINIDAD: S1=25%, S2=18%, S3=22%, S4=20%, S5=15%
            SELECT
                sop.ciudad,
                CASE
                    WHEN {current_week} = 1 THEN
                        COALESCE(sop.sop_total_mes, 0)
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) +
                        CASE WHEN sop.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.92, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.75, 0) END
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        CASE WHEN sop.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.80, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.57, 0) END
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) +
                        CASE WHEN sop.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.60, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.35, 0) END
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) +
                        CASE WHEN sop.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.32, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.15, 0) END
                END as total_bob
            FROM sop_ciudades_sin_gerente sop
            LEFT JOIN ventas_reales_semanales vr ON sop.ciudad = vr.ciudad
        )
        SELECT ciudad, total_bob as py_{year}_bob
        FROM (
            SELECT ciudad, total_bob FROM ciudades_con_gerente
            UNION ALL
            SELECT ciudad, total_bob FROM ciudades_sin_gerente
        ) unificado
        ORDER BY py_{year}_bob DESC
        """
        return self.execute_query(query)

    def get_proyecciones_ciudad_marca_hibrido(self, year: int, month: int, day: int) -> pd.DataFrame:
        """
        Obtener proyecciones híbridas por ciudad Y marca directorio (para drill-down)
        ENFOQUE HÍBRIDO: Combina ventas reales de semanas CALENDARIO + proyecciones de semanas futuras

        CORREGIDO: Usa semanas calendario (Lun-Dom) + ponderaciones SOP personalizadas
        Similar a get_proyecciones_marca() pero con GROUP BY ciudad y marcadir
        Output: DataFrame con [ciudad, marcadir, py_2025_bob]
        """
        # Calcular rangos de semanas calendario
        weeks = self.get_calendar_week_ranges(year, month)
        current_week = self.get_current_calendar_week(year, month, day)

        # Extraer rangos de días para cada semana
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        WITH ventas_reales_semanales AS (
            -- Obtener ventas reales por marca, ciudad y semana CALENDARIO
            SELECT
                UPPER(marcadir) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
                SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
                SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
                SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s4,
                SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s5
            FROM {self.schema}.td_ventas_bob_historico
            WHERE anio = {year}
                AND mes = {month}
                AND dia <= {day}
                AND UPPER(ciudad) != 'TURISMO'
                AND UPPER(canal) != 'TURISMO'
                AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY UPPER(marcadir), UPPER(ciudad)
        ),
        proyecciones_gerentes_base AS (
            -- Obtener proyecciones de gerentes por semana (convertir USD a BOB, SUMAR y NORMALIZAR)
            SELECT
                UPPER(nombre_marca) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
                END) as proy_s1,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
                END) as proy_s2,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
                END) as proy_s3,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
                END) as proy_s4,
                SUM(CASE
                    WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * {self.tipo_cambio}
                    ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
                END) as proy_s5
            FROM {self.schema}.fact_proyecciones
            WHERE anio_proyeccion = {year}
                AND mes_proyeccion = {month}
                AND UPPER(ciudad) != 'TURISMO'
            GROUP BY UPPER(nombre_marca), UPPER(ciudad)
        ),
        ciudades_marcas_todas AS (
            -- Obtener todas las combinaciones únicas de marca-ciudad
            SELECT DISTINCT marcadir, ciudad FROM ventas_reales_semanales
            UNION
            SELECT DISTINCT marcadir, ciudad FROM proyecciones_gerentes_base
        ),
        proyecciones_gerentes AS (
            -- Aplicar lógica híbrida: Ventas reales + Proyecciones futuras (SEMANAS CALENDARIO)
            SELECT
                ct.marcadir,
                ct.ciudad,
                CASE
                    -- Semana calendario 1: Proyección completa
                    WHEN {current_week} = 1 THEN
                        COALESCE(pg.proy_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana calendario 2: Real S1 + Proy S2-S5
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                        COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana calendario 3: Real S1-S2 + Proy S3-S5
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(pg.proy_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana calendario 4: Real S1-S3 + Proy S4-S5
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)

                    -- Semana calendario 5: Real S1-S4 + Proy S5
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) + COALESCE(pg.proy_s5, 0)
                END as total_bob
            FROM ciudades_marcas_todas ct
            LEFT JOIN proyecciones_gerentes_base pg
                ON ct.marcadir = pg.marcadir AND ct.ciudad = pg.ciudad
            LEFT JOIN ventas_reales_semanales vr
                ON ct.marcadir = vr.marcadir AND ct.ciudad = vr.ciudad
            WHERE ct.ciudad NOT IN ({self._get_ciudades_sin_gerente_sql(year)})
        ),
        sop_ciudades_sin_gerente_base AS (
            -- Obtener SOP de ciudades sin gerente (NORMALIZADO A MAYUSCULAS)
            SELECT
                UPPER(marcadirectorio) as marcadir,
                UPPER(ciudad) as ciudad,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
            FROM {self.schema}.factpresupuesto_mensual
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) IN ({self._get_ciudades_sin_gerente_sql(year)})
                AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY UPPER(marcadirectorio), UPPER(ciudad)
        ),
        ciudades_sin_gerente_todas AS (
            -- Obtener todas las marcas con ventas reales O SOP en ciudades sin gerente
            SELECT DISTINCT marcadir, ciudad
            FROM ventas_reales_semanales
            WHERE ciudad IN ({self._get_ciudades_sin_gerente_sql(year)})
            UNION
            SELECT DISTINCT marcadir, ciudad
            FROM sop_ciudades_sin_gerente_base
        ),
        sop_ciudades_sin_gerente AS (
            -- Aplicar lógica híbrida con SOP ponderado (SEMANAS CALENDARIO + PESOS ESPECÍFICOS)
            -- ORURO: S1=8%, S2=12%, S3=20%, S4=28%, S5=32%
            -- TRINIDAD: S1=25%, S2=18%, S3=22%, S4=20%, S5=15%
            SELECT
                ot.marcadir,
                ot.ciudad,
                CASE
                    -- Semana calendario 1: SOP completo (100%)
                    WHEN {current_week} = 1 THEN
                        COALESCE(sop.sop_total_mes, 0)

                    -- Semana calendario 2: Real S1 + SOP ponderado para S2-S5
                    WHEN {current_week} = 2 THEN
                        COALESCE(vr.venta_real_s1, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.92, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.75, 0) END

                    -- Semana calendario 3: Real S1-S2 + SOP ponderado para S3-S5
                    WHEN {current_week} = 3 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.80, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.57, 0) END

                    -- Semana calendario 4: Real S1-S3 + SOP ponderado para S4-S5
                    WHEN {current_week} = 4 THEN
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.60, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.35, 0) END

                    -- Semana calendario 5: Real S1-S4 + SOP ponderado para S5
                    ELSE
                        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                        COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) +
                        CASE WHEN ot.ciudad = 'ORURO' THEN COALESCE(sop.sop_total_mes * 0.32, 0)
                             ELSE COALESCE(sop.sop_total_mes * 0.15, 0) END
                END as total_bob
            FROM ciudades_sin_gerente_todas ot
            LEFT JOIN sop_ciudades_sin_gerente_base sop
                ON ot.marcadir = sop.marcadir AND ot.ciudad = sop.ciudad
            LEFT JOIN ventas_reales_semanales vr
                ON ot.marcadir = vr.marcadir AND ot.ciudad = vr.ciudad
        )
        SELECT marcadir, ciudad, total_bob as py_{year}_bob
        FROM (
            SELECT marcadir, ciudad, total_bob FROM proyecciones_gerentes
            UNION ALL
            SELECT marcadir, ciudad, total_bob FROM sop_ciudades_sin_gerente
        ) unificado
        WHERE UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        ORDER BY ciudad, py_{year}_bob DESC
        """
        return self.execute_query(query)

    def get_ventas_semanales_ciudad(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener ventas semanales por ciudad (SEMANAS CALENDARIO)"""
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            ciudad,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana1_c9l,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana2_c9l,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana3_c9l,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana4_c9l,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana5_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        """
        return self.execute_query(query)

    # === QUERIES POR CIUDAD Y MARCA DIRECTORIO ===

    def get_ventas_historicas_ciudad_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener ventas históricas por ciudad y marca directorio"""
        query = f"""
        SELECT
            ciudad,
            marcadir,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as vendido_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as vendido_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad, marcadir
        ORDER BY ciudad, SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_avance_actual_ciudad_marca(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener avance actual por ciudad y marca directorio"""
        query = f"""
        SELECT
            ciudad,
            marcadir,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as avance_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as avance_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad, marcadir
        ORDER BY ciudad, SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_presupuesto_general_ciudad_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener presupuesto general por ciudad y marca directorio"""
        query = f"""
        SELECT
            ciudad,
            marcadirectorio as marcadir,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general_bob,
            SUM(CAST(c9l AS NUMERIC)) as ppto_general_c9l
        FROM {self.schema}.factpresupuesto_general
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad, marcadirectorio
        ORDER BY ciudad, SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_sop_ciudad_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener SOP (presupuesto mensual) por ciudad y marca directorio"""
        query = f"""
        SELECT
            ciudad,
            marcadirectorio as marcadir,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob,
            SUM(CAST(c9l AS NUMERIC)) as sop_c9l
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad, marcadirectorio
        ORDER BY ciudad, SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_stock_ciudad_marca(self) -> pd.DataFrame:
        """Obtener stock actual por ciudad y marca directorio"""
        query = f"""
        SELECT
            ciudad,
            marcadirectorio as marcadir,
            SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) as stock_c9l
        FROM {self.schema}.td_stock_sap
        WHERE UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            AND UPPER(ciudad) != 'TURISMO'
        GROUP BY ciudad, marcadirectorio
        HAVING SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) > 0
        ORDER BY ciudad, SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) DESC
        """
        return self.execute_query(query)

    def get_venta_promedio_diaria_ciudad_marca(self, year: int, month: int) -> pd.DataFrame:
        """Obtener venta promedio diaria por ciudad y marca directorio para calcular cobertura"""
        query = f"""
        SELECT
            ciudad,
            marcadir,
            AVG(CAST(c9l AS NUMERIC)) as venta_promedio_diaria_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad, marcadir
        ORDER BY ciudad, marcadir
        """
        return self.execute_query(query)

    # === QUERIES POR CANAL ===
    
    def get_ventas_historicas_canal(self, year: int, month: int) -> pd.DataFrame:
        """Obtener ventas históricas por canal"""
        query = f"""
        SELECT 
            canal,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as vendido_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as vendido_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY canal
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_avance_actual_canal(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener avance actual por canal"""
        query = f"""
        SELECT 
            canal,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as avance_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as avance_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY canal
        ORDER BY SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_presupuesto_general_canal(self, year: int, month: int) -> pd.DataFrame:
        """Obtener presupuesto general por canal"""
        query = f"""
        SELECT 
            canal,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general_bob,
            SUM(CAST(c9l AS NUMERIC)) as ppto_general_c9l
        FROM {self.schema}.factpresupuesto_general
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY canal
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_sop_canal(self, year: int, month: int) -> pd.DataFrame:
        """Obtener SOP por canal"""
        query = f"""
        SELECT 
            canal,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob,
            SUM(CAST(c9l AS NUMERIC)) as sop_c9l
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY canal
        ORDER BY SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)
    
    def get_ventas_semanales_canal(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener ventas semanales por canal (SEMANAS CALENDARIO)"""
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            canal,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana1_c9l,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana2_c9l,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana3_c9l,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana4_c9l,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana5_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY canal
        """
        return self.execute_query(query)
    
    def calcular_py_canal(self, year: int, month: int, day: int, total_py: float) -> pd.DataFrame:
        """
        Calcular proyección por canal usando multiplicador ponderado
        Fórmula: Clavei = 0.10×(Ri/∑R) + 0.04×(Qi/∑Q) + 0.06×(Si/∑S) + 0.80×(Ti/∑T)
        """
        query = f"""
        WITH datos_canales AS (
            SELECT 
                c.canal,
                -- Vendido año anterior (R)
                SUM(CASE WHEN c.anio = {year-1} AND c.mes = {month} 
                    THEN CAST(c.fin_01_ingreso AS NUMERIC) ELSE 0 END) as vendido_anterior,
                -- Avance actual (T)
                SUM(CASE WHEN c.anio = {year} AND c.mes = {month} AND c.dia <= {day}
                    THEN CAST(c.fin_01_ingreso AS NUMERIC) ELSE 0 END) as avance_actual
            FROM {self.schema}.td_ventas_bob_historico c
            WHERE UPPER(c.ciudad) != 'TURISMO'
                AND UPPER(c.canal) != 'TURISMO'
                AND UPPER(c.marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            GROUP BY c.canal
        ),
        presupuestos AS (
            SELECT 
                canal,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general
            FROM {self.schema}.factpresupuesto_general
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) != 'TURISMO'
                AND UPPER(canal) != 'TURISMO'
            GROUP BY canal
        ),
        sop AS (
            SELECT 
                canal,
                SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop
            FROM {self.schema}.factpresupuesto_mensual
            WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
                AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
                AND UPPER(ciudad) != 'TURISMO'
                AND UPPER(canal) != 'TURISMO'
            GROUP BY canal
        ),
        totales AS (
            SELECT 
                SUM(d.vendido_anterior) as total_vendido,
                SUM(p.ppto_general) as total_ppto,
                SUM(s.sop) as total_sop,
                SUM(d.avance_actual) as total_avance
            FROM datos_canales d
            LEFT JOIN presupuestos p ON d.canal = p.canal
            LEFT JOIN sop s ON d.canal = s.canal
        )
        SELECT 
            d.canal,
            d.vendido_anterior,
            d.avance_actual,
            COALESCE(p.ppto_general, 0) as ppto_general,
            COALESCE(s.sop, 0) as sop,
            -- Multiplicador ponderado
            (0.10 * (d.vendido_anterior / NULLIF(t.total_vendido, 0)) +
             0.04 * (COALESCE(p.ppto_general, 0) / NULLIF(t.total_ppto, 0)) +
             0.06 * (COALESCE(s.sop, 0) / NULLIF(t.total_sop, 0)) +
             0.80 * (d.avance_actual / NULLIF(t.total_avance, 0))) as multiplicador
        FROM datos_canales d
        LEFT JOIN presupuestos p ON d.canal = p.canal
        LEFT JOIN sop s ON d.canal = s.canal
        CROSS JOIN totales t
        ORDER BY multiplicador DESC
        """
        
        df = self.execute_query(query)
        
        # Aplicar el total de proyección al multiplicador
        if not df.empty:
            df[f'py_{year}_bob'] = df['multiplicador'] * total_py

        return df

    def get_hitrate_mensual(self, year: int) -> pd.DataFrame:
        """
        Obtener Hit Rate y Eficiencia mensual para el año en curso

        Args:
            year: Año a analizar

        Returns:
            DataFrame con Hit Rate y Eficiencia por mes
        """
        query = f"""
        WITH per_cliente AS (
            SELECT
                mes_visita,
                codigo_cliente,
                MAX(CASE WHEN tipo_visita = 'Ventas' THEN 1 ELSE 0 END) AS tuvo_venta,
                MAX(CASE WHEN tipo_visita = 'Visita' THEN 1 ELSE 0 END) AS tuvo_visita,
                MAX(CASE WHEN tipo_visita = 'No Visita' THEN 1 ELSE 0 END) AS no_visita
            FROM {self.schema}.fact_eficiencia_hitrate
            WHERE anio_visita = {year}
            GROUP BY mes_visita, codigo_cliente
        )
        SELECT
            mes_visita,
            CASE mes_visita
                WHEN 1 THEN 'ENERO'
                WHEN 2 THEN 'FEBRERO'
                WHEN 3 THEN 'MARZO'
                WHEN 4 THEN 'ABRIL'
                WHEN 5 THEN 'MAYO'
                WHEN 6 THEN 'JUNIO'
                WHEN 7 THEN 'JULIO'
                WHEN 8 THEN 'AGOSTO'
                WHEN 9 THEN 'SEPTIEMBRE'
                WHEN 10 THEN 'OCTUBRE'
                WHEN 11 THEN 'NOVIEMBRE'
                WHEN 12 THEN 'DICIEMBRE'
            END AS mes,
            COUNT(*) AS clientes_totales,
            SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) AS clientes_contactados,
            SUM(tuvo_venta) AS clientes_con_venta,
            -- Eficiencia: % de clientes contactados sobre el total
            ROUND(
                100.0 * SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) /
                COUNT(*)
            , 2) AS eficiencia,
            -- Hit Rate: % de clientes con venta sobre contactados
            ROUND(
                100.0 * SUM(tuvo_venta) /
                NULLIF(SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END), 0)
            , 2) AS hit_rate
        FROM per_cliente
        GROUP BY mes_visita
        ORDER BY mes_visita
        """
        return self.execute_query(query)

    def get_hitrate_ytd(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener Hit Rate y Eficiencia YTD (Year to Date)

        Args:
            year: Año a analizar
            month: Mes hasta el cual calcular

        Returns:
            DataFrame con Hit Rate y Eficiencia YTD
        """
        query = f"""
        WITH per_cliente AS (
            SELECT
                codigo_cliente,
                MAX(CASE WHEN tipo_visita = 'Ventas' THEN 1 ELSE 0 END) AS tuvo_venta,
                MAX(CASE WHEN tipo_visita = 'Visita' THEN 1 ELSE 0 END) AS tuvo_visita,
                MAX(CASE WHEN tipo_visita = 'No Visita' THEN 1 ELSE 0 END) AS no_visita
            FROM {self.schema}.fact_eficiencia_hitrate
            WHERE anio_visita = {year}
                AND mes_visita <= {month}
            GROUP BY codigo_cliente
        )
        SELECT
            'YTD' as periodo,
            COUNT(*) AS clientes_totales,
            SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) AS clientes_contactados,
            SUM(tuvo_venta) AS clientes_con_venta,
            ROUND(
                100.0 * SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) /
                COUNT(*)
            , 2) AS eficiencia,
            ROUND(
                100.0 * SUM(tuvo_venta) /
                NULLIF(SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END), 0)
            , 2) AS hit_rate
        FROM per_cliente
        """
        return self.execute_query(query)

    def get_hitrate_por_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener Hit Rate y Eficiencia por ciudad para un mes específico

        Args:
            year: Año a analizar
            month: Mes a analizar

        Returns:
            DataFrame con Hit Rate y Eficiencia por ciudad
        """
        query = f"""
        WITH per_cliente_ciudad AS (
            SELECT
                ciudad_no_concrecion as ciudad,
                codigo_cliente,
                MAX(CASE WHEN tipo_visita = 'Ventas' THEN 1 ELSE 0 END) AS tuvo_venta,
                MAX(CASE WHEN tipo_visita = 'Visita' THEN 1 ELSE 0 END) AS tuvo_visita,
                MAX(CASE WHEN tipo_visita = 'No Visita' THEN 1 ELSE 0 END) AS no_visita
            FROM {self.schema}.fact_eficiencia_hitrate
            WHERE anio_visita = {year}
                AND mes_visita = {month}
            GROUP BY ciudad_no_concrecion, codigo_cliente
        )
        SELECT
            ciudad,
            COUNT(*) AS clientes_totales,
            SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) AS clientes_contactados,
            SUM(tuvo_venta) AS clientes_con_venta,
            ROUND(
                100.0 * SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) /
                COUNT(*)
            , 2) AS eficiencia,
            ROUND(
                100.0 * SUM(tuvo_venta) /
                NULLIF(SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END), 0)
            , 2) AS hit_rate
        FROM per_cliente_ciudad
        WHERE ciudad IS NOT NULL
        GROUP BY ciudad
        ORDER BY hit_rate DESC
        """
        return self.execute_query(query)

    def get_hitrate_historico_por_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener Hit Rate y Eficiencia histórico por ciudad (todos los meses del año)

        Args:
            year: Año a analizar
            month: Mes hasta el cual calcular

        Returns:
            DataFrame con Hit Rate y Eficiencia por ciudad y mes
        """
        query = f"""
        WITH per_cliente_ciudad AS (
            SELECT
                mes_visita,
                ciudad_no_concrecion as ciudad,
                codigo_cliente,
                MAX(CASE WHEN tipo_visita = 'Ventas' THEN 1 ELSE 0 END) AS tuvo_venta,
                MAX(CASE WHEN tipo_visita = 'Visita' THEN 1 ELSE 0 END) AS tuvo_visita,
                MAX(CASE WHEN tipo_visita = 'No Visita' THEN 1 ELSE 0 END) AS no_visita
            FROM {self.schema}.fact_eficiencia_hitrate
            WHERE anio_visita = {year}
                AND mes_visita <= {month}
            GROUP BY mes_visita, ciudad_no_concrecion, codigo_cliente
        )
        SELECT
            ciudad,
            mes_visita,
            COUNT(*) AS clientes_totales,
            SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) AS clientes_contactados,
            SUM(tuvo_venta) AS clientes_con_venta,
            ROUND(
                100.0 * SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END) /
                COUNT(*)
            , 2) AS eficiencia,
            ROUND(
                100.0 * SUM(tuvo_venta) /
                NULLIF(SUM(CASE WHEN tuvo_visita = 1 OR tuvo_venta = 1 THEN 1 ELSE 0 END), 0)
            , 2) AS hit_rate
        FROM per_cliente_ciudad
        WHERE ciudad IS NOT NULL
        GROUP BY ciudad, mes_visita
        ORDER BY ciudad, mes_visita
        """
        return self.execute_query(query)

    # === NUEVAS QUERIES PARA SUBFAMILIA ===

    def get_ventas_historicas_marca_subfamilia(self, year: int, month: int) -> pd.DataFrame:
        """Obtener ventas históricas por marca y subfamilia"""
        query = f"""
        SELECT
            marcadir,
            subfamilia,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as vendido_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as vendido_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir, subfamilia
        ORDER BY marcadir, SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_avance_actual_marca_subfamilia(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener avance actual por marca y subfamilia"""
        query = f"""
        SELECT
            marcadir,
            subfamilia,
            SUM(CAST(fin_01_ingreso AS NUMERIC)) as avance_{year}_bob,
            SUM(CAST(c9l AS NUMERIC)) as avance_{year}_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir, subfamilia
        ORDER BY marcadir, SUM(CAST(fin_01_ingreso AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_presupuesto_general_marca_subfamilia(self, year: int, month: int) -> pd.DataFrame:
        """Obtener presupuesto general por marca y subfamilia"""
        query = f"""
        SELECT
            marcadirectorio as marcadir,
            subfamilia,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as ppto_general_bob,
            SUM(CAST(c9l AS NUMERIC)) as ppto_general_c9l
        FROM {self.schema}.factpresupuesto_general
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadirectorio, subfamilia
        ORDER BY marcadirectorio, SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_sop_marca_subfamilia(self, year: int, month: int) -> pd.DataFrame:
        """Obtener SOP (presupuesto mensual) por marca y subfamilia"""
        query = f"""
        SELECT
            marcadirectorio as marcadir,
            subfamilia,
            SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_bob,
            SUM(CAST(c9l AS NUMERIC)) as sop_c9l
        FROM {self.schema}.factpresupuesto_mensual
        WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
            AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadirectorio, subfamilia
        ORDER BY marcadirectorio, SUM(CAST(ingreso_neto_sus AS NUMERIC)) DESC
        """
        return self.execute_query(query)

    def get_stock_marca_subfamilia(self) -> pd.DataFrame:
        """Obtener stock actual por marca y subfamilia"""
        query = f"""
        SELECT
            marcadirectorio as marcadir,
            subfamilia,
            SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) as stock_c9l
        FROM {self.schema}.td_stock_sap
        WHERE UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
            AND UPPER(ciudad) != 'TURISMO'
        GROUP BY marcadirectorio, subfamilia
        HAVING SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) > 0
        ORDER BY marcadirectorio, SUM(CAST(disponible AS NUMERIC) * CAST(volumen AS NUMERIC) / 9) DESC
        """
        return self.execute_query(query)

    def get_ventas_semanales_marca_subfamilia(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener ventas semanales por marca y subfamilia (SEMANAS CALENDARIO)"""
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            marcadir,
            subfamilia,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana1_c9l,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana2_c9l,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana3_c9l,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana4_c9l,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(c9l AS NUMERIC) ELSE 0 END) as semana5_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir, subfamilia
        ORDER BY marcadir, subfamilia
        """
        return self.execute_query(query)

    def get_proyecciones_semanales_por_ciudad(self, year: int, month: int) -> pd.DataFrame:
        """
        Obtener proyecciones semanales desglosadas por ciudad
        Excluye ciudades sin gerente (dinamico por ano) y Turismo
        - 2025 y antes: Excluye Oruro y Trinidad
        - 2026 en adelante: Solo excluye Trinidad (Oruro ya tiene gerente)
        """
        query = f"""
        SELECT
            ciudad,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
            END) as total_semana1,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
            END) as total_semana2,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
            END) as total_semana3,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
            END) as total_semana4,
            SUM(CASE
                WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * {self.tipo_cambio}
                ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
            END) as total_semana5
        FROM {self.schema}.fact_proyecciones
        WHERE anio_proyeccion = {year}
            AND mes_proyeccion = {month}
            AND UPPER(ciudad) NOT IN ('TURISMO', {self._get_ciudades_sin_gerente_sql(year)})
        GROUP BY ciudad
        ORDER BY ciudad
        """
        return self.execute_query(query)

    def get_ventas_semanales_por_ciudad_detalle(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener ventas semanales desglosadas por cada ciudad (SEMANAS CALENDARIO)"""
        weeks = self.get_calendar_week_ranges(year, month)
        s1_start, s1_end = weeks[0]
        s2_start, s2_end = weeks[1]
        s3_start, s3_end = weeks[2]
        s4_start, s4_end = weeks[3]
        s5_start, s5_end = weeks[4]

        query = f"""
        SELECT
            ciudad,
            SUM(CASE WHEN dia BETWEEN {s1_start} AND {s1_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana1_bob,
            SUM(CASE WHEN dia BETWEEN {s2_start} AND {s2_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana2_bob,
            SUM(CASE WHEN dia BETWEEN {s3_start} AND {s3_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana3_bob,
            SUM(CASE WHEN dia BETWEEN {s4_start} AND {s4_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana4_bob,
            SUM(CASE WHEN dia BETWEEN {s5_start} AND {s5_end} THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as semana5_bob
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY ciudad
        ORDER BY ciudad
        """
        return self.execute_query(query)

    def get_venta_promedio_diaria_marca_subfamilia(self, year: int, month: int, day: int) -> pd.DataFrame:
        """Obtener venta promedio diaria por marca y subfamilia para cálculo de cobertura"""
        query = f"""
        SELECT
            marcadir,
            subfamilia,
            COUNT(DISTINCT fecha) as dias_con_venta,
            SUM(CAST(c9l AS NUMERIC)) as total_c9l,
            SUM(CAST(c9l AS NUMERIC)) / NULLIF(COUNT(DISTINCT fecha), 0) as venta_promedio_diaria_c9l
        FROM {self.schema}.td_ventas_bob_historico
        WHERE anio = {year}
            AND mes = {month}
            AND dia <= {day}
            AND UPPER(ciudad) != 'TURISMO'
            AND UPPER(canal) != 'TURISMO'
            AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
        GROUP BY marcadir, subfamilia
        ORDER BY marcadir, total_c9l DESC
        """
        return self.execute_query(query)