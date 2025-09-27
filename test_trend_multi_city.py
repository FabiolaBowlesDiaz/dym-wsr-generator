"""
Script de prueba para el gráfico de tendencias multi-ciudad
"""

import os
import sys
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager
from core.trend_chart_generator import TrendChartGenerator

def test_multi_city_trends():
    """Probar el sistema de gráficos multi-ciudad"""

    # Cargar variables de entorno
    load_dotenv()

    # Configuración
    current_date = datetime(2025, 9, 23)
    current_year = 2025
    current_month = 9
    current_day = 23

    print("\n" + "="*60)
    print("PRUEBA DEL SISTEMA DE TENDENCIAS MULTI-CIUDAD")
    print("="*60)
    print(f"Fecha: {current_date.strftime('%d/%m/%Y')}")
    print(f"Período: Mes {current_month}/{current_year}")

    try:
        # Configuración de base de datos
        db_config = {
            'DB_HOST': os.getenv('DB_HOST'),
            'DB_PORT': os.getenv('DB_PORT'),
            'DB_NAME': os.getenv('DB_NAME'),
            'DB_USER': os.getenv('DB_USER'),
            'DB_PASSWORD': os.getenv('DB_PASSWORD'),
            'DB_SCHEMA': os.getenv('DB_SCHEMA', 'public')
        }

        # Inicializar conexión a DB
        db_manager = DatabaseManager(db_config)
        trend_generator = TrendChartGenerator(current_date)

        # 1. Obtener datos generales (nacionales)
        print("\nObteniendo datos nacionales...")
        ventas_semanales = db_manager.get_ventas_semanales_nacional(
            current_year, current_month, current_day
        )
        proyecciones_semanales = db_manager.get_proyecciones_semanales_nacional(
            current_year, current_month
        )
        sop_oruro_trinidad = db_manager.get_sop_oruro_trinidad(
            current_year, current_month
        )

        print(f"   * Ventas semanales: {len(ventas_semanales)} registros")
        print(f"   * Proyecciones semanales: {len(proyecciones_semanales)} registros")
        print(f"   * SOP Oruro/Trinidad: {len(sop_oruro_trinidad)} registros")

        # 2. Obtener datos por ciudad
        print("\nObteniendo datos por ciudad...")
        ventas_por_ciudad = db_manager.get_ventas_semanales_por_ciudad_detalle(
            current_year, current_month, current_day
        )
        proyecciones_por_ciudad = db_manager.get_proyecciones_semanales_por_ciudad(
            current_year, current_month
        )

        print(f"   * Ventas por ciudad: {len(ventas_por_ciudad)} ciudades")
        if not ventas_por_ciudad.empty:
            ciudades_ventas = ventas_por_ciudad['ciudad'].unique()
            print(f"     - Ciudades con ventas: {', '.join(ciudades_ventas)}")

        print(f"   * Proyecciones por ciudad: {len(proyecciones_por_ciudad)} ciudades")
        if not proyecciones_por_ciudad.empty:
            ciudades_proy = proyecciones_por_ciudad['ciudad'].unique()
            print(f"     - Ciudades con proyecciones: {', '.join(ciudades_proy)}")

        # 3. Procesar datos multi-ciudad
        print("\nProcesando datos multi-ciudad...")
        chart_data = trend_generator.process_weekly_data_multi_city(
            ventas_semanales,
            proyecciones_semanales,
            ventas_por_ciudad,
            proyecciones_por_ciudad,
            sop_oruro_trinidad
        )

        print(f"   * Vistas generadas: {len(chart_data)} total")
        print(f"     - Vistas disponibles: {', '.join(chart_data.keys())}")

        # 4. Mostrar resumen de datos generales
        print("\nDATOS GENERALES (NACIONAL):")
        general_data = chart_data.get('general', {})
        if general_data:
            print(f"   Semanas: {general_data.get('semanas', [])}")
            print(f"   Ventas BOB: {[f'{v:,.0f}' for v in general_data.get('ventas_bob', [])]}")
            print(f"   Proyecciones BOB: {[f'{p:,.0f}' for p in general_data.get('proyecciones_bob', [])]}")
            print(f"   Cumplimiento %: {general_data.get('cumplimiento_bob', [])}")

            totales = general_data.get('totales', {})
            print(f"\n   TOTALES:")
            print(f"   - Venta Total: {totales.get('venta_bob', 0):,.2f} BOB")
            print(f"   - Proyección Total: {totales.get('proyeccion_bob', 0):,.2f} BOB")
            print(f"   - Cumplimiento: {totales.get('cumplimiento_bob', 0):.1f}%")

        # 5. Mostrar datos de una ciudad ejemplo
        print("\nEJEMPLO - DATOS DE SANTA CRUZ:")
        santa_cruz_data = chart_data.get('santa_cruz', {})
        if santa_cruz_data:
            print(f"   Ventas BOB: {[f'{v:,.0f}' for v in santa_cruz_data.get('ventas_bob', [])]}")
            print(f"   Proyecciones BOB: {[f'{p:,.0f}' for p in santa_cruz_data.get('proyecciones_bob', [])]}")
            print(f"   Cumplimiento %: {santa_cruz_data.get('cumplimiento_bob', [])}")

        # 6. Generar HTML
        print("\nGenerando HTML con selector de ciudades...")
        chart_html = trend_generator.generate_chart_html(chart_data)

        # Guardar HTML para revisión
        output_file = f"test_multi_city_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(f"output/{output_file}", 'w', encoding='utf-8') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Test Multi-Ciudad - Análisis de Tendencias</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                </style>
            </head>
            <body>
                {chart_html}
            </body>
            </html>
            """)

        print(f"   * HTML generado: output/{output_file}")
        print("\nPRUEBA COMPLETADA EXITOSAMENTE")

        return True

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if 'db_manager' in locals():
            try:
                db_manager.close_connection()
            except:
                pass

if __name__ == "__main__":
    success = test_multi_city_trends()
    sys.exit(0 if success else 1)