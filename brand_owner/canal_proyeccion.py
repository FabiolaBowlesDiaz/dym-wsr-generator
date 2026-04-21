"""
Proyeccion de cierre por canal para Brand Owner (Pernod Ricard).

Replica la formula ponderada del WSR principal pero trabajando SOLO sobre datos
filtrados a marcas Pernod (re-agregados desde canal x marca).

Formula del WSR principal:
    Clave_i = 0.10 x (R_i/sumR) + 0.04 x (Q_i/sumQ)
            + 0.06 x (S_i/sumS) + 0.80 x (T_i/sumT)
    PY_canal_i = Clave_i x total_PY

Donde:
    R = Vendido ano anterior
    Q = Ppto general (anual)
    S = SOP (presupuesto mensual)
    T = Avance actual

Como el Brand Owner NO trae ppto_general a nivel canal x marca (solo SOP),
redistribuimos el peso 0.04 de Q proporcionalmente entre los demas:
    R: 0.10/0.96 = 0.104
    S: 0.06/0.96 = 0.063
    T: 0.80/0.96 = 0.833
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Pesos (sin Q, redistribuidos)
W_R = 0.104   # Vendido ano anterior
W_S = 0.063   # SOP
W_T = 0.833   # Avance actual
# Suma = 1.000


def calcular_py_canal_pernod(canal_data: dict, total_py_pernod_bob: float,
                              current_year: int, previous_year: int) -> pd.DataFrame:
    """
    Calcular proyeccion por canal para marcas Pernod usando formula ponderada.

    Args:
        canal_data: Dict con DataFrames re-agregados (ya filtrados a Pernod):
                    - 'ventas_historicas' → canal, vendido_{prev}_bob, vendido_{prev}_c9l
                    - 'avance_actual' → canal, avance_{year}_bob, avance_{year}_c9l
                    - 'sop' → canal, sop_bob, sop_c9l
        total_py_pernod_bob: Proyeccion total de marcas Pernod en BOB
        current_year: Ano en curso (ej: 2026)
        previous_year: Ano anterior (ej: 2025)

    Returns:
        DataFrame con columnas ['canal', 'py_{year}_bob']
    """
    if total_py_pernod_bob <= 0:
        logger.warning("[Canal PY Pernod] total_py = 0, no se puede proyectar")
        return pd.DataFrame(columns=['canal', f'py_{current_year}_bob'])

    # Columnas esperadas
    vendido_col = f'vendido_{previous_year}_bob'
    avance_col = f'avance_{current_year}_bob'

    # Empezar con avance (piedra angular — peso 0.833)
    df_av = canal_data.get('avance_actual', pd.DataFrame())
    if df_av.empty or avance_col not in df_av.columns:
        logger.warning("[Canal PY Pernod] Sin datos de avance")
        return pd.DataFrame(columns=['canal', f'py_{current_year}_bob'])

    df = df_av[['canal', avance_col]].copy()
    df = df.rename(columns={avance_col: 'T'})

    # Merge vendido ano anterior (R)
    df_vh = canal_data.get('ventas_historicas', pd.DataFrame())
    if not df_vh.empty and vendido_col in df_vh.columns:
        df = df.merge(
            df_vh[['canal', vendido_col]].rename(columns={vendido_col: 'R'}),
            on='canal', how='left'
        )
    else:
        df['R'] = 0

    # Merge SOP (S)
    df_sop = canal_data.get('sop', pd.DataFrame())
    if not df_sop.empty and 'sop_bob' in df_sop.columns:
        df = df.merge(
            df_sop[['canal', 'sop_bob']].rename(columns={'sop_bob': 'S'}),
            on='canal', how='left'
        )
    else:
        df['S'] = 0

    df = df.fillna(0)

    # Calcular ratios (participacion de cada canal en cada metrica)
    sum_R = df['R'].sum()
    sum_S = df['S'].sum()
    sum_T = df['T'].sum()

    df['ratio_R'] = df['R'] / sum_R if sum_R > 0 else 0
    df['ratio_S'] = df['S'] / sum_S if sum_S > 0 else 0
    df['ratio_T'] = df['T'] / sum_T if sum_T > 0 else 0

    # Clave ponderada
    df['clave'] = (W_R * df['ratio_R']
                   + W_S * df['ratio_S']
                   + W_T * df['ratio_T'])

    # Ajuste: si un canal solo tiene avance (no R ni S), dominara por T pero el
    # resto de la clave sera 0 — lo cual es correcto.

    # PY canal = clave × total_py_pernod
    py_col = f'py_{current_year}_bob'
    df[py_col] = df['clave'] * total_py_pernod_bob

    # Mantener solo columnas finales
    result = df[['canal', py_col]].copy()

    logger.info(f"[Canal PY Pernod] {len(result)} canales — total proyectado: "
                f"{result[py_col].sum():,.0f} BOB (target: {total_py_pernod_bob:,.0f})")
    return result
