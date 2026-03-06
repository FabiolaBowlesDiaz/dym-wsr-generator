"""
Módulo de Ajuste por Eventos Móviles para Proyección Estadística

Problema: Holt-Winters aprende estacionalidad fija (ej: "marzo siempre vende X").
Pero eventos móviles como Carnaval cambian de mes entre años:
  - Carnaval 2025 → Marzo
  - Carnaval 2026 → Febrero

Si el modelo aprendió que "marzo es alto" por Carnaval 2025, proyectará
marzo 2026 alto y febrero 2026 normal — exactamente al revés.

Solución: Ajuste post-forecast multiplicativo.
  1. Forecast con Holt-Winters estándar (sin modificar)
  2. Detectar si un evento móvil cambió de mes vs los años de entrenamiento
  3. Si el evento es NUEVO en el mes target → boost (ej: +15% Carnaval)
  4. Si el evento SE FUE del mes target → reducción (ej: -15% Carnaval)

Usa el calendario existente de utils/business_days.py como fuente de verdad.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .. import config as cfg

logger = logging.getLogger(__name__)


class EventCalendar:
    """
    Calendario de eventos móviles para ajuste de proyecciones.

    Se alimenta del BusinessDaysCalculator existente en utils/business_days.py,
    que ya tiene los festivos fijos y móviles de Bolivia para 2025 y 2026.
    """

    def __init__(self):
        """Inicializa importando el calendario existente del proyecto."""
        try:
            from utils.business_days import BusinessDaysCalculator
            self._bdc = BusinessDaysCalculator()
            self._available = True
        except ImportError:
            logger.warning(
                "No se pudo importar BusinessDaysCalculator. "
                "Ajuste por eventos no disponible."
            )
            self._bdc = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def _classify_mobile_holiday(self, comment: str) -> Optional[str]:
        """
        Dado el comentario de un festivo móvil (ej: "Carnaval Lunes - 16 Febrero"),
        devuelve el event_id correspondiente (ej: 'carnaval').

        Usa EVENT_KEYWORDS de config.py para mapear.
        """
        comment_lower = comment.lower()
        for keyword, event_id in cfg.EVENT_KEYWORDS.items():
            if keyword in comment_lower:
                return event_id
        return None

    def get_events_by_month(self, year: int) -> Dict[int, List[str]]:
        """
        Para un año dado, retorna {mes: [lista de event_ids]}.

        Ejemplo para 2026:
            {2: ['carnaval'], 4: ['viernes_santo'], 6: ['corpus_christi']}

        Ejemplo para 2025:
            {3: ['carnaval'], 4: ['viernes_santo'], 6: ['corpus_christi']}
        """
        if not self._available:
            return {}

        if year not in self._bdc.mobile_holidays:
            logger.debug(f"Año {year} no tiene festivos móviles definidos")
            return {}

        events_by_month: Dict[int, List[str]] = {}

        # mobile_holidays es {year: [(mes, dia), ...]}
        # Pero necesitamos los comentarios para saber qué evento es.
        # El BusinessDaysCalculator no guarda comentarios, así que usamos
        # un mapeo hardcoded basado en la posición y el mes.
        #
        # Patrón del calendario: siempre son 4 entradas en orden:
        #   [0] Carnaval Lunes, [1] Carnaval Martes,
        #   [2] Viernes Santo, [3] Corpus Christi

        holidays = self._bdc.mobile_holidays[year]

        # Mapear por posición (el orden en business_days.py es consistente)
        event_map = [
            'carnaval',         # Carnaval Lunes
            'carnaval',         # Carnaval Martes (mismo evento, mismo mes)
            'viernes_santo',    # Viernes Santo
            'corpus_christi',   # Corpus Christi
        ]

        for i, (month, day) in enumerate(holidays):
            if i < len(event_map):
                event_id = event_map[i]
                if month not in events_by_month:
                    events_by_month[month] = []
                # Evitar duplicados (Carnaval Lunes y Martes son el mismo evento)
                if event_id not in events_by_month[month]:
                    events_by_month[month].append(event_id)

        return events_by_month

    def calculate_event_adjustment(
        self,
        target_year: int,
        target_month: int,
        training_years: Optional[List[int]] = None
    ) -> Dict:
        """
        Calcula el factor de ajuste para un mes/año dado basado en
        si hay eventos que se movieron.

        Args:
            target_year: Año de la proyección (ej: 2026)
            target_month: Mes de la proyección (ej: 2)
            training_years: Años usados en el entrenamiento del modelo.
                           Si None, usa los últimos N años según config.

        Returns:
            Dict con:
              - 'adjustment_factor': float (ej: 1.15 = +15% boost)
              - 'events_in_target': lista de eventos en el mes target
              - 'events_new': eventos nuevos (no estaban en este mes en training)
              - 'events_gone': eventos que se fueron (estaban y ya no están)
              - 'explanation': texto explicativo
        """
        if not self._available:
            return {
                'adjustment_factor': 1.0,
                'events_in_target': [],
                'events_new': [],
                'events_gone': [],
                'explanation': 'Calendario no disponible'
            }

        # Determinar años de training
        if training_years is None:
            training_years = list(range(
                target_year - cfg.TRAINING_YEARS_LOOKBACK,
                target_year
            ))

        # Obtener eventos del mes target en el año de proyección
        target_events = self.get_events_by_month(target_year)
        events_in_target = target_events.get(target_month, [])

        # Obtener eventos del mismo mes en años de training
        # Un evento es "históricamente presente" si aparece en este mes
        # en al menos la mitad de los años de training
        training_event_counts: Dict[str, int] = {}
        valid_training_years = 0

        for yr in training_years:
            yr_events = self.get_events_by_month(yr)
            if yr_events:  # Solo contar años que tienen data
                valid_training_years += 1
                for event_id in yr_events.get(target_month, []):
                    training_event_counts[event_id] = \
                        training_event_counts.get(event_id, 0) + 1

        # Threshold: el evento debe haber estado en >50% de los años de training
        threshold = max(1, valid_training_years / 2)

        historically_present = {
            eid for eid, count in training_event_counts.items()
            if count >= threshold
        }

        # Eventos NUEVOS: están en target pero no estaban históricamente
        events_new = [e for e in events_in_target if e not in historically_present]

        # Eventos que SE FUERON: estaban históricamente pero no están en target
        events_gone = [e for e in historically_present if e not in events_in_target]

        # Calcular factor de ajuste multiplicativo
        factor = 1.0
        explanations = []

        for event_id in events_new:
            impact = cfg.EVENT_IMPACTS.get(event_id, 0.0)
            if abs(impact) > 0.001:
                factor *= (1.0 + impact)
                explanations.append(
                    f"+{impact:.0%} por {event_id.upper()} (nuevo en mes {target_month})"
                )

        for event_id in events_gone:
            impact = cfg.EVENT_IMPACTS.get(event_id, 0.0)
            if abs(impact) > 0.001:
                factor *= (1.0 - impact)
                explanations.append(
                    f"-{impact:.0%} por {event_id.upper()} (se fue del mes {target_month})"
                )

        explanation = "; ".join(explanations) if explanations else "Sin ajuste por eventos"

        return {
            'adjustment_factor': round(factor, 4),
            'events_in_target': events_in_target,
            'events_new': events_new,
            'events_gone': events_gone,
            'explanation': explanation
        }
