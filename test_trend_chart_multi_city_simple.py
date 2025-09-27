"""
Script de prueba simple para el gráfico de tendencias multi-ciudad con datos simulados
"""

import os
import sys
from datetime import datetime
import pandas as pd

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trend_chart_generator import TrendChartGenerator

def create_mock_data():
    """Crear datos simulados para probar"""

    # Datos nacionales (suma de todas las ciudades)
    ventas_semanales = pd.DataFrame({
        'semana1_bob': [6174504.93],
        'semana2_bob': [7244805.61],
        'semana3_bob': [7717979.65],
        'semana4_bob': [454472.32],
        'semana5_bob': [0]
    })

    proyecciones_semanales = pd.DataFrame({
        'total_semana1': [2836099.90],
        'total_semana2': [5783806.32],
        'total_semana3': [6655148.26],
        'total_semana4': [6450575.44],
        'total_semana5': [2814498.08]
    })

    # Datos por ciudad
    ventas_por_ciudad = pd.DataFrame({
        'ciudad': ['SANTA CRUZ', 'COCHABAMBA', 'LA PAZ', 'EL ALTO', 'TARIJA', 'SUCRE', 'POTOSI'],
        'semana1_bob': [1860000, 1920000, 1315000, 662000, 311000, 331500, 107500],
        'semana2_bob': [2160000, 2232000, 1529000, 770000, 361500, 385500, 125000],
        'semana3_bob': [2310000, 2387000, 1636000, 824000, 386750, 412500, 133750],
        'semana4_bob': [136350, 140950, 96650, 48650, 22825, 24350, 7900],
        'semana5_bob': [0, 0, 0, 0, 0, 0, 0]
    })

    proyecciones_por_ciudad = pd.DataFrame({
        'ciudad': ['SANTA CRUZ', 'COCHABAMBA', 'LA PAZ', 'EL ALTO', 'TARIJA', 'SUCRE', 'POTOSI'],
        'total_semana1': [840000, 810000, 620000, 345000, 150000, 135000, 80000],
        'total_semana2': [1740000, 1679000, 1285000, 715000, 311000, 280000, 165000],
        'total_semana3': [2010000, 1939000, 1484000, 826000, 359250, 323500, 191000],
        'total_semana4': [1950000, 1881000, 1440000, 801000, 348500, 313750, 185250],
        'total_semana5': [840000, 810000, 620000, 345000, 150000, 135000, 80000]
    })

    # SOP Oruro y Trinidad (vacío para simplificar)
    sop_oruro_trinidad = pd.DataFrame()

    return ventas_semanales, proyecciones_semanales, ventas_por_ciudad, proyecciones_por_ciudad, sop_oruro_trinidad

def test_multi_city_trends_simple():
    """Probar el sistema de gráficos multi-ciudad con datos simulados"""

    # Configuración
    current_date = datetime(2025, 9, 23)

    print("="*60)
    print("PRUEBA SIMPLE DEL SISTEMA MULTI-CIUDAD")
    print("="*60)
    print(f"Fecha: {current_date.strftime('%d/%m/%Y')}")

    try:
        # Inicializar generador
        trend_generator = TrendChartGenerator(current_date)
        print("* Generador inicializado")

        # Crear datos simulados
        ventas_semanales, proyecciones_semanales, ventas_por_ciudad, proyecciones_por_ciudad, sop_oruro_trinidad = create_mock_data()
        print("* Datos simulados creados")

        # Procesar datos multi-ciudad
        print("\nProcesando datos multi-ciudad...")
        chart_data = trend_generator.process_weekly_data_multi_city(
            ventas_semanales,
            proyecciones_semanales,
            ventas_por_ciudad,
            proyecciones_por_ciudad,
            sop_oruro_trinidad
        )

        print(f"* Vistas generadas: {len(chart_data)} total")
        print(f"  - Vistas disponibles: {', '.join(chart_data.keys())}")

        # Mostrar resumen de datos generales
        print("\nDATOS GENERALES (NACIONAL):")
        general_data = chart_data.get('general', {})
        if general_data:
            totales = general_data.get('totales', {})
            print(f"  - Venta Total: {totales.get('venta_bob', 0):,.2f} BOB")
            print(f"  - Proyeccion Total: {totales.get('proyeccion_bob', 0):,.2f} BOB")
            print(f"  - Cumplimiento: {totales.get('cumplimiento_bob', 0):.1f}%")

        # Mostrar datos de Santa Cruz
        print("\nDATOS DE SANTA CRUZ:")
        santa_cruz_data = chart_data.get('santa_cruz', {})
        if santa_cruz_data:
            totales_sc = santa_cruz_data.get('totales', {})
            print(f"  - Venta Total: {totales_sc.get('venta_bob', 0):,.2f} BOB")
            print(f"  - Proyeccion Total: {totales_sc.get('proyeccion_bob', 0):,.2f} BOB")
            print(f"  - Cumplimiento: {totales_sc.get('cumplimiento_bob', 0):.1f}%")

        # Generar HTML
        print("\nGenerando HTML con selector de ciudades...")
        chart_html = trend_generator.generate_chart_html(chart_data)

        # Guardar HTML
        output_file = f"test_multi_city_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path = f"output/{output_file}"

        # Crear directorio si no existe
        os.makedirs("output", exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Multi-Ciudad - Análisis de Tendencias</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .header {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 PRUEBA DEL SISTEMA MULTI-CIUDAD</h1>
        <p>Prueba del nuevo sistema de análisis de tendencias con selector por ciudad</p>
        <p><strong>Fecha de prueba:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    {chart_html}
    <div style="background: white; padding: 20px; margin-top: 20px; border-radius: 8px;">
        <h3>Instrucciones de Prueba:</h3>
        <ol>
            <li>El gráfico debe mostrar inicialmente datos GENERAL-NACIONAL</li>
            <li>Al hacer clic en los botones de ciudad, debe cambiar dinámicamente</li>
            <li>Los datos deben coincidir con los valores mostrados arriba</li>
            <li>No debe incluir Oruro ni Trinidad en los botones</li>
        </ol>
    </div>
</body>
</html>
            """)

        print(f"* HTML generado: {output_path}")
        print("\nPRUEBA COMPLETADA EXITOSAMENTE")
        print(f"\nAbre el archivo {output_path} en tu navegador para ver el resultado")

        return True

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_multi_city_trends_simple()
    sys.exit(0 if success else 1)