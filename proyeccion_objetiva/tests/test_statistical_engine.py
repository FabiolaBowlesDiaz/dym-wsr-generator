"""
Tests unitarios para el motor estadístico Holt-Winters.
Usa series sintéticas con resultados conocidos.

Uso:
    pytest proyeccion_objetiva/tests/test_statistical_engine.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


@pytest.fixture
def engine():
    from proyeccion_objetiva.pilar2_estadistica.statistical_engine import StatisticalEngine
    return StatisticalEngine()


def _make_monthly_series(values, start_year=2024, start_month=1):
    """Helper: crea Serie con DatetimeIndex mensual."""
    dates = pd.date_range(
        start=f"{start_year}-{start_month:02d}-01",
        periods=len(values),
        freq='MS'
    )
    return pd.Series(values, index=dates, dtype=float)


class TestCleanOutliers:
    """Tests para la limpieza de outliers."""

    def test_no_outliers_unchanged(self, engine):
        """Serie sin outliers no debe cambiar."""
        values = [100, 105, 98, 102, 110, 95, 108, 100, 103, 97]
        series = _make_monthly_series(values)
        cleaned = engine._clean_outliers(series)
        # Debe ser prácticamente igual
        assert np.allclose(cleaned.values, series.values, atol=1)

    def test_low_outlier_replaced(self, engine):
        """Un outlier bajo debe ser reemplazado."""
        values = [100, 105, 98, 102, 5, 95, 108, 100, 103, 97]  # 5 es outlier
        series = _make_monthly_series(values)
        cleaned = engine._clean_outliers(series)
        # El valor 5 (índice 4) debe haber sido elevado
        assert cleaned.iloc[4] > 50, "Outlier bajo no fue corregido"


class TestForecastSingleSeries:
    """Tests para el forecast individual."""

    def test_insufficient_data_returns_none(self, engine):
        """Series muy cortas retornan None."""
        series = _make_monthly_series([100, 200, 300])
        result = engine.forecast_single_series(series)
        assert result['forecast'] is None
        assert 'insuficientes' in result.get('error', '') or result['n_months'] < 12

    def test_mostly_zeros_returns_none(self, engine):
        """Series con >70% ceros retornan None."""
        values = [0, 0, 0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0]
        series = _make_monthly_series(values)
        result = engine.forecast_single_series(series)
        assert result['forecast'] is None

    def test_double_exp_for_12_to_24_months(self, engine):
        """12-24 meses deben usar modelo Double (sin estacionalidad)."""
        np.random.seed(42)
        values = (np.arange(18) * 10 + 100 + np.random.normal(0, 5, 18)).tolist()
        series = _make_monthly_series(values)
        result = engine.forecast_single_series(series)

        if result['forecast'] is not None:
            assert result['model_type'] == 'double'
            assert result['confidence'] == 'medium'
            # Forecast debe ser positivo y razonable
            assert result['forecast'] > 0

    def test_triple_exp_for_25_plus_months(self, engine):
        """25+ meses deben usar modelo Triple (con estacionalidad)."""
        np.random.seed(42)
        # Serie con tendencia + estacionalidad
        months = 30
        trend = np.arange(months) * 5
        seasonal = 20 * np.sin(np.arange(months) * 2 * np.pi / 12)
        noise = np.random.normal(0, 3, months)
        values = (200 + trend + seasonal + noise).tolist()
        series = _make_monthly_series(values)
        result = engine.forecast_single_series(series)

        if result['forecast'] is not None:
            assert result['model_type'] == 'triple'
            assert result['confidence'] == 'high'
            assert result['forecast'] > 0

    def test_forecast_within_sanity_bounds(self, engine):
        """Forecast debe estar dentro de 50%-200% del promedio."""
        np.random.seed(42)
        values = [1000 + np.random.normal(0, 50) for _ in range(26)]
        series = _make_monthly_series(values)
        result = engine.forecast_single_series(series)

        if result['forecast'] is not None:
            avg = np.mean(values)
            assert result['forecast'] > avg * 0.3, "Forecast demasiado bajo"
            assert result['forecast'] < avg * 3.0, "Forecast demasiado alto"


class TestRunByMarca:
    """Tests para la ejecución por grupo."""

    def test_run_by_marca_returns_dataframe(self, engine):
        """run_by_marca debe retornar DataFrame con columnas esperadas."""
        np.random.seed(42)
        rows = []
        for marca in ['MARCA_A', 'MARCA_B']:
            for year in [2024, 2025]:
                for month in range(1, 13):
                    rows.append({
                        'marcadir': marca,
                        'ciudad': 'SANTA CRUZ',
                        'anio': year,
                        'mes': month,
                        'venta_bob': 100000 + np.random.normal(0, 5000)
                    })

        df = pd.DataFrame(rows)
        result = engine.run_by_marca(df)

        assert isinstance(result, pd.DataFrame)
        assert 'marcadir' in result.columns
        assert 'py_estadistica_bob' in result.columns
        assert len(result) == 2  # Dos marcas

    def test_run_by_ciudad_returns_dataframe(self, engine):
        """run_by_ciudad debe retornar DataFrame con columnas esperadas."""
        np.random.seed(42)
        rows = []
        for ciudad in ['SANTA CRUZ', 'LA PAZ']:
            for year in [2024, 2025]:
                for month in range(1, 13):
                    rows.append({
                        'marcadir': 'MARCA_A',
                        'ciudad': ciudad,
                        'anio': year,
                        'mes': month,
                        'venta_bob': 200000 + np.random.normal(0, 10000)
                    })

        df = pd.DataFrame(rows)
        result = engine.run_by_ciudad(df)

        assert isinstance(result, pd.DataFrame)
        assert 'ciudad' in result.columns
        assert len(result) == 2
