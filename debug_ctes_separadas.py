"""
Ejecutar cada CTE por separado para ver dónde está el problema
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
print("DEBUG: PROYECCIONES_GERENTES (SOLO CIUDADES CON GERENTE)")
print("="*80)

query1 = """
WITH ventas_reales_semanales AS (
    SELECT
        marcadir,
        ciudad,
        SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
        SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
        SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3
    FROM auto.td_ventas_bob_historico
    WHERE anio = 2025 AND mes = 10 AND dia <= 27
        AND UPPER(ciudad) != 'TURISMO'
        AND UPPER(canal) != 'TURISMO'
        AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY marcadir, ciudad
),
proyecciones_gerentes_base AS (
    SELECT
        nombre_marca as marcadir,
        ciudad,
        SUM(CASE WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * 6.96
                 ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0) END) as proy_s4,
        SUM(CASE WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * 6.96
                 ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0) END) as proy_s5
    FROM auto.fact_proyecciones
    WHERE anio_proyeccion = 2025 AND mes_proyeccion = 10
        AND UPPER(ciudad) != 'TURISMO'
    GROUP BY nombre_marca, ciudad
),
ciudades_todas AS (
    SELECT DISTINCT marcadir, ciudad FROM ventas_reales_semanales
    UNION
    SELECT DISTINCT marcadir, ciudad FROM proyecciones_gerentes_base
),
proyecciones_gerentes AS (
    SELECT
        ct.marcadir,
        ct.ciudad,
        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
        COALESCE(vr.venta_real_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0) as total_bob
    FROM ciudades_todas ct
    LEFT JOIN proyecciones_gerentes_base pg
        ON ct.marcadir = pg.marcadir AND ct.ciudad = pg.ciudad
    LEFT JOIN ventas_reales_semanales vr
        ON ct.marcadir = vr.marcadir AND ct.ciudad = vr.ciudad
    WHERE UPPER(ct.ciudad) NOT IN ('ORURO', 'TRINIDAD')
)
SELECT marcadir, SUM(total_bob) as total_gerentes
FROM proyecciones_gerentes
WHERE UPPER(marcadir) = 'CASA REAL'
GROUP BY marcadir
"""

result1 = db.execute_query(query1)
print(result1.to_string(index=False))
print()

print("="*80)
print("DEBUG: SOP_CIUDADES_SIN_GERENTE (ORURO Y TRINIDAD)")
print("="*80)

query2 = """
WITH ventas_reales_semanales AS (
    SELECT
        marcadir,
        ciudad,
        SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
        SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
        SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3
    FROM auto.td_ventas_bob_historico
    WHERE anio = 2025 AND mes = 10 AND dia <= 27
        AND UPPER(ciudad) != 'TURISMO'
        AND UPPER(canal) != 'TURISMO'
        AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY marcadir, ciudad
),
sop_ciudades_sin_gerente_base AS (
    SELECT
        marcadirectorio as marcadir,
        ciudad,
        SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
    FROM auto.factpresupuesto_mensual
    WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = 2025
        AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = 10
        AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
        AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY marcadirectorio, ciudad
),
sop_ciudades_sin_gerente AS (
    SELECT
        sop.marcadir,
        sop.ciudad,
        COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
        COALESCE(vr.venta_real_s3, 0) + (sop.sop_total_mes / 5.0) * 2 as total_bob
    FROM sop_ciudades_sin_gerente_base sop
    LEFT JOIN ventas_reales_semanales vr
        ON sop.marcadir = vr.marcadir AND sop.ciudad = vr.ciudad
)
SELECT marcadir, SUM(total_bob) as total_oruro_trinidad
FROM sop_ciudades_sin_gerente
WHERE UPPER(marcadir) = 'CASA REAL'
GROUP BY marcadir
"""

result2 = db.execute_query(query2)
print(result2.to_string(index=False))
print()

print("="*80)
print("RESUMEN")
print("="*80)
print(f"Total Gerentes:        {result1['total_gerentes'].values[0]:,.2f} BOB" if not result1.empty else "Total Gerentes: No data")
print(f"Total Oruro/Trinidad:  {result2['total_oruro_trinidad'].values[0]:,.2f} BOB" if not result2.empty else "Total Oruro/Trinidad: No data")
print(f"TOTAL COMBINADO:       {result1['total_gerentes'].values[0] + result2['total_oruro_trinidad'].values[0]:,.2f} BOB" if not result1.empty and not result2.empty else "No data")
print()
print(f"Esperado:              6,607,069.07 BOB")
print(f"Diferencia:            {6607069.07 - (result1['total_gerentes'].values[0] + result2['total_oruro_trinidad'].values[0]):,.2f} BOB" if not result1.empty and not result2.empty else "No data")

db.disconnect()
