"""
Test para ver los valores exactos de ciudad en ambas tablas
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
print("VALORES DE CIUDAD EN td_ventas_bob_historico (Casa Real, Oruro/Trinidad)")
print("="*80)

query1 = """
SELECT DISTINCT
    ciudad,
    UPPER(ciudad) as ciudad_upper,
    marcadir,
    UPPER(marcadir) as marcadir_upper,
    LENGTH(ciudad) as len_ciudad,
    LENGTH(UPPER(ciudad)) as len_ciudad_upper
FROM auto.td_ventas_bob_historico
WHERE anio = 2025 AND mes = 10
    AND UPPER(marcadir) = 'CASA REAL'
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
ORDER BY ciudad
"""

result1 = db.execute_query(query1)
print(result1.to_string(index=False))
print()

print("="*80)
print("VALORES DE CIUDAD EN factpresupuesto_mensual (Casa Real, Oruro/Trinidad)")
print("="*80)

query2 = """
SELECT DISTINCT
    ciudad,
    UPPER(ciudad) as ciudad_upper,
    marcadirectorio,
    UPPER(marcadirectorio) as marcadir_upper,
    LENGTH(ciudad) as len_ciudad,
    LENGTH(UPPER(ciudad)) as len_ciudad_upper
FROM auto.factpresupuesto_mensual
WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
    AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
    AND UPPER(marcadirectorio) = 'CASA REAL'
    AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
ORDER BY ciudad
"""

result2 = db.execute_query(query2)
print(result2.to_string(index=False))
print()

print("="*80)
print("TEST JOIN - ¿Coinciden los valores normalizados?")
print("="*80)

query3 = """
WITH ventas AS (
    SELECT DISTINCT
        UPPER(marcadir) as marcadir,
        UPPER(ciudad) as ciudad
    FROM auto.td_ventas_bob_historico
    WHERE anio = 2025 AND mes = 10
        AND UPPER(marcadir) = 'CASA REAL'
        AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
),
sop AS (
    SELECT DISTINCT
        UPPER(marcadirectorio) as marcadir,
        UPPER(ciudad) as ciudad
    FROM auto.factpresupuesto_mensual
    WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
        AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
        AND UPPER(marcadirectorio) = 'CASA REAL'
        AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
)
SELECT
    sop.marcadir as sop_marca,
    sop.ciudad as sop_ciudad,
    ventas.marcadir as ventas_marca,
    ventas.ciudad as ventas_ciudad,
    CASE WHEN ventas.marcadir IS NOT NULL THEN 'MATCH' ELSE 'NO MATCH' END as resultado
FROM sop
LEFT JOIN ventas
    ON sop.marcadir = ventas.marcadir AND sop.ciudad = ventas.ciudad
"""

result3 = db.execute_query(query3)
print(result3.to_string(index=False))

db.disconnect()
