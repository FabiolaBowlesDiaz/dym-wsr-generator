"""
Script de prueba para validar el cálculo del PY2025 en C9L
Fórmula: (Avance 2025 C9L * PY2025 BOB) / Avance 2025 BOB
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Simular datos de prueba
def create_test_data():
    """Crear datos de prueba para validar la fórmula"""
    data = {
        'marcadir': ['Casa Real', 'Don Roberto', 'Mendocino', 'Campos de Solana'],
        'vendido_2024_bob': [1000000, 800000, 600000, 400000],
        'vendido_2024_c9l': [50000, 40000, 30000, 20000],
        'avance_2025_bob': [1100000, 880000, 660000, 440000],
        'avance_2025_c9l': [55000, 44000, 33000, 22000],
        'py_2025_bob': [1200000, 900000, 650000, 450000],  # Proyección gerentes en BOB
        'sop_bob': [1150000, 850000, 640000, 430000],
        'sop_c9l': [57500, 42500, 32000, 21500],
        'ppto_general_bob': [1100000, 820000, 620000, 420000],
        'ppto_general_c9l': [55000, 41000, 31000, 21000]
    }
    return pd.DataFrame(data)

def calculate_py2025_c9l(df):
    """Calcular PY2025 para C9L usando la nueva fórmula"""
    results = []

    print("=" * 80)
    print("CÁLCULO DE PY2025 PARA C9L")
    print("Fórmula: (Avance 2025 C9L * PY2025 BOB) / Avance 2025 BOB")
    print("=" * 80)
    print()

    for idx, row in df.iterrows():
        marca = row['marcadir']
        avance_c9l = row['avance_2025_c9l']
        py_bob = row['py_2025_bob']
        avance_bob = row['avance_2025_bob']
        sop_c9l = row['sop_c9l']

        # Calcular usando la nueva fórmula
        if avance_bob > 0:
            py_c9l_nuevo = (avance_c9l * py_bob) / avance_bob
        else:
            py_c9l_nuevo = 0

        # Comparar con el método anterior (usar SOP)
        py_c9l_anterior = sop_c9l

        # Calcular diferencia
        diferencia = py_c9l_nuevo - py_c9l_anterior
        pct_cambio = ((py_c9l_nuevo / py_c9l_anterior) - 1) * 100 if py_c9l_anterior > 0 else 0

        results.append({
            'Marca': marca,
            'Avance 2025 C9L': avance_c9l,
            'PY 2025 BOB': py_bob,
            'Avance 2025 BOB': avance_bob,
            'PY C9L (Anterior-SOP)': py_c9l_anterior,
            'PY C9L (Nueva Fórmula)': py_c9l_nuevo,
            'Diferencia': diferencia,
            '% Cambio': pct_cambio
        })

        print(f"Marca: {marca}")
        print(f"  Avance 2025 C9L: {avance_c9l:,.0f}")
        print(f"  PY 2025 BOB (Proyección Gerentes): {py_bob:,.0f}")
        print(f"  Avance 2025 BOB: {avance_bob:,.0f}")
        print(f"  PY C9L Anterior (SOP): {py_c9l_anterior:,.0f}")
        print(f"  PY C9L Nueva Fórmula: {py_c9l_nuevo:,.0f}")
        print(f"  Diferencia: {diferencia:,.0f}")
        print(f"  % Cambio: {pct_cambio:.2f}%")
        print()

    # Crear DataFrame con resultados
    results_df = pd.DataFrame(results)

    # Calcular totales
    print("=" * 80)
    print("TOTALES")
    print("=" * 80)

    total_avance_c9l = df['avance_2025_c9l'].sum()
    total_py_bob = df['py_2025_bob'].sum()
    total_avance_bob = df['avance_2025_bob'].sum()
    total_sop_c9l = df['sop_c9l'].sum()

    if total_avance_bob > 0:
        total_py_c9l_nuevo = (total_avance_c9l * total_py_bob) / total_avance_bob
    else:
        total_py_c9l_nuevo = 0

    total_py_c9l_anterior = total_sop_c9l
    total_diferencia = total_py_c9l_nuevo - total_py_c9l_anterior
    total_pct_cambio = ((total_py_c9l_nuevo / total_py_c9l_anterior) - 1) * 100 if total_py_c9l_anterior > 0 else 0

    print(f"Total Avance 2025 C9L: {total_avance_c9l:,.0f}")
    print(f"Total PY 2025 BOB: {total_py_bob:,.0f}")
    print(f"Total Avance 2025 BOB: {total_avance_bob:,.0f}")
    print(f"Total PY C9L Anterior (SOP): {total_py_c9l_anterior:,.0f}")
    print(f"Total PY C9L Nueva Fórmula: {total_py_c9l_nuevo:,.0f}")
    print(f"Total Diferencia: {total_diferencia:,.0f}")
    print(f"Total % Cambio: {total_pct_cambio:.2f}%")

    return results_df

def test_edge_cases():
    """Probar casos extremos para la división por cero"""
    print("\n" + "=" * 80)
    print("PRUEBA DE CASOS EXTREMOS")
    print("=" * 80)
    print()

    # Caso 1: División por cero
    print("Caso 1: Avance BOB = 0 (División por cero)")
    avance_c9l = 1000
    py_bob = 5000
    avance_bob = 0

    if avance_bob > 0:
        py_c9l = (avance_c9l * py_bob) / avance_bob
    else:
        py_c9l = 0

    print(f"  Avance C9L: {avance_c9l}")
    print(f"  PY BOB: {py_bob}")
    print(f"  Avance BOB: {avance_bob}")
    print(f"  PY C9L Calculado: {py_c9l}")
    print(f"  Resultado: {'Manejado correctamente (devuelve 0)' if py_c9l == 0 else 'Error'}")
    print()

    # Caso 2: Valores normales
    print("Caso 2: Valores normales")
    avance_c9l = 1000
    py_bob = 20000
    avance_bob = 10000

    if avance_bob > 0:
        py_c9l = (avance_c9l * py_bob) / avance_bob
    else:
        py_c9l = 0

    print(f"  Avance C9L: {avance_c9l}")
    print(f"  PY BOB: {py_bob}")
    print(f"  Avance BOB: {avance_bob}")
    print(f"  PY C9L Calculado: {py_c9l}")
    print(f"  Verificación: {avance_c9l} * {py_bob} / {avance_bob} = {py_c9l}")
    print()

if __name__ == "__main__":
    print("\n" + "PRUEBA DE CALCULO PY2025 PARA C9L")
    print("=" * 80)
    print(f"Fecha de prueba: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Crear y mostrar datos de prueba
    df = create_test_data()

    # Calcular y mostrar resultados
    results = calculate_py2025_c9l(df)

    # Probar casos extremos
    test_edge_cases()

    print("\nPrueba completada exitosamente")