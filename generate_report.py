"""
Script simplificado para generar el reporte WSR
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

# Configuración de logging sin emojis
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wsr_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Remover emojis de los mensajes de log
def clean_log(msg):
    """Limpiar emojis del mensaje"""
    import re
    return re.sub(r'[\U0001F000-\U0001F9FF]|[\U00002600-\U000027FF]|[\u2705\u274c]', '', msg)

from wsr_generator_main import WSRGeneratorSystem

def main():
    """Función principal para ejecutar el generador"""
    try:
        print("="*50)
        print("WSR GENERATOR - DYM")
        print("="*50)

        # Crear instancia del sistema
        generator = WSRGeneratorSystem()

        # Generar reporte
        success = generator.generate()

        if success:
            print("\n" + "="*50)
            print("REPORTE GENERADO EXITOSAMENTE")
            print("="*50)
            return 0
        else:
            print("\n" + "="*50)
            print("ERROR EN LA GENERACION DEL REPORTE")
            print("Revisa el archivo wsr_generator.log para mas detalles")
            print("="*50)
            return 1

    except Exception as e:
        print(f"\nError critico: {e}")
        logger.error(f"Error critico en main: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())