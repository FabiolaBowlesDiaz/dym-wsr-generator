"""
Script de configuración inicial para WSR Generator
Crea la estructura de directorios y archivos necesarios
"""

import os
import sys
from pathlib import Path


def create_project_structure():
    """Crear la estructura de directorios del proyecto"""
    
    print("🚀 Configurando WSR Generator...")
    print("-" * 50)
    
    # Directorio base del proyecto
    base_dir = Path.cwd()
    
    # Estructura de directorios
    directories = [
        "core",
        "utils",
        "templates",
        "output",
        "logs",
        "data",
        "tests"
    ]
    
    # Crear directorios
    for dir_name in directories:
        dir_path = base_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✓ Directorio creado: {dir_name}/")
    
    # Crear archivos __init__.py
    init_dirs = ["core", "utils", "tests"]
    for dir_name in init_dirs:
        init_file = base_dir / dir_name / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Package initialization"""')
            print(f"✓ Archivo creado: {dir_name}/__init__.py")
    
    # Crear archivo .env de ejemplo si no existe
    env_example = base_dir / ".env.example"
    if not env_example.exists():
        env_content = """# Configuración de Base de Datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dym_database
DB_USER=tu_usuario
DB_PASSWORD=tu_password
DB_SCHEMA=conexion_auto

# Configuración de OpenRouter (opcional)
OPENROUTER_API_KEY=tu_api_key_aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=anthropic/claude-opus-4.6
FALLBACK_MODEL=anthropic/claude-sonnet-4.6

# Configuración de logging
LOG_LEVEL=INFO

# Configuración de negocio
TIPO_CAMBIO=6.96
"""
        env_example.write_text(env_content)
        print("✓ Archivo creado: .env.example")
    
    # Crear archivo .gitignore si no existe
    gitignore = base_dir / ".gitignore"
    if not gitignore.exists():
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Logs
*.log
logs/

# Output files
output/*.html
output/*.pdf

# Environment variables
.env

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary data
data/*.csv
data/*.xlsx
*.tmp
"""
        gitignore.write_text(gitignore_content)
        print("✓ Archivo creado: .gitignore")
    
    print("-" * 50)
    print("✅ Estructura del proyecto creada exitosamente!")
    
    return True


def check_dependencies():
    """Verificar que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...")
    print("-" * 50)
    
    required_packages = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'psycopg2': 'psycopg2-binary',
        'dotenv': 'python-dotenv'
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✓ {package_name} instalado")
        except ImportError:
            print(f"✗ {package_name} NO instalado")
            missing_packages.append(package_name)
    
    if missing_packages:
        print("\n⚠️  Faltan dependencias por instalar:")
        print(f"   Ejecuta: pip install {' '.join(missing_packages)}")
        print("   O: pip install -r requirements.txt")
        return False
    
    print("-" * 50)
    print("✅ Todas las dependencias están instaladas!")
    return True


def create_sample_files():
    """Crear archivos de muestra para los módulos"""
    print("\n📄 Creando archivos de módulos...")
    print("-" * 50)
    
    base_dir = Path.cwd()
    
    # Nota sobre los archivos de módulos
    files_to_create = {
        "core/database.py": "Módulo de base de datos",
        "core/data_processor.py": "Módulo de procesamiento",
        "core/html_generator.py": "Módulo generador HTML",
        "utils/formatters.py": "Utilidades de formato",
        "utils/constants.py": "Constantes del proyecto"
    }
    
    print("ℹ️  Los siguientes archivos deben ser copiados desde los artifacts:")
    for file_path, description in files_to_create.items():
        print(f"   - {file_path}: {description}")
    
    print("\n📝 Instrucciones:")
    print("1. Copia los módulos desde los artifacts generados")
    print("2. Configura tu archivo .env con las credenciales de base de datos")
    print("3. Ejecuta: python wsr_generator_main.py")
    
    return True


def main():
    """Función principal del setup"""
    print("\n" + "="*50)
    print("WSR GENERATOR - SETUP")
    print("="*50 + "\n")
    
    # Crear estructura
    if not create_project_structure():
        return 1
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n⚠️  Instala las dependencias faltantes antes de continuar")
        return 1
    
    # Información sobre archivos
    create_sample_files()
    
    print("\n" + "="*50)
    print("🎉 CONFIGURACIÓN COMPLETADA")
    print("="*50)
    print("\nPróximos pasos:")
    print("1. Copia tu archivo .env.example a .env")
    print("2. Configura las credenciales en .env")
    print("3. Copia los módulos desde los artifacts")
    print("4. Ejecuta: python wsr_generator_main.py")
    print("\n¡Listo para generar reportes!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())