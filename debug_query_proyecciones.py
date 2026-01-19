"""
Ejecutar el query completo de proyecciones para ver qué devuelve para Casa Real
"""

import os
from dotenv import load_dotenv
from core.database import DatabaseManager

load_dotenv()

config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'schema': os.getenv('DB_SCHEMA', 'auto')
}

db = DatabaseManager(config)
db.connect()

print("="*80)
print("EJECUTANDO QUERY get_proyecciones_marca() PARA CASA REAL")
print("="*80)
print()

# Llamar a la función real
result = db.get_proyecciones_marca(2025, 10, 27)

# Filtrar solo Casa Real
casa_real = result[result['marcadir'].str.upper() == 'CASA REAL']

if not casa_real.empty:
    print("RESULTADO PARA CASA REAL:")
    print(casa_real.to_string(index=False))
    print()
    py_value = casa_real['py_2025_bob'].values[0]
    print(f"PY 2025 Casa Real: {py_value:,.2f} BOB")
else:
    print("No se encontró Casa Real en el resultado")

print()
print("="*80)
print("COMPARACIÓN:")
print("="*80)
print(f"Esperado (cálculo manual):  6,607,069.07 BOB")
print(f"Obtenido (query):           {casa_real['py_2025_bob'].values[0]:,.2f} BOB" if not casa_real.empty else "N/A")
print(f"Diferencia:                 {6607069.07 - casa_real['py_2025_bob'].values[0]:,.2f} BOB" if not casa_real.empty else "N/A")

db.disconnect()
