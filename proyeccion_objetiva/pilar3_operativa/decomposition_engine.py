"""
Motor de Descomposición Operativa (Revenue Tree)
Proyecta ventas como: Venta = Cobertura × Hit Rate × Drop Size

Cada componente se proyecta independientemente usando un promedio
móvil ponderado (WMA) con ajuste estacional.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple

from .. import config as cfg

logger = logging.getLogger(__name__)


class RevenueTreeEngine:
    """
    Proyecta ventas descomponiendo en tres factores operativos:
    Cobertura (clientes), Hit Rate (conversión), Drop Size (venta/cliente).
    """

    def project_component(self, series: pd.Series, method: str = 'wma') -> Dict:
        """
        Proyecta un componente individual hacia adelante un mes.

        Args:
            series: Serie temporal mensual del componente (indexada por periodo)
            method: Método de proyección ('wma' = Weighted Moving Average)

        Returns:
            Dict con:
              - 'projected': valor proyectado
              - 'trend_pct': tendencia % vs promedio de 3 meses anteriores
              - 'seasonal_factor': factor estacional aplicado
              - 'method': método usado
              - 'sufficient_data': bool
        """
        if series is None or len(series) < 3:
            return {
                'projected': None,
                'trend_pct': None,
                'seasonal_factor': None,
                'method': method,
                'sufficient_data': False
            }

        # Últimos 3 valores para WMA
        # series.iloc[-3:] retorna en orden cronológico [antiguo, medio, reciente]
        # WMA_WEIGHTS está en orden [reciente, medio, antiguo], así que lo invertimos
        recent = series.iloc[-3:].values
        weights = np.array(cfg.WMA_WEIGHTS[::-1])  # invertir: [antiguo, medio, reciente]
        wma = np.average(recent, weights=weights)

        # Factor estacional: ratio vs mismo-mes-año-anterior
        seasonal_factor = 1.0
        if len(series) >= 13:
            same_month_last_year = series.iloc[-12]
            if same_month_last_year > 0 and not np.isnan(same_month_last_year):
                # Comparar el último valor real vs el de hace 12 meses
                current_val = series.iloc[-1]
                seasonal_factor = current_val / same_month_last_year
                # Amortiguar el factor estacional para no sobreajustar
                seasonal_factor = 0.7 + 0.3 * seasonal_factor
                # Limitar entre 0.5 y 2.0
                seasonal_factor = max(0.5, min(2.0, seasonal_factor))

        projected = wma * seasonal_factor

        # Tendencia: % cambio del último valor vs promedio de 3 meses anteriores
        avg_3m = series.iloc[-3:].mean()
        prev_avg = series.iloc[-6:-3].mean() if len(series) >= 6 else avg_3m
        trend_pct = ((avg_3m / prev_avg) - 1) * 100 if prev_avg > 0 else 0.0

        return {
            'projected': max(0, projected),
            'trend_pct': round(trend_pct, 1),
            'seasonal_factor': round(seasonal_factor, 3),
            'method': method,
            'sufficient_data': True
        }

    def calculate_projection(
        self,
        cob_series: pd.Series,
        hr_series: pd.Series,
        ds_series: pd.Series
    ) -> Dict:
        """
        Calcula proyección operativa para una combinación marca/ciudad.

        PY_Operativa = Cobertura_proj × HitRate_proj × DropSize_proj

        Args:
            cob_series: Serie mensual de cobertura (clientes únicos)
            hr_series: Serie mensual de hit rate (% como decimal, ej: 0.72)
            ds_series: Serie mensual de drop size (BOB por cliente)

        Returns:
            Dict con componentes individuales y resultado final
        """
        cob_proj = self.project_component(cob_series)
        hr_proj = self.project_component(hr_series)
        ds_proj = self.project_component(ds_series)

        # Calcular proyección compuesta
        py_operativa = None
        if (cob_proj['sufficient_data'] and
                hr_proj['sufficient_data'] and
                ds_proj['sufficient_data']):

            cob_val = cob_proj['projected']
            hr_val = hr_proj['projected'] / 100.0  # HR viene en %
            ds_val = ds_proj['projected']

            py_operativa = cob_val * hr_val * ds_val

        return {
            'cobertura': cob_proj,
            'hit_rate': hr_proj,
            'drop_size': ds_proj,
            'py_operativa_bob': py_operativa,
            'sufficient_data': py_operativa is not None
        }

    def run_by_ciudad(
        self,
        cobertura_df: pd.DataFrame,
        hitrate_df: pd.DataFrame,
        dropsize_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Ejecuta proyección operativa para todas las ciudades.

        Args:
            cobertura_df: DataFrame con columnas (ciudad, anio, mes, clientes_unicos)
            hitrate_df: DataFrame con columnas (ciudad, anio, mes, hit_rate)
            dropsize_df: DataFrame con columnas (ciudad, anio, mes, dropsize_bob)

        Returns:
            DataFrame con proyecciones por ciudad
        """
        results = []

        # Protección: DataFrames vacíos
        if cobertura_df.empty or hitrate_df.empty or dropsize_df.empty:
            return pd.DataFrame(results)

        # Agregar cobertura y dropsize a nivel ciudad
        cob_ciudad = (cobertura_df
                      .groupby(['ciudad', 'anio', 'mes'])['clientes_unicos']
                      .sum()
                      .reset_index())

        ds_ciudad = (dropsize_df
                     .groupby(['ciudad', 'anio', 'mes'])
                     .agg({'total_venta': 'sum', 'clientes': 'sum'})
                     .reset_index())
        ds_ciudad['dropsize_bob'] = np.where(
            ds_ciudad['clientes'] > 0,
            ds_ciudad['total_venta'] / ds_ciudad['clientes'],
            0
        )

        ciudades = sorted(set(cob_ciudad['ciudad'].unique()) &
                          set(hitrate_df['ciudad'].unique()))

        for ciudad in ciudades:
            try:
                # Extraer series temporales
                cob_s = self._extract_series(
                    cob_ciudad[cob_ciudad['ciudad'] == ciudad],
                    'clientes_unicos'
                )
                hr_s = self._extract_series(
                    hitrate_df[hitrate_df['ciudad'] == ciudad],
                    'hit_rate'
                )
                ds_s = self._extract_series(
                    ds_ciudad[ds_ciudad['ciudad'] == ciudad],
                    'dropsize_bob'
                )

                projection = self.calculate_projection(cob_s, hr_s, ds_s)

                results.append({
                    'ciudad': ciudad,
                    'py_operativa_bob': projection['py_operativa_bob'],
                    'cobertura_proj': projection['cobertura']['projected'],
                    'cobertura_trend': projection['cobertura']['trend_pct'],
                    'hitrate_proj': projection['hit_rate']['projected'],
                    'hitrate_trend': projection['hit_rate']['trend_pct'],
                    'dropsize_proj': projection['drop_size']['projected'],
                    'dropsize_trend': projection['drop_size']['trend_pct'],
                    'sufficient_data': projection['sufficient_data']
                })

            except Exception as e:
                logger.warning(f"Error proyectando ciudad {ciudad}: {e}")
                results.append({
                    'ciudad': ciudad,
                    'py_operativa_bob': None,
                    'sufficient_data': False
                })

        return pd.DataFrame(results)

    def run_by_marca(
        self,
        cobertura_df: pd.DataFrame,
        hitrate_df: pd.DataFrame,
        dropsize_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Ejecuta proyección operativa para todas las marcas.

        Nota: Hit Rate no tiene marca en la fuente, así que se usa
        el HR de la ciudad correspondiente como proxy.
        Para marca a nivel nacional, se usa el HR nacional promedio.

        Args:
            cobertura_df: DataFrame con (marcadir, ciudad, anio, mes, clientes_unicos)
            hitrate_df: DataFrame con (ciudad, anio, mes, hit_rate)
            dropsize_df: DataFrame con (marcadir, ciudad, anio, mes, dropsize_bob)

        Returns:
            DataFrame con proyecciones por marca
        """
        results = []

        # Protección: DataFrames vacíos
        if cobertura_df.empty or hitrate_df.empty or dropsize_df.empty:
            return pd.DataFrame(results)

        # Agregar a nivel marca (todas las ciudades)
        cob_marca = (cobertura_df
                     .groupby(['marcadir', 'anio', 'mes'])['clientes_unicos']
                     .sum()
                     .reset_index())

        ds_marca = (dropsize_df
                    .groupby(['marcadir', 'anio', 'mes'])
                    .agg({'total_venta': 'sum', 'clientes': 'sum'})
                    .reset_index())
        ds_marca['dropsize_bob'] = np.where(
            ds_marca['clientes'] > 0,
            ds_marca['total_venta'] / ds_marca['clientes'],
            0
        )

        # Hit rate nacional (promedio ponderado de todas las ciudades)
        hr_nacional = (hitrate_df
                       .groupby(['anio', 'mes'])
                       .agg({
                           'clientes_con_venta': 'sum',
                           'clientes_contactados': 'sum'
                       })
                       .reset_index())
        hr_nacional['hit_rate'] = np.where(
            hr_nacional['clientes_contactados'] > 0,
            100.0 * hr_nacional['clientes_con_venta'] / hr_nacional['clientes_contactados'],
            0
        )

        marcas = sorted(cob_marca['marcadir'].unique())

        for marca in marcas:
            try:
                cob_s = self._extract_series(
                    cob_marca[cob_marca['marcadir'] == marca],
                    'clientes_unicos'
                )
                # Usar HR nacional como proxy (no hay HR por marca)
                hr_s = self._extract_series(hr_nacional, 'hit_rate')
                ds_s = self._extract_series(
                    ds_marca[ds_marca['marcadir'] == marca],
                    'dropsize_bob'
                )

                projection = self.calculate_projection(cob_s, hr_s, ds_s)

                results.append({
                    'marcadir': marca,
                    'py_operativa_bob': projection['py_operativa_bob'],
                    'cobertura_proj': projection['cobertura']['projected'],
                    'cobertura_trend': projection['cobertura']['trend_pct'],
                    'hitrate_proj': projection['hit_rate']['projected'],
                    'hitrate_trend': projection['hit_rate']['trend_pct'],
                    'dropsize_proj': projection['drop_size']['projected'],
                    'dropsize_trend': projection['drop_size']['trend_pct'],
                    'sufficient_data': projection['sufficient_data']
                })

            except Exception as e:
                logger.warning(f"Error proyectando marca {marca}: {e}")
                results.append({
                    'marcadir': marca,
                    'py_operativa_bob': None,
                    'sufficient_data': False
                })

        return pd.DataFrame(results)

    def _extract_series(self, df: pd.DataFrame, value_col: str) -> pd.Series:
        """
        Convierte un DataFrame con columnas (anio, mes, value_col)
        en una Serie indexada cronológicamente.
        """
        if df.empty:
            return pd.Series(dtype=float)

        temp = df.copy()
        temp = temp.sort_values(['anio', 'mes'])
        temp['period'] = temp['anio'] * 100 + temp['mes']
        series = temp.set_index('period')[value_col]
        return series
