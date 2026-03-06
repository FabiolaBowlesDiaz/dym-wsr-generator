"""
Orquestador de Proyección Objetiva
Ejecuta ambos motores (estadístico y operativo), merge con PY Gerente,
y calcula spread/diagnóstico para el WSR.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from datetime import datetime

from . import config as cfg
from .data_fetcher import ProjectionDataFetcher
from .pilar2_estadistica.statistical_engine import StatisticalEngine
from .pilar3_operativa.decomposition_engine import RevenueTreeEngine

logger = logging.getLogger(__name__)


class ProjectionProcessor:
    """
    Orquesta la generación de proyecciones objetivas para el WSR.

    Flujo:
      1. Obtiene datos históricos del DWH
      2. Ejecuta motor estadístico (Holt-Winters) → PY Estadística
      3. Ejecuta motor operativo (Cob × HR × DS) → PY Operativa
      4. Merge con PY Gerente (ya disponible en el WSR)
      5. Calcula spread y diagnóstico
    """

    def __init__(self, db_manager, current_date: datetime, schema: str = 'auto'):
        """
        Args:
            db_manager: DatabaseManager del WSR (ya conectado)
            current_date: Fecha actual del reporte
            schema: Schema del DWH
        """
        self.db_manager = db_manager
        self.current_date = current_date
        self.schema = schema

        self.data_fetcher = ProjectionDataFetcher(db_manager, schema)
        # El motor estadístico recibe año/mes target para ajuste por eventos móviles
        self.stat_engine = StatisticalEngine(
            target_year=current_date.year,
            target_month=current_date.month
        )
        self.decomp_engine = RevenueTreeEngine()

    def generate_projections(
        self,
        py_gerente_marca: Optional[pd.DataFrame] = None,
        py_gerente_ciudad: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Genera todas las proyecciones objetivas.

        Args:
            py_gerente_marca: DataFrame del WSR con PY del gerente por marca
                              (columna esperada: py_{year}_bob)
            py_gerente_ciudad: DataFrame del WSR con PY del gerente por ciudad

        Returns:
            Dict con:
              - 'by_marca': DataFrame comparativo triple pilar por marca
              - 'by_ciudad': DataFrame comparativo triple pilar por ciudad
              - 'decomposition_ciudad': DataFrame con Cob/HR/DS por ciudad
              - 'decomposition_marca': DataFrame con Cob/HR/DS por marca
              - 'resumen_nacional': Dict con totales nacionales
              - 'schema_validation': Resultado de validación FactVentas
        """
        # 1. Obtener datos del DWH
        logger.info("📊 [Proyección Objetiva] Obteniendo datos...")
        data = self.data_fetcher.fetch_all()

        # 2. Motor Estadístico
        logger.info("📈 [Proyección Objetiva] Ejecutando motor estadístico...")
        py_est_marca = self.stat_engine.run_by_marca(data['ventas_historicas'])
        py_est_ciudad = self.stat_engine.run_by_ciudad(data['ventas_historicas'])
        py_est_subfamilia = self.stat_engine.run_by_subfamilia(data['ventas_historicas_subfamilia'])
        py_est_canal = self.stat_engine.run_by_canal(data['ventas_historicas_canal'])
        py_est_ciudad_marca = self.stat_engine.run_by_ciudad_marca(data['ventas_historicas'])

        # 3. Motor Operativo
        logger.info("🎯 [Proyección Objetiva] Ejecutando motor operativo...")
        py_op_marca = self.decomp_engine.run_by_marca(
            data['cobertura'], data['hitrate'], data['dropsize']
        )
        py_op_ciudad = self.decomp_engine.run_by_ciudad(
            data['cobertura'], data['hitrate'], data['dropsize']
        )

        # 4. Merge con PY Gerente y calcular comparativos
        year = self.current_date.year
        py_col = f'py_{year}_bob'

        comparativo_marca = self._build_comparativo(
            py_gerente=py_gerente_marca,
            py_estadistica=py_est_marca,
            py_operativa=py_op_marca,
            key_col='marcadir',
            py_col=py_col
        )

        comparativo_ciudad = self._build_comparativo(
            py_gerente=py_gerente_ciudad,
            py_estadistica=py_est_ciudad,
            py_operativa=py_op_ciudad,
            key_col='ciudad',
            py_col=py_col
        )

        # 5. Resumen nacional
        resumen = self._calculate_resumen_nacional(
            comparativo_marca, comparativo_ciudad
        )

        logger.info("✅ [Proyección Objetiva] Proyecciones generadas exitosamente")

        return {
            'by_marca': comparativo_marca,
            'by_ciudad': comparativo_ciudad,
            'decomposition_ciudad': py_op_ciudad,
            'decomposition_marca': py_op_marca,
            'resumen_nacional': resumen,
            'schema_validation': data['schema_validation'],
            'est_by_subfamilia': py_est_subfamilia,
            'est_by_canal': py_est_canal,
            'est_by_ciudad_marca': py_est_ciudad_marca,
        }

    def _build_comparativo(
        self,
        py_gerente: Optional[pd.DataFrame],
        py_estadistica: pd.DataFrame,
        py_operativa: pd.DataFrame,
        key_col: str,
        py_col: str
    ) -> pd.DataFrame:
        """
        Construye tabla comparativa triple pilar con spread y diagnóstico.

        Args:
            py_gerente: DataFrame del WSR con PY del gerente
            py_estadistica: DataFrame del motor estadístico
            py_operativa: DataFrame del motor operativo
            key_col: Columna clave ('marcadir' o 'ciudad')
            py_col: Nombre de la columna de PY gerente (ej: 'py_2026_bob')

        Returns:
            DataFrame con todas las proyecciones lado a lado
        """
        # Empezar con PY Estadística (incluir event info si existe)
        cols_to_keep = [key_col, 'py_estadistica_bob', 'model_type', 'confidence']
        for extra_col in ['event_adjustment', 'event_factor', 'py_estadistica_bob_raw']:
            if extra_col in py_estadistica.columns:
                cols_to_keep.append(extra_col)
        result = py_estadistica[cols_to_keep].copy()

        # Merge PY Operativa
        op_col = 'py_operativa_bob'
        if not py_operativa.empty and key_col in py_operativa.columns:
            result = result.merge(
                py_operativa[[key_col, op_col]],
                on=key_col,
                how='outer'
            )
        else:
            result[op_col] = None

        # Merge PY Gerente
        if py_gerente is not None and not py_gerente.empty:
            ger_df = py_gerente.copy()

            # Normalizar nombre de columna clave
            if key_col not in ger_df.columns:
                # Intentar encontrar columna equivalente
                for col in ger_df.columns:
                    if col.lower() in [key_col.lower(), 'marca', 'marcadirectorio']:
                        ger_df = ger_df.rename(columns={col: key_col})
                        break

            if key_col in ger_df.columns and py_col in ger_df.columns:
                result = result.merge(
                    ger_df[[key_col, py_col]].rename(
                        columns={py_col: 'py_gerente_bob'}
                    ),
                    on=key_col,
                    how='outer'
                )
            else:
                result['py_gerente_bob'] = None
        else:
            result['py_gerente_bob'] = None

        # Calcular spread y diagnóstico
        result['spread'] = self._calculate_spread(
            result.get('py_gerente_bob'),
            result.get('py_estadistica_bob')
        )
        result['diagnostico'] = result['spread'].apply(self._diagnose_spread)

        # Ordenar por PY Estadística descendente
        result = result.sort_values('py_estadistica_bob', ascending=False, na_position='last')

        return result

    def _calculate_spread(
        self,
        py_gerente: Optional[pd.Series],
        py_estadistica: Optional[pd.Series]
    ) -> pd.Series:
        """Calcula spread = (PY_Gerente / PY_Estadística) - 1"""
        if py_gerente is None or py_estadistica is None:
            return pd.Series([None] * len(py_estadistica) if py_estadistica is not None else [])

        return np.where(
            (py_estadistica.notna()) & (py_estadistica > 0) & (py_gerente.notna()),
            (py_gerente / py_estadistica) - 1,
            None
        )

    def _diagnose_spread(self, spread) -> str:
        """Diagnóstico automático basado en el spread."""
        if spread is None or pd.isna(spread):
            return "Sin datos"

        spread = float(spread)

        if spread > cfg.SPREAD_OPTIMISTA_THRESHOLD:
            return "Gerente optimista vs datos"
        elif spread < cfg.SPREAD_CONSERVADOR_THRESHOLD:
            return "Gerente conservador vs datos"
        elif abs(spread) < cfg.SPREAD_CONSENSO_THRESHOLD:
            return "Alto consenso"
        else:
            return "Leve divergencia"

    def _calculate_resumen_nacional(
        self,
        comparativo_marca: pd.DataFrame,
        comparativo_ciudad: pd.DataFrame
    ) -> Dict:
        """Calcula totales nacionales de las tres proyecciones."""
        def safe_sum(df, col):
            if col in df.columns:
                return df[col].dropna().sum()
            return 0

        total_est_marca = safe_sum(comparativo_marca, 'py_estadistica_bob')
        total_op_marca = safe_sum(comparativo_marca, 'py_operativa_bob')
        total_ger_marca = safe_sum(comparativo_marca, 'py_gerente_bob')

        total_est_ciudad = safe_sum(comparativo_ciudad, 'py_estadistica_bob')
        total_op_ciudad = safe_sum(comparativo_ciudad, 'py_operativa_bob')
        total_ger_ciudad = safe_sum(comparativo_ciudad, 'py_gerente_bob')

        # Spread nacional
        spread_nacional = None
        if total_est_marca > 0 and total_ger_marca > 0:
            spread_nacional = (total_ger_marca / total_est_marca) - 1

        return {
            'by_marca': {
                'py_gerente': total_ger_marca,
                'py_estadistica': total_est_marca,
                'py_operativa': total_op_marca,
                'spread': spread_nacional,
                'diagnostico': self._diagnose_spread(spread_nacional)
            },
            'by_ciudad': {
                'py_gerente': total_ger_ciudad,
                'py_estadistica': total_est_ciudad,
                'py_operativa': total_op_ciudad,
            }
        }
