"""
Motor Estadístico Holt-Winters para Proyección Objetiva
Adaptación standalone de la lógica de TripleExpModel del proyecto
FORECAST-DM de Marcelo (dym-forecast-marcelo/).

Extrae solo la lógica core (~150 líneas) sin las dependencias pesadas
del FORECAST-DM (Docker, Poetry, DataControlCenter, Features, Frame).

Incluye ajuste post-forecast por eventos móviles (Carnaval, Semana Santa)
usando el calendario de utils/business_days.py.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple

from .. import config as cfg

logger = logging.getLogger(__name__)

# Importar calendario de eventos (protegido)
try:
    from .event_calendar import EventCalendar
    EVENT_CALENDAR_AVAILABLE = True
except ImportError:
    EVENT_CALENDAR_AVAILABLE = False
    logger.debug("EventCalendar no disponible, sin ajuste por eventos")

# Intentar importar statsmodels (dependencia nueva)
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning(
        "statsmodels no está instalado. El motor estadístico no estará disponible. "
        "Instalar con: pip install statsmodels>=0.14.0"
    )


class StatisticalEngine:
    """
    Forecast estadístico usando Holt-Winters (Triple Exponential Smoothing).

    Lógica adaptada de:
    - replace_low_outliers_rolling() → _clean_outliers()
    - TripleExpModel.train() + predict() → forecast_single_series()
    - exp_smoothing_predict_groups() → run_all_groups()

    Incluye ajuste post-forecast por eventos móviles cuando el calendario
    está disponible (Carnaval, Semana Santa cambian de mes entre años).
    """

    def __init__(self, target_year: int = None, target_month: int = None):
        """
        Args:
            target_year: Año de la proyección (ej: 2026). Si None, no aplica ajuste.
            target_month: Mes de la proyección (ej: 2). Si None, no aplica ajuste.
        """
        self.target_year = target_year
        self.target_month = target_month

        # Inicializar calendario de eventos
        self._event_calendar = None
        self._event_adjustment = None

        if target_year and target_month and EVENT_CALENDAR_AVAILABLE:
            try:
                self._event_calendar = EventCalendar()
                if self._event_calendar.available:
                    self._event_adjustment = \
                        self._event_calendar.calculate_event_adjustment(
                            target_year, target_month
                        )
                    if self._event_adjustment['adjustment_factor'] != 1.0:
                        logger.info(
                            f"Ajuste por eventos para {target_year}-{target_month:02d}: "
                            f"factor={self._event_adjustment['adjustment_factor']}, "
                            f"{self._event_adjustment['explanation']}"
                        )
            except Exception as e:
                logger.warning(f"Error inicializando calendario de eventos: {e}")

    def _apply_event_adjustment(self, forecast_value: float) -> Tuple[float, Optional[Dict]]:
        """
        Aplica ajuste post-forecast por eventos móviles.

        Args:
            forecast_value: Valor del forecast de Holt-Winters

        Returns:
            Tupla (forecast_ajustado, dict_info_ajuste o None)
        """
        if (self._event_adjustment is None or
                self._event_adjustment['adjustment_factor'] == 1.0):
            return forecast_value, None

        factor = self._event_adjustment['adjustment_factor']
        adjusted = forecast_value * factor

        return adjusted, {
            'factor': factor,
            'original_forecast': forecast_value,
            'explanation': self._event_adjustment['explanation'],
            'events_new': self._event_adjustment['events_new'],
            'events_gone': self._event_adjustment['events_gone'],
        }

    def _clean_outliers(self, series: pd.Series) -> pd.Series:
        """
        Limpia outliers bajos en una serie temporal usando rolling mean.

        Adaptado de replace_low_outliers_rolling() en triple.py líneas 90-147.
        Solo corrige outliers BAJOS (caídas anómalas), no picos altos.

        Args:
            series: Serie temporal mensual

        Returns:
            Serie con outliers bajos reemplazados por rolling mean
        """
        s = series.copy()

        window = cfg.OUTLIER_WINDOW
        z_thresh = cfg.OUTLIER_Z_THRESH

        # Rolling center (media móvil centrada)
        roll_center = s.rolling(window=window, center=True, min_periods=1).mean()

        # Rolling std para variabilidad local
        roll_std = s.rolling(window=window, center=True, min_periods=2).std()

        # Fallback: si std es 0 o NaN, usar std global
        global_std = s.std()
        roll_std = roll_std.replace(0, np.nan).fillna(
            global_std if global_std > 0 else 1.0
        )

        # Z-score relativo al rolling center
        z = (s - roll_center) / roll_std

        # Condición de outlier bajo (una cola)
        # Nota: con window=5, el max |z| de un solo punto es (n-1)/√n ≈ 1.79
        # Para series cortas, usamos un umbral adaptativo más permisivo
        effective_z_thresh = min(z_thresh, (window - 1) / np.sqrt(window) * 0.95)
        cond_z = z < -effective_z_thresh
        cond_ratio = s < (roll_center * 0.4)  # min_ratio = 0.4

        low_outlier = cond_z & cond_ratio

        # Reemplazar solo outliers bajos
        s[low_outlier] = roll_center[low_outlier]

        n_replaced = low_outlier.sum()
        if n_replaced > 0:
            logger.debug(f"Outliers bajos reemplazados: {n_replaced}")

        return s

    def forecast_single_series(
        self,
        monthly_series: pd.Series,
        horizon: int = 1
    ) -> Dict:
        """
        Genera forecast para una serie temporal mensual.

        Lógica adaptada de TripleExpModel.train() + predict() en triple.py.
        - N ≥ 25: Triple Exp (Holt-Winters con estacionalidad aditiva, tendencia amortiguada)
        - 12 ≤ N < 25: Double Exp (tendencia sin estacionalidad)
        - N < 12 o >70% ceros: None ("datos insuficientes")

        Args:
            monthly_series: Serie con índice DatetimeIndex (frecuencia mensual)
            horizon: Meses a proyectar hacia adelante

        Returns:
            Dict con:
              - 'forecast': valor(es) proyectado(s)
              - 'model_type': 'triple', 'double', o None
              - 'n_months': longitud de la serie
              - 'confidence': 'high', 'medium', 'low'
        """
        if not STATSMODELS_AVAILABLE:
            return {
                'forecast': None,
                'model_type': None,
                'n_months': 0,
                'confidence': None,
                'error': 'statsmodels no instalado'
            }

        n = len(monthly_series)

        # Verificar datos suficientes
        if n < cfg.MIN_MONTHS_MINIMUM:
            return {
                'forecast': None,
                'model_type': None,
                'n_months': n,
                'confidence': None,
                'error': f'Solo {n} meses (mín: {cfg.MIN_MONTHS_MINIMUM})'
            }

        # Verificar exceso de ceros
        zero_pct = (monthly_series <= 0).sum() / n
        if zero_pct > cfg.ZERO_THRESHOLD:
            return {
                'forecast': None,
                'model_type': None,
                'n_months': n,
                'confidence': None,
                'error': f'{zero_pct:.0%} ceros (umbral: {cfg.ZERO_THRESHOLD:.0%})'
            }

        # Limpiar outliers (adaptado de triple.py línea 266)
        y = self._clean_outliers(monthly_series)

        # Epsilon shift para evitar problemas con ceros (triple.py línea 267)
        epsilon = 1e-6
        y = y + epsilon

        # Asegurar frecuencia mensual
        if not hasattr(y.index, 'freq') or y.index.freq is None:
            y = y.asfreq('MS')

        try:
            if n >= cfg.MIN_MONTHS_TRIPLE:
                # Triple Exponential: tendencia + estacionalidad
                model = ExponentialSmoothing(
                    y,
                    trend='add',
                    seasonal='add',
                    seasonal_periods=cfg.SEASONAL_PERIOD,
                    damped_trend=True
                ).fit(optimized=True)
                model_type = 'triple'
                confidence = 'high'

            else:
                # Double Exponential: solo tendencia, sin estacionalidad
                model = ExponentialSmoothing(
                    y,
                    trend='add',
                    seasonal=None,
                    damped_trend=True
                ).fit(optimized=True)
                model_type = 'double'
                confidence = 'medium'

            # Forecast (adaptado de triple.py líneas 356-358)
            preds = model.forecast(horizon)
            forecast_values = preds.clip(lower=0).values

            raw_forecast = forecast_values[0] if horizon == 1 else forecast_values

            # Aplicar ajuste por eventos móviles (post-forecast)
            event_info = None
            if isinstance(raw_forecast, (int, float)):
                adjusted_forecast, event_info = self._apply_event_adjustment(raw_forecast)
            else:
                adjusted_forecast = raw_forecast

            return {
                'forecast': adjusted_forecast,
                'forecast_raw': raw_forecast,  # Sin ajuste por eventos
                'model_type': model_type,
                'n_months': n,
                'confidence': confidence,
                'event_adjustment': event_info,
                'error': None
            }

        except Exception as e:
            logger.warning(f"Error en Holt-Winters (n={n}): {e}")
            return {
                'forecast': None,
                'model_type': None,
                'n_months': n,
                'confidence': None,
                'error': str(e)
            }

    def run_by_marca(self, ventas_df: pd.DataFrame, value_col: str = 'venta_bob') -> pd.DataFrame:
        """
        Ejecuta forecast estadístico para todas las marcas.

        Adaptado del patrón de exp_smoothing_predict_groups() en helper_functions.py.

        Args:
            ventas_df: DataFrame con (marcadir, ciudad, anio, mes, venta_bob/venta_c9l)
            value_col: Columna de valor a proyectar (default: 'venta_bob')

        Returns:
            DataFrame con (marcadir, py_estadistica_{suffix}, model_type, confidence, n_months)
        """
        suffix = value_col.replace('venta_', '')  # 'bob' o 'c9l'
        py_col = f'py_estadistica_{suffix}'

        # Agregar a nivel marca (sumar todas las ciudades)
        marca_mensual = (ventas_df
                         .groupby(['marcadir', 'anio', 'mes'])[value_col]
                         .sum()
                         .reset_index())

        marcas = sorted(marca_mensual['marcadir'].unique())
        results = []

        for marca in marcas:
            marca_data = marca_mensual[marca_mensual['marcadir'] == marca].copy()
            series = self._df_to_monthly_series(marca_data, value_col)

            if series is None:
                results.append({
                    'marcadir': marca,
                    py_col: None,
                    'model_type': None,
                    'confidence': None,
                    'n_months': 0
                })
                continue

            result = self.forecast_single_series(series)
            row = {
                'marcadir': marca,
                py_col: result['forecast'],
                'model_type': result['model_type'],
                'confidence': result['confidence'],
                'n_months': result['n_months']
            }
            # Agregar info de ajuste por eventos si existe
            if result.get('event_adjustment'):
                row['event_adjustment'] = result['event_adjustment']['explanation']
                row['event_factor'] = result['event_adjustment']['factor']
                row[f'{py_col}_raw'] = result.get('forecast_raw')
            results.append(row)

        return pd.DataFrame(results)

    def run_by_ciudad(self, ventas_df: pd.DataFrame, value_col: str = 'venta_bob') -> pd.DataFrame:
        """
        Ejecuta forecast estadístico para todas las ciudades.

        Args:
            ventas_df: DataFrame con (marcadir, ciudad, anio, mes, venta_bob/venta_c9l)
            value_col: Columna de valor a proyectar (default: 'venta_bob')

        Returns:
            DataFrame con (ciudad, py_estadistica_{suffix}, model_type, confidence, n_months)
        """
        suffix = value_col.replace('venta_', '')
        py_col = f'py_estadistica_{suffix}'

        # Agregar a nivel ciudad (sumar todas las marcas)
        ciudad_mensual = (ventas_df
                          .groupby(['ciudad', 'anio', 'mes'])[value_col]
                          .sum()
                          .reset_index())

        ciudades = sorted(ciudad_mensual['ciudad'].unique())
        results = []

        for ciudad in ciudades:
            ciudad_data = ciudad_mensual[ciudad_mensual['ciudad'] == ciudad].copy()
            series = self._df_to_monthly_series(ciudad_data, value_col)

            if series is None:
                results.append({
                    'ciudad': ciudad,
                    py_col: None,
                    'model_type': None,
                    'confidence': None,
                    'n_months': 0
                })
                continue

            result = self.forecast_single_series(series)
            row = {
                'ciudad': ciudad,
                py_col: result['forecast'],
                'model_type': result['model_type'],
                'confidence': result['confidence'],
                'n_months': result['n_months']
            }
            # Agregar info de ajuste por eventos si existe
            if result.get('event_adjustment'):
                row['event_adjustment'] = result['event_adjustment']['explanation']
                row['event_factor'] = result['event_adjustment']['factor']
                row[f'{py_col}_raw'] = result.get('forecast_raw')
            results.append(row)

        return pd.DataFrame(results)

    def run_by_subfamilia(self, ventas_subfam_df: pd.DataFrame, value_col: str = 'venta_bob') -> pd.DataFrame:
        """
        Ejecuta forecast estadístico para cada par (marca, subfamilia).

        Args:
            ventas_subfam_df: DataFrame con (marcadir, subfamilia, anio, mes, venta_bob/venta_c9l)
            value_col: Columna de valor a proyectar (default: 'venta_bob')

        Returns:
            DataFrame con (marcadir, subfamilia, py_estadistica_{suffix}, model_type, confidence, n_months)
        """
        suffix = value_col.replace('venta_', '')
        py_col = f'py_estadistica_{suffix}'

        if ventas_subfam_df.empty:
            return pd.DataFrame(columns=['marcadir', 'subfamilia', py_col,
                                         'model_type', 'confidence', 'n_months'])

        # Aggregate to ensure one row per (marcadir, subfamilia, anio, mes)
        agg_df = (ventas_subfam_df
                  .groupby(['marcadir', 'subfamilia', 'anio', 'mes'])[value_col]
                  .sum()
                  .reset_index())

        results = []
        groups = agg_df.groupby(['marcadir', 'subfamilia'])

        for (marca, subfam), group_data in groups:
            series = self._df_to_monthly_series(group_data, value_col)

            if series is None:
                results.append({
                    'marcadir': marca,
                    'subfamilia': subfam,
                    py_col: None,
                    'model_type': None,
                    'confidence': None,
                    'n_months': 0
                })
                continue

            result = self.forecast_single_series(series)
            row = {
                'marcadir': marca,
                'subfamilia': subfam,
                py_col: result['forecast'],
                'model_type': result['model_type'],
                'confidence': result['confidence'],
                'n_months': result['n_months']
            }
            if result.get('event_adjustment'):
                row['event_adjustment'] = result['event_adjustment']['explanation']
                row['event_factor'] = result['event_adjustment']['factor']
                row[f'{py_col}_raw'] = result.get('forecast_raw')
            results.append(row)

        return pd.DataFrame(results)

    def run_by_canal(self, ventas_canal_df: pd.DataFrame, value_col: str = 'venta_bob') -> pd.DataFrame:
        """
        Ejecuta forecast estadístico para cada canal.

        Args:
            ventas_canal_df: DataFrame con (canal, anio, mes, venta_bob/venta_c9l)
            value_col: Columna de valor a proyectar (default: 'venta_bob')

        Returns:
            DataFrame con (canal, py_estadistica_{suffix}, model_type, confidence, n_months)
        """
        suffix = value_col.replace('venta_', '')
        py_col = f'py_estadistica_{suffix}'

        if ventas_canal_df.empty:
            return pd.DataFrame(columns=['canal', py_col,
                                         'model_type', 'confidence', 'n_months'])

        results = []
        canales = sorted(ventas_canal_df['canal'].unique())

        for canal in canales:
            canal_data = ventas_canal_df[ventas_canal_df['canal'] == canal].copy()
            series = self._df_to_monthly_series(canal_data, value_col)

            if series is None:
                results.append({
                    'canal': canal,
                    py_col: None,
                    'model_type': None,
                    'confidence': None,
                    'n_months': 0
                })
                continue

            result = self.forecast_single_series(series)
            row = {
                'canal': canal,
                py_col: result['forecast'],
                'model_type': result['model_type'],
                'confidence': result['confidence'],
                'n_months': result['n_months']
            }
            if result.get('event_adjustment'):
                row['event_adjustment'] = result['event_adjustment']['explanation']
                row['event_factor'] = result['event_adjustment']['factor']
                row[f'{py_col}_raw'] = result.get('forecast_raw')
            results.append(row)

        return pd.DataFrame(results)

    def run_by_ciudad_marca(self, ventas_df: pd.DataFrame, value_col: str = 'venta_bob') -> pd.DataFrame:
        """
        Ejecuta forecast estadístico para cada par (ciudad, marca).
        Usa los datos de Query 4 que ya vienen a nivel marcadir × ciudad.

        Args:
            ventas_df: DataFrame con (marcadir, ciudad, anio, mes, venta_bob/venta_c9l)
            value_col: Columna de valor a proyectar (default: 'venta_bob')

        Returns:
            DataFrame con (ciudad, marcadir, py_estadistica_{suffix}, model_type, confidence, n_months)
        """
        suffix = value_col.replace('venta_', '')
        py_col = f'py_estadistica_{suffix}'

        if ventas_df.empty:
            return pd.DataFrame(columns=['ciudad', 'marcadir', py_col,
                                         'model_type', 'confidence', 'n_months'])

        results = []
        groups = ventas_df.groupby(['ciudad', 'marcadir'])

        for (ciudad, marca), group_data in groups:
            series = self._df_to_monthly_series(group_data, value_col)

            if series is None:
                results.append({
                    'ciudad': ciudad,
                    'marcadir': marca,
                    py_col: None,
                    'model_type': None,
                    'confidence': None,
                    'n_months': 0
                })
                continue

            result = self.forecast_single_series(series)
            row = {
                'ciudad': ciudad,
                'marcadir': marca,
                py_col: result['forecast'],
                'model_type': result['model_type'],
                'confidence': result['confidence'],
                'n_months': result['n_months']
            }
            if result.get('event_adjustment'):
                row['event_adjustment'] = result['event_adjustment']['explanation']
                row['event_factor'] = result['event_adjustment']['factor']
                row[f'{py_col}_raw'] = result.get('forecast_raw')
            results.append(row)

        return pd.DataFrame(results)

    def _df_to_monthly_series(
        self, df: pd.DataFrame, value_col: str
    ) -> Optional[pd.Series]:
        """
        Convierte DataFrame con (anio, mes, value_col) en Serie con DatetimeIndex
        mensual, que es lo que statsmodels necesita.
        """
        if df.empty:
            return None

        temp = df.copy()
        temp['date'] = pd.to_datetime(
            temp['anio'].astype(str) + '-' + temp['mes'].astype(str).str.zfill(2) + '-01'
        )
        temp = temp.sort_values('date')
        series = temp.set_index('date')[value_col]
        series = series.asfreq('MS')

        # Excluir mes actual (incompleto) — HW necesita solo meses cerrados
        if self.target_year and self.target_month:
            cutoff = pd.Timestamp(f'{self.target_year}-{self.target_month:02d}-01')
            series = series[series.index < cutoff]

        # Detectar gaps en la serie (meses faltantes en el DWH)
        n_gaps = series.isna().sum()
        if n_gaps > 0:
            gap_months = series[series.isna()].index.strftime('%Y-%m').tolist()
            logger.warning(
                f"DWH: {n_gaps} mes(es) sin datos: {gap_months}. "
                f"Se rellenan con 0 — esto puede desestabilizar el forecast. "
                f"Verificar carga de datos en td_ventas_bob_historico."
            )

        # Rellenar meses faltantes con 0
        series = series.fillna(0)

        return series
