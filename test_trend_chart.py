"""
Script de prueba para el gráfico de tendencia comparativa
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trend_chart_generator import TrendChartGenerator

def test_trend_chart():
    """Probar la generación del gráfico de tendencia"""

    print("=" * 50)
    print("PRUEBA DEL GRÁFICO DE TENDENCIA COMPARATIVA")
    print("=" * 50)

    # Inicializar generador
    current_date = datetime.now()
    generator = TrendChartGenerator(current_date)

    # Crear datos de prueba simulados
    print("\n1. Creando datos de prueba...")

    # Datos de ventas semanales (simulados - solo BOB)
    ventas_data = {
        'semana1_bob': [2500000],
        'semana2_bob': [3100000],
        'semana3_bob': [2800000],
        'semana4_bob': [3500000],
        'semana5_bob': [1200000]
    }
    ventas_df = pd.DataFrame(ventas_data)

    # Datos de proyecciones (simulados)
    proyecciones_data = {
        'total_semana1': [3000000],
        'total_semana2': [3500000],
        'total_semana3': [3200000],
        'total_semana4': [3800000],
        'total_semana5': [2000000]
    }
    proyecciones_df = pd.DataFrame(proyecciones_data)

    print("   - Ventas semanales creadas")
    print("   - Proyecciones semanales creadas")

    # Procesar datos
    print("\n2. Procesando datos semanales...")
    try:
        chart_data = generator.process_weekly_data(ventas_df, proyecciones_df)
        print("   [OK] Datos procesados correctamente")

        # Mostrar resumen
        print("\n3. Resumen de datos procesados:")
        print(f"   - Semanas procesadas: {len(chart_data['semanas'])}")
        print(f"   - Total venta BOB: {chart_data['totales']['venta_bob']:,.2f}")
        print(f"   - Total proyección BOB: {chart_data['totales']['proyeccion_bob']:,.2f}")
        print(f"   - Cumplimiento BOB: {chart_data['totales']['cumplimiento_bob']:.1f}%")

        # Generar HTML
        print("\n4. Generando HTML del gráfico...")
        html = generator.generate_chart_html(chart_data)

        # Guardar archivo de prueba
        output_path = Path("output") / f"test_trend_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path.parent.mkdir(exist_ok=True)

        # Crear HTML completo de prueba
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prueba - Gráfico de Tendencia Comparativa</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1e3a8a;
            text-align: center;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PRUEBA - Gráfico de Tendencia Comparativa (Solo BOB)</h1>
        {html}
    </div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)

        print(f"   [OK] HTML generado y guardado en: {output_path}")

        # Intentar abrir en navegador
        import webbrowser
        file_url = f"file:///{output_path.absolute()}"
        print(f"\n5. Abriendo en navegador: {file_url}")
        webbrowser.open(file_url)

        print("\n" + "=" * 50)
        print("[OK] PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"\n[ERROR] Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_trend_chart()
    sys.exit(0 if success else 1)