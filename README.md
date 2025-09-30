# WSR Generator - DYM
Sistema automatizado para generar Weekly Sales Report (WSR) de DYM

## Descripción del Proyecto

Este sistema genera automáticamente reportes semanales de ventas (WSR) para DYM, consolidando datos de:
- Ventas por marca, ciudad y canal
- Proyecciones y presupuestos
- Hit Rate y eficiencia
- Stock y cobertura
- Análisis de tendencias comparativas
- Comentarios de gerentes

El reporte se genera en formato HTML con tablas interactivas y gráficos de tendencia.

## Requisitos Previos

### Software Requerido
- **Python**: Versión 3.8 o superior
- **PostgreSQL**: Acceso a base de datos DWH (servidor 192.168.80.85)
- **Sistema Operativo**: Linux/Windows

### Dependencias de Python
Ver archivo `requirements.txt` para lista completa. Principales dependencias:
- pandas >= 1.5.0
- numpy >= 1.23.0
- psycopg2-binary >= 2.9.0
- python-dotenv >= 0.20.0
- openai >= 1.0.0
- requests >= 2.28.0
- colorlog >= 6.6.0
- pydantic >= 1.10.0

## Instalación

### 1. Clonar el Repositorio
```bash
git clone https://github.com/FabiolaBowlesDiaz/dym-wsr-generator.git
cd dym-wsr-generator
```

### 2. Crear Entorno Virtual
```bash
# En Linux/Mac
python3 -m venv venv
source venv/bin/activate

# En Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Crear archivo `.env` en la raíz del proyecto con la siguiente configuración:

```ini
# OpenRouter Configuration (para análisis de comentarios con IA)
OPENROUTER_API_KEY=sk-or-v1-[YOUR_API_KEY]
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=anthropic/claude-opus-4.1
FALLBACK_MODEL=anthropic/claude-sonnet-4

# Database Configuration
DB_HOST=192.168.80.85
DB_PORT=5432
DB_NAME=dwh_saiv
DB_SCHEMA=auto
DB_USER=automatizacion
DB_PASSWORD=Aut0SAIV.
DB_TYPE=postgresql

# Report Configuration
REPORT_OUTPUT_PATH=./output/
COMPANY_NAME=DYM
CURRENT_YEAR=2025
PREVIOUS_YEAR=2024

# Logging
LOG_LEVEL=INFO
LOG_FILE=wsr_generator.log
```

**IMPORTANTE**: Las credenciales de base de datos y API key deben ser provistas por el equipo de TI/Administración.

## Ejecución del Sistema

### Ejecución Manual
```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Ejecutar el generador
python wsr_generator_main.py
```

### Verificar Ejecución Exitosa
El sistema mostrará mensajes de progreso en consola:
```
==================================================
WSR GENERATOR - DYM
==================================================
📅 Fecha: 30/09/2025
📊 Período: Mes 9/2025
📈 Análisis hasta el día: 30

🔗 Conectando a la base de datos...
📥 Obteniendo datos...
🔄 Procesando datos...
📊 Calculando métricas del resumen ejecutivo...
💬 Analizando comentarios de gerentes...
📊 Generando gráfico de tendencia comparativa...
📈 Obteniendo datos de Hit Rate y Eficiencia...
📄 Generando reporte HTML...

✅ Reporte generado exitosamente: output/WSR_DYM_2025_09_20250930_143022.html
```

## Outputs del Sistema

### Archivo de Reporte
- **Ubicación**: `./output/`
- **Formato**: `WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html`
- **Ejemplo**: `WSR_DYM_2025_09_20250930_143022.html`
- **Contenido**: Reporte HTML completo con tablas y gráficos interactivos

### Archivo de Logs
- **Ubicación**: `./wsr_generator.log`
- **Contenido**: Logs detallados de cada ejecución (conexión DB, queries, procesamiento, errores)

## Automatización

El sistema debe ejecutarse **todos los lunes** para generar el reporte semanal.

### Opción 1: Cron Job (Linux)

#### Configurar Cron Job
```bash
# Editar crontab
crontab -e

# Agregar la siguiente línea para ejecutar todos los lunes a las 6:00 AM
0 6 * * 1 cd /ruta/completa/al/proyecto && /ruta/completa/al/proyecto/venv/bin/python wsr_generator_main.py >> /ruta/logs/wsr_cron.log 2>&1
```

#### Ejemplo Completo
```bash
# Ejecutar todos los lunes a las 6:00 AM
0 6 * * 1 cd /opt/dym-wsr-generator && /opt/dym-wsr-generator/venv/bin/python wsr_generator_main.py >> /var/log/wsr_cron.log 2>&1
```

#### Verificar Cron Job
```bash
# Listar cron jobs activos
crontab -l

