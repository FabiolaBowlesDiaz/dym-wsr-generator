"""
validate_drivers.py - Cross-validation of DriversEngine output vs direct SQL queries.

Compares cobertura, hit_rate, drop_size, and VSLY trends computed by DriversEngine
against independent SQL queries to fact_ventas_detallado.

Usage:
    python scripts/validate_drivers.py

Requires VPN connectivity to 192.168.80.85.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path for imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


def get_db_config():
    """Load DB config from environment variables."""
    return {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }


def build_direct_query(schema, start_date, end_date):
    """Build direct SQL query for fact_ventas_detallado."""
    return f"""
    SELECT
        marca,
        COUNT(DISTINCT cod_cliente) AS cobertura,
        COUNT(DISTINCT cuf_factura) AS pedidos,
        ROUND(
            COUNT(DISTINCT cuf_factura)::NUMERIC /
            NULLIF(COUNT(DISTINCT cod_cliente), 0), 2
        ) AS hit_rate,
        ROUND(
            SUM(ingreso_neto_bob) /
            NULLIF(COUNT(DISTINCT cuf_factura), 0), 2
        ) AS drop_size,
        SUM(ingreso_neto_bob) AS venta_total
    FROM {schema}.fact_ventas_detallado
    WHERE UPPER(marca) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
      AND UPPER(ciudad) NOT IN ('TURISMO')
      AND fecha >= '{start_date}'
      AND fecha <= '{end_date}'
    GROUP BY marca
    ORDER BY marca
    """


def run_validation():
    """Main validation routine."""
    from core.database import DatabaseManager
    from proyeccion_objetiva.pilar3_operativa.drivers_engine import DriversEngine

    now = datetime.now()
    schema = os.getenv('DB_SCHEMA', 'auto')
    db_config = get_db_config()

    print(f"=== DRIVER VALIDATION: {now.strftime('%B %Y')} STD (dia 1-{now.day}) ===")
    print(f"Schema: {schema}")
    print(f"DB Host: {db_config['host']}")
    print()

    # --- Connect ---
    try:
        db = DatabaseManager(db_config, schema)
        # Quick connectivity check
        test_df = db.execute_query(f"SELECT 1 AS test")
        if test_df.empty:
            print("ERROR: Database connectivity test failed (empty result).")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        print("Ensure VPN is active and .env is configured correctly.")
        sys.exit(1)

    # --- 1. Engine output ---
    print("[1/5] Running DriversEngine.calculate_by_marca()...")
    engine = DriversEngine(db, schema=schema, current_date=now)
    df_engine = engine.calculate_by_marca()

    if df_engine.empty:
        print("ERROR: DriversEngine returned empty DataFrame. No data for current period?")
        sys.exit(1)

    print(f"      Engine returned {len(df_engine)} brands")
    is_std = df_engine['is_std'].iloc[0] if 'is_std' in df_engine.columns else False

    if not is_std:
        print("WARNING: Engine used FALLBACK mode (not STD). Direct comparison uses STD dates.")
        print("         Results may differ if the engine fell back to a different period.")

    # --- 2. Direct SQL queries ---
    current_start = f"{now.year}-{now.month:02d}-01"
    current_end = f"{now.year}-{now.month:02d}-{now.day:02d}"
    yoy_start = f"{now.year - 1}-{now.month:02d}-01"
    yoy_end = f"{now.year - 1}-{now.month:02d}-{now.day:02d}"

    print(f"[2/5] Direct SQL: current period {current_start} to {current_end}...")
    sql_current = build_direct_query(schema, current_start, current_end)
    df_direct_current = db.execute_query(sql_current)
    print(f"      Direct returned {len(df_direct_current)} brands (current)")

    print(f"[3/5] Direct SQL: YoY period {yoy_start} to {yoy_end}...")
    sql_yoy = build_direct_query(schema, yoy_start, yoy_end)
    df_direct_yoy = db.execute_query(sql_yoy)
    print(f"      Direct returned {len(df_direct_yoy)} brands (YoY)")

    # --- 3. Compute direct VSLY trends ---
    print("[4/5] Computing direct VSLY trends...")
    df_direct = df_direct_current.copy()

    if not df_direct_yoy.empty:
        yoy_map = df_direct_yoy.set_index('marca')[['cobertura', 'hit_rate', 'drop_size']].to_dict('index')

        direct_cob_trend = []
        direct_hr_trend = []
        direct_ds_trend = []

        for _, row in df_direct.iterrows():
            marca = row['marca']
            yoy_data = yoy_map.get(marca)
            if yoy_data:
                cob_yoy = float(yoy_data['cobertura'])
                hr_yoy = float(yoy_data['hit_rate'])
                ds_yoy = float(yoy_data['drop_size'])
                direct_cob_trend.append((float(row['cobertura']) / cob_yoy - 1) if cob_yoy > 0 else None)
                direct_hr_trend.append((float(row['hit_rate']) / hr_yoy - 1) if hr_yoy > 0 else None)
                direct_ds_trend.append((float(row['drop_size']) / ds_yoy - 1) if ds_yoy > 0 else None)
            else:
                direct_cob_trend.append(None)
                direct_hr_trend.append(None)
                direct_ds_trend.append(None)

        df_direct['cobertura_trend_direct'] = direct_cob_trend
        df_direct['hitrate_trend_direct'] = direct_hr_trend
        df_direct['dropsize_trend_direct'] = direct_ds_trend
    else:
        df_direct['cobertura_trend_direct'] = None
        df_direct['hitrate_trend_direct'] = None
        df_direct['dropsize_trend_direct'] = None

    # --- 4. Merge and compare ---
    print("[5/5] Comparing Engine vs Direct...")
    print()

    # Normalize marca columns for join
    df_engine_cmp = df_engine.copy()
    df_engine_cmp['marca_upper'] = df_engine_cmp['marca'].str.upper().str.strip()
    df_direct['marca_upper'] = df_direct['marca'].str.upper().str.strip()

    merged = df_engine_cmp.merge(
        df_direct,
        on='marca_upper',
        how='outer',
        suffixes=('_engine', '_direct'),
        indicator=True
    )

    # Tolerances
    TOL_EXACT = 0        # cobertura: exact integer match
    TOL_RATE = 0.01      # hit_rate, drop_size
    TOL_TREND = 0.005    # VSLY trends
    TOL_MULT = 0.01      # multiplicative identity (1%)

    # Comparison results
    results = []
    brand_pass_count = 0
    brand_total = 0

    # Header
    print(f"{'MARCA':<25} | {'Metric':<14} | {'Engine':>12} | {'Direct':>12} | {'Diff':>10} | {'Status':<6}")
    print("-" * 90)

    for _, row in merged.iterrows():
        if row['_merge'] == 'left_only':
            marca = row.get('marca_engine', row['marca_upper'])
            print(f"{str(marca):<25} | {'ALL':<14} | {'present':>12} | {'MISSING':>12} | {'---':>10} | {'SKIP':<6}")
            continue
        elif row['_merge'] == 'right_only':
            marca = row.get('marca_direct', row['marca_upper'])
            print(f"{str(marca):<25} | {'ALL':<14} | {'MISSING':>12} | {'present':>12} | {'---':>10} | {'SKIP':<6}")
            continue

        marca = row.get('marca_engine', row['marca_upper'])
        brand_total += 1
        all_pass = True

        checks = [
            ('cobertura', float(row['cobertura_engine']), float(row['cobertura_direct']), TOL_EXACT),
            ('hit_rate', float(row['hit_rate_engine']), float(row['hit_rate_direct']), TOL_RATE),
            ('drop_size', float(row['drop_size_engine']), float(row['drop_size_direct']), TOL_RATE),
        ]

        # Add trend checks if available
        eng_cob_trend = row.get('cobertura_trend')
        dir_cob_trend = row.get('cobertura_trend_direct')
        eng_hr_trend = row.get('hitrate_trend')
        dir_hr_trend = row.get('hitrate_trend_direct')
        eng_ds_trend = row.get('dropsize_trend')
        dir_ds_trend = row.get('dropsize_trend_direct')

        if pd.notna(eng_cob_trend) and pd.notna(dir_cob_trend):
            checks.append(('cob_trend', float(eng_cob_trend), float(dir_cob_trend), TOL_TREND))
        if pd.notna(eng_hr_trend) and pd.notna(dir_hr_trend):
            checks.append(('hr_trend', float(eng_hr_trend), float(dir_hr_trend), TOL_TREND))
        if pd.notna(eng_ds_trend) and pd.notna(dir_ds_trend):
            checks.append(('ds_trend', float(eng_ds_trend), float(dir_ds_trend), TOL_TREND))

        for metric, eng_val, dir_val, tol in checks:
            diff = abs(eng_val - dir_val)
            if tol == 0:
                status = "PASS" if eng_val == dir_val else "FAIL"
            else:
                status = "PASS" if diff <= tol else "FAIL"

            if status == "FAIL":
                all_pass = False

            # Format values
            if metric == 'cobertura':
                eng_str = f"{int(eng_val):>12d}"
                dir_str = f"{int(dir_val):>12d}"
                diff_str = f"{int(eng_val - dir_val):>10d}"
            elif 'trend' in metric:
                eng_str = f"{eng_val:>12.4f}"
                dir_str = f"{dir_val:>12.4f}"
                diff_str = f"{diff:>10.4f}"
            else:
                eng_str = f"{eng_val:>12.2f}"
                dir_str = f"{dir_val:>12.2f}"
                diff_str = f"{diff:>10.2f}"

            print(f"{str(marca):<25} | {metric:<14} | {eng_str} | {dir_str} | {diff_str} | {status:<6}")

            results.append({
                'marca': marca,
                'metric': metric,
                'engine': eng_val,
                'direct': dir_val,
                'diff': diff,
                'status': status,
            })

        if all_pass:
            brand_pass_count += 1

    # --- 5. Multiplicative identity check ---
    print()
    print("=" * 90)
    print("MULTIPLICATIVE IDENTITY CHECK: Cobertura x HitRate x DropSize ~= Venta Total")
    print("-" * 90)
    print(f"{'MARCA':<25} | {'Cob*HR*DS':>14} | {'Venta Total':>14} | {'Diff %':>10} | {'Status':<6}")
    print("-" * 90)

    mult_pass = 0
    mult_total = 0

    for _, row in merged.iterrows():
        if row['_merge'] != 'both':
            continue

        marca = row.get('marca_direct', row['marca_upper'])
        cob = float(row['cobertura_direct'])
        hr = float(row['hit_rate_direct'])
        ds = float(row['drop_size_direct'])
        venta = float(row['venta_total_direct'])

        computed = cob * hr * ds
        if venta > 0:
            pct_diff = abs(computed - venta) / venta
        else:
            pct_diff = 0.0 if computed == 0 else 1.0

        status = "PASS" if pct_diff <= TOL_MULT else "FAIL"
        mult_total += 1
        if status == "PASS":
            mult_pass += 1

        print(f"{str(marca):<25} | {computed:>14,.2f} | {venta:>14,.2f} | {pct_diff:>9.2%} | {status:<6}")

    # --- 6. Summary ---
    print()
    print("=" * 90)
    print("SUMMARY")
    print("-" * 90)
    total_checks = len(results)
    passed_checks = sum(1 for r in results if r['status'] == 'PASS')
    failed_checks = total_checks - passed_checks
    print(f"  Metric checks:  {passed_checks}/{total_checks} passed")
    print(f"  Brands:         {brand_pass_count}/{brand_total} brands passed ALL metric checks")
    print(f"  Multiplicative: {mult_pass}/{mult_total} brands within 1% tolerance")
    print()

    if failed_checks == 0 and mult_pass == mult_total:
        print("OVERALL: PASS -- All driver metrics match between Engine and Direct SQL")
    else:
        print("OVERALL: FAIL -- Some discrepancies found (see details above)")
        if failed_checks > 0:
            print()
            print("FAILED CHECKS:")
            for r in results:
                if r['status'] == 'FAIL':
                    print(f"  WARNING: Discrepancy in {r['marca']}/{r['metric']} "
                          f"-- Engine={r['engine']}, Direct={r['direct']}, Diff={r['diff']}")

    return failed_checks == 0 and mult_pass == mult_total


if __name__ == '__main__':
    try:
        success = run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
