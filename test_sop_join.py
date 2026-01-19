"""
Test específico para verificar el JOIN en sop_ciudades_sin_gerente
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
print("TEST: sop_ciudades_sin_gerente CON JOIN A ventas_reales_semanales")
print("="*80)

query = """
WITH ventas_reales_semanales AS (
    SELECT
        UPPER(marcadir) as marcadir,
        UPPER(ciudad) as ciudad,
        SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
        SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
        SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3
    FROM auto.td_ventas_bob_historico
    WHERE anio = 2025 AND mes = 10 AND dia <= 27
        AND UPPER(ciudad) != 'TURISMO'
        AND UPPER(canal) != 'TURISMO'
        AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY UPPER(marcadir), UPPER(ciudad)
),
sop_ciudades_sin_gerente_base AS (
    SELECT
        UPPER(marcadirectorio) as marcadir,
        UPPER(ciudad) as ciudad,
        SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
    FROM auto.factpresupuesto_mensual
    WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
        AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
        AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
        AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY UPPER(marcadirectorio), UPPER(ciudad)
)
SELECT
    sop.marcadir,
    sop.ciudad,
    sop.sop_total_mes,
    vr.venta_real_s1,
    vr.venta_real_s2,
    vr.venta_real_s3,
    COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
    COALESCE(vr.venta_real_s3, 0) + (sop.sop_total_mes / 5.0) * 2 as total_bob
FROM sop_ciudades_sin_gerente_base sop
LEFT JOIN ventas_reales_semanales vr
    ON sop.marcadir = vr.marcadir AND sop.ciudad = vr.ciudad
WHERE UPPER(sop.marcadir) = 'CASA REAL'
"""

result = db.execute_query(query)
print(result.to_string(index=False))
print()
print(f"Total: {result['total_bob'].sum():,.2f} BOB")
print(f"Esperado: 534,374.80 BOB (346,080.44 ventas + 188,294.36 SOP)")

db.disconnect()
