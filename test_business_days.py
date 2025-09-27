"""
Script de prueba para verificar el cálculo de días laborales
"""

from datetime import datetime
from utils.business_days import BusinessDaysCalculator, get_business_days_info


def test_various_dates():
    """Probar el cálculo para diferentes fechas"""
    calculator = BusinessDaysCalculator()

    # Lista de fechas de prueba
    test_dates = [
        datetime(2025, 1, 15),   # Enero 2025
        datetime(2025, 2, 28),   # Febrero 2025
        datetime(2025, 3, 15),   # Marzo 2025 (con Carnaval)
        datetime(2025, 4, 20),   # Abril 2025 (con Viernes Santo)
        datetime(2025, 5, 15),   # Mayo 2025 (con Día del Trabajo)
        datetime(2025, 6, 22),   # Junio 2025 (con Corpus Christi y Año Nuevo Aymara)
        datetime(2025, 8, 10),   # Agosto 2025 (con Día de la Independencia)
        datetime(2025, 9, 19),   # Septiembre 2025 (19 de septiembre)
        datetime(2025, 9, 22),   # Septiembre 2025 (actual)
        datetime(2025, 11, 15),  # Noviembre 2025 (con Día de los Difuntos)
        datetime(2025, 12, 25),  # Diciembre 2025 (Navidad)
    ]

    print("=" * 80)
    print("CÁLCULO DE DÍAS LABORALES PARA DIFERENTES FECHAS")
    print("=" * 80)

    for date in test_dates:
        dias_mes, dias_avance, porcentaje = calculator.calculate_business_days(date)
        month_name = date.strftime("%B %Y")
        print(f"\nFecha: {date.strftime('%d de %B de %Y')}")
        print(f"  - Días laborales del mes: {dias_mes}")
        print(f"  - Días laborales hasta la fecha: {dias_avance}")
        print(f"  - Porcentaje de avance: {porcentaje:.2f}%")

    print("\n" + "=" * 80)


def test_holidays():
    """Verificar los festivos del año"""
    calculator = BusinessDaysCalculator()

    print("\nFESTIVOS DE BOLIVIA PARA 2025:")
    print("-" * 40)

    holidays = calculator.get_holidays_for_year(2025)
    for holiday in sorted(holidays):
        print(f"  {holiday.strftime('%d de %B')} - {holiday.strftime('%A')}")


def compare_with_hardcoded():
    """Comparar con los valores hardcodeados anteriores"""
    calculator = BusinessDaysCalculator()

    # Fecha del 19 de septiembre 2025 (como estaba hardcodeado)
    sept_19 = datetime(2025, 9, 19)
    dias_mes, dias_avance, porcentaje = calculator.calculate_business_days(sept_19)

    print("\n" + "=" * 80)
    print("COMPARACIÓN CON VALORES HARDCODEADOS")
    print("=" * 80)
    print(f"\nFecha de referencia: 19 de Septiembre 2025")
    print("\nValores hardcodeados anteriores:")
    print("  - Días laborales del mes: 26")
    print("  - Días laborales de avance: 16")
    print("  - Porcentaje de avance: 61.54%")
    print("\nValores calculados dinámicamente:")
    print(f"  - Días laborales del mes: {dias_mes}")
    print(f"  - Días laborales de avance: {dias_avance}")
    print(f"  - Porcentaje de avance: {porcentaje:.2f}%")

    # Fecha actual
    current = datetime.now()
    dias_mes_actual, dias_avance_actual, porcentaje_actual = calculator.calculate_business_days(current)

    print(f"\nFecha actual: {current.strftime('%d de %B de %Y')}")
    print(f"  - Días laborales del mes: {dias_mes_actual}")
    print(f"  - Días laborales de avance: {dias_avance_actual}")
    print(f"  - Porcentaje de avance: {porcentaje_actual:.2f}%")


if __name__ == "__main__":
    test_various_dates()
    test_holidays()
    compare_with_hardcoded()