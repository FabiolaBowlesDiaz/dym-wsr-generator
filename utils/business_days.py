"""
Módulo para cálculo de días laborales
Calcula días laborales excluyendo domingos y festivos de Bolivia
"""

from datetime import datetime, timedelta
from typing import Tuple, List
import calendar


class BusinessDaysCalculator:
    """Calculador de días laborales para Bolivia"""

    def __init__(self):
        """Inicializar con festivos de Bolivia"""
        # Festivos fijos de Bolivia (día, mes)
        self.fixed_holidays = [
            (1, 1),   # Año Nuevo
            (22, 1),  # Estado Plurinacional de Bolivia
            (1, 5),   # Día del Trabajo
            (21, 6),  # Año Nuevo Aymara
            (6, 8),   # Día de la Independencia
            (2, 11),  # Día de los Difuntos
            (25, 12), # Navidad
        ]

        # Festivos móviles por año (mes, día)
        # Estos cambian cada año según la fecha de Pascua
        self.mobile_holidays = {
            2024: [
                (2, 12),  # Carnaval Lunes - 12 Febrero
                (2, 13),  # Carnaval Martes - 13 Febrero
                (3, 29),  # Viernes Santo - 29 Marzo
                (5, 30),  # Corpus Christi - 30 Mayo
            ],
            2025: [
                (3, 3),   # Carnaval Lunes - 3 Marzo
                (3, 4),   # Carnaval Martes - 4 Marzo
                (4, 18),  # Viernes Santo - 18 Abril
                (6, 19),  # Corpus Christi - 19 Junio
            ],
            2026: [
                (2, 16),  # Carnaval Lunes - 16 Febrero
                (2, 17),  # Carnaval Martes - 17 Febrero
                (4, 3),   # Viernes Santo - 3 Abril
                (6, 4),   # Corpus Christi - 4 Junio
            ],
            # Para agregar años futuros, simplemente añadir:
            # 2027: [(mes, día), ...],
        }

    def get_holidays_for_year(self, year: int) -> List[datetime]:
        """
        Obtener lista de festivos para un año específico

        Args:
            year: Año para obtener festivos

        Returns:
            Lista de fechas festivas
        """
        holidays = []

        # Agregar festivos fijos
        for day, month in self.fixed_holidays:
            try:
                holiday = datetime(year, month, day)
                holidays.append(holiday)
            except ValueError:
                # En caso de fecha inválida
                continue

        # Agregar festivos móviles del año desde el diccionario
        if year in self.mobile_holidays:
            for month, day in self.mobile_holidays[year]:
                try:
                    holidays.append(datetime(year, month, day))
                except ValueError:
                    continue

        return holidays

    def is_business_day(self, date: datetime, holidays: List[datetime] = None) -> bool:
        """
        Verificar si una fecha es día laboral

        Args:
            date: Fecha a verificar
            holidays: Lista opcional de festivos

        Returns:
            True si es día laboral, False si no
        """
        # Domingo es 6 en weekday()
        if date.weekday() == 6:
            return False

        # Verificar si es festivo
        if holidays:
            for holiday in holidays:
                if date.date() == holiday.date():
                    return False

        return True

    def calculate_business_days(self, current_date: datetime) -> Tuple[int, int, float]:
        """
        Calcular días laborales del mes y días laborales transcurridos

        Args:
            current_date: Fecha actual para el cálculo

        Returns:
            Tupla con:
            - dias_laborales_mes: Total de días laborales del mes
            - dias_laborales_avance: Días laborales transcurridos hasta la fecha
            - porcentaje_avance: Porcentaje de avance del mes
        """
        year = current_date.year
        month = current_date.month
        day = current_date.day

        # Obtener festivos del año
        holidays = self.get_holidays_for_year(year)

        # Calcular días laborales del mes completo
        _, last_day = calendar.monthrange(year, month)
        dias_laborales_mes = 0

        for d in range(1, last_day + 1):
            date = datetime(year, month, d)
            if self.is_business_day(date, holidays):
                dias_laborales_mes += 1

        # Calcular días laborales transcurridos hasta la fecha actual
        dias_laborales_avance = 0

        for d in range(1, min(day + 1, last_day + 1)):
            date = datetime(year, month, d)
            if self.is_business_day(date, holidays):
                dias_laborales_avance += 1

        # Calcular porcentaje de avance
        porcentaje_avance = 0
        if dias_laborales_mes > 0:
            porcentaje_avance = (dias_laborales_avance / dias_laborales_mes) * 100

        return dias_laborales_mes, dias_laborales_avance, porcentaje_avance

    def calculate_working_days_between(self, start_date: datetime, end_date: datetime) -> int:
        """
        Calcular días laborales entre dos fechas

        Args:
            start_date: Fecha inicial
            end_date: Fecha final

        Returns:
            Número de días laborales entre las fechas
        """
        if start_date > end_date:
            return 0

        holidays = self.get_holidays_for_year(start_date.year)
        if end_date.year != start_date.year:
            holidays.extend(self.get_holidays_for_year(end_date.year))

        working_days = 0
        current = start_date

        while current <= end_date:
            if self.is_business_day(current, holidays):
                working_days += 1
            current += timedelta(days=1)

        return working_days


def get_business_days_info(current_date: datetime = None) -> dict:
    """
    Función de conveniencia para obtener información de días laborales

    Args:
        current_date: Fecha para el cálculo (por defecto: fecha actual)

    Returns:
        Diccionario con información de días laborales
    """
    if current_date is None:
        current_date = datetime.now()

    calculator = BusinessDaysCalculator()
    dias_laborales_mes, dias_laborales_avance, porcentaje_avance = calculator.calculate_business_days(current_date)

    return {
        'dias_laborales_mes': dias_laborales_mes,
        'dias_laborales_avance': dias_laborales_avance,
        'porcentaje_avance': porcentaje_avance,
        'fecha_calculo': current_date.strftime('%Y-%m-%d')
    }


if __name__ == "__main__":
    # Prueba del calculador
    info = get_business_days_info()
    print(f"Información de días laborales:")
    print(f"  Fecha de cálculo: {info['fecha_calculo']}")
    print(f"  Días laborales del mes: {info['dias_laborales_mes']}")
    print(f"  Días laborales transcurridos: {info['dias_laborales_avance']}")
    print(f"  Porcentaje de avance: {info['porcentaje_avance']:.2f}%")