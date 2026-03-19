"""
Drivers Engine - Revenue Tree Decomposition
Venta = Cobertura x Hit Rate x Drop Size

Fuente: fact_ventas_detallado (DWH)
Calcula los 3 drivers operativos a 4 niveles:
  1. Por marca (nacional)
  2. Por marca + submarca (drilldown)
  3. Por ciudad
  4. Por ciudad + marca (drilldown)

Definiciones (Option A - Frecuencia):
  Cobertura = COUNT(DISTINCT cod_cliente)          -- clientes unicos que compraron
  Hit Rate  = COUNT(DISTINCT cuf_factura) / Cob    -- pedidos por cliente (frecuencia)
  Drop Size = SUM(ingreso_neto_bob) / pedidos      -- BOB por pedido (ticket)
  Check: Cob x HR x DS = Venta total (exacto)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TABLE_VENTAS_DETALLADO = "fact_ventas_detallado"

EXCLUDED_BRANDS = ("NINGUNA", "SIN MARCA ASIGNADA")
EXCLUDED_CITIES = ("TURISMO",)
EXCLUDED_CHANNELS = ("TURISMO",)

# Mapeo de nombres inconsistentes en canal_on_of
CHANNEL_NAME_FIXES = {
    "E-COMERCE": "E-COMMERCE",
}


class DriversEngine:
    """
    Motor de Drivers Operativos basado en fact_ventas_detallado.
    Calcula Cobertura, Hit Rate y Drop Size a multiples niveles
    y computa tendencias YoY para diagnostico.
    """

    def __init__(self, db_manager, schema: str = 'auto', current_date=None):
        self.db = db_manager
        self.schema = schema
        if current_date is None:
            from datetime import datetime
            current_date = datetime.now()
        self.current_date = current_date

    def _build_query(self, group_cols: List[str]) -> str:
        """Construye query base para fact_ventas_detallado agrupado por las columnas indicadas."""
        excluded_brands_sql = ", ".join(f"'{b}'" for b in EXCLUDED_BRANDS)
        excluded_cities_sql = ", ".join(f"'{c}'" for c in EXCLUDED_CITIES)

        group_sql = ", ".join(group_cols)

        return f"""
        SELECT
            {group_sql},
            EXTRACT(YEAR FROM fecha)::INT AS anio,
            EXTRACT(MONTH FROM fecha)::INT AS mes,
            COUNT(DISTINCT cod_cliente) AS cobertura,
            COUNT(DISTINCT cuf_factura) AS pedidos,
            ROUND(
                COUNT(DISTINCT cuf_factura)::NUMERIC /
                NULLIF(COUNT(DISTINCT cod_cliente), 0), 2
            ) AS hit_rate,
            ROUND(
                SUM(ingreso_neto_bob) /
                NULLIF(COUNT(DISTINCT cuf_factura), 0), 2
            ) AS drop_size,
            SUM(ingreso_neto_bob) AS venta_total
        FROM {self.schema}.{TABLE_VENTAS_DETALLADO}
        WHERE UPPER(marca) NOT IN ({excluded_brands_sql})
          AND UPPER(ciudad) NOT IN ({excluded_cities_sql})
        GROUP BY {group_sql}, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha)
        ORDER BY {group_sql}, anio, mes
        """

    def _fetch_monthly(self, group_cols: List[str]) -> pd.DataFrame:
        """Ejecuta la query y retorna datos mensuales."""
        query = self._build_query(group_cols)
        try:
            df = self.db.execute_query(query)
            if df.empty:
                logger.warning(f"[Drivers] Sin datos de fact_ventas_detallado para {group_cols}")
            else:
                logger.info(f"[Drivers] {len(df)} registros mensuales para {group_cols}")
            return df
        except Exception as e:
            logger.error(f"[Drivers] Error consultando fact_ventas_detallado: {e}")
            return pd.DataFrame()

    # ==================================================================
    # STD (Same-to-Date): mes actual al dia N vs mismos dias AA
    # ==================================================================

    def _build_std_query(self, group_cols: List[str], start_date: str, end_date: str) -> str:
        """Query para un rango de fechas especifico (sin agrupacion mensual)."""
        excluded_brands_sql = ", ".join(f"'{b}'" for b in EXCLUDED_BRANDS)
        excluded_cities_sql = ", ".join(f"'{c}'" for c in EXCLUDED_CITIES)
        group_sql = ", ".join(group_cols)

        return f"""
        SELECT
            {group_sql},
            COUNT(DISTINCT cod_cliente) AS cobertura,
            COUNT(DISTINCT cuf_factura) AS pedidos,
            ROUND(
                COUNT(DISTINCT cuf_factura)::NUMERIC /
                NULLIF(COUNT(DISTINCT cod_cliente), 0), 2
            ) AS hit_rate,
            ROUND(
                SUM(ingreso_neto_bob) /
                NULLIF(COUNT(DISTINCT cuf_factura), 0), 2
            ) AS drop_size,
            SUM(ingreso_neto_bob) AS venta_total
        FROM {self.schema}.{TABLE_VENTAS_DETALLADO}
        WHERE UPPER(marca) NOT IN ({excluded_brands_sql})
          AND UPPER(ciudad) NOT IN ({excluded_cities_sql})
          AND fecha >= '{start_date}'
          AND fecha <= '{end_date}'
        GROUP BY {group_sql}
        ORDER BY {group_sql}
        """

    def _fetch_std_period(self, group_cols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Ejecuta query STD para un rango de fechas."""
        query = self._build_std_query(group_cols, start_date, end_date)
        try:
            df = self.db.execute_query(query)
            logger.info(f"[Drivers STD] {len(df)} registros para {start_date} a {end_date}")
            return df
        except Exception as e:
            logger.error(f"[Drivers STD] Error: {e}")
            return pd.DataFrame()

    def _compute_std(self, group_cols: List[str]) -> pd.DataFrame:
        """
        Same-to-Date: mes actual (al dia N) vs mismos N dias del año anterior.
        Si el mes actual no tiene datos, cae a fallback (ultimo mes completo YoY).

        Returns:
            DataFrame con: group_cols + cobertura, hit_rate, drop_size,
                           cobertura_trend, hitrate_trend, dropsize_trend,
                           venta_total, sufficient_data, ref_mes, ref_anio,
                           ref_dia (None en fallback), is_std (bool)
        """
        cd = self.current_date

        # Periodo actual: dia 1 al dia actual del mes
        current_start = f"{cd.year}-{cd.month:02d}-01"
        current_end = f"{cd.year}-{cd.month:02d}-{cd.day:02d}"

        # Mismo periodo año anterior
        yoy_start = f"{cd.year - 1}-{cd.month:02d}-01"
        yoy_end = f"{cd.year - 1}-{cd.month:02d}-{cd.day:02d}"

        logger.info(f"[Drivers STD] Periodo actual: {current_start} a {current_end}")
        logger.info(f"[Drivers STD] Periodo YoY:    {yoy_start} a {yoy_end}")

        df_current = self._fetch_std_period(group_cols, current_start, current_end)

        if df_current.empty:
            logger.info("[Drivers STD] Sin datos del mes actual, usando fallback YoY mensual")
            monthly = self._fetch_monthly(group_cols)
            return self._compute_yoy_fallback(monthly, group_cols)

        df_yoy = self._fetch_std_period(group_cols, yoy_start, yoy_end)

        # Merge current + YoY por las columnas clave
        if not df_yoy.empty:
            merged = df_current.merge(df_yoy, on=group_cols, how='left', suffixes=('', '_yoy'))
        else:
            merged = df_current.copy()

        results = []
        for _, row in merged.iterrows():
            key_values = {col: row[col] for col in group_cols}

            cob = float(row['cobertura'])
            hr = float(row['hit_rate'])
            ds = float(row['drop_size'])
            venta = float(row['venta_total'])

            cob_trend = hr_trend = ds_trend = None
            has_yoy = 'cobertura_yoy' in row.index and pd.notna(row.get('cobertura_yoy'))

            if has_yoy:
                cob_yoy = float(row['cobertura_yoy'])
                hr_yoy = float(row['hit_rate_yoy'])
                ds_yoy = float(row['drop_size_yoy'])
                if cob_yoy > 0:
                    cob_trend = (cob / cob_yoy) - 1
                if hr_yoy > 0:
                    hr_trend = (hr / hr_yoy) - 1
                if ds_yoy > 0:
                    ds_trend = (ds / ds_yoy) - 1

            result_row = {**key_values}
            result_row.update({
                'cobertura': round(cob),
                'hit_rate': round(hr, 2),
                'drop_size': round(ds, 2),
                'cobertura_trend': round(cob_trend, 4) if cob_trend is not None else None,
                'hitrate_trend': round(hr_trend, 4) if hr_trend is not None else None,
                'dropsize_trend': round(ds_trend, 4) if ds_trend is not None else None,
                'venta_total': round(venta, 2),
                'sufficient_data': has_yoy,
                'ref_mes': cd.month,
                'ref_anio': cd.year,
                'ref_dia': cd.day,
                'is_std': True,
            })
            results.append(result_row)

        result_df = pd.DataFrame(results)
        if not result_df.empty and 'venta_total' in result_df.columns:
            result_df = result_df.sort_values('venta_total', ascending=False)

        return result_df

    # ==================================================================
    # Fallback: ultimo mes completo vs mismo mes año anterior
    # ==================================================================

    def _compute_yoy_fallback(self, monthly_df: pd.DataFrame, key_cols: List[str]) -> pd.DataFrame:
        """
        Fallback cuando el mes actual no tiene datos en fact_ventas_detallado.
        Usa el ultimo mes completo y lo compara YoY.
        """
        if monthly_df.empty:
            return pd.DataFrame()

        monthly_df = monthly_df.copy()
        monthly_df['periodo'] = monthly_df['anio'] * 100 + monthly_df['mes']

        # Excluir mes actual (datos parciales)
        current_periodo = self.current_date.year * 100 + self.current_date.month
        monthly_df = monthly_df[monthly_df['periodo'] < current_periodo]

        if monthly_df.empty:
            return pd.DataFrame()

        results = []

        for keys, group in monthly_df.groupby(key_cols):
            if isinstance(keys, str):
                keys = (keys,)

            group = group.sort_values('periodo')
            if len(group) == 0:
                continue

            row = dict(zip(key_cols, keys))

            last = group.iloc[-1]
            ref_mes = int(last['mes'])
            ref_anio = int(last['anio'])

            cob_current = float(last['cobertura'])
            hr_current = float(last['hit_rate'])
            ds_current = float(last['drop_size'])
            venta_current = float(last['venta_total'])

            yoy_periodo = (ref_anio - 1) * 100 + ref_mes
            yoy_row = group[group['periodo'] == yoy_periodo]

            cob_trend = hr_trend = ds_trend = None
            has_yoy = False

            if not yoy_row.empty:
                has_yoy = True
                yoy = yoy_row.iloc[0]
                if yoy['cobertura'] > 0:
                    cob_trend = (cob_current / float(yoy['cobertura'])) - 1
                if yoy['hit_rate'] > 0:
                    hr_trend = (hr_current / float(yoy['hit_rate'])) - 1
                if yoy['drop_size'] > 0:
                    ds_trend = (ds_current / float(yoy['drop_size'])) - 1

            row.update({
                'cobertura': round(cob_current),
                'hit_rate': round(hr_current, 2),
                'drop_size': round(ds_current, 2),
                'cobertura_trend': round(cob_trend, 4) if cob_trend is not None else None,
                'hitrate_trend': round(hr_trend, 4) if hr_trend is not None else None,
                'dropsize_trend': round(ds_trend, 4) if ds_trend is not None else None,
                'venta_total': round(venta_current, 2),
                'sufficient_data': has_yoy,
                'ref_mes': ref_mes,
                'ref_anio': ref_anio,
                'ref_dia': None,
                'is_std': False,
            })
            results.append(row)

        result_df = pd.DataFrame(results)
        if not result_df.empty and 'venta_total' in result_df.columns:
            result_df = result_df.sort_values('venta_total', ascending=False)

        return result_df

    # ------------------------------------------------------------------
    # Niveles de calculo (ahora usan STD con fallback automatico)
    # ------------------------------------------------------------------
    def calculate_by_marca(self) -> pd.DataFrame:
        """Calcula drivers a nivel marca nacional."""
        return self._compute_std(['marca'])

    def calculate_by_marca_submarca(self) -> pd.DataFrame:
        """Calcula drivers a nivel marca + submarca."""
        return self._compute_std(['marca', 'submarca'])

    def calculate_by_ciudad(self) -> pd.DataFrame:
        """Calcula drivers a nivel ciudad."""
        return self._compute_std(['ciudad'])

    def calculate_by_ciudad_marca(self) -> pd.DataFrame:
        """Calcula drivers a nivel ciudad + marca."""
        return self._compute_std(['ciudad', 'marca'])

    def calculate_by_canal(self) -> pd.DataFrame:
        """Calcula drivers a nivel canal (canal_on_of)."""
        df = self._compute_std(['canal_on_of'])
        return self._normalize_canal_df(df)

    def calculate_by_canal_subcanal(self) -> pd.DataFrame:
        """Calcula drivers a nivel canal + subcanal."""
        df = self._compute_std(['canal_on_of', 'subcanal'])
        return self._normalize_canal_df(df)

    def _normalize_canal_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza nombres de canal: renombra columna y corrige typos."""
        if df.empty:
            return df
        df = df.copy()
        if 'canal_on_of' in df.columns:
            # Corregir nombres inconsistentes
            df['canal_on_of'] = df['canal_on_of'].replace(CHANNEL_NAME_FIXES)
            # Renombrar a 'canal' para consistencia con el WSR
            df = df.rename(columns={'canal_on_of': 'canal'})
        # Excluir canales no deseados
        if 'canal' in df.columns:
            df = df[~df['canal'].str.upper().isin(EXCLUDED_CHANNELS)]
        return df

    # ------------------------------------------------------------------
    # Metodo maestro: calcula todos los niveles
    # ------------------------------------------------------------------
    def calculate_all(self) -> Dict[str, pd.DataFrame]:
        """
        Ejecuta el calculo de drivers en los 6 niveles.

        Returns:
            Dict con claves:
              - 'by_marca': DataFrame con drivers por marca
              - 'by_marca_submarca': DataFrame con drivers por marca+submarca
              - 'by_ciudad': DataFrame con drivers por ciudad
              - 'by_ciudad_marca': DataFrame con drivers por ciudad+marca
              - 'by_canal': DataFrame con drivers por canal
              - 'by_canal_subcanal': DataFrame con drivers por canal+subcanal
        """
        logger.info("[Drivers] Calculando drivers operativos...")

        by_marca = self.calculate_by_marca()
        by_marca_sub = self.calculate_by_marca_submarca()
        by_ciudad = self.calculate_by_ciudad()
        by_ciudad_marca = self.calculate_by_ciudad_marca()
        by_canal = self.calculate_by_canal()
        by_canal_sub = self.calculate_by_canal_subcanal()

        total_marcas = len(by_marca) if not by_marca.empty else 0
        total_ciudades = len(by_ciudad) if not by_ciudad.empty else 0
        total_canales = len(by_canal) if not by_canal.empty else 0
        logger.info(
            f"[Drivers] Completado: {total_marcas} marcas, {total_ciudades} ciudades, {total_canales} canales"
        )

        return {
            'by_marca': by_marca,
            'by_marca_submarca': by_marca_sub,
            'by_ciudad': by_ciudad,
            'by_ciudad_marca': by_ciudad_marca,
            'by_canal': by_canal,
            'by_canal_subcanal': by_canal_sub,
        }

    @staticmethod
    def diagnose_trend(cob_trend, hr_trend, ds_trend, threshold=0.02) -> str:
        """
        Genera diagnostico automatico basado en las tendencias.

        Args:
            cob_trend: tendencia de cobertura (decimal, ej: -0.08)
            hr_trend: tendencia de hit rate (decimal)
            ds_trend: tendencia de drop size (decimal)
            threshold: umbral para considerar "estable" (default +-2%)

        Returns:
            String con diagnostico
        """
        if any(t is None for t in [cob_trend, hr_trend, ds_trend]):
            return "Datos insuficientes"

        cob_down = cob_trend < -threshold
        hr_down = hr_trend < -threshold
        ds_down = ds_trend < -threshold

        if cob_down and not hr_down and not ds_down:
            return "Problema de ruta/cobertura"
        elif not cob_down and hr_down and not ds_down:
            return "Problema de conversion/selling"
        elif not cob_down and not hr_down and ds_down:
            return "Problema de mix/precio"
        elif cob_down and hr_down and ds_down:
            return "Problema sistemico"
        elif cob_down and hr_down:
            return "Problema de cobertura + conversion"
        elif cob_down and ds_down:
            return "Problema de cobertura + mix"
        elif hr_down and ds_down:
            return "Problema de conversion + mix"
        else:
            return "Estable"
