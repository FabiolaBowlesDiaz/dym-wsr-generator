"""
Script para debuggear el cálculo de PY 2025 para Havana
Muestra el desglose detallado por ciudad
"""

import os
from dotenv import load_dotenv
from core.database import DatabaseManager
import pandas as pd

load_dotenv()

# Configuración
config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'schema': os.getenv('DB_SCHEMA', 'auto')
}

db = DatabaseManager(config)
db.connect()

print("="*80)
print("ANÁLISIS PY 2025 PARA HAVANA - DÍA 27 (SEMANA 4)")
print("="*80)
print()

# 1. VENTAS REALES POR CIUDAD (S1, S2, S3) - SIN Oruro/Trinidad
print("1. VENTAS REALES HAVANA POR CIUDAD (Semanas 1, 2, 3) - Ciudades con Gerente")
print("-"*80)

query_ventas = """
SELECT
    ciudad,
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as total_ventas_reales
FROM auto.td_ventas_bob_historico
WHERE anio = 2025 AND mes = 10 AND dia <= 27
    AND UPPER(marcadir) = 'HAVANA'
    AND UPPER(ciudad) NOT IN ('ORURO', 'TRINIDAD', 'TURISMO')
    AND UPPER(canal) != 'TURISMO'
GROUP BY ciudad
ORDER BY ciudad
"""

df_ventas = db.execute_query(query_ventas)
print(df_ventas.to_string(index=False))
print()
print(f"TOTAL VENTAS REALES (S1+S2+S3) - Sin Oruro/Trinidad: {df_ventas['total_ventas_reales'].sum():,.2f} BOB")
print()
print()

# 2. PROYECCIONES GERENTES POR CIUDAD (S4, S5)
print("2. PROYECCIONES GERENTES HAVANA POR CIUDAD (Semanas 4 y 5)")
print("-"*80)

query_proy = """
SELECT
    ciudad,
    nombre_marca,
    SUM(CASE
        WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * 6.96
        ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
    END) as proy_s4,
    SUM(CASE
        WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * 6.96
        ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
    END) as proy_s5,
    SUM(CASE
        WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * 6.96
        ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
    END) +
    SUM(CASE
        WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * 6.96
        ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
    END) as total_proy
FROM auto.fact_proyecciones
WHERE anio_proyeccion = 2025 AND mes_proyeccion = 10
    AND UPPER(nombre_marca) = 'HAVANA'
    AND UPPER(ciudad) NOT IN ('ORURO', 'TRINIDAD', 'TURISMO')
GROUP BY ciudad, nombre_marca
ORDER BY ciudad
"""

df_proy = db.execute_query(query_proy)
if not df_proy.empty:
    print(df_proy.to_string(index=False))
    print()
    print(f"TOTAL PROYECCIONES GERENTES (S4+S5): {df_proy['total_proy'].sum():,.2f} BOB")
else:
    print("No hay proyecciones de gerentes para Havana")
    print()
print()
print()

# 3. SOP ORURO Y TRINIDAD
print("3. SOP ORURO Y TRINIDAD (Prorrateado para S4 y S5)")
print("-"*80)

query_sop = """
SELECT
    ciudad,
    marcadirectorio,
    SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes,
    (SUM(CAST(ingreso_neto_sus AS NUMERIC)) / 5.0) * 2 as sop_s4_s5
FROM auto.factpresupuesto_mensual
WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
    AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
    AND UPPER(marcadirectorio) = 'HAVANA'
GROUP BY ciudad, marcadirectorio
ORDER BY ciudad
"""

df_sop = db.execute_query(query_sop)
if not df_sop.empty:
    print(df_sop.to_string(index=False))
    print()
    print(f"TOTAL SOP S4+S5 (Oruro + Trinidad): {df_sop['sop_s4_s5'].sum():,.2f} BOB")
else:
    print("No hay datos de SOP para Oruro/Trinidad con Havana")
    print()

print()
print()

# 4. VENTAS REALES ORURO Y TRINIDAD (S1, S2, S3)
print("4. VENTAS REALES ORURO Y TRINIDAD (Semanas 1, 2, 3)")
print("-"*80)

query_ventas_ot = """
SELECT
    ciudad,
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as total_ventas_reales
FROM auto.td_ventas_bob_historico
WHERE anio = 2025 AND mes = 10 AND dia <= 27
    AND UPPER(marcadir) = 'HAVANA'
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
GROUP BY ciudad
ORDER BY ciudad
"""

df_ventas_ot = db.execute_query(query_ventas_ot)
if not df_ventas_ot.empty:
    print(df_ventas_ot.to_string(index=False))
    print()
    print(f"TOTAL VENTAS REALES ORURO+TRINIDAD (S1+S2+S3): {df_ventas_ot['total_ventas_reales'].sum():,.2f} BOB")
else:
    print("No hay ventas reales para Oruro/Trinidad con Havana")
    print()

print()
print()

# 5. CÁLCULO FINAL
print("="*80)
print("CÁLCULO FINAL PY 2025 HAVANA")
print("="*80)
print()

total_ventas_reales = df_ventas['total_ventas_reales'].sum()
total_proy_gerentes = df_proy['total_proy'].sum() if not df_proy.empty else 0
total_ventas_ot = df_ventas_ot['total_ventas_reales'].sum() if not df_ventas_ot.empty else 0
total_sop_ot = df_sop['sop_s4_s5'].sum() if not df_sop.empty else 0

print(f"Ciudades con Gerente:")
print(f"  - Ventas Reales (S1+S2+S3):     {total_ventas_reales:>15,.2f} BOB")
print(f"  - Proyecciones (S4+S5):         {total_proy_gerentes:>15,.2f} BOB")
print(f"  - Subtotal:                     {total_ventas_reales + total_proy_gerentes:>15,.2f} BOB")
print()
print(f"Oruro y Trinidad:")
print(f"  - Ventas Reales (S1+S2+S3):     {total_ventas_ot:>15,.2f} BOB")
print(f"  - SOP Prorrateado (S4+S5):      {total_sop_ot:>15,.2f} BOB")
print(f"  - Subtotal:                     {total_ventas_ot + total_sop_ot:>15,.2f} BOB")
print()
print("-"*80)
print(f"PY 2025 HAVANA TOTAL:             {total_ventas_reales + total_proy_gerentes + total_ventas_ot + total_sop_ot:>15,.2f} BOB")
print("="*80)
print()

# 6. COMPARACIÓN CON EL RESULTADO DEL QUERY
print("COMPARACIÓN CON RESULTADO DEL QUERY get_proyecciones_marca()")
print("-"*80)

result = db.get_proyecciones_marca(2025, 10, 27)
havana = result[result['marcadir'].str.upper() == 'HAVANA']

if not havana.empty:
    py_query = havana['py_2025_bob'].values[0]
    py_manual = total_ventas_reales + total_proy_gerentes + total_ventas_ot + total_sop_ot
    print(f"PY 2025 Query:   {py_query:,.2f} BOB")
    print(f"PY 2025 Manual:  {py_manual:,.2f} BOB")
    print(f"Diferencia:      {abs(py_query - py_manual):,.2f} BOB")
else:
    print("No se encontró Havana en el resultado del query")

db.disconnect()
