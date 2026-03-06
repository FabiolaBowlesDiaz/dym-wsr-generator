"""
Test de validación de esquema contra el DWH real.
Ejecutar para confirmar que FactVentas tiene las columnas esperadas.

Uso:
    pytest proyeccion_objetiva/tests/test_validate_factventas.py -v
"""

import os
import sys
import pytest
import logging

# Agregar el directorio padre al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def db_manager():
    """Conexión real al DWH para tests de validación."""
    from core.database import DatabaseManager

    config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    schema = os.getenv('DB_SCHEMA', 'auto')

    dm = DatabaseManager(config, schema)
    if not dm.connect():
        pytest.skip("No se pudo conectar al DWH")

    yield dm
    dm.disconnect()


@pytest.fixture(scope="module")
def data_fetcher(db_manager):
    """Instancia de ProjectionDataFetcher."""
    from proyeccion_objetiva.data_fetcher import ProjectionDataFetcher
    return ProjectionDataFetcher(db_manager, db_manager.schema)


class TestFactVentasSchema:
    """Validar que FactVentas existe y tiene las columnas esperadas."""

    def test_schema_validation(self, data_fetcher):
        """Query 0: Descubrimiento de esquema."""
        result = data_fetcher.validate_factventas_schema()

        assert result['exists'], "FactVentas no existe en el schema"
        print(f"\nColumnas encontradas: {result['found_columns']}")
        print(f"Columnas faltantes: {result['missing_columns']}")

        if not result['all_expected_present']:
            logger.warning(
                f"Columnas faltantes: {result['missing_columns']}. "
                f"Se usará fallback con td_ventas_bob_historico."
            )


class TestCoberturaData:
    """Validar datos de cobertura."""

    def test_cobertura_returns_data(self, data_fetcher):
        """Query 1: Cobertura mensual tiene datos."""
        df = data_fetcher.get_cobertura_mensual(months_back=12)
        assert not df.empty, "No hay datos de cobertura"
        assert 'clientes_unicos' in df.columns
        print(f"\nCobertura: {len(df)} registros, "
              f"{df['clientes_unicos'].sum()} clientes únicos totales")

    def test_cobertura_has_required_columns(self, data_fetcher):
        """Verificar columnas mínimas."""
        df = data_fetcher.get_cobertura_mensual(months_back=3)
        required = {'anio', 'mes', 'clientes_unicos'}
        assert required.issubset(set(df.columns)), \
            f"Faltan columnas: {required - set(df.columns)}"


class TestDropSizeData:
    """Validar datos de drop size."""

    def test_dropsize_returns_data(self, data_fetcher):
        """Query 2: Drop size tiene datos."""
        df = data_fetcher.get_dropsize_mensual(months_back=12)
        assert not df.empty, "No hay datos de drop size"
        assert 'dropsize_bob' in df.columns
        print(f"\nDrop size: {len(df)} registros, "
              f"promedio BOB {df['dropsize_bob'].mean():,.0f}")

    def test_dropsize_positive(self, data_fetcher):
        """Drop size debe ser positivo."""
        df = data_fetcher.get_dropsize_mensual(months_back=6)
        if not df.empty:
            assert (df['dropsize_bob'] >= 0).all(), "Hay drop sizes negativos"


class TestHitRateData:
    """Validar datos de hit rate."""

    def test_hitrate_returns_data(self, data_fetcher):
        """Query 3: Hit rate histórico tiene datos."""
        df = data_fetcher.get_hitrate_mensual_historico(months_back=12)
        assert not df.empty, "No hay datos de hit rate"
        assert 'hit_rate' in df.columns
        print(f"\nHit rate: {len(df)} registros, ciudades: {df['ciudad'].nunique()}")

    def test_hitrate_reasonable_range(self, data_fetcher):
        """Hit rate debe estar entre 0 y 100."""
        df = data_fetcher.get_hitrate_mensual_historico(months_back=6)
        if not df.empty:
            assert (df['hit_rate'] >= 0).all(), "Hit rate negativos"
            assert (df['hit_rate'] <= 100).all(), "Hit rate > 100%"


class TestVentasHistoricas:
    """Validar datos de ventas históricas."""

    def test_ventas_returns_data(self, data_fetcher):
        """Query 4: Ventas históricas tienen datos."""
        df = data_fetcher.get_ventas_mensuales_historicas(months_back=24)
        assert not df.empty, "No hay ventas históricas"
        print(f"\nVentas históricas: {len(df)} registros, "
              f"marcas: {df['marcadir'].nunique()}, "
              f"ciudades: {df['ciudad'].nunique()}, "
              f"meses: {df.groupby(['anio','mes']).ngroups}")

    def test_ventas_sufficient_depth(self, data_fetcher):
        """Debe haber al menos 12 meses de datos para Holt-Winters."""
        df = data_fetcher.get_ventas_mensuales_historicas(months_back=36)
        if not df.empty:
            n_months = df.groupby(['anio', 'mes']).ngroups
            assert n_months >= 12, \
                f"Solo hay {n_months} meses de datos (mín: 12 para Double Exp)"
            print(f"\nProfundidad: {n_months} meses disponibles")


class TestFetchAll:
    """Test integrado del fetch completo."""

    def test_fetch_all_returns_all_keys(self, data_fetcher):
        """fetch_all() debe retornar todas las claves esperadas."""
        data = data_fetcher.fetch_all(
            months_back_components=6,
            months_back_historico=12
        )
        expected_keys = {'cobertura', 'dropsize', 'hitrate',
                         'ventas_historicas', 'schema_validation'}
        assert expected_keys.issubset(set(data.keys())), \
            f"Faltan claves: {expected_keys - set(data.keys())}"