# Ver logs del cron
cat /var/log/wsr_cron.log
```

### Opción 2: Task Scheduler (Windows)

#### Crear Tarea Programada

1. **Abrir Task Scheduler**
   - Presionar `Win + R`, escribir `taskschd.msc`

2. **Crear Nueva Tarea**
   - Clic en "Create Task" (Crear tarea)
   - **Nombre**: DYM WSR Generator
   - **Descripción**: Genera reporte semanal de ventas todos los lunes

3. **Configurar Trigger (Disparador)**
   - Tab "Triggers" → "New"
   - **Begin the task**: On a schedule
   - **Settings**: Weekly
   - **Days**: Monday (Lunes)
   - **Time**: 06:00:00
   - **Enabled**: ✓

4. **Configurar Action (Acción)**
   - Tab "Actions" → "New"
   - **Action**: Start a program
   - **Program/script**:
     ```
     C:\ruta\completa\al\proyecto\venv\Scripts\python.exe
     ```
   - **Add arguments**:
     ```
     wsr_generator_main.py
     ```
   - **Start in**:
     ```
     C:\ruta\completa\al\proyecto
     ```

5. **Configurar Condiciones**
   - Tab "Conditions"
   - Desmarcar "Start the task only if the computer is on AC power"

6. **Configurar Settings**
   - Tab "Settings"
   - ✓ Allow task to be run on demand
   - ✓ Run task as soon as possible after a scheduled start is missed
   - ✓ If the task fails, restart every: 10 minutes

#### Script BAT Alternativo (Windows)
Crear archivo `run_wsr_generator.bat`:
```bat
@echo off
cd /d "C:\ruta\completa\al\proyecto"
call venv\Scripts\activate
python wsr_generator_main.py >> logs\wsr_execution.log 2>&1
deactivate
```

Configurar Task Scheduler para ejecutar este archivo .bat

## Configuración de Envío de Correo

**NOTA**: El sistema actualmente genera el reporte HTML pero NO incluye funcionalidad de envío automático por correo.

### Implementación Requerida

El equipo de sistemas deberá implementar el envío de correo mediante una de estas opciones:

#### Opción A: Servidor SMTP Corporativo
Agregar configuración SMTP al archivo `.env`:
```ini
# Email Configuration
SMTP_HOST=smtp.empresa.com
SMTP_PORT=587
SMTP_USER=wsr-generator@empresa.com
SMTP_PASSWORD=password_seguro
SMTP_USE_TLS=True

# Recipients
EMAIL_TO=director1@empresa.com,director2@empresa.com
EMAIL_CC=gerencia@empresa.com
EMAIL_SUBJECT_PREFIX=[WSR DYM]
```

#### Opción B: Script Post-Ejecución
Crear script que envíe el último archivo generado:
```bash
# send_wsr_email.sh (Linux)
#!/bin/bash
LATEST_REPORT=$(ls -t output/WSR_DYM_*.html | head -1)
echo "Adjunto encontrará el reporte WSR de DYM" | mail -s "WSR DYM - Semana $(date +%V)" -a "$LATEST_REPORT" director1@empresa.com,director2@empresa.com
```

```powershell
# send_wsr_email.ps1 (Windows PowerShell)
$latestReport = Get-ChildItem -Path "output\WSR_DYM_*.html" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Send-MailMessage -From "wsr-generator@empresa.com" -To "director1@empresa.com", "director2@empresa.com" -Subject "WSR DYM - Semana $(Get-Date -UFormat %V)" -Body "Adjunto encontrará el reporte WSR de DYM" -Attachments $latestReport.FullName -SmtpServer "smtp.empresa.com"
```

#### Opción C: Integración con Microsoft Power Automate/Outlook
Configurar flujo que detecte nuevos archivos en carpeta `output/` y los envíe automáticamente.

### Destinatarios del Reporte
**IMPORTANTE**: Coordinar con el área correspondiente la lista completa de destinatarios (directores y gerentes).

## Logs y Monitoreo

### Archivo de Log Principal
- **Ubicación**: `./wsr_generator.log`
- **Rotación**: Manual (considerar implementar rotación automática)
- **Nivel de detalle**: INFO (configurable en `.env` con `LOG_LEVEL`)

### Qué Monitorear
1. **Errores de Conexión DB**: Buscar "❌ No se pudo conectar a la base de datos"
2. **Errores de Queries**: Verificar mensajes de error en queries SQL
3. **Datos Vacíos**: Alertas sobre tablas sin datos
4. **Finalización Exitosa**: Buscar "✅ Reporte generado exitosamente"

### Comando para Revisar Últimos Errores
```bash
# Ver últimas 50 líneas del log
tail -50 wsr_generator.log

