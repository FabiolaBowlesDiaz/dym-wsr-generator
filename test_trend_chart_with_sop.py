"""
Script de prueba para el gráfico de tendencia con SOP de Oruro y Trinidad
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trend_chart_generator import TrendChartGenerator

def test_trend_chart_with_sop():
    """Probar la generación del gráfico de tendencia con SOP incluido"""

    print("=" * 60)
    print("PRUEBA DEL GRAFICO DE TENDENCIA CON SOP ORURO/TRINIDAD")
    print("=" * 60)

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

    # Datos de proyecciones de gerentes (simulados)
    proyecciones_data = {
        'total_semana1': [3000000],
        'total_semana2': [3500000],
        'total_semana3': [3200000],
        'total_semana4': [3800000],
        'total_semana5': [2000000]
    }
    proyecciones_df = pd.DataFrame(proyecciones_data)

    # Datos de SOP Oruro y Trinidad (simulados)
    sop_data = {
        'ciudad': ['ORURO', 'TRINIDAD'],
        'sop_mensual': [500000, 300000]  # 500K Oruro, 300K Trinidad
    }
    sop_df = pd.DataFrame(sop_data)

    print("   - Ventas semanales creadas")
    print("   - Proyecciones de gerentes creadas")
    print("   - SOP Oruro y Trinidad creado")
    print(f"     * ORURO: {sop_data['sop_mensual'][0]:,.0f} BOB mensual")
    print(f"     * TRINIDAD: {sop_data['sop_mensual'][1]:,.0f} BOB mensual")

    # Mostrar distribución semanal esperada
    print("\n2. Distribución semanal esperada del SOP:")

    oruro_sop = sop_data['sop_mensual'][0]
    trinidad_sop = sop_data['sop_mensual'][1]

    oruro_dist = [0.08, 0.12, 0.20, 0.28, 0.32]
    trinidad_dist = [0.25, 0.45, 0.20, 0.10, 0.00]

    for i in range(5):
        oruro_week = oruro_sop * oruro_dist[i]
        trinidad_week = trinidad_sop * trinidad_dist[i]
        total_week = oruro_week + trinidad_week

        print(f"   Semana {i+1}: Oruro {oruro_week:,.0f} + Trinidad {trinidad_week:,.0f} = {total_week:,.0f} BOB")

    # Procesar datos
    print("\n3. Procesando datos semanales...")
    try:
        chart_data = generator.process_weekly_data(ventas_df, proyecciones_df, sop_df)
        print("   [OK] Datos procesados correctamente")

        # Mostrar resumen
        print("\n4. Resumen de datos procesados:")
        print(f"   - Semanas procesadas: {len(chart_data['semanas'])}")

        print("\n   Desglose por semana:")
        for i, semana in enumerate(chart_data['semanas']):
            venta = chart_data['ventas_bob'][i]
            proyeccion = chart_data['proyecciones_bob'][i]
            cumplimiento = chart_data['cumplimiento_bob'][i]

            print(f"   {semana}:")
            print(f"     - Venta: {venta:,.0f} BOB")
            print(f"     - Proyección total: {proyeccion:,.0f} BOB (gerentes + SOP)")
            print(f"     - Cumplimiento: {cumplimiento:.1f}%")

        print(f"\n   TOTALES:")
        print(f"   - Total venta BOB: {chart_data['totales']['venta_bob']:,.2f}")
        print(f"   - Total proyección BOB: {chart_data['totales']['proyeccion_bob']:,.2f}")
        print(f"   - Cumplimiento BOB: {chart_data['totales']['cumplimiento_bob']:.1f}%")

        # Generar HTML
        print("\n5. Generando HTML del gráfico...")
        html = generator.generate_chart_html(chart_data)

        # Guardar archivo de prueba
        output_path = Path("output") / f"test_trend_chart_sop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path.parent.mkdir(exist_ok=True)

        # Crear HTML completo de prueba
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prueba - Gráfico de Tendencia con SOP Oruro/Trinidad</title>
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
        .info-box {{
            background: #e0f2fe;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            border-left: 4px solid #0277bd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PRUEBA - Gráfico de Tendencia con SOP Oruro/Trinidad</h1>
        <div class="info-box">
            <h3>Datos de Prueba:</h3>
            <p><strong>SOP Oruro:</strong> 500,000 BOB mensual (8%, 12%, 20%, 28%, 32%)</p>
            <p><strong>SOP Trinidad:</strong> 300,000 BOB mensual (25%, 45%, 20%, 10%, 0%)</p>
            <p><strong>Proyecciones incluidas:</strong> Gerentes + SOP distribuido semanalmente</p>
        </div>
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
        print(f"\n6. Abriendo en navegador: {file_url}")
        webbrowser.open(file_url)

        print("\n" + "=" * 60)
        print("[OK] PRUEBA COMPLETADA EXITOSAMENTE")
        print("El gráfico ahora incluye SOP distribuido de Oruro y Trinidad")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[ERROR] Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_trend_chart_with_sop()
    sys.exit(0 if success else 1)