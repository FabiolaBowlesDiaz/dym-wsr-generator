"""
Verificar el cálculo correcto - ¿Qué ciudades deben ir en cada CTE?
"""

import os
from dotenv import load_dotenv
from core.database import DatabaseManager

load_dotenv()

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
print("VERIFICACIÓN: ¿Qué debe ir en proyecciones_gerentes?")
print("="*80)
print()

# Ventas reales SIN Oruro/Trinidad
query1 = """
SELECT
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as total_ventas_reales
FROM auto.td_ventas_bob_historico
WHERE anio = 2025 AND mes = 10 AND dia <= 27
    AND UPPER(marcadir) = 'CASA REAL'
    AND UPPER(ciudad) NOT IN ('ORURO', 'TRINIDAD', 'TURISMO')
    AND UPPER(canal) != 'TURISMO'
"""

result1 = db.execute_query(query1)
ventas_sin_ot = result1['total_ventas_reales'].values[0]
print(f"1. Ventas Reales (S1+S2+S3) SIN Oruro/Trinidad: {ventas_sin_ot:,.2f} BOB")

# Proyecciones gerentes (S4+S5)
query2 = """
SELECT
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
    AND UPPER(nombre_marca) = 'CASA REAL'
    AND UPPER(ciudad) NOT IN ('ORURO', 'TRINIDAD', 'TURISMO')
"""

result2 = db.execute_query(query2)
proy_gerentes = result2['total_proy'].values[0]
print(f"2. Proyecciones Gerentes (S4+S5): {proy_gerentes:,.2f} BOB")

total_proy_gerentes = ventas_sin_ot + proy_gerentes
print(f"3. Total proyecciones_gerentes: {total_proy_gerentes:,.2f} BOB")
print()

print("="*80)
print("VERIFICACIÓN: ¿Qué debe ir en sop_ciudades_sin_gerente?")
print("="*80)
print()

# Ventas reales DE Oruro/Trinidad
query3 = """
SELECT
    SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) +
    SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as total_ventas_reales
FROM auto.td_ventas_bob_historico
WHERE anio = 2025 AND mes = 10 AND dia <= 27
    AND UPPER(marcadir) = 'CASA REAL'
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
"""

result3 = db.execute_query(query3)
ventas_ot = result3['total_ventas_reales'].values[0]
print(f"1. Ventas Reales (S1+S2+S3) Oruro+Trinidad: {ventas_ot:,.2f} BOB")

# SOP prorrateado
query4 = """
SELECT
    (SUM(CAST(ingreso_neto_sus AS NUMERIC)) / 5.0) * 2 as sop_s4_s5
FROM auto.factpresupuesto_mensual
WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
    AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
    AND UPPER(marcadirectorio) = 'CASA REAL'
"""

result4 = db.execute_query(query4)
sop_ot = result4['sop_s4_s5'].values[0]
print(f"2. SOP Prorrateado (S4+S5): {sop_ot:,.2f} BOB")

total_sop = ventas_ot + sop_ot
print(f"3. Total sop_ciudades_sin_gerente: {total_sop:,.2f} BOB")
print()

print("="*80)
print("CÁLCULO FINAL")
print("="*80)
print(f"proyecciones_gerentes:     {total_proy_gerentes:,.2f} BOB")
print(f"sop_ciudades_sin_gerente:  {total_sop:,.2f} BOB")
print(f"TOTAL PY 2025:             {total_proy_gerentes + total_sop:,.2f} BOB")
print(f"Esperado:                  6,607,069.07 BOB")
print(f"Diferencia:                {6607069.07 - (total_proy_gerentes + total_sop):,.2f} BOB")

db.disconnect()
