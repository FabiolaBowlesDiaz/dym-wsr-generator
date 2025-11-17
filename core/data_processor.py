"""
Módulo de Procesamiento de Datos para WSR Generator
Maneja la consolidación de datos y cálculo de KPIs
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
    """Procesador de datos para el WSR"""
    
    def __init__(self, current_date: datetime):
        """
        Inicializar el procesador de datos
        
        Args:
            current_date: Fecha actual para el reporte
        """
        self.current_date = current_date
        self.current_year = current_date.year
        self.current_month = current_date.month
        self.current_day = current_date.day
        self.previous_year = self.current_year - 1
        
    def consolidate_marca_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Consolidar todos los datos por marca

        Args:
            data: Diccionario con DataFrames de diferentes fuentes

        Returns:
            DataFrame consolidado con todos los KPIs por marca
        """
        logger.info("Consolidando datos por marca...")

        # Normalizar los datos antes de consolidar
        normalized_data = {}
        for key, df_data in data.items():
            if not df_data.empty:
                normalized_data[key] = self._normalize_dataframe_columns(df_data, ['marcadir'])
            else:
                normalized_data[key] = df_data

        # Comenzar con el DataFrame base
        df = self._get_base_dataframe(normalized_data, 'marca')

        # Agregar ventas históricas
        if 'ventas_historicas' in normalized_data and not normalized_data['ventas_historicas'].empty:
            df = pd.merge(df, normalized_data['ventas_historicas'], on='marcadir', how='outer')

        # Agregar avance actual
        if 'avance_actual' in normalized_data and not normalized_data['avance_actual'].empty:
            df = pd.merge(df, normalized_data['avance_actual'], on='marcadir', how='outer')

        # Agregar presupuestos
        if 'ppto_general' in normalized_data and not normalized_data['ppto_general'].empty:
            df = pd.merge(df, normalized_data['ppto_general'], on='marcadir', how='outer')

        if 'sop' in normalized_data and not normalized_data['sop'].empty:
            df = pd.merge(df, normalized_data['sop'], on='marcadir', how='outer')

        # Agregar proyecciones
        if 'proyecciones' in normalized_data and not normalized_data['proyecciones'].empty:
            df = pd.merge(df, normalized_data['proyecciones'], on='marcadir', how='outer')

        # Agregar stock
        if 'stock' in normalized_data and not normalized_data['stock'].empty:
            df = pd.merge(df, normalized_data['stock'], on='marcadir', how='left')

        # Agregar ventas semanales
        if 'ventas_semanales' in normalized_data and not normalized_data['ventas_semanales'].empty:
            df = pd.merge(df, normalized_data['ventas_semanales'], on='marcadir', how='left')

        # Agregar venta promedio diaria
        if 'venta_promedio_diaria' in normalized_data and not normalized_data['venta_promedio_diaria'].empty:
            df = pd.merge(df, normalized_data['venta_promedio_diaria'][['marcadir', 'venta_promedio_diaria_c9l']],
                         on='marcadir', how='left')

        # Llenar NaN con 0
        df = df.fillna(0)

        # Calcular KPIs
        df = self._calculate_marca_kpis(df)

        # Ordenar por avance descendente
        avance_col = f'avance_{self.current_year}_bob'
        if avance_col in df.columns:
            df = df.sort_values(avance_col, ascending=False)

        logger.info(f"Consolidación completa: {len(df)} marcas procesadas")
        return df

    def consolidate_marca_subfamilia_data(self, data: Dict[str, pd.DataFrame], data_subfamilia: Dict[str, pd.DataFrame]) -> Dict:
        """
        Consolidar datos jerárquicos por marca y subfamilia

        Args:
            data: Diccionario con DataFrames a nivel marca (incluye proyecciones)
            data_subfamilia: Diccionario con DataFrames a nivel marca-subfamilia

        Returns:
            Diccionario con estructura jerárquica marca -> subfamilia
        """
        logger.info("Consolidando datos jerárquicos por marca y subfamilia...")

        # Primero consolidar datos a nivel marca (incluye proyecciones)
        df_marca = self.consolidate_marca_data(data)

        # Normalizar datos de subfamilia
        normalized_subfamilia = {}
        for key, df_data in data_subfamilia.items():
            if not df_data.empty:
                normalized_subfamilia[key] = self._normalize_dataframe_columns(df_data, ['marcadir', 'subfamilia'])
            else:
                normalized_subfamilia[key] = df_data

        # Crear DataFrame base para subfamilia
        df_subfamilia = pd.DataFrame()

        # Consolidar datos de subfamilia
        if 'ventas_historicas_subfamilia' in normalized_subfamilia and not normalized_subfamilia['ventas_historicas_subfamilia'].empty:
            df_subfamilia = normalized_subfamilia['ventas_historicas_subfamilia']

        # Agregar avance actual por subfamilia
        if 'avance_actual_subfamilia' in normalized_subfamilia and not normalized_subfamilia['avance_actual_subfamilia'].empty:
            if df_subfamilia.empty:
                df_subfamilia = normalized_subfamilia['avance_actual_subfamilia']
            else:
                df_subfamilia = pd.merge(df_subfamilia, normalized_subfamilia['avance_actual_subfamilia'],
                                        on=['marcadir', 'subfamilia'], how='outer')

        # Agregar presupuestos por subfamilia
        if 'ppto_general_subfamilia' in normalized_subfamilia and not normalized_subfamilia['ppto_general_subfamilia'].empty:
            df_subfamilia = pd.merge(df_subfamilia, normalized_subfamilia['ppto_general_subfamilia'],
                                    on=['marcadir', 'subfamilia'], how='outer')

        if 'sop_subfamilia' in normalized_subfamilia and not normalized_subfamilia['sop_subfamilia'].empty:
            df_subfamilia = pd.merge(df_subfamilia, normalized_subfamilia['sop_subfamilia'],
                                    on=['marcadir', 'subfamilia'], how='outer')

        # Agregar stock por subfamilia
        if 'stock_subfamilia' in normalized_subfamilia and not normalized_subfamilia['stock_subfamilia'].empty:
            df_subfamilia = pd.merge(df_subfamilia, normalized_subfamilia['stock_subfamilia'],
                                    on=['marcadir', 'subfamilia'], how='left')

        # Agregar venta promedio diaria por subfamilia
        if 'venta_promedio_diaria_subfamilia' in normalized_subfamilia and not normalized_subfamilia['venta_promedio_diaria_subfamilia'].empty:
            df_subfamilia = pd.merge(df_subfamilia,
                                    normalized_subfamilia['venta_promedio_diaria_subfamilia'][['marcadir', 'subfamilia', 'venta_promedio_diaria_c9l']],
                                    on=['marcadir', 'subfamilia'], how='left')

        # Llenar NaN con 0
        df_subfamilia = df_subfamilia.fillna(0)

        # Calcular KPIs para subfamilia
        df_subfamilia = self._calculate_marca_subfamilia_kpis(df_subfamilia)

        # Crear estructura jerárquica
        resultado = {
            'marca_totales': df_marca,
            'marca_subfamilia': df_subfamilia,
            'estructura_jerarquica': self._crear_estructura_jerarquica(df_marca, df_subfamilia)
        }

        logger.info(f"Consolidación jerárquica completa: {len(df_marca)} marcas, {len(df_subfamilia)} subfamilias")
        return resultado

    def _calculate_marca_subfamilia_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular KPIs para datos de marca-subfamilia"""

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        vendido_c9l = f'vendido_{self.previous_year}_c9l'
        avance_c9l = f'avance_{self.current_year}_c9l'

        # Calcular KPIs básicos (sin proyecciones)
        if 'ppto_general_bob' in df.columns and avance_col in df.columns:
            df['AV_PG'] = df.apply(lambda x: ((x[avance_col] / x['ppto_general_bob']) - 1)
                                  if x['ppto_general_bob'] > 0 else 0, axis=1)

        if 'sop_bob' in df.columns and avance_col in df.columns:
            df['AV_SOP'] = df.apply(lambda x: ((x[avance_col] / x['sop_bob']) - 1)
                                   if x['sop_bob'] > 0 else 0, axis=1)

        # Calcular precios
        if vendido_col in df.columns and vendido_c9l in df.columns:
            df[f'precio_{self.previous_year}'] = df.apply(lambda x: x[vendido_col] / x[vendido_c9l]
                                                          if x[vendido_c9l] > 0 else 0, axis=1)

        if avance_col in df.columns and avance_c9l in df.columns:
            df[f'precio_{self.current_year}'] = df.apply(lambda x: x[avance_col] / x[avance_c9l]
                                                         if x[avance_c9l] > 0 else 0, axis=1)

        # Incremento de precio
        precio_prev = f'precio_{self.previous_year}'
        precio_curr = f'precio_{self.current_year}'
        if precio_prev in df.columns and precio_curr in df.columns:
            df['inc_precio'] = df.apply(lambda x: ((x[precio_curr] / x[precio_prev]) - 1)
                                       if x[precio_prev] > 0 else 0, axis=1)

        # Cobertura
        if 'stock_c9l' in df.columns and 'venta_promedio_diaria_c9l' in df.columns:
            df['cobertura_dias'] = df.apply(lambda x: x['stock_c9l'] / x['venta_promedio_diaria_c9l']
                                           if x['venta_promedio_diaria_c9l'] > 0 else 0, axis=1)

        return df

    def _crear_estructura_jerarquica(self, df_marca: pd.DataFrame, df_subfamilia: pd.DataFrame) -> Dict:
        """
        Crear estructura jerárquica para facilitar la renderización

        Returns:
            Diccionario con estructura marca -> subfamilias
        """
        estructura = {}

        for _, marca_row in df_marca.iterrows():
            marca = marca_row['marcadir']

            # Obtener subfamilias para esta marca
            subfamilias = df_subfamilia[df_subfamilia['marcadir'] == marca]

            estructura[marca] = {
                'datos_marca': marca_row.to_dict(),
                'subfamilias': subfamilias.to_dict('records') if not subfamilias.empty else []
            }

        return estructura
    
    def consolidate_ciudad_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Consolidar todos los datos por ciudad

        Args:
            data: Diccionario con DataFrames de diferentes fuentes

        Returns:
            DataFrame consolidado con todos los KPIs por ciudad
        """
        logger.info("Consolidando datos por ciudad...")

        # Normalizar los datos antes de consolidar
        normalized_data = {}
        for key, df_data in data.items():
            if not df_data.empty:
                normalized_data[key] = self._normalize_dataframe_columns(df_data, ['ciudad'])
            else:
                normalized_data[key] = df_data

        # Comenzar con el DataFrame base
        df = self._get_base_dataframe(normalized_data, 'ciudad')

        # Agregar ventas históricas
        if 'ventas_historicas' in normalized_data and not normalized_data['ventas_historicas'].empty:
            df = pd.merge(df, normalized_data['ventas_historicas'], on='ciudad', how='outer')

        # Agregar avance actual
        if 'avance_actual' in normalized_data and not normalized_data['avance_actual'].empty:
            df = pd.merge(df, normalized_data['avance_actual'], on='ciudad', how='outer')

        # Agregar presupuestos
        if 'ppto_general' in normalized_data and not normalized_data['ppto_general'].empty:
            df = pd.merge(df, normalized_data['ppto_general'], on='ciudad', how='outer')

        if 'sop' in normalized_data and not normalized_data['sop'].empty:
            df = pd.merge(df, normalized_data['sop'], on='ciudad', how='outer')

        # Agregar proyecciones
        if 'proyecciones' in normalized_data and not normalized_data['proyecciones'].empty:
            df = pd.merge(df, normalized_data['proyecciones'], on='ciudad', how='outer')

        # Agregar ventas semanales
        if 'ventas_semanales' in normalized_data and not normalized_data['ventas_semanales'].empty:
            df = pd.merge(df, normalized_data['ventas_semanales'], on='ciudad', how='left')
        
        # Llenar NaN con 0
        df = df.fillna(0)

        # Calcular PY C9L usando fórmula proporcional (igual que marca)
        # PY C9L = (Avance C9L × PY BOB) / Avance BOB
        avance_c9l_col = f'avance_{self.current_year}_c9l'
        avance_bob_col = f'avance_{self.current_year}_bob'
        py_bob_col = f'py_{self.current_year}_bob'

        if avance_c9l_col in df.columns and avance_bob_col in df.columns and py_bob_col in df.columns:
            df[f'py_{self.current_year}_c9l'] = df.apply(
                lambda row: (row[avance_c9l_col] * row[py_bob_col]) / row[avance_bob_col]
                if row[avance_bob_col] > 0 else 0,
                axis=1
            )
        else:
            df[f'py_{self.current_year}_c9l'] = 0

        # Calcular KPIs
        df = self._calculate_ciudad_kpis(df)
        
        # Ordenar por avance descendente
        avance_col = f'avance_{self.current_year}_bob'
        if avance_col in df.columns:
            df = df.sort_values(avance_col, ascending=False)
        
        # Ordenar ciudades en un orden específico si es necesario
        orden_ciudades = ['Santa Cruz', 'Cochabamba', 'La Paz', 'El Alto',
                         'Tarija', 'Sucre', 'Oruro', 'Potosi', 'Trinidad']

        df['orden'] = df['ciudad'].apply(lambda x: orden_ciudades.index(x)
                                         if x in orden_ciudades else 999)
        df = df.sort_values('orden').drop('orden', axis=1)
        
        logger.info(f"Consolidación completa: {len(df)} ciudades procesadas")
        return df

    def consolidate_ciudad_marca_data(self, data: Dict[str, pd.DataFrame], data_ciudad_marca: Dict[str, pd.DataFrame]) -> Dict:
        """
        Consolidar datos jerárquicos por ciudad y marca directorio

        Args:
            data: Diccionario con DataFrames a nivel ciudad (para totales)
            data_ciudad_marca: Diccionario con DataFrames a nivel ciudad-marca

        Returns:
            Diccionario con estructura jerárquica ciudad -> marca
        """
        logger.info("Consolidando datos jerárquicos por ciudad y marca directorio...")

        # Primero consolidar datos a nivel ciudad (totales)
        df_ciudad = self.consolidate_ciudad_data(data)

        # Normalizar datos de ciudad-marca
        normalized_ciudad_marca = {}
        for key, df_data in data_ciudad_marca.items():
            if not df_data.empty:
                normalized_ciudad_marca[key] = self._normalize_dataframe_columns(df_data, ['ciudad', 'marcadir'])
            else:
                normalized_ciudad_marca[key] = df_data

        # Crear DataFrame base para ciudad-marca
        df_ciudad_marca = pd.DataFrame()

        # Consolidar datos de ciudad-marca
        if 'ventas_historicas_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['ventas_historicas_ciudad_marca'].empty:
            df_ciudad_marca = normalized_ciudad_marca['ventas_historicas_ciudad_marca']

        # Agregar avance actual por ciudad-marca
        if 'avance_actual_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['avance_actual_ciudad_marca'].empty:
            if df_ciudad_marca.empty:
                df_ciudad_marca = normalized_ciudad_marca['avance_actual_ciudad_marca']
            else:
                df_ciudad_marca = pd.merge(df_ciudad_marca, normalized_ciudad_marca['avance_actual_ciudad_marca'],
                                        on=['ciudad', 'marcadir'], how='outer')

        # Agregar presupuestos por ciudad-marca
        if 'ppto_general_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['ppto_general_ciudad_marca'].empty:
            df_ciudad_marca = pd.merge(df_ciudad_marca, normalized_ciudad_marca['ppto_general_ciudad_marca'],
                                    on=['ciudad', 'marcadir'], how='outer')

        if 'sop_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['sop_ciudad_marca'].empty:
            df_ciudad_marca = pd.merge(df_ciudad_marca, normalized_ciudad_marca['sop_ciudad_marca'],
                                    on=['ciudad', 'marcadir'], how='outer')

        # Agregar stock por ciudad-marca
        if 'stock_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['stock_ciudad_marca'].empty:
            df_ciudad_marca = pd.merge(df_ciudad_marca, normalized_ciudad_marca['stock_ciudad_marca'],
                                    on=['ciudad', 'marcadir'], how='left')

        # Agregar venta promedio diaria por ciudad-marca
        if 'venta_promedio_diaria_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['venta_promedio_diaria_ciudad_marca'].empty:
            df_ciudad_marca = pd.merge(df_ciudad_marca,
                                    normalized_ciudad_marca['venta_promedio_diaria_ciudad_marca'][['ciudad', 'marcadir', 'venta_promedio_diaria_c9l']],
                                    on=['ciudad', 'marcadir'], how='left')

        # Agregar proyecciones por ciudad-marca (ENFOQUE HÍBRIDO)
        if 'proyecciones_ciudad_marca' in normalized_ciudad_marca and not normalized_ciudad_marca['proyecciones_ciudad_marca'].empty:
            df_ciudad_marca = pd.merge(df_ciudad_marca, normalized_ciudad_marca['proyecciones_ciudad_marca'],
                                    on=['ciudad', 'marcadir'], how='left')

        # Llenar NaN con 0
        df_ciudad_marca = df_ciudad_marca.fillna(0)

        # Calcular KPIs para ciudad-marca (CON proyecciones)
        df_ciudad_marca = self._calculate_ciudad_marca_kpis(df_ciudad_marca)

        # Ordenar por ciudad y luego por avance descendente
        avance_col = f'avance_{self.current_year}_bob'
        if avance_col in df_ciudad_marca.columns:
            # Primero ordenar por ciudad según el orden establecido
            orden_ciudades = ['Santa Cruz', 'Cochabamba', 'La Paz', 'El Alto',
                             'Tarija', 'Sucre', 'Oruro', 'Potosi', 'Trinidad']
            df_ciudad_marca['orden'] = df_ciudad_marca['ciudad'].apply(
                lambda x: orden_ciudades.index(x) if x in orden_ciudades else 999
            )
            df_ciudad_marca = df_ciudad_marca.sort_values(['orden', avance_col], ascending=[True, False])
            df_ciudad_marca = df_ciudad_marca.drop('orden', axis=1)

        # Crear estructura jerárquica
        resultado = {
            'ciudad_totales': df_ciudad,
            'ciudad_marca': df_ciudad_marca,
            'estructura_jerarquica': self._crear_estructura_jerarquica_ciudad_marca(df_ciudad, df_ciudad_marca)
        }

        logger.info(f"Consolidación jerárquica completa: {len(df_ciudad)} ciudades, {len(df_ciudad_marca)} ciudad-marca")
        return resultado

    def _calculate_ciudad_marca_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular KPIs para datos de ciudad-marca (CON proyecciones híbridas)"""

        # Columnas esperadas
        vendido_col = f'vendido_{self.previous_year}_bob'
        avance_col = f'avance_{self.current_year}_bob'
        py_col = f'py_{self.current_year}_bob'
        vendido_c9l = f'vendido_{self.previous_year}_c9l'
        avance_c9l = f'avance_{self.current_year}_c9l'

        # Calcular KPIs básicos
        if 'ppto_general_bob' in df.columns and avance_col in df.columns:
            df['AV_PG'] = df.apply(lambda x: ((x[avance_col] / x['ppto_general_bob']) - 1)
                                  if x['ppto_general_bob'] > 0 else 0, axis=1)

        if 'sop_bob' in df.columns and avance_col in df.columns:
            df['AV_SOP'] = df.apply(lambda x: ((x[avance_col] / x['sop_bob']) - 1)
                                   if x['sop_bob'] > 0 else 0, axis=1)

        # Calcular PY C9L usando fórmula proporcional: (Avance C9L × PY BOB) / Avance BOB
        py_c9l_col = f'py_{self.current_year}_c9l'
        if avance_c9l in df.columns and py_col in df.columns and avance_col in df.columns:
            df[py_c9l_col] = df.apply(
                lambda x: (x[avance_c9l] * x[py_col]) / x[avance_col]
                if x[avance_col] > 0 else 0,
                axis=1
            )

        # Calcular PY25/V24 usando proyección híbrida
        if vendido_col in df.columns and py_col in df.columns:
            df['PY_V'] = df.apply(lambda x: ((x[py_col] / x[vendido_col]) - 1)
                                 if x[vendido_col] > 0 else 0, axis=1)

        # Calcular PY/SOP - Proyección de Cierre sobre SOP
        if 'sop_bob' in df.columns and py_col in df.columns:
            df['PY_SOP'] = df.apply(lambda x: ((x[py_col] / x['sop_bob']) - 1)
                                    if x['sop_bob'] > 0 else 0, axis=1)

        # Calcular precios
        if vendido_col in df.columns and vendido_c9l in df.columns:
            df[f'precio_{self.previous_year}'] = df.apply(lambda x: x[vendido_col] / x[vendido_c9l]
                                                          if x[vendido_c9l] > 0 else 0, axis=1)

        if avance_col in df.columns and avance_c9l in df.columns:
            df[f'precio_{self.current_year}'] = df.apply(lambda x: x[avance_col] / x[avance_c9l]
                                                         if x[avance_c9l] > 0 else 0, axis=1)

        # Incremento de precio
        precio_prev = f'precio_{self.previous_year}'
        precio_curr = f'precio_{self.current_year}'
        if precio_prev in df.columns and precio_curr in df.columns:
            df['inc_precio'] = df.apply(lambda x: ((x[precio_curr] / x[precio_prev]) - 1)
                                       if x[precio_prev] > 0 else 0, axis=1)

        # Cobertura
        if 'stock_c9l' in df.columns and 'venta_promedio_diaria_c9l' in df.columns:
            df['cobertura_dias'] = df.apply(lambda x: x['stock_c9l'] / x['venta_promedio_diaria_c9l']
                                           if x['venta_promedio_diaria_c9l'] > 0 else 0, axis=1)

        return df

    def _crear_estructura_jerarquica_ciudad_marca(self, df_ciudad: pd.DataFrame, df_ciudad_marca: pd.DataFrame) -> Dict:
        """
        Crear estructura jerárquica para facilitar la renderización

        Returns:
            Diccionario con estructura ciudad -> marcas
        """
        estructura = {}

        for _, ciudad_row in df_ciudad.iterrows():
            ciudad = ciudad_row['ciudad']

            # Obtener marcas para esta ciudad
            marcas = df_ciudad_marca[df_ciudad_marca['ciudad'] == ciudad]

            estructura[ciudad] = {
                'datos_ciudad': ciudad_row.to_dict(),
                'marcas': marcas.to_dict('records') if not marcas.empty else []
            }

        return estructura

    def consolidate_canal_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Consolidar todos los datos por canal

        Args:
            data: Diccionario con DataFrames de diferentes fuentes

        Returns:
            DataFrame consolidado con todos los KPIs por canal
        """
        logger.info("Consolidando datos por canal...")

        # Normalizar los datos antes de consolidar
        normalized_data = {}
        for key, df_data in data.items():
            if not df_data.empty:
                normalized_data[key] = self._normalize_dataframe_columns(df_data, ['canal'])
            else:
                normalized_data[key] = df_data

        # Comenzar con el DataFrame base
        df = self._get_base_dataframe(normalized_data, 'canal')

        # Agregar ventas históricas
        if 'ventas_historicas' in normalized_data and not normalized_data['ventas_historicas'].empty:
            df = pd.merge(df, normalized_data['ventas_historicas'], on='canal', how='outer')

        # Agregar avance actual
        if 'avance_actual' in normalized_data and not normalized_data['avance_actual'].empty:
            df = pd.merge(df, normalized_data['avance_actual'], on='canal', how='outer')

        # Agregar presupuestos
        if 'ppto_general' in normalized_data and not normalized_data['ppto_general'].empty:
            df = pd.merge(df, normalized_data['ppto_general'], on='canal', how='outer')

        if 'sop' in normalized_data and not normalized_data['sop'].empty:
            df = pd.merge(df, normalized_data['sop'], on='canal', how='outer')

        # Agregar proyecciones calculadas por multiplicador
        if 'proyecciones_canal' in normalized_data and not normalized_data['proyecciones_canal'].empty:
            py_col = f'py_{self.current_year}_bob'
            df = pd.merge(df, normalized_data['proyecciones_canal'][['canal', py_col]],
                         on='canal', how='left')

        # Agregar ventas semanales
        if 'ventas_semanales' in normalized_data and not normalized_data['ventas_semanales'].empty:
            df = pd.merge(df, normalized_data['ventas_semanales'], on='canal', how='left')
        
        # Llenar NaN con 0
        df = df.fillna(0)

        # Calcular PY C9L usando fórmula proporcional (igual que marca)
        # PY C9L = (Avance C9L × PY BOB) / Avance BOB
        avance_c9l_col = f'avance_{self.current_year}_c9l'
        avance_bob_col = f'avance_{self.current_year}_bob'
        py_bob_col = f'py_{self.current_year}_bob'

        if avance_c9l_col in df.columns and avance_bob_col in df.columns and py_bob_col in df.columns:
            df[f'py_{self.current_year}_c9l'] = df.apply(
                lambda row: (row[avance_c9l_col] * row[py_bob_col]) / row[avance_bob_col]
                if row[avance_bob_col] > 0 else 0,
                axis=1
            )
        else:
            df[f'py_{self.current_year}_c9l'] = 0

        # Calcular KPIs
        df = self._calculate_canal_kpis(df)
        
        # Ordenar por avance descendente
        avance_col = f'avance_{self.current_year}_bob'
        if avance_col in df.columns:
            df = df.sort_values(avance_col, ascending=False)
        
        logger.info(f"Consolidación completa: {len(df)} canales procesados")
        return df
    
    def _normalize_string(self, value):
        """Normalizar strings para evitar duplicados por capitalización"""
        if pd.isna(value):
            return value
        return str(value).strip().title()

    def _normalize_dataframe_columns(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Normalizar columnas específicas en un DataFrame"""
        df_copy = df.copy()
        for col in columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(self._normalize_string)
        return df_copy

    def _get_base_dataframe(self, data: Dict[str, pd.DataFrame], tipo: str) -> pd.DataFrame:
        """Obtener DataFrame base según el tipo"""
        column_name = {'marca': 'marcadir', 'ciudad': 'ciudad', 'canal': 'canal'}[tipo]

        # Recopilar todos los valores únicos de todas las fuentes
        all_values = set()

        for key in ['ventas_historicas', 'avance_actual', 'ppto_general', 'sop', 'proyecciones', 'ventas_semanales']:
            if key in data and not data[key].empty and column_name in data[key].columns:
                # Normalizar valores antes de agregarlos al conjunto
                normalized_values = data[key][column_name].apply(self._normalize_string).dropna().unique()
                all_values.update(normalized_values)

        # Si no hay valores, retornar DataFrame vacío
        if not all_values:
            return pd.DataFrame({column_name: []})

        # Crear DataFrame con valores únicos normalizados
        return pd.DataFrame({column_name: sorted(list(all_values))})
    
    def _calculate_marca_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular KPIs específicos para marcas"""
        year = self.current_year
        prev_year = self.previous_year
        
        # Columnas esperadas
        vendido_col = f'vendido_{prev_year}_bob'
        vendido_c9l_col = f'vendido_{prev_year}_c9l'
        avance_col = f'avance_{year}_bob'
        avance_c9l_col = f'avance_{year}_c9l'
        py_col = f'py_{year}_bob'
        
        # Calcular precios promedio
        if vendido_col in df.columns and vendido_c9l_col in df.columns:
            df[f'precio_{prev_year}'] = (df[vendido_col] / df[vendido_c9l_col]).replace([np.inf, -np.inf], 0)
        
        if avance_col in df.columns and avance_c9l_col in df.columns:
            df[f'precio_{year}'] = (df[avance_col] / df[avance_c9l_col]).replace([np.inf, -np.inf], 0)
        
        # Incremento de precio
        precio_prev = f'precio_{prev_year}'
        precio_curr = f'precio_{year}'
        if precio_prev in df.columns and precio_curr in df.columns:
            df['inc_precio'] = ((df[precio_curr] / df[precio_prev]) - 1).replace([np.inf, -np.inf], 0)
        
        # KPIs de performance
        if avance_col in df.columns:
            if 'ppto_general_bob' in df.columns:
                df['AV_PG'] = ((df[avance_col] / df['ppto_general_bob']) - 1).replace([np.inf, -np.inf], 0)
            
            if 'sop_bob' in df.columns:
                df['AV_SOP'] = ((df[avance_col] / df['sop_bob']) - 1).replace([np.inf, -np.inf], 0)
        
        if py_col in df.columns and vendido_col in df.columns:
            df['PY_V'] = ((df[py_col] / df[vendido_col]) - 1).replace([np.inf, -np.inf], 0)

        # PY/SOP - Proyección de Cierre sobre SOP
        if py_col in df.columns and 'sop_bob' in df.columns:
            df['PY_SOP'] = ((df[py_col] / df['sop_bob']) - 1).replace([np.inf, -np.inf], 0)

        # Cobertura de stock
        if 'stock_c9l' in df.columns and 'venta_promedio_diaria_c9l' in df.columns:
            df['cobertura_dias'] = (df['stock_c9l'] / df['venta_promedio_diaria_c9l']).replace([np.inf, -np.inf], 0)
        
        # KPIs para C9L
        if avance_c9l_col in df.columns:
            if 'ppto_general_c9l' in df.columns:
                df['AV_PG_C9L'] = ((df[avance_c9l_col] / df['ppto_general_c9l']) - 1).replace([np.inf, -np.inf], 0)
            
            if 'sop_c9l' in df.columns:
                df['AV_SOP_C9L'] = ((df[avance_c9l_col] / df['sop_c9l']) - 1).replace([np.inf, -np.inf], 0)
        
        return df
    
    def _calculate_ciudad_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular KPIs específicos para ciudades"""
        year = self.current_year
        prev_year = self.previous_year
        
        # Columnas esperadas
        vendido_col = f'vendido_{prev_year}_bob'
        avance_col = f'avance_{year}_bob'
        py_col = f'py_{year}_bob'
        
        # KPIs de performance BOB
        if avance_col in df.columns:
            if 'ppto_general_bob' in df.columns:
                df['AV_PG'] = ((df[avance_col] / df['ppto_general_bob']) - 1).replace([np.inf, -np.inf], 0)
            
            if 'sop_bob' in df.columns:
                df['AV_SOP'] = ((df[avance_col] / df['sop_bob']) - 1).replace([np.inf, -np.inf], 0)
        
        if py_col in df.columns and vendido_col in df.columns:
            df['PY_V'] = ((df[py_col] / df[vendido_col]) - 1).replace([np.inf, -np.inf], 0)

        # PY/SOP - Proyección de Cierre sobre SOP
        if py_col in df.columns and 'sop_bob' in df.columns:
            df['PY_SOP'] = ((df[py_col] / df['sop_bob']) - 1).replace([np.inf, -np.inf], 0)

        # KPIs para C9L
        vendido_c9l_col = f'vendido_{prev_year}_c9l'
        avance_c9l_col = f'avance_{year}_c9l'
        py_c9l_col = f'py_{year}_c9l'
        
        if avance_c9l_col in df.columns:
            if 'ppto_general_c9l' in df.columns:
                df['AV_PG_C9L'] = ((df[avance_c9l_col] / df['ppto_general_c9l']) - 1).replace([np.inf, -np.inf], 0)
            
            if 'sop_c9l' in df.columns:
                df['AV_SOP_C9L'] = ((df[avance_c9l_col] / df['sop_c9l']) - 1).replace([np.inf, -np.inf], 0)
        
        if py_c9l_col in df.columns and vendido_c9l_col in df.columns:
            df['PY_V_C9L'] = ((df[py_c9l_col] / df[vendido_c9l_col]) - 1).replace([np.inf, -np.inf], 0)
        
        return df
    
    def _calculate_canal_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular KPIs específicos para canales"""
        # Misma lógica que ciudades
        return self._calculate_ciudad_kpis(df)
    
    def calculate_executive_summary(self, marcas_df: pd.DataFrame, 
                                   ciudades_df: pd.DataFrame, 
                                   canales_df: pd.DataFrame) -> Dict:
        """
        Calcular métricas para el resumen ejecutivo
        
        Args:
            marcas_df: DataFrame consolidado de marcas
            ciudades_df: DataFrame consolidado de ciudades
            canales_df: DataFrame consolidado de canales
            
        Returns:
            Diccionario con métricas del resumen ejecutivo
        """
        year = self.current_year
        prev_year = self.previous_year
        
        summary = {
            'fecha_generacion': self.current_date.strftime('%d/%m/%Y'),
            'mes': self.current_month,
            'año': year,
            'dia_actual': self.current_day
        }
        
        # Calcular totales desde marcas
        if not marcas_df.empty:
            avance_col = f'avance_{year}_bob'
            vendido_col = f'vendido_{prev_year}_bob'
            py_col = f'py_{year}_bob'
            
            summary['total_avance'] = marcas_df[avance_col].sum() if avance_col in marcas_df else 0
            summary['total_vendido_anterior'] = marcas_df[vendido_col].sum() if vendido_col in marcas_df else 0
            summary['total_py'] = marcas_df[py_col].sum() if py_col in marcas_df else 0
            summary['total_ppto_general'] = marcas_df['ppto_general_bob'].sum() if 'ppto_general_bob' in marcas_df else 0
            summary['total_sop'] = marcas_df['sop_bob'].sum() if 'sop_bob' in marcas_df else 0
            
            # KPIs principales
            if summary['total_ppto_general'] > 0:
                summary['av_pg'] = (summary['total_avance'] / summary['total_ppto_general']) - 1
            else:
                summary['av_pg'] = 0
            
            if summary['total_sop'] > 0:
                summary['av_sop'] = (summary['total_avance'] / summary['total_sop']) - 1
            else:
                summary['av_sop'] = 0
            
            if summary['total_vendido_anterior'] > 0:
                summary['py_v24'] = (summary['total_py'] / summary['total_vendido_anterior']) - 1
            else:
                summary['py_v24'] = 0
            
            # Análisis de stock
            if 'cobertura_dias' in marcas_df:
                marcas_criticas = marcas_df[marcas_df['cobertura_dias'] < 15]['marcadir'].tolist()
                marcas_exceso = marcas_df[marcas_df['cobertura_dias'] > 180]['marcadir'].tolist()
                summary['marcas_stock_critico'] = marcas_criticas[:5]  # Top 5
                summary['marcas_stock_exceso'] = marcas_exceso[:5]  # Top 5
            
            # Top performers
            if 'PY_V' in marcas_df:
                top_crecimiento = marcas_df.nlargest(3, 'PY_V')[['marcadir', 'PY_V']].to_dict('records')
                summary['top_crecimiento'] = top_crecimiento
                
                bottom_crecimiento = marcas_df.nsmallest(3, 'PY_V')[['marcadir', 'PY_V']].to_dict('records')
                summary['bottom_crecimiento'] = bottom_crecimiento
        
        # Análisis por ciudad
        if not ciudades_df.empty and 'AV_SOP' in ciudades_df:
            mejor_ciudad = ciudades_df.nlargest(1, 'AV_SOP').iloc[0]
            peor_ciudad = ciudades_df.nsmallest(1, 'AV_SOP').iloc[0]
            
            summary['mejor_ciudad'] = {
                'nombre': mejor_ciudad['ciudad'],
                'av_sop': mejor_ciudad['AV_SOP']
            }
            summary['peor_ciudad'] = {
                'nombre': peor_ciudad['ciudad'],
                'av_sop': peor_ciudad['AV_SOP']
            }
        
        # Análisis por canal
        if not canales_df.empty and 'AV_SOP' in canales_df:
            mejor_canal = canales_df.nlargest(1, 'AV_SOP').iloc[0]
            summary['mejor_canal'] = {
                'nombre': mejor_canal['canal'],
                'av_sop': mejor_canal['AV_SOP']
            }
        
        return summary
    
    def generate_comentarios_analysis(self, comentarios_df: pd.DataFrame) -> str:
        """
        Generar análisis de comentarios de gerentes
        
        Args:
            comentarios_df: DataFrame con comentarios de gerentes
            
        Returns:
            Texto con análisis de comentarios
        """
        if comentarios_df.empty:
            return "No hay comentarios disponibles de los gerentes para este período."
        
        # Agrupar comentarios por gerente/ciudad
        analisis = []
        
        for usuario in comentarios_df['usuario'].unique():
            df_usuario = comentarios_df[comentarios_df['usuario'] == usuario]
            ciudades = df_usuario['ciudad'].unique()
            
            # Consolidar comentarios no vacíos
            comentarios_relevantes = []
            
            for _, row in df_usuario.iterrows():
                for semana in ['com_s1', 'com_s2', 'com_s3', 'com_s4', 'com_s5']:
                    if row[semana] and len(row[semana].strip()) > 0:
                        comentarios_relevantes.append({
                            'marca': row['nombre_marca'],
                            'ciudad': row['ciudad'],
                            'comentario': row[semana],
                            'semana': semana.replace('com_s', 'Semana ')
                        })
            
            if comentarios_relevantes:
                gerente_nombre = self._get_gerente_nombre(usuario)
                ciudades_str = ', '.join(ciudades)
                
                # Extraer temas principales
                temas = self._extract_temas_principales(comentarios_relevantes)
                
                if temas:
                    analisis.append(f"En {ciudades_str}, {gerente_nombre} reporta: {'. '.join(temas)}")
        
        if not analisis:
            return "Los gerentes no reportaron situaciones especiales en sus proyecciones para este período."
        
        return " ".join(analisis)
    
    def _get_gerente_nombre(self, usuario: str) -> str:
        """Mapear usuario a nombre de gerente"""
        gerentes = {
            'jvelasco': 'Jvelasco',
            'mvillafane': 'Mvillafane',
            'mcabrerizo': 'Mvillafane',
            'jblacutt': 'Jblacutt',
            'ppelaez': 'Ppelaez'
        }
        return gerentes.get(usuario.lower(), usuario)
    
    def _extract_temas_principales(self, comentarios: list) -> list:
        """Extraer temas principales de los comentarios"""
        temas = []
        palabras_clave = {
            'cupeo': 'cupeo limitando distribución',
            'contrabando': 'competencia del contrabando afectando precios',
            'quiebre': 'quiebres de stock',
            'precio': 'ajustes de precio afectando rotación',
            'feria': 'inicio de feria comercial',
            'rotacion': 'cambios en rotación de productos',
            'stock': 'situaciones de inventario',
            'competencia': 'presión competitiva'
        }
        
        # Analizar comentarios y extraer temas
        temas_encontrados = set()
        marcas_afectadas = set()
        
        for item in comentarios:
            comentario_lower = item['comentario'].lower()
            marca = item['marca']
            
            for palabra, descripcion in palabras_clave.items():
                if palabra in comentario_lower:
                    temas_encontrados.add(descripcion)
                    marcas_afectadas.add(marca)
        
        # Construir resumen
        if temas_encontrados:
            temas_str = list(temas_encontrados)
            if len(marcas_afectadas) <= 3:
                marcas_str = f" afectando a {', '.join(list(marcas_afectadas)[:3])}"
            else:
                marcas_str = f" afectando a {len(marcas_afectadas)} marcas"
            
            for tema in temas_str[:3]:  # Máximo 3 temas principales
                temas.append(tema + marcas_str)
        
        return temas

    def process_hitrate_data(self, hitrate_mensual: pd.DataFrame, hitrate_ytd: pd.DataFrame,
                             hitrate_ciudad: pd.DataFrame, hitrate_ciudad_historico: pd.DataFrame) -> Dict:
        """
        Procesar datos de Hit Rate y Eficiencia para el reporte

        Args:
            hitrate_mensual: DataFrame con Hit Rate mensual
            hitrate_ytd: DataFrame con Hit Rate YTD
            hitrate_ciudad: DataFrame con Hit Rate por ciudad del mes actual
            hitrate_ciudad_historico: DataFrame con Hit Rate histórico por ciudad

        Returns:
            Diccionario con datos procesados para visualización
        """
        logger.info("Procesando datos de Hit Rate y Eficiencia...")

        resultado = {
            'mensual': self._process_hitrate_mensual(hitrate_mensual),
            'ytd': self._process_hitrate_ytd(hitrate_ytd),
            'ciudad_actual': self._process_hitrate_ciudad(hitrate_ciudad),
            'ciudad_historico': self._process_hitrate_ciudad_historico(hitrate_ciudad_historico),
            'summary_metrics': self._calculate_hitrate_summary(hitrate_mensual, hitrate_ytd)
        }

        return resultado

    def _process_hitrate_mensual(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesar datos mensuales de Hit Rate"""
        if df.empty:
            return df

        # Asegurar que las columnas numéricas sean float
        numeric_cols = ['clientes_totales', 'clientes_contactados', 'clientes_con_venta', 'eficiencia', 'hit_rate']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Calcular efectividad total
        df['efectividad_total'] = (df['eficiencia'] * df['hit_rate']) / 100

        # Agregar indicadores de tendencia
        if len(df) > 1:
            df['tendencia_hitrate'] = df['hit_rate'].diff()
            df['tendencia_eficiencia'] = df['eficiencia'].diff()

        return df

    def _process_hitrate_ytd(self, df: pd.DataFrame) -> Dict:
        """Procesar datos YTD de Hit Rate"""
        if df.empty:
            return {
                'eficiencia': 0,
                'hit_rate': 0,
                'clientes_totales': 0,
                'clientes_contactados': 0,
                'clientes_con_venta': 0
            }

        row = df.iloc[0]
        return {
            'eficiencia': row.get('eficiencia', 0),
            'hit_rate': row.get('hit_rate', 0),
            'clientes_totales': int(row.get('clientes_totales', 0)),
            'clientes_contactados': int(row.get('clientes_contactados', 0)),
            'clientes_con_venta': int(row.get('clientes_con_venta', 0))
        }

    def _process_hitrate_ciudad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesar datos de Hit Rate por ciudad"""
        if df.empty:
            return df

        # Asegurar que las columnas numéricas sean float
        numeric_cols = ['clientes_totales', 'clientes_contactados', 'clientes_con_venta', 'eficiencia', 'hit_rate']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Calcular efectividad total
        df['efectividad_total'] = (df['eficiencia'] * df['hit_rate']) / 100

        # Clasificar performance
        df['performance_hitrate'] = df['hit_rate'].apply(self._classify_hitrate_performance)
        df['performance_eficiencia'] = df['eficiencia'].apply(self._classify_eficiencia_performance)

        return df

    def _process_hitrate_ciudad_historico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesar datos históricos de Hit Rate por ciudad"""
        if df.empty:
            return df

        # Asegurar que las columnas numéricas sean float
        numeric_cols = ['clientes_totales', 'clientes_contactados', 'clientes_con_venta', 'eficiencia', 'hit_rate']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Pivotar para crear matriz ciudad x mes
        df_pivot_hitrate = df.pivot_table(
            index='ciudad',
            columns='mes_visita',
            values='hit_rate',
            aggfunc='mean'
        ).fillna(0)

        df_pivot_eficiencia = df.pivot_table(
            index='ciudad',
            columns='mes_visita',
            values='eficiencia',
            aggfunc='mean'
        ).fillna(0)

        return {
            'hitrate_matrix': df_pivot_hitrate,
            'eficiencia_matrix': df_pivot_eficiencia
        }

    def _calculate_hitrate_summary(self, df_mensual: pd.DataFrame, ytd_data: pd.DataFrame) -> Dict:
        """Calcular métricas resumen de Hit Rate"""
        if df_mensual.empty:
            return {
                'promedio_hitrate': 0,
                'promedio_eficiencia': 0,
                'mejor_mes_hitrate': 'N/D',
                'mejor_mes_eficiencia': 'N/D',
                'tendencia_general': 'Sin datos'
            }

        # Calcular promedios
        promedio_hitrate = df_mensual['hit_rate'].mean()
        promedio_eficiencia = df_mensual['eficiencia'].mean()

        # Identificar mejores meses
        mejor_mes_hitrate_idx = df_mensual['hit_rate'].idxmax()
        mejor_mes_eficiencia_idx = df_mensual['eficiencia'].idxmax()

        mejor_mes_hitrate = df_mensual.loc[mejor_mes_hitrate_idx, 'mes'] if not pd.isna(mejor_mes_hitrate_idx) else 'N/D'
        mejor_mes_eficiencia = df_mensual.loc[mejor_mes_eficiencia_idx, 'mes'] if not pd.isna(mejor_mes_eficiencia_idx) else 'N/D'

        # Determinar tendencia general
        if len(df_mensual) >= 3:
            ultimos_3_meses = df_mensual.tail(3)
            tendencia_hitrate = ultimos_3_meses['hit_rate'].iloc[-1] - ultimos_3_meses['hit_rate'].iloc[0]
            if tendencia_hitrate > 2:
                tendencia_general = 'Mejorando'
            elif tendencia_hitrate < -2:
                tendencia_general = 'Declinando'
            else:
                tendencia_general = 'Estable'
        else:
            tendencia_general = 'Datos insuficientes'

        return {
            'promedio_hitrate': promedio_hitrate,
            'promedio_eficiencia': promedio_eficiencia,
            'mejor_mes_hitrate': mejor_mes_hitrate,
            'mejor_mes_eficiencia': mejor_mes_eficiencia,
            'tendencia_general': tendencia_general
        }

    def _classify_hitrate_performance(self, value):
        """Clasificar performance de Hit Rate"""
        if value >= 80:
            return 'Excelente'
        elif value >= 70:
            return 'Bueno'
        elif value >= 60:
            return 'Regular'
        else:
            return 'Deficiente'

    def _classify_eficiencia_performance(self, value):
        """Clasificar performance de Eficiencia"""
        if value >= 90:
            return 'Excelente'
        elif value >= 80:
            return 'Bueno'
        elif value >= 70:
            return 'Regular'
        else:
            return 'Deficiente'