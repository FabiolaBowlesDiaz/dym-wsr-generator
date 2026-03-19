"""
Tests de integración para el ProjectionProcessor (orquestador).
Incluye test de sanidad y test de resiliencia.

Uso:
    pytest proyeccion_objetiva/tests/test_projection_processor.py -v
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestProjectionProcessorUnit:
    """Tests unitarios con mocks (no requieren DWH)."""

    def _mock_data_fetcher(self):
        """Crea datos mock que simulan lo que retornaría el DWH."""
        rows_ventas = []
        rows_cob = []
        rows_ds = []
        rows_hr = []
        rows_subfam = []
        rows_canal = []

        for marca in ['BRANCA', 'HAVANA', 'CASA REAL']:
            for ciudad in ['SANTA CRUZ', 'LA PAZ', 'COCHABAMBA']:
                for year in [2024, 2025]:
                    for month in range(1, 13):
                        base_venta = 500000 + np.random.normal(0, 20000)
                        n_clientes = 250 + np.random.randint(-30, 30)

                        rows_ventas.append({
                            'marcadir': marca, 'ciudad': ciudad,
                            'anio': year, 'mes': month,
                            'venta_bob': base_venta,
                            'venta_c9l': base_venta / 200
                        })
                        rows_cob.append({
                            'marcadir': marca, 'ciudad': ciudad,
                            'anio': year, 'mes': month,
                            'clientes_unicos': n_clientes
                        })
                        rows_ds.append({
                            'marcadir': marca, 'ciudad': ciudad,
                            'anio': year, 'mes': month,
                            'total_venta': base_venta,
                            'total_c9l': base_venta / 200,
                            'clientes': n_clientes,
                            'dropsize_bob': base_venta / n_clientes,
                            'dropsize_c9l': (base_venta / 200) / n_clientes
                        })
                        rows_subfam.append({
                            'marcadir': marca, 'subfamilia': f'{marca}_SUB1',
                            'anio': year, 'mes': month,
                            'venta_bob': base_venta * 0.6,
                            'venta_c9l': (base_venta * 0.6) / 200
                        })
                        rows_subfam.append({
                            'marcadir': marca, 'subfamilia': f'{marca}_SUB2',
                            'anio': year, 'mes': month,
                            'venta_bob': base_venta * 0.4,
                            'venta_c9l': (base_venta * 0.4) / 200
                        })

                        if marca == 'BRANCA':  # HR solo por ciudad, evitar duplicados
                            rows_hr.append({
                                'ciudad': ciudad,
                                'anio': year, 'mes': month,
                                'clientes_totales': 500,
                                'clientes_contactados': 380,
                                'clientes_con_venta': 260,
                                'eficiencia': 76.0,
                                'hit_rate': 68.4 + np.random.uniform(-2, 2)
                            })

        # Canal data (aggregate across marcas/ciudades)
        for canal in ['TRADICIONAL', 'MODERNO']:
            for year in [2024, 2025]:
                for month in range(1, 13):
                    rows_canal.append({
                        'canal': canal,
                        'anio': year, 'mes': month,
                        'venta_bob': 2000000 + np.random.normal(0, 50000),
                        'venta_c9l': 10000 + np.random.normal(0, 250)
                    })

        return {
            'ventas_historicas': pd.DataFrame(rows_ventas),
            'cobertura': pd.DataFrame(rows_cob),
            'dropsize': pd.DataFrame(rows_ds),
            'hitrate': pd.DataFrame(rows_hr),
            'ventas_historicas_subfamilia': pd.DataFrame(rows_subfam),
            'ventas_historicas_canal': pd.DataFrame(rows_canal),
            'schema_validation': {'exists': True, 'all_expected_present': True}
        }

    def test_build_comparativo_spread(self):
        """Spread se calcula correctamente."""
        from proyeccion_objetiva.projection_processor import ProjectionProcessor

        # Mock db_manager
        mock_db = MagicMock()
        processor = ProjectionProcessor(mock_db, datetime(2026, 2, 22))

        py_est = pd.DataFrame({
            'marcadir': ['BRANCA', 'HAVANA'],
            'py_estadistica_bob': [1000000, 800000],
            'model_type': ['triple', 'double'],
            'confidence': ['high', 'medium']
        })

        py_op = pd.DataFrame({
            'marcadir': ['BRANCA', 'HAVANA'],
            'py_operativa_bob': [950000, 850000]
        })

        py_ger = pd.DataFrame({
            'marcadir': ['BRANCA', 'HAVANA'],
            'py_2026_bob': [1100000, 750000]  # BRANCA +10%, HAVANA -6.25%
        })

        result = processor._build_comparativo(
            py_gerente=py_ger,
            py_estadistica=py_est,
            py_operativa=py_op,
            key_col='marcadir',
            py_col='py_2026_bob'
        )

        assert 'spread' in result.columns
        assert 'diagnostico' in result.columns

        branca = result[result['marcadir'] == 'BRANCA'].iloc[0]
        # Spread = (1.1M / 1.0M) - 1 = 0.10
        assert abs(float(branca['spread']) - 0.10) < 0.01

    def test_diagnose_spread_categories(self):
        """Diagnóstico correcto según umbrales de spread."""
        from proyeccion_objetiva.projection_processor import ProjectionProcessor

        mock_db = MagicMock()
        processor = ProjectionProcessor(mock_db, datetime(2026, 2, 22))

        assert 'optimista' in processor._diagnose_spread(0.15).lower()
        assert 'conservador' in processor._diagnose_spread(-0.12).lower()
        assert 'consenso' in processor._diagnose_spread(0.03).lower()
        assert 'divergencia' in processor._diagnose_spread(0.07).lower()
        assert 'sin datos' in processor._diagnose_spread(None).lower()

    def test_full_pipeline_with_mock(self):
        """Pipeline completo con datos mock."""
        from proyeccion_objetiva.projection_processor import ProjectionProcessor

        mock_db = MagicMock()
        processor = ProjectionProcessor(mock_db, datetime(2026, 2, 22))

        # Mock data_fetcher.fetch_all
        mock_data = self._mock_data_fetcher()
        processor.data_fetcher.fetch_all = MagicMock(return_value=mock_data)

        # Mock PY Gerente
        py_ger_marca = pd.DataFrame({
            'marcadir': ['BRANCA', 'HAVANA', 'CASA REAL'],
            'py_2026_bob': [1500000, 1200000, 900000]
        })

        result = processor.generate_projections(
            py_gerente_marca=py_ger_marca
        )

        assert 'by_marca' in result
        assert 'by_ciudad' in result
        assert 'decomposition_ciudad' in result
        assert 'resumen_nacional' in result
        assert 'est_by_subfamilia' in result
        assert 'est_by_canal' in result
        assert 'est_by_ciudad_marca' in result

        # Verificar que hay datos
        assert not result['by_marca'].empty
        assert not result['by_ciudad'].empty
        assert not result['est_by_subfamilia'].empty
        assert not result['est_by_canal'].empty
        assert not result['est_by_ciudad_marca'].empty


class TestSanityChecks:
    """Tests de sanidad: proyecciones dentro de rangos razonables."""

    def test_projections_positive(self):
        """Todas las proyecciones deben ser >= 0."""
        from proyeccion_objetiva.projection_processor import ProjectionProcessor

        mock_db = MagicMock()
        processor = ProjectionProcessor(mock_db, datetime(2026, 2, 22))

        # Crear datos sintéticos simples
        np.random.seed(42)
        rows = []
        for marca in ['A', 'B']:
            for ciudad in ['X', 'Y']:
                for y in [2024, 2025]:
                    for m in range(1, 13):
                        rows.append({
                            'marcadir': marca, 'ciudad': ciudad,
                            'anio': y, 'mes': m,
                            'venta_bob': 100000 + np.random.normal(0, 5000),
                            'venta_c9l': 500
                        })

        ventas_df = pd.DataFrame(rows)

        from proyeccion_objetiva.pilar2_estadistica.statistical_engine import StatisticalEngine
        engine = StatisticalEngine()
        result = engine.run_by_marca(ventas_df)

        for _, row in result.iterrows():
            if row['py_estadistica_bob'] is not None:
                assert row['py_estadistica_bob'] >= 0, \
                    f"Proyección negativa para {row['marcadir']}"


class TestResiliencia:
    """Tests de resiliencia: el WSR debe funcionar aunque el módulo falle."""

    def test_empty_data_handled(self):
        """DriversEngine diagnose_trend con estable retorna Estable."""
        from proyeccion_objetiva.pilar3_operativa.drivers_engine import DriversEngine

        result = DriversEngine.diagnose_trend(0.01, 0.01, 0.01)
        assert result == "Estable"

    def test_diagnose_trend_handles_none(self):
        """DriversEngine.diagnose_trend con None retorna datos insuficientes."""
        from proyeccion_objetiva.pilar3_operativa.drivers_engine import DriversEngine

        result = DriversEngine.diagnose_trend(None, 0.01, -0.05)
        assert result == "Datos insuficientes"

        result2 = DriversEngine.diagnose_trend(-0.05, 0.01, 0.0)
        assert result2 == "Problema de ruta/cobertura"

    def test_html_generator_with_empty_data(self):
        """HTML generator con datos vacíos no causa excepciones."""
        from proyeccion_objetiva.visualizacion.projection_html_generator import ProjectionHTMLGenerator

        gen = ProjectionHTMLGenerator()
        html = gen.generate_full_section({
            'by_marca': pd.DataFrame(),
            'by_ciudad': pd.DataFrame(),
            'decomposition_ciudad': pd.DataFrame(),
            'decomposition_marca': pd.DataFrame(),
            'resumen_nacional': {}
        })
        assert isinstance(html, str)
