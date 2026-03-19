"""
Nowcast Engine - Bayesian Credibility Blending

Combina el forecast estadistico (Holt-Winters) con el ritmo actual de ventas
(Run Rate) usando un peso de credibilidad basado en dias laborales transcurridos.

Formula: PY_Sistema = w * Run_Rate + (1-w) * HW_Forecast
donde w = dias_laborales_avance / dias_laborales_mes

Al inicio del mes (w ~ 0): PY Sistema = HW (prior estadistico domina)
A fin de mes (w ~ 1): PY Sistema = Run Rate (dato observado domina)
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class NowcastEngine:
    """
    Motor de Nowcasting por credibilidad bayesiana.

    Recibe DataFrames que ya contienen tanto el avance actual como el forecast HW,
    y calcula PY Sistema como blend ponderado por dias laborales.
    """

    def __init__(self, current_date: datetime, dias_laborales_mes: int, dias_laborales_avance: int):
        """
        Args:
            current_date: Fecha actual del reporte
            dias_laborales_mes: Total de dias laborales del mes
            dias_laborales_avance: Dias laborales transcurridos hasta hoy
        """
        self.current_date = current_date
        self.dias_laborales_mes = dias_laborales_mes
        self.dias_laborales_avance = dias_laborales_avance
        self.w = dias_laborales_avance / dias_laborales_mes if dias_laborales_mes > 0 else 0

        logger.info(
            f"[Nowcast] Credibilidad w={self.w:.3f} "
            f"({dias_laborales_avance}/{dias_laborales_mes} dias laborales)"
        )

    def calculate(self, df: pd.DataFrame, avance_col: str,
                  hw_col: str = 'py_estadistica_bob',
                  value_suffix: str = 'bob') -> pd.DataFrame:
        """
        Calcula PY Sistema para cada fila del DataFrame.

        Args:
            df: DataFrame con avance actual y HW forecast ya mergeados
            avance_col: Columna de avance actual (ej: 'avance_2026_bob')
            hw_col: Columna del forecast HW (default: 'py_estadistica_bob')
            value_suffix: Sufijo para columnas de salida ('bob' o 'c9l')

        Returns:
            DataFrame con columnas adicionales:
            - py_sistema_{suffix}: blend bayesiano
            - run_rate_{suffix}: extrapolacion lineal del avance
            - spread_sistema_{suffix}: (PY Gerente / PY Sistema) - 1
        """
        result = df.copy()

        avance = result[avance_col].fillna(0) if avance_col in result.columns else pd.Series(0, index=result.index)
        hw = result[hw_col].fillna(0) if hw_col in result.columns else pd.Series(0, index=result.index)

        # Run Rate = avance extrapolado al mes completo
        if self.w > 0:
            run_rate = avance / self.w
        else:
            run_rate = pd.Series(0, index=result.index)

        # Bayesian blend
        py_sistema = self.w * run_rate + (1 - self.w) * hw

        result[f'py_sistema_{value_suffix}'] = py_sistema
        result[f'run_rate_{value_suffix}'] = run_rate

        # Spread: (PY Gerente / PY Sistema) - 1
        py_col_candidates = [c for c in result.columns if c.startswith('py_') and c.endswith(f'_{value_suffix}')
                             and c not in (f'py_sistema_{value_suffix}', f'py_estadistica_{value_suffix}')]
        if py_col_candidates:
            py_gerente = result[py_col_candidates[0]].fillna(0)
        else:
            py_gerente = pd.Series(0, index=result.index)

        spread_col = 'spread_sistema' if value_suffix == 'bob' else f'spread_sistema_{value_suffix}'
        result[spread_col] = np.where(
            py_sistema > 0,
            (py_gerente / py_sistema) - 1,
            np.nan
        )

        return result

    def get_metadata(self) -> dict:
        """Retorna metadata del nowcast para uso en narrativa."""
        return {
            'w': self.w,
            'dias_laborales_mes': self.dias_laborales_mes,
            'dias_laborales_avance': self.dias_laborales_avance,
            'pct_mes': self.w * 100,
            'metodo': f"{self.w:.0%} Run Rate + {1-self.w:.0%} Holt-Winters"
        }
