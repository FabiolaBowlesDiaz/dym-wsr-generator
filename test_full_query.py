"""
Test completo del query de proyecciones - replicando database.py
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
print("TEST: QUERY COMPLETO DE PROYECCIONES (REPLICANDO database.py)")
print("="*80)

year = 2025
month = 10
day = 27

query = f"""
WITH ventas_reales_semanales AS (
    SELECT
        UPPER(marcadir) as marcadir,
        UPPER(ciudad) as ciudad,
        SUM(CASE WHEN dia BETWEEN 1 AND 7 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s1,
        SUM(CASE WHEN dia BETWEEN 8 AND 14 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s2,
        SUM(CASE WHEN dia BETWEEN 15 AND 21 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s3,
        SUM(CASE WHEN dia BETWEEN 22 AND 28 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s4,
        SUM(CASE WHEN dia > 28 THEN CAST(fin_01_ingreso AS NUMERIC) ELSE 0 END) as venta_real_s5
    FROM auto.td_ventas_bob_historico
    WHERE anio = {year}
        AND mes = {month}
        AND dia <= {day}
        AND UPPER(ciudad) != 'TURISMO'
        AND UPPER(canal) != 'TURISMO'
        AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY UPPER(marcadir), UPPER(ciudad)
),
proyecciones_gerentes_base AS (
    SELECT
        UPPER(nombre_marca) as marcadir,
        UPPER(ciudad) as ciudad,
        SUM(CASE
            WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana1 AS NUMERIC), 0) * 6.96
            ELSE COALESCE(CAST(total_semana1 AS NUMERIC), 0)
        END) as proy_s1,
        SUM(CASE
            WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana2 AS NUMERIC), 0) * 6.96
            ELSE COALESCE(CAST(total_semana2 AS NUMERIC), 0)
        END) as proy_s2,
        SUM(CASE
            WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana3 AS NUMERIC), 0) * 6.96
            ELSE COALESCE(CAST(total_semana3 AS NUMERIC), 0)
        END) as proy_s3,
        SUM(CASE
            WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana4 AS NUMERIC), 0) * 6.96
            ELSE COALESCE(CAST(total_semana4 AS NUMERIC), 0)
        END) as proy_s4,
        SUM(CASE
            WHEN moneda = 'USD' THEN COALESCE(CAST(total_semana5 AS NUMERIC), 0) * 6.96
            ELSE COALESCE(CAST(total_semana5 AS NUMERIC), 0)
        END) as proy_s5
    FROM auto.fact_proyecciones
    WHERE anio_proyeccion = {year}
        AND mes_proyeccion = {month}
        AND UPPER(ciudad) != 'TURISMO'
    GROUP BY UPPER(nombre_marca), UPPER(ciudad)
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
        CASE
            WHEN {day} <= 7 THEN
                COALESCE(pg.proy_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
            WHEN {day} BETWEEN 8 AND 14 THEN
                COALESCE(vr.venta_real_s1, 0) + COALESCE(pg.proy_s2, 0) + COALESCE(pg.proy_s3, 0) +
                COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
            WHEN {day} BETWEEN 15 AND 21 THEN
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                COALESCE(pg.proy_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
            WHEN {day} BETWEEN 22 AND 28 THEN
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                COALESCE(vr.venta_real_s3, 0) + COALESCE(pg.proy_s4, 0) + COALESCE(pg.proy_s5, 0)
            ELSE
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) + COALESCE(pg.proy_s5, 0)
        END as total_bob
    FROM ciudades_todas ct
    LEFT JOIN proyecciones_gerentes_base pg
        ON ct.marcadir = pg.marcadir AND ct.ciudad = pg.ciudad
    LEFT JOIN ventas_reales_semanales vr
        ON ct.marcadir = vr.marcadir AND ct.ciudad = vr.ciudad
    WHERE ct.ciudad NOT IN ('ORURO', 'TRINIDAD')
),
sop_ciudades_sin_gerente_base AS (
    SELECT
        UPPER(marcadirectorio) as marcadir,
        UPPER(ciudad) as ciudad,
        SUM(CAST(ingreso_neto_sus AS NUMERIC)) as sop_total_mes
    FROM auto.factpresupuesto_mensual
    WHERE EXTRACT(YEAR FROM CAST(tiempo_key AS DATE)) = {year}
        AND EXTRACT(MONTH FROM CAST(tiempo_key AS DATE)) = {month}
        AND UPPER(ciudad) IN ('ORURO', 'TRINIDAD')
        AND UPPER(marcadirectorio) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
    GROUP BY UPPER(marcadirectorio), UPPER(ciudad)
),
sop_ciudades_sin_gerente AS (
    SELECT
        sop.marcadir,
        sop.ciudad,
        CASE
            WHEN {day} <= 7 THEN
                sop.sop_total_mes
            WHEN {day} BETWEEN 8 AND 14 THEN
                COALESCE(vr.venta_real_s1, 0) + (sop.sop_total_mes / 5.0) * 4
            WHEN {day} BETWEEN 15 AND 21 THEN
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                (sop.sop_total_mes / 5.0) * 3
            WHEN {day} BETWEEN 22 AND 28 THEN
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                COALESCE(vr.venta_real_s3, 0) + (sop.sop_total_mes / 5.0) * 2
            ELSE
                COALESCE(vr.venta_real_s1, 0) + COALESCE(vr.venta_real_s2, 0) +
                COALESCE(vr.venta_real_s3, 0) + COALESCE(vr.venta_real_s4, 0) +
                (sop.sop_total_mes / 5.0)
        END as total_bob
    FROM sop_ciudades_sin_gerente_base sop
    LEFT JOIN ventas_reales_semanales vr
        ON sop.marcadir = vr.marcadir AND sop.ciudad = vr.ciudad
),
-- Debug: Ver resultados intermedios
debug_proy AS (
    SELECT marcadir, SUM(total_bob) as total FROM proyecciones_gerentes GROUP BY marcadir
),
debug_sop AS (
    SELECT marcadir, SUM(total_bob) as total FROM sop_ciudades_sin_gerente GROUP BY marcadir
)
SELECT
    COALESCE(p.marcadir, s.marcadir) as marcadir,
    COALESCE(p.total, 0) as proy_gerentes,
    COALESCE(s.total, 0) as sop_oruro_trinidad,
    COALESCE(p.total, 0) + COALESCE(s.total, 0) as py_2025_bob
FROM debug_proy p
FULL OUTER JOIN debug_sop s ON p.marcadir = s.marcadir
WHERE COALESCE(p.marcadir, s.marcadir) = 'CASA REAL'
"""

result = db.execute_query(query)
print(result.to_string(index=False))
print()
print(f"Esperado:  6,607,069.07 BOB")
print(f"Diferencia: {6607069.07 - result['py_2025_bob'].values[0]:,.2f} BOB" if not result.empty else "No data")

db.disconnect()