# Buscar errores específicos
grep "ERROR" wsr_generator.log
grep "❌" wsr_generator.log
```

## Solución de Problemas

### Error: No se puede conectar a la base de datos
**Causa**: Credenciales incorrectas o servidor inaccesible
**Solución**:
1. Verificar que el servidor 192.168.80.85 sea accesible
2. Confirmar credenciales en `.env`
3. Verificar firewall/reglas de red
4. Probar conexión manual: `psql -h 192.168.80.85 -U automatizacion -d dwh_saiv`

### Error: Módulo no encontrado (ModuleNotFoundError)
**Causa**: Dependencias no instaladas o entorno virtual no activado
**Solución**:
```bash
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
```

### Error: API Key inválida (OpenRouter)
**Causa**: API key de OpenRouter incorrecta o vencida
**Solución**:
1. Verificar `OPENROUTER_API_KEY` en `.env`
2. Contactar al administrador para obtener nueva key
3. Verificar que la cuenta tenga créditos disponibles

### Reporte Vacío o con Datos Incompletos
**Causa**: Datos no disponibles en la base de datos para el período
**Solución**:
1. Revisar `wsr_generator.log` para ver qué queries fallaron
2. Verificar que las tablas en la base de datos tengan datos actualizados
3. Contactar al equipo de Data Warehouse

### Cron Job no se Ejecuta
**Causa**: Permisos, rutas incorrectas o entorno no configurado
**Solución**:
1. Verificar logs del cron: `/var/log/syslog` o `/var/log/cron`
2. Probar ejecución manual del comando del cron
3. Verificar permisos de ejecución: `chmod +x wsr_generator_main.py`
4. Asegurar rutas absolutas en cron job

## Estructura del Proyecto

```
dym-wsr-generator/
├── core/                          # Módulos principales
│   ├── database.py               # Gestión de conexiones y queries DB
│   ├── data_processor.py         # Procesamiento y cálculos de datos
│   ├── html_generator.py         # Generación de HTML del reporte
│   └── trend_chart_generator.py  # Gráficos de tendencia interactivos
├── utils/                         # Utilidades
│   └── html_tables.py            # Generación de tablas HTML
├── templates/                     # Plantillas HTML (si aplica)
├── data/                          # Datos temporales/cache
├── output/                        # Reportes HTML generados
├── logs/                          # Logs adicionales
├── tests/                         # Tests unitarios
├── test_*.py                      # Tests funcionales
├── wsr_generator_main.py         # Punto de entrada principal
├── generate_report.py            # Script alternativo de generación
├── setup.py                       # Configuración del paquete
├── requirements.txt              # Dependencias Python
├── .env                          # Variables de entorno (NO versionar)
├── .gitignore                    # Archivos ignorados por git
└── README.md                     # Este archivo
```

## Mantenimiento

### Actualizar el Sistema
```bash
cd /ruta/al/proyecto
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Backup de Configuración
```bash
# Hacer backup del .env
cp .env .env.backup

# Backup de reportes generados
tar -czf backup_reportes_$(date +%Y%m%d).tar.gz output/
```

### Limpieza de Archivos Antiguos
```bash
# Eliminar reportes con más de 90 días
find output/ -name "WSR_DYM_*.html" -mtime +90 -delete

# Rotar logs
mv wsr_generator.log wsr_generator_$(date +%Y%m%d).log
gzip wsr_generator_$(date +%Y%m%d).log
```

## Seguridad

### Consideraciones Importantes
1. **Archivo .env**: NO versionar ni compartir públicamente (contiene credenciales)
2. **Permisos del archivo .env**: `chmod 600 .env` (solo lectura para owner)
3. **Credenciales DB**: Usar usuario con permisos de solo lectura
4. **API Keys**: Rotar periódicamente
5. **Logs**: Los logs pueden contener información sensible, proteger acceso

### Usuarios y Permisos Recomendados
- Usuario del sistema: `wsr-automation` (sin privilegios sudo)
- Directorio de instalación: `/opt/dym-wsr-generator` con permisos 750
- Propietario archivos: `wsr-automation:wsr-automation`

## Información de Contacto

### Soporte y Consultas
**Desarrollador/Responsable**: Fabiola Bowles
**Email**: fbowles@theblankinc.com
**Empresa**: The Blank Inc. - IA Consulting

### Escalamiento
Para problemas técnicos o dudas sobre:
- **Funcionalidad del reporte**: Contactar a Fabiola Bowles
- **Acceso a base de datos**: Contactar al equipo de Data Warehouse/DBA
- **Infraestructura/servidores**: Contactar al equipo de Sistemas/IT
- **Contenido de negocio**: Contactar al área de Análisis Comercial DYM

## Historial de Versiones

- **v1.0** (Septiembre 2025): Versión inicial con todas las funcionalidades core
  - Generación automática de WSR
  - Soporte multi-ciudad y multi-marca
  - Gráficos de tendencia interactivos
  - Análisis de Hit Rate y cobertura de stock
  - Integración con OpenRouter/Claude para análisis de comentarios

## Notas Adicionales

### Consideraciones de Rendimiento
- Tiempo de ejecución promedio: 2-5 minutos
- Consumo de memoria: ~200-500 MB
- Tamaño del reporte HTML: ~500 KB - 2 MB

### Actualizaciones Anuales Requeridas
- Actualizar `CURRENT_YEAR` y `PREVIOUS_YEAR` en `.env` al inicio de cada año
- Verificar que las tablas de presupuesto del nuevo año estén cargadas en la DB

### Exclusiones Aplicadas por el Sistema
El sistema automáticamente excluye:
- Ciudad/Canal: "Turismo"
- Marcas: "Ninguna", "Sin marca asignada"
- Estas exclusiones están hardcodeadas en `data_processor.py`

---

**Última actualización**: Septiembre 2025
**Versión del documento**: 1.0
