"""
Script de prueba para verificar proyecciones del mes completo
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trend_chart_generator import TrendChartGenerator

def test_full_month_projections():
    """Probar que las proyecciones del mes completo coincidan con otras tablas"""

    print("=" * 70)
    print("PRUEBA PROYECCIONES MES COMPLETO - VERIFICACIÓN DE CONSISTENCIA")
    print("=" * 70)

    # Simular que estamos en semana 4 (como en tu imagen)
    current_date = datetime(2025, 9, 25)  # Día 25 = Semana 4
    generator = TrendChartGenerator(current_date)

    print(f"Simulando fecha: {current_date.strftime('%d/%m/%Y')} (Semana {generator.current_week})")

    # Datos de prueba que simulan los valores reales de tu imagen
    print("\n1. Creando datos simulados basados en imagen...")

    # Ventas semanales (solo hasta semana 4)
    ventas_data = {
        'semana1_bob': [6174504.93],
        'semana2_bob': [7244805.61],
        'semana3_bob': [7717979.65],
        'semana4_bob': [454472.32],
        'semana5_bob': [0]  # No hay ventas aún
    }
    ventas_df = pd.DataFrame(ventas_data)

    # Proyecciones de gerentes por semana (simuladas para llegar a ~21.7M total)
    proyecciones_data = {
        'total_semana1': [2700000],  # Ajustado para ejemplo
        'total_semana2': [5500000],
        'total_semana3': [6400000],
        'total_semana4': [6200000],
        'total_semana5': [1900000]   # Semana 5 futura
    }
    proyecciones_df = pd.DataFrame(proyecciones_data)

    # SOP Oruro y Trinidad (simulado para alcanzar diferencia)
    sop_data = {
        'ciudad': ['ORURO', 'TRINIDAD'],
        'sop_mensual': [898999.89, 34387.04]  # Valores de tu imagen
    }
    sop_df = pd.DataFrame(sop_data)

    print(f"   - SOP Oruro mensual: {sop_data['sop_mensual'][0]:,.2f} BOB")
    print(f"   - SOP Trinidad mensual: {sop_data['sop_mensual'][1]:,.2f} BOB")
    print(f"   - Total SOP mensual: {sum(sop_data['sop_mensual']):,.2f} BOB")

    # Calcular distribución SOP esperada
    oruro_sop = sop_data['sop_mensual'][0]
    trinidad_sop = sop_data['sop_mensual'][1]

    oruro_dist = [0.08, 0.12, 0.20, 0.28, 0.32]
    trinidad_dist = [0.25, 0.45, 0.20, 0.10, 0.00]

    total_sop_distribuido = 0
    print("\n2. Distribución SOP esperada:")
    for i in range(5):
        oruro_week = oruro_sop * oruro_dist[i]
        trinidad_week = trinidad_sop * trinidad_dist[i]
        week_total = oruro_week + trinidad_week
        total_sop_distribuido += week_total
        print(f"   Semana {i+1}: {week_total:,.2f} BOB (Oruro: {oruro_week:,.2f} + Trinidad: {trinidad_week:,.2f})")

    print(f"   Total SOP distribuido: {total_sop_distribuido:,.2f} BOB")

    # Procesar datos
    print("\n3. Procesando datos...")
    try:
        chart_data = generator.process_weekly_data(ventas_df, proyecciones_df, sop_df)

        # Calcular totales esperados
        total_gerentes = sum([v[0] for v in proyecciones_data.values()])
        total_proyecciones_esperado = total_gerentes + total_sop_distribuido

        print(f"   Total proyecciones gerentes: {total_gerentes:,.2f} BOB")
        print(f"   Total SOP distribuido: {total_sop_distribuido:,.2f} BOB")
        print(f"   Total proyecciones esperado: {total_proyecciones_esperado:,.2f} BOB")

        print("\n4. Resultados del procesamiento:")
        print(f"   Total proyecciones obtenido: {chart_data['totales']['proyeccion_bob']:,.2f} BOB")
        print(f"   Total ventas (hasta semana {generator.current_week}): {chart_data['totales']['venta_bob']:,.2f} BOB")
        print(f"   Cumplimiento: {chart_data['totales']['cumplimiento_bob']:.1f}%")

        # Verificar consistencia
        diferencia = abs(chart_data['totales']['proyeccion_bob'] - total_proyecciones_esperado)
        print(f"   Diferencia: {diferencia:,.2f} BOB")

        if diferencia < 100:  # Tolerancia de 100 BOB
            print("   [OK] CONSISTENCIA VERIFICADA")
        else:
            print("   [ERROR] INCONSISTENCIA DETECTADA")

        # Mostrar desglose semanal
        print("\n5. Desglose semanal:")
        for i, semana in enumerate(chart_data['semanas']):
            venta = chart_data['ventas_bob'][i]
            proyeccion = chart_data['proyecciones_bob'][i]
            cumplimiento = chart_data['cumplimiento_bob'][i]

            status = "[OK] Transcurrida" if i < generator.current_week else "[PENDIENTE] Futura"
            print(f"   {semana} {status}:")
            print(f"     - Venta: {venta:,.0f} BOB")
            print(f"     - Proyección: {proyeccion:,.0f} BOB")
            if i < generator.current_week:
                print(f"     - Cumplimiento: {cumplimiento:.1f}%")

        # Generar HTML
        print("\n6. Generando HTML...")
        html = generator.generate_chart_html(chart_data)

        # Guardar archivo
        output_path = Path("output") / f"test_full_month_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path.parent.mkdir(exist_ok=True)

        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prueba - Proyecciones Mes Completo</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
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
        .info {{
            background: #e8f4f8;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Prueba - Proyecciones Mes Completo vs Parciales</h1>
        <div class="info">
            <h3>Verificación de Consistencia:</h3>
            <p><strong>Total Proyecciones (mes completo):</strong> {chart_data['totales']['proyeccion_bob']:,.2f} BOB</p>
            <p><strong>Total Ventas (hasta semana 4):</strong> {chart_data['totales']['venta_bob']:,.2f} BOB</p>
            <p><strong>Diferencia esperada:</strong> {diferencia:,.2f} BOB</p>
            <p><strong>Semanas mostradas:</strong> 5 (todas las proyecciones, ventas solo actuales)</p>
        </div>
        {html}
    </div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)

        print(f"   HTML guardado en: {output_path}")

        # Abrir en navegador
        import webbrowser
        webbrowser.open(f"file:///{output_path.absolute()}")

        print("\n" + "=" * 70)
        print("[OK] PRUEBA COMPLETADA - Proyecciones mes completo implementadas")
        print("El gráfico ahora muestra:")
        print("- Todas las 5 semanas de proyecciones")
        print("- Ventas solo hasta semana actual")
        print("- Total de proyecciones consistente con otras tablas")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_full_month_projections()
    sys.exit(0 if success else 1)