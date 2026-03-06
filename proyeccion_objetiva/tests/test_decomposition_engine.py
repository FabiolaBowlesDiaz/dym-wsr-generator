"""
Tests unitarios para el motor de descomposición operativa (Revenue Tree).

Uso:
    pytest proyeccion_objetiva/tests/test_decomposition_engine.py -v
"""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def engine():
    from proyeccion_objetiva.pilar3_operativa.decomposition_engine import RevenueTreeEngine
    return RevenueTreeEngine()


def _make_period_series(values, start_ym=202401):
    """Helper: crea Serie indexada por periodo YYYYMM."""
    periods = []
    year = start_ym // 100
    month = start_ym % 100
    for _ in range(len(values)):
        periods.append(year * 100 + month)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return pd.Series(values, index=periods, dtype=float)


class TestProjectComponent:
    """Tests para project_component (WMA + estacionalidad)."""

    def test_insufficient_data(self, engine):
        """Menos de 3 datos retorna insufficient."""
        series = _make_period_series([10, 20])
        result = engine.project_component(series)
        assert result['sufficient_data'] is False
        assert result['projected'] is None

    def test_basic_wma(self, engine):
        """WMA con 3 valores, sin estacionalidad (< 13 meses)."""
        # Últimos 3: [100, 110, 120], pesos [0.2, 0.3, 0.5]
        values = [80, 90, 100, 110, 120]
        series = _make_period_series(values)
        result = engine.project_component(series)

        assert result['sufficient_data'] is True
        # WMA = 120*0.5 + 110*0.3 + 100*0.2 = 60 + 33 + 20 = 113
        # Sin estacionalidad (< 13 meses), factor = 1.0
        assert abs(result['projected'] - 113.0) < 1.0
        assert result['seasonal_factor'] == 1.0

    def test_trend_calculation(self, engine):
        """Tendencia positiva cuando últimos 3 meses > anteriores 3."""
        values = [50, 55, 60, 80, 85, 90]
        series = _make_period_series(values)
        result = engine.project_component(series)

        assert result['trend_pct'] > 0, "Tendencia debería ser positiva"

    def test_trend_negative(self, engine):
        """Tendencia negativa cuando últimos 3 meses < anteriores 3."""
        values = [90, 85, 80, 60, 55, 50]
        series = _make_period_series(values)
        result = engine.project_component(series)

        assert result['trend_pct'] < 0, "Tendencia debería ser negativa"

    def test_with_seasonal_factor(self, engine):
        """Con 13+ datos, debe aplicar factor estacional."""
        values = [100] * 12 + [120]  # 13 meses, último sube a 120
        series = _make_period_series(values)
        result = engine.project_component(series)

        assert result['sufficient_data'] is True
        # seasonal_factor = 0.7 + 0.3 * (120/100) = 0.7 + 0.36 = 1.06
        assert 1.0 < result['seasonal_factor'] < 1.5

    def test_projected_never_negative(self, engine):
        """Proyección nunca debe ser negativa."""
        values = [10, 5, 2, 1, 0.5]
        series = _make_period_series(values)
        result = engine.project_component(series)

        if result['sufficient_data']:
            assert result['projected'] >= 0


class TestCalculateProjection:
    """Tests para calculate_projection (Cob × HR × DS)."""

    def test_full_calculation(self, engine):
        """Multiplicación correcta de los tres componentes."""
        cob = _make_period_series([400, 420, 450])  # clientes
        hr = _make_period_series([70, 72, 75])       # % hit rate
        ds = _make_period_series([2800, 2900, 3000])  # BOB drop size

        result = engine.calculate_projection(cob, hr, ds)

        assert result['sufficient_data'] is True
        assert result['py_operativa_bob'] is not None
        # Debería ser aprox: 450*0.75*3000 = ~1,012,500 (ajustado por WMA)
        assert result['py_operativa_bob'] > 500000

    def test_missing_component_returns_none(self, engine):
        """Si falta un componente, py_operativa es None."""
        cob = _make_period_series([400, 420, 450])
        hr = _make_period_series([70])  # Insuficiente
        ds = _make_period_series([2800, 2900, 3000])

        result = engine.calculate_projection(cob, hr, ds)
        assert result['sufficient_data'] is False


class TestRunByGroups:
    """Tests para run_by_ciudad y run_by_marca."""

    def _make_test_data(self):
        """Genera DataFrames de prueba para cobertura, hitrate, dropsize."""
        rows_cob = []
        rows_ds = []
        rows_hr = []

        for ciudad in ['SCZ', 'LPZ']:
            for year in [2024, 2025]:
                for month in range(1, 13):
                    rows_cob.append({
                        'marcadir': 'MARCA_A', 'ciudad': ciudad,
                        'anio': year, 'mes': month,
                        'clientes_unicos': 300 + np.random.randint(-20, 20)
                    })
                    rows_ds.append({
                        'marcadir': 'MARCA_A', 'ciudad': ciudad,
                        'anio': year, 'mes': month,
                        'total_venta': 900000 + np.random.randint(-50000, 50000),
                        'total_c9l': 5000,
                        'clientes': 300,
                        'dropsize_bob': 3000 + np.random.randint(-200, 200),
                        'dropsize_c9l': 16.7
                    })
                    rows_hr.append({
                        'ciudad': ciudad,
                        'anio': year, 'mes': month,
                        'clientes_totales': 500,
                        'clientes_contactados': 400,
                        'clientes_con_venta': 280,
                        'eficiencia': 80.0,
                        'hit_rate': 70.0 + np.random.uniform(-3, 3)
                    })

        return (pd.DataFrame(rows_cob),
                pd.DataFrame(rows_hr),
                pd.DataFrame(rows_ds))

    def test_run_by_ciudad(self, engine):
        """Proyección por ciudad retorna resultados para cada ciudad."""
        cob, hr, ds = self._make_test_data()
        result = engine.run_by_ciudad(cob, hr, ds)

        assert isinstance(result, pd.DataFrame)
        assert 'ciudad' in result.columns
        assert 'py_operativa_bob' in result.columns
        assert len(result) == 2  # SCZ y LPZ

    def test_run_by_marca(self, engine):
        """Proyección por marca retorna resultados."""
        cob, hr, ds = self._make_test_data()
        result = engine.run_by_marca(cob, hr, ds)

        assert isinstance(result, pd.DataFrame)
        assert 'marcadir' in result.columns
        assert len(result) >= 1
