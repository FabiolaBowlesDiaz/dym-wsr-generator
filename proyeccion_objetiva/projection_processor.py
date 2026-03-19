"""
Orquestador de Proyección Objetiva
Ejecuta ambos motores (estadístico y operativo), merge con PY Gerente,
y prepara datos para el Resumen Ejecutivo (Sección 4) del WSR.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from datetime import datetime

from . import config as cfg
from .data_fetcher import ProjectionDataFetcher
from .pilar2_estadistica.statistical_engine import StatisticalEngine
from .pilar3_operativa.drivers_engine import DriversEngine

logger = logging.getLogger(__name__)


class ProjectionProcessor:
    """
    Orquesta la generación de proyecciones objetivas para el WSR.

    Flujo:
      1. Obtiene datos históricos del DWH
      2. Ejecuta motor estadístico (Holt-Winters) → PY Estadística
      3. Ejecuta motor operativo (Drivers) → diagnóstico operativo
      4. Prepara datos para Resumen Ejecutivo (gráfica + tabla)
    """

    def __init__(self, db_manager, current_date: datetime, schema: str = 'auto'):
        self.db_manager = db_manager
        self.current_date = current_date
        self.schema = schema

        self.data_fetcher = ProjectionDataFetcher(db_manager, schema)
        self.stat_engine = StatisticalEngine(
            target_year=current_date.year,
            target_month=current_date.month
        )
        self.drivers_engine = DriversEngine(db_manager, schema, current_date)

    def generate_projections(
        self,
        py_gerente_marca: Optional[pd.DataFrame] = None,
        py_gerente_ciudad: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Genera todas las proyecciones objetivas.

        Returns:
            Dict con claves para HW por nivel, drivers, y datos históricos nacionales
            para el Resumen Ejecutivo.
        """
        # 1. Obtener datos del DWH
        logger.info("[Proyeccion Objetiva] Obteniendo datos...")
        data = self.data_fetcher.fetch_all()

        # 2. Motor Estadístico - BOB
        logger.info("[Proyeccion Objetiva] Ejecutando motor estadistico...")
        py_est_marca = self.stat_engine.run_by_marca(data['ventas_historicas'])
        py_est_ciudad = self.stat_engine.run_by_ciudad(data['ventas_historicas'])
        py_est_subfamilia = self.stat_engine.run_by_subfamilia(data['ventas_historicas_subfamilia'])
        py_est_canal = self.stat_engine.run_by_canal(data['ventas_historicas_canal'])
        py_est_ciudad_marca = self.stat_engine.run_by_ciudad_marca(data['ventas_historicas'])

        # 2b. Motor Estadístico - C9L
        logger.info("[Proyeccion Objetiva] Ejecutando motor estadistico C9L...")
        py_est_marca_c9l = self.stat_engine.run_by_marca(data['ventas_historicas'], value_col='venta_c9l')
        py_est_ciudad_c9l = self.stat_engine.run_by_ciudad(data['ventas_historicas'], value_col='venta_c9l')
        py_est_subfamilia_c9l = self.stat_engine.run_by_subfamilia(data['ventas_historicas_subfamilia'], value_col='venta_c9l')
        py_est_canal_c9l = self.stat_engine.run_by_canal(data['ventas_historicas_canal'], value_col='venta_c9l')
        py_est_ciudad_marca_c9l = self.stat_engine.run_by_ciudad_marca(data['ventas_historicas'], value_col='venta_c9l')

        # 3. Motor Operativo (Drivers de Performance)
        logger.info("[Proyeccion Objetiva] Ejecutando motor de drivers operativos...")
        drivers_data = {}
        try:
            drivers_data = self.drivers_engine.calculate_all()
            logger.info(f"[Drivers] {len(drivers_data.get('by_marca', []))} marcas, "
                        f"{len(drivers_data.get('by_ciudad', []))} ciudades")
        except Exception as e:
            logger.warning(f"[Drivers] Error calculando drivers operativos: {e}")

        # 4. Datos históricos nacionales para gráfica ejecutiva
        historico_nacional = {
            'ventas_nacionales': data.get('ventas_nacionales', pd.DataFrame()),
            'sop_nacional': data.get('sop_nacional', pd.DataFrame()),
            'py_gerente_nacional': data.get('py_gerente_nacional', pd.DataFrame()),
        }

        logger.info("[Proyeccion Objetiva] Proyecciones generadas exitosamente")

        return {
            # HW por nivel (usados en tablas de performance Secciones 1-3)
            'est_by_marca': py_est_marca,
            'est_by_ciudad': py_est_ciudad,
            'est_by_subfamilia': py_est_subfamilia,
            'est_by_canal': py_est_canal,
            'est_by_ciudad_marca': py_est_ciudad_marca,
            'est_by_marca_c9l': py_est_marca_c9l,
            'est_by_subfamilia_c9l': py_est_subfamilia_c9l,
            'est_by_canal_c9l': py_est_canal_c9l,
            'est_by_ciudad_c9l': py_est_ciudad_c9l,
            'est_by_ciudad_marca_c9l': py_est_ciudad_marca_c9l,
            # Drivers (usados en tablas de performance Secciones 1-3)
            'drivers_data': drivers_data,
            # Datos para Sección 4: Resumen Ejecutivo
            'historico_nacional': historico_nacional,
            'schema_validation': data['schema_validation'],
        }
