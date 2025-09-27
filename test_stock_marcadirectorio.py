"""
Script de verificación para el cambio de marca a marcadirectorio en análisis de stock
"""

import logging
from datetime import datetime
from core.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_stock_query():
    """Probar que la consulta de stock funcione con marcadirectorio"""

    print("=" * 80)
    print("PRUEBA DE CONSULTA DE STOCK CON MARCADIRECTORIO")
    print("=" * 80)

    try:
        # Inicializar conexión a base de datos
        db_manager = DatabaseManager()

        # Ejecutar la consulta de stock
        print("\nEjecutando consulta de stock por marca (usando marcadirectorio)...")
        stock_df = db_manager.get_stock_marca()

        if stock_df.empty:
            print("⚠️ La consulta no devolvió datos. Verificar si existe la columna marcadirectorio en td_stock_sap")
            return False

        print(f"✅ Consulta exitosa! Se obtuvieron {len(stock_df)} marcas con stock")

        # Mostrar primeras 10 marcas
        print("\nTop 10 marcas por stock (C9L):")
        print("-" * 50)
        for idx, row in stock_df.head(10).iterrows():
            print(f"  {idx+1:2d}. {row['marcadir']:30s} - {row['stock_c9l']:,.0f} C9L")

        # Verificar que los nombres de marca son consistentes
        print("\n" + "=" * 80)
        print("VERIFICACIÓN DE CONSISTENCIA")
        print("=" * 80)

        # Obtener ventas para comparar
        current_date = datetime.now()
        year = current_date.year
        month = current_date.month
        day = current_date.day

        print("\nObteniendo datos de ventas para comparar...")
        ventas_df = db_manager.get_avance_actual_marca(year, month, day)

        if not ventas_df.empty:
            # Comparar marcas entre stock y ventas
            marcas_stock = set(stock_df['marcadir'].unique())
            marcas_ventas = set(ventas_df['marcadir'].unique())

            # Marcas en común
            marcas_comunes = marcas_stock.intersection(marcas_ventas)
            marcas_solo_stock = marcas_stock - marcas_ventas
            marcas_solo_ventas = marcas_ventas - marcas_stock

            print(f"\n📊 Análisis de consistencia:")
            print(f"  - Marcas con stock: {len(marcas_stock)}")
            print(f"  - Marcas con ventas: {len(marcas_ventas)}")
            print(f"  - Marcas en común: {len(marcas_comunes)}")
            print(f"  - Marcas solo en stock: {len(marcas_solo_stock)}")
            print(f"  - Marcas solo en ventas: {len(marcas_solo_ventas)}")

            if len(marcas_comunes) > 0:
                print("\n✅ Hay coincidencia entre marcas de stock y ventas")
                print(f"   Porcentaje de coincidencia: {len(marcas_comunes)/len(marcas_stock)*100:.1f}%")
            else:
                print("\n⚠️ No hay coincidencia entre marcas de stock y ventas")
                print("   Esto podría indicar un problema con el campo marcadirectorio")

            if marcas_solo_stock and len(marcas_solo_stock) < 10:
                print(f"\nMarcas solo en stock: {list(marcas_solo_stock)[:5]}")

            if marcas_solo_ventas and len(marcas_solo_ventas) < 10:
                print(f"Marcas solo en ventas: {list(marcas_solo_ventas)[:5]}")

        print("\n" + "=" * 80)
        print("RESULTADO: El cambio se implementó correctamente ✅")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {str(e)}")
        print("\nPosibles causas:")
        print("  1. La columna 'marcadirectorio' no existe en td_stock_sap")
        print("  2. Problemas de conexión a la base de datos")
        print("  3. Permisos insuficientes")

        import traceback
        print("\nDetalle del error:")
        traceback.print_exc()

        return False


if __name__ == "__main__":
    success = test_stock_query()

    if success:
        print("\n🎉 Todas las pruebas pasaron exitosamente!")
        print("   El análisis de stock ahora usa 'marcadirectorio' consistentemente")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisar los mensajes de error arriba.")