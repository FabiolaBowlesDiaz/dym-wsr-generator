"""
Script de prueba para verificar la implementación de Hit Rate
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos propios
from core.database import DatabaseManager
from core.data_processor import DataProcessor

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_hitrate_queries():
    """Probar las consultas de Hit Rate"""

    # Configuración de base de datos
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    schema = os.getenv('DB_SCHEMA', 'auto')

    # Inicializar componentes
    db_manager = DatabaseManager(db_config, schema)
    current_date = datetime.now()
    data_processor = DataProcessor(current_date)

    try:
        # Conectar a la base de datos
        logger.info("🔗 Conectando a la base de datos...")
        if not db_manager.connect():
            logger.error("❌ No se pudo conectar a la base de datos")
            return False

        logger.info("✅ Conexión exitosa")

        # Probar cada query de Hit Rate
        logger.info("\n📊 Probando queries de Hit Rate...")

        # 1. Hit Rate mensual
        logger.info("\n1. Hit Rate mensual...")
        hitrate_mensual = db_manager.get_hitrate_mensual(current_date.year)
        if not hitrate_mensual.empty:
            logger.info(f"   ✓ {len(hitrate_mensual)} meses de datos obtenidos")
            logger.info(f"   Columnas: {list(hitrate_mensual.columns)}")
            logger.info(f"   Primer registro:")
            logger.info(f"   {hitrate_mensual.head(1).to_dict('records')[0]}")
        else:
            logger.warning("   ⚠️ No se obtuvieron datos mensuales")

        # 2. Hit Rate YTD
        logger.info("\n2. Hit Rate YTD...")
        hitrate_ytd = db_manager.get_hitrate_ytd(current_date.year, current_date.month)
        if not hitrate_ytd.empty:
            logger.info(f"   ✓ Datos YTD obtenidos")
            logger.info(f"   {hitrate_ytd.to_dict('records')[0]}")
        else:
            logger.warning("   ⚠️ No se obtuvieron datos YTD")

        # 3. Hit Rate por ciudad
        logger.info("\n3. Hit Rate por ciudad...")
        hitrate_ciudad = db_manager.get_hitrate_por_ciudad(current_date.year, current_date.month)
        if not hitrate_ciudad.empty:
            logger.info(f"   ✓ {len(hitrate_ciudad)} ciudades con datos")
            logger.info(f"   Top 3 ciudades por Hit Rate:")
            for idx, row in hitrate_ciudad.head(3).iterrows():
                logger.info(f"   - {row['ciudad']}: {row['hit_rate']:.1f}% HR, {row['eficiencia']:.1f}% Ef")
        else:
            logger.warning("   ⚠️ No se obtuvieron datos por ciudad")

        # 4. Hit Rate histórico por ciudad
        logger.info("\n4. Hit Rate histórico por ciudad...")
        hitrate_ciudad_hist = db_manager.get_hitrate_historico_por_ciudad(current_date.year, current_date.month)
        if not hitrate_ciudad_hist.empty:
            logger.info(f"   ✓ {len(hitrate_ciudad_hist)} registros históricos")
            ciudades_unicas = hitrate_ciudad_hist['ciudad'].nunique()
            meses_unicos = hitrate_ciudad_hist['mes_visita'].nunique()
            logger.info(f"   {ciudades_unicas} ciudades x {meses_unicos} meses")
        else:
            logger.warning("   ⚠️ No se obtuvieron datos históricos")

        # Probar procesamiento de datos
        logger.info("\n🔄 Probando procesamiento de datos...")
        if not hitrate_mensual.empty:
            hitrate_data = data_processor.process_hitrate_data(
                hitrate_mensual, hitrate_ytd, hitrate_ciudad, hitrate_ciudad_hist
            )

            logger.info("✓ Datos procesados correctamente")
            logger.info(f"  Claves en hitrate_data: {list(hitrate_data.keys())}")

            # Mostrar resumen
            summary = hitrate_data.get('summary_metrics', {})
            logger.info(f"\n📈 Resumen de métricas:")
            logger.info(f"  Promedio Hit Rate: {summary.get('promedio_hitrate', 0):.1f}%")
            logger.info(f"  Promedio Eficiencia: {summary.get('promedio_eficiencia', 0):.1f}%")
            logger.info(f"  Mejor mes Hit Rate: {summary.get('mejor_mes_hitrate', 'N/D')}")
            logger.info(f"  Tendencia: {summary.get('tendencia_general', 'N/D')}")

        # Cerrar conexión
        db_manager.disconnect()
        logger.info("\n✅ Pruebas completadas exitosamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error en las pruebas: {e}", exc_info=True)
        db_manager.disconnect()
        return False


if __name__ == "__main__":
    logger.info("="*50)
    logger.info("TEST DE HIT RATE Y EFICIENCIA")
    logger.info("="*50)

    success = test_hitrate_queries()

    if success:
        logger.info("\n✅ TODAS LAS PRUEBAS PASARON")
    else:
        logger.info("\n❌ ALGUNAS PRUEBAS FALLARON")
        logger.info("Revisa los logs para más detalles")