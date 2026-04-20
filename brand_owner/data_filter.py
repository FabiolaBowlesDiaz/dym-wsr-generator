"""
Filtrado y re-agregacion de datos para el WSR Brand Owner.

Toma los DataFrames crudos del DatabaseManager (que traen TODAS las marcas)
y los filtra a solo marcas Pernod. Para ciudad y canal, re-agrega desde
los datos cruzados (ciudad×marca, canal×marca) para obtener totales
que reflejan solo marcas Pernod.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def filter_dataframe(df: pd.DataFrame, pernod_brands: List[str],
                     brand_col: str = 'marcadir') -> pd.DataFrame:
    """
    Filtrar un DataFrame para mantener solo marcas Pernod.

    Args:
        df: DataFrame con columna de marca
        pernod_brands: Lista de marcas Pernod en UPPER
        brand_col: Nombre de la columna de marca

    Returns:
        DataFrame filtrado
    """
    if df.empty or brand_col not in df.columns:
        return df

    mask = df[brand_col].str.upper().isin(pernod_brands)
    filtered = df[mask].copy()
    logger.info(f"Filtrado {brand_col}: {len(df)} -> {len(filtered)} filas "
                f"({len(filtered)}/{len(df)} = {len(filtered)/max(len(df),1)*100:.0f}%)")
    return filtered


def filter_data_dict(data: Dict[str, pd.DataFrame], pernod_brands: List[str],
                     brand_col: str = 'marcadir') -> Dict[str, pd.DataFrame]:
    """
    Filtrar todos los DataFrames de un diccionario de datos por marcas Pernod.

    Args:
        data: Diccionario {nombre: DataFrame} como lo retorna _fetch_marca_data()
        pernod_brands: Lista de marcas Pernod en UPPER
        brand_col: Nombre de la columna de marca

    Returns:
        Diccionario con DataFrames filtrados
    """
    filtered = {}
    for key, df in data.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            if brand_col in df.columns:
                filtered[key] = filter_dataframe(df, pernod_brands, brand_col)
            else:
                # DataFrame sin columna de marca (ej: nacional) — pasar tal cual
                filtered[key] = df
        else:
            filtered[key] = df
    return filtered


def exclude_inactive_brands(pernod_brands: List[str],
                            ventas_df: pd.DataFrame,
                            prev_year: int) -> List[str]:
    """
    Excluir marcas Pernod que no reportan ventas en el ano anterior.

    Args:
        pernod_brands: Lista completa de marcas Pernod
        ventas_df: DataFrame de ventas historicas con columna vendido_{year}_c9l
        prev_year: Ano anterior

    Returns:
        Lista filtrada de marcas activas
    """
    if ventas_df.empty:
        return pernod_brands

    c9l_col = f'vendido_{prev_year}_c9l'
    if c9l_col not in ventas_df.columns:
        logger.warning(f"Columna {c9l_col} no encontrada — no se filtran marcas inactivas")
        return pernod_brands

    # Marcas con ventas > 0 en el ano anterior
    active = ventas_df[ventas_df[c9l_col] > 0]['marcadir'].str.upper().unique()
    filtered = [b for b in pernod_brands if b in active]

    removed = set(pernod_brands) - set(filtered)
    if removed:
        logger.info(f"Marcas Pernod sin ventas en {prev_year} (excluidas): {removed}")

    logger.info(f"Marcas Pernod activas: {len(filtered)} de {len(pernod_brands)}")
    return filtered


def reaggregate_by_dimension(df_detail: pd.DataFrame,
                             group_col: str,
                             pernod_brands: List[str]) -> pd.DataFrame:
    """
    Filtrar un DataFrame cruzado (dimension×marca) por Pernod y re-agregar
    por la dimension principal.

    Ejemplo: ciudad_marca DataFrame → filtrar a Pernod → groupby('ciudad').sum()
    Esto da totales por ciudad que reflejan SOLO marcas Pernod.

    Args:
        df_detail: DataFrame con columnas [group_col, 'marcadir', metricas...]
        group_col: Columna de agrupacion ('ciudad' o 'canal')
        pernod_brands: Lista de marcas Pernod

    Returns:
        DataFrame agregado por group_col (sin columna marcadir)
    """
    if df_detail.empty:
        return df_detail

    # Filtrar a marcas Pernod
    filtered = filter_dataframe(df_detail, pernod_brands)
    if filtered.empty:
        return filtered

    # Identificar columnas numericas para sumar
    numeric_cols = filtered.select_dtypes(include=[np.number]).columns.tolist()

    # Agrupar por dimension principal
    aggregated = filtered.groupby(group_col, as_index=False)[numeric_cols].sum()

    logger.info(f"Re-agregado {group_col}: {len(filtered)} filas detalle "
                f"-> {len(aggregated)} {group_col}s")
    return aggregated


def build_ciudad_from_ciudad_marca(data_ciudad_marca: Dict[str, pd.DataFrame],
                                    pernod_brands: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Construir datos de ciudad (solo Pernod) desde datos ciudad×marca.

    Pipeline: fetch ciudad_marca → filtrar Pernod → groupby ciudad → totales Pernod-only

    Args:
        data_ciudad_marca: Dict con DataFrames de ciudad×marca
        pernod_brands: Lista de marcas Pernod

    Returns:
        Dict con DataFrames agregados por ciudad (formato compatible con DataProcessor)
    """
    result = {}
    for key, df in data_ciudad_marca.items():
        if isinstance(df, pd.DataFrame) and not df.empty and 'ciudad' in df.columns:
            result[key] = reaggregate_by_dimension(df, 'ciudad', pernod_brands)
        else:
            result[key] = df
    return result


def build_canal_from_canal_marca(data_canal_marca: Dict[str, pd.DataFrame],
                                  pernod_brands: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Construir datos de canal (solo Pernod) desde datos canal×marca.

    Pipeline: fetch canal_marca → filtrar Pernod → groupby canal → totales Pernod-only

    Args:
        data_canal_marca: Dict con DataFrames de canal×marca
        pernod_brands: Lista de marcas Pernod

    Returns:
        Dict con DataFrames agregados por canal (formato compatible con DataProcessor)
    """
    result = {}
    for key, df in data_canal_marca.items():
        if isinstance(df, pd.DataFrame) and not df.empty and 'canal' in df.columns:
            result[key] = reaggregate_by_dimension(df, 'canal', pernod_brands)
        else:
            result[key] = df
    return result
