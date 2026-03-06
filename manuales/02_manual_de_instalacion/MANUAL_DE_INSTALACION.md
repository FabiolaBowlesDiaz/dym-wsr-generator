---
titulo: Manual de Instalacion
subtitulo: WSR Generator DyM — Instalacion, configuracion y puesta en marcha del sistema
version: 3.0
fecha: Marzo 2026
audiencia: Gerencia de IT / Equipo de Sistemas
---

# Manual de Instalacion — WSR Generator DyM

## 1. Requisitos previos

### 1.1 Hardware minimo

| Componente | Requisito minimo | Recomendado |
|------------|------------------|-------------|
| **RAM** | 512 MB disponible | 1 GB disponible |
| **Disco** | 500 MB libre | 2 GB libre (incluye historial de reportes) |
| **CPU** | 1 core | 2+ cores |
| **Red** | Acceso a red interna 192.168.80.x | Conexion estable >= 10 Mbps |

> **Nota:** El consumo de memoria durante la ejecucion es de 200-500 MB aproximadamente, dependiendo del volumen de datos. El procesamiento estadistico (Holt-Winters) es la operacion mas intensiva en recursos.

### 1.2 Software requerido

| Software | Version minima | Proposito | Descarga |
|----------|---------------|-----------|----------|
| **Python** | 3.8+ (recomendado 3.10+) | Runtime del sistema | python.org |
| **pip** | Incluido con Python | Gestor de paquetes | Incluido |
| **Git** | 2.30+ | Control de versiones | git-scm.com |
| **Navegador web** | Chrome/Firefox/Edge actualizado | Visualizar reportes | — |

**No se requiere** instalar PostgreSQL localmente — el sistema se conecta al servidor DWH remoto.

### 1.3 Acceso a red y servicios

| Servicio | Host | Puerto | Protocolo | Requerido |
|----------|------|--------|-----------|-----------|
| **Data Warehouse (DWH)** | 192.168.80.85 | 5432 | PostgreSQL | Si |
| **OpenRouter API** | openrouter.ai | 443 | HTTPS | Opcional (analisis IA) |

> **Importante:** El servidor donde se instale el WSR debe tener **acceso de red** al servidor `192.168.80.85` en el puerto `5432`. Verifique con el equipo de redes que no haya firewalls bloqueando esta conexion.

### 1.4 Credenciales requeridas

Antes de iniciar la instalacion, asegurese de tener:

1. **Credenciales de la base de datos DWH** (usuario, contrasena, nombre de base de datos)
2. **API Key de OpenRouter** (opcional, solo si se desea analisis con IA)
3. **Acceso al repositorio** del proyecto (URL de clonacion)

> **Precaucion:** Las credenciales de base de datos deben ser de un usuario con **permisos de SOLO LECTURA** en el esquema `auto` de la base `dwh_saiv`. Nunca use credenciales con permisos de escritura.

---

## 2. Instalacion paso a paso

### 2.1 Clonar el repositorio

```bash
# Navegar al directorio donde se instalara el proyecto
cd /opt/aplicaciones    # Linux
cd C:\Aplicaciones      # Windows

# Clonar el repositorio
git clone <URL_DEL_REPOSITORIO> wsr_generator_dym

# Ingresar al directorio del proyecto
cd wsr_generator_dym
```

Si no se usa Git, copie manualmente la carpeta completa del proyecto al servidor de destino.

### 2.2 Crear entorno virtual (venv)

El entorno virtual aisla las dependencias del proyecto del sistema operativo, evitando conflictos con otras aplicaciones Python.

```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual

# En Windows (CMD):
venv\Scripts\activate

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# En Linux/Mac:
source venv/bin/activate
```

Verificar que el entorno esta activo (el prompt debe mostrar `(venv)`):

```bash
(venv) $ python --version
Python 3.10.x
```

> **Precaucion:** Todas las operaciones siguientes deben ejecutarse **con el entorno virtual activo**. Si cierra la terminal, debe reactivar el venv antes de ejecutar cualquier comando.

### 2.3 Instalar dependencias

```bash
pip install -r requirements.txt
```

**Dependencias principales que se instalaran:**

| Paquete | Version | Proposito |
|---------|---------|-----------|
| `pandas` | >= 1.5.0 | Manipulacion y analisis de datos |
| `numpy` | >= 1.23.0 | Calculos numericos |
| `psycopg2-binary` | >= 2.9.0 | Driver PostgreSQL |
| `python-dotenv` | >= 0.20.0 | Carga de variables de entorno (.env) |
| `openai` | >= 1.0.0 | Cliente para APIs compatibles con OpenAI (OpenRouter) |
| `requests` | >= 2.28.0 | Peticiones HTTP |
| `statsmodels` | >= 0.14.0 | Modelo estadistico Holt-Winters |
| `scipy` | >= 1.10.0 | Funciones cientificas auxiliares |
| `pydantic` | >= 1.10.0 | Validacion de datos y configuracion |
| `colorlog` | >= 6.6.0 | Logging con colores en consola |
| `pytest` | >= 7.0.0 | Framework de testing (desarrollo) |
| `black` | >= 22.0.0 | Formateador de codigo (desarrollo) |
| `flake8` | >= 4.0.0 | Linter de codigo (desarrollo) |

Verificar la instalacion:

```bash
pip list | grep -E "pandas|psycopg2|statsmodels"
```

### 2.4 Configurar archivo .env

El archivo `.env` contiene todas las variables de configuracion del sistema. **Este archivo es confidencial y no debe compartirse ni subirse a repositorios.**

**Paso 1:** Crear el archivo `.env` a partir del ejemplo:

```bash
# Si existe .env.example:
cp .env.example .env

# Si no existe, crear uno nuevo:
touch .env    # Linux
type nul > .env    # Windows
```

**Paso 2:** Editar el archivo `.env` con los valores correspondientes a su entorno:

```ini
# =============================================
# CONFIGURACION DE BASE DE DATOS
# =============================================
DB_HOST=192.168.80.85
DB_PORT=5432
DB_NAME=dwh_saiv
DB_SCHEMA=auto
DB_USER=automatizacion
DB_PASSWORD=<CONTRASENA_PROPORCIONADA_POR_DBA>
DB_TYPE=postgresql

# =============================================
# CONFIGURACION DE OPENROUTER (Opcional - IA)
# =============================================
OPENROUTER_API_KEY=<SU_API_KEY_OPENROUTER>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=anthropic/claude-opus-4.1
FALLBACK_MODEL=anthropic/claude-sonnet-4

# =============================================
# CONFIGURACION DEL REPORTE
# =============================================
REPORT_OUTPUT_PATH=./output/
COMPANY_NAME=DYM
CURRENT_YEAR=2026
PREVIOUS_YEAR=2025

# =============================================
# CONFIGURACION DE LOGGING
# =============================================
LOG_LEVEL=INFO
LOG_FILE=wsr_generator.log
```

**Tabla de referencia de variables:**

| Variable | Descripcion | Valor por defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `DB_HOST` | IP del servidor DWH | 192.168.80.85 | Si |
| `DB_PORT` | Puerto PostgreSQL | 5432 | Si |
| `DB_NAME` | Nombre de la base de datos | dwh_saiv | Si |
| `DB_SCHEMA` | Esquema de base de datos | auto | Si |
| `DB_USER` | Usuario de base de datos | automatizacion | Si |
| `DB_PASSWORD` | Contrasena del usuario DB | — | Si |
| `DB_TYPE` | Tipo de motor de base de datos | postgresql | Si |
| `OPENROUTER_API_KEY` | API Key para OpenRouter | — | No (desactiva analisis IA) |
| `OPENROUTER_BASE_URL` | URL base de la API OpenRouter | https://openrouter.ai/api/v1 | No |
| `DEFAULT_MODEL` | Modelo LLM principal | anthropic/claude-opus-4.1 | No |
| `FALLBACK_MODEL` | Modelo LLM de respaldo | anthropic/claude-sonnet-4 | No |
| `REPORT_OUTPUT_PATH` | Directorio para reportes generados | ./output/ | Si |
| `COMPANY_NAME` | Nombre de la empresa en el reporte | DYM | Si |
| `CURRENT_YEAR` | Ano fiscal actual | (ano actual) | Si |
| `PREVIOUS_YEAR` | Ano fiscal anterior (comparacion) | (ano actual - 1) | Si |
| `LOG_LEVEL` | Nivel de log (DEBUG, INFO, WARNING, ERROR) | INFO | Si |
| `LOG_FILE` | Nombre del archivo de log | wsr_generator.log | Si |

> **Precaucion:** El archivo `.env` contiene credenciales sensibles. En Linux, configure permisos restrictivos: `chmod 600 .env`. En Windows, asegurese de que solo el usuario de servicio tenga acceso de lectura.

### 2.5 Crear estructura de directorios

El proyecto incluye un script de setup que crea las carpetas necesarias:

```bash
python setup.py
```

Este script:
- Crea los directorios: `core/`, `utils/`, `templates/`, `output/`, `logs/`, `data/`, `tests/`
- Crea archivos `__init__.py` donde sean necesarios
- Verifica que las dependencias principales estan instaladas
- Muestra instrucciones de configuracion

> **Nota:** Si las carpetas ya existen (porque clono el repositorio completo), el script las omite sin errores.

---

## 3. Verificacion de la instalacion

### 3.1 Test de conexion a base de datos

Ejecute el siguiente comando para verificar la conexion al DWH:

```bash
python -c "
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cur = conn.cursor()
    cur.execute('SELECT current_database(), current_user, version()')
    db, user, ver = cur.fetchone()
    print(f'Conexion exitosa!')
    print(f'  Base de datos: {db}')
    print(f'  Usuario: {user}')
    print(f'  Version PostgreSQL: {ver[:50]}...')
    cur.close()
    conn.close()
except Exception as e:
    print(f'Error de conexion: {e}')
"
```

**Resultado esperado:**

```
Conexion exitosa!
  Base de datos: dwh_saiv
  Usuario: automatizacion
  Version PostgreSQL: PostgreSQL 14.x ...
```

### 3.2 Test de dependencias

```bash
python -c "
import pandas; print(f'pandas: {pandas.__version__}')
import numpy; print(f'numpy: {numpy.__version__}')
import psycopg2; print(f'psycopg2: {psycopg2.__version__}')
import statsmodels; print(f'statsmodels: {statsmodels.__version__}')
import dotenv; print(f'python-dotenv: OK')
import openai; print(f'openai: {openai.__version__}')
print('Todas las dependencias instaladas correctamente.')
"
```

### 3.3 Ejecucion de prueba

```bash
python wsr_generator_main.py
```

**Criterios de exito:**

1. No hay errores de tipo `ModuleNotFoundError`
2. La conexion a la base de datos se establece exitosamente
3. Se genera un archivo `.html` en la carpeta `output/`
4. El reporte se abre automaticamente en el navegador
5. El reporte contiene datos y todas las secciones son visibles

**Tiempo esperado de la primera ejecucion:** 2-5 minutos.

### 3.4 Verificar el reporte generado

Abra el archivo generado en `output/` y verifique:

- El encabezado muestra "WEEKLY SALES REPORT - DYM"
- El resumen ejecutivo muestra KPIs con valores numericos (no "N/D" en todo)
- Las tablas de marca, ciudad y canal tienen datos
- El grafico de tendencia se renderiza (requiere conexion a internet para Chart.js CDN)
- El pie de pagina muestra la fecha, version y tipo de cambio

---

## 4. Configuracion de ejecucion automatica

### 4.1 Linux: Cron job

Para ejecutar el WSR automaticamente cada lunes a las 8:00 AM:

**Paso 1:** Abrir el crontab del usuario:

```bash
crontab -e
```

**Paso 2:** Agregar la siguiente linea:

```cron
# WSR Generator DyM - Cada lunes a las 8:00 AM
0 8 * * 1 cd /opt/aplicaciones/wsr_generator_dym && /opt/aplicaciones/wsr_generator_dym/venv/bin/python wsr_generator_main.py >> /opt/aplicaciones/wsr_generator_dym/logs/cron_output.log 2>&1
```

**Desglose del cron:**

| Campo | Valor | Significado |
|-------|-------|-------------|
| Minuto | 0 | A los 0 minutos |
| Hora | 8 | A las 8:00 AM |
| Dia del mes | * | Cualquier dia |
| Mes | * | Cualquier mes |
| Dia de la semana | 1 | Lunes |

> **Importante:** Use **rutas absolutas** tanto para el directorio del proyecto como para el ejecutable de Python dentro del venv. Las rutas relativas no funcionan en cron.

**Paso 3:** Verificar que el cron esta registrado:

```bash
crontab -l
```

### 4.2 Windows: Task Scheduler (paso a paso)

**Paso 1:** Abrir el Programador de Tareas
- Presione `Win + R`, escriba `taskschd.msc` y presione Enter

**Paso 2:** Crear tarea basica
- En el panel derecho, clic en **"Crear tarea..."** (no "Crear tarea basica")

**Paso 3:** Pestana "General"
- Nombre: `WSR Generator DyM`
- Descripcion: `Genera el reporte semanal de ventas DyM cada lunes`
- Marcar: **"Ejecutar tanto si el usuario ha iniciado sesion como si no"**
- Marcar: **"Ejecutar con los privilegios mas altos"**

**Paso 4:** Pestana "Desencadenadores"
- Clic en "Nuevo..."
- Iniciar la tarea: **Segun una programacion**
- Configuracion: **Semanalmente**
- Inicio: (seleccionar el proximo lunes a las 08:00)
- Repetir cada: **1 semana**
- Dias: marcar solo **Lunes**
- Aceptar

**Paso 5:** Pestana "Acciones"
- Clic en "Nuevo..."
- Accion: **Iniciar un programa**
- Programa o script: `C:\Aplicaciones\wsr_generator_dym\run_wsr.bat`
- Iniciar en: `C:\Aplicaciones\wsr_generator_dym`
- Aceptar

**Paso 6:** Pestana "Condiciones"
- Desmarcar: "Iniciar la tarea solo si el equipo esta conectado a CA"
- Marcar: "Activar el equipo para ejecutar esta tarea" (si es un servidor)

**Paso 7:** Pestana "Configuracion"
- Marcar: "Permitir que la tarea se ejecute a peticion"
- Marcar: "Si la tarea no finaliza en 30 min, detenerla"
- Aceptar e ingresar credenciales del usuario Windows

### 4.3 Script BAT alternativo (Windows)

Cree el archivo `run_wsr.bat` en la raiz del proyecto:

```bat
@echo off
REM =============================================
REM  WSR Generator DyM - Script de ejecucion
REM =============================================
REM  Este script activa el venv y ejecuta el generador.
REM  Usar con Task Scheduler para ejecucion automatica.
REM =============================================

cd /d "C:\Aplicaciones\wsr_generator_dym"

echo [%date% %time%] Iniciando WSR Generator... >> logs\bat_execution.log

call venv\Scripts\activate.bat

python wsr_generator_main.py >> logs\bat_execution.log 2>&1

echo [%date% %time%] Ejecucion finalizada. >> logs\bat_execution.log
```

> **Nota:** Ajuste la ruta `C:\Aplicaciones\wsr_generator_dym` a la ubicacion real de su instalacion.

---

## 5. Configuracion de envio por correo (opcional)

### 5.1 Opcion A: SMTP corporativo

Si la empresa cuenta con un servidor SMTP, puede configurar un script de envio automatico que se ejecute despues del generador.

Cree el archivo `enviar_reporte.py`:

```python
import smtplib
import os
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# Configuracion SMTP
SMTP_HOST = "smtp.empresa.com"
SMTP_PORT = 587
SMTP_USER = "reportes@empresa.com"
SMTP_PASSWORD = "password"

# Destinatarios
DESTINATARIOS = [
    "gerencia.comercial@empresa.com",
    "gerencia.general@empresa.com",
]

# Encontrar el reporte mas reciente
output_dir = os.path.join(os.path.dirname(__file__), 'output')
reportes = sorted(glob.glob(os.path.join(output_dir, 'WSR_DYM_*.html')))

if not reportes:
    print("No se encontraron reportes para enviar.")
    exit(1)

ultimo_reporte = reportes[-1]
nombre_archivo = os.path.basename(ultimo_reporte)

# Construir email
msg = MIMEMultipart()
msg['From'] = SMTP_USER
msg['To'] = ', '.join(DESTINATARIOS)
msg['Subject'] = f'WSR DyM - Reporte Semanal ({nombre_archivo})'

body = """
Estimados,

Adjunto encontraran el Reporte Semanal de Ventas (WSR) de DyM.

Este reporte fue generado automaticamente por el WSR Generator v3.0.

Saludos cordiales,
Equipo de Sistemas
"""

msg.attach(MIMEText(body, 'plain'))

# Adjuntar reporte
with open(ultimo_reporte, 'rb') as f:
    part = MIMEBase('text', 'html')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{nombre_archivo}"')
    msg.attach(part)

# Enviar
try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()
    print(f"Reporte enviado exitosamente a {len(DESTINATARIOS)} destinatarios.")
except Exception as e:
    print(f"Error al enviar: {e}")
```

### 5.2 Opcion B: Script post-ejecucion

Modifique el archivo `.bat` o cron para ejecutar el envio despues de la generacion:

**Linux (cron):**
```cron
0 8 * * 1 cd /opt/wsr && ./venv/bin/python wsr_generator_main.py && ./venv/bin/python enviar_reporte.py >> logs/cron.log 2>&1
```

**Windows (BAT):**
```bat
python wsr_generator_main.py >> logs\execution.log 2>&1
python enviar_reporte.py >> logs\execution.log 2>&1
```

### 5.3 Opcion C: Power Automate / Outlook

Para entornos Microsoft 365, una alternativa sin codigo es usar **Power Automate**:

1. Crear un flujo que monitoree la carpeta `output/` en busca de nuevos archivos `.html`
2. Cuando detecte un archivo nuevo, enviarlo como adjunto a los destinatarios configurados
3. Opcionalmente, mover el archivo a una carpeta de "enviados" para evitar reenvios

Esta opcion requiere que la carpeta `output/` sea accesible desde OneDrive o SharePoint.

---

## 6. Diagrama de arquitectura

### 6.1 Flujo de datos del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WSR GENERATOR DyM v3.0                          │
│                    Diagrama de Arquitectura                          │
└─────────────────────────────────────────────────────────────────────┘

  ┌─────────────┐         ┌─────────────────────┐
  │  PostgreSQL  │         │   OpenRouter API     │
  │  DWH (dwh_  │         │   (openrouter.ai)    │
  │   saiv)     │         │                      │
  │             │         │  claude-opus-4.1     │
  │ 192.168.80  │         │  claude-sonnet-4     │
  │ .85:5432    │         │  (fallback)          │
  └──────┬──────┘         └──────────┬───────────┘
         │ SQL (psycopg2)            │ HTTPS (openai SDK)
         │ Puerto 5432               │ Puerto 443
         │                           │
         ▼                           ▼
  ┌──────────────────────────────────────────────┐
  │          wsr_generator_main.py                │
  │          (Orquestador principal)              │
  │                                               │
  │  1. Conectar a DB                             │
  │  2. Fetch datos (5 dimensiones)               │
  │  3. Procesar KPIs                             │
  │  4. Generar analisis IA (opcional)            │
  │  5. Generar graficos                          │
  │  6. Generar Proyeccion Objetiva               │
  │  7. Ensamblar HTML                            │
  │  8. Guardar en output/                        │
  └───────────────────────┬──────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │  core/       │ │  utils/      │ │ proyeccion_  │
  │              │ │              │ │ objetiva/    │
  │ database.py  │ │ business_    │ │              │
  │ data_        │ │ days.py      │ │ Pilar 1:     │
  │ processor.py │ │              │ │ PY Gerente   │
  │ html_        │ │ llm_         │ │              │
  │ generator.py │ │ processor.py │ │ Pilar 2:     │
  │ trend_chart_ │ │              │ │ Holt-Winters │
  │ generator.py │ │ html_        │ │              │
  │              │ │ tables.py    │ │ Pilar 3:     │
  └──────────────┘ └──────────────┘ │ Revenue Tree │
                                    └──────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │     output/          │
              │                      │
              │  WSR_DYM_2025_10_    │
              │  20251028_143022     │
              │  .html               │
              │                      │
              │  (500KB - 2MB,       │
              │   autocontenido)     │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Navegador Web      │
              │   (apertura auto)    │
              └──────────────────────┘
```

### 6.2 Tablas de base de datos consultadas

```
  Schema: auto
  ┌─────────────────────────────────────────────────────────┐
  │                    DWH (dwh_saiv)                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ td_ventas_bob_historico     │ ← Ventas diarias       │
  │  │ (principal fuente de datos) │   por marca/ciudad/     │
  │  │                             │   canal/subfamilia     │
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ factpresupuesto_general     │ ← Presupuesto anual    │
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ factpresupuesto_mensual     │ ← SOP mensual          │
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ fact_proyecciones           │ ← Proyecciones de      │
  │  │                             │   gerentes regionales  │
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ td_stock_sap               │ ← Stock actual SAP      │
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ fact_eficiencia_hitrate     │ ← Datos de visitas      │
  │  │                             │   y eficiencia comercial│
  │  └─────────────────────────────┘                        │
  │                                                          │
  │  ┌─────────────────────────────┐                        │
  │  │ FactVentas                  │ ← Ventas granulares     │
  │  │                             │   (modulo proyeccion)  │
  │  └─────────────────────────────┘                        │
  └─────────────────────────────────────────────────────────┘
```

### 6.3 Puertos y servicios requeridos

| Servicio | Protocolo | Puerto | Direccion | Notas |
|----------|-----------|--------|-----------|-------|
| PostgreSQL (DWH) | TCP | 5432 | Servidor → 192.168.80.85 | Unico requisito de red interna |
| OpenRouter API | HTTPS | 443 | Servidor → Internet | Opcional. Solo para analisis IA |
| Chart.js CDN | HTTPS | 443 | Navegador → Internet | Solo al visualizar el reporte |

> **Nota:** Si la red no permite acceso a Internet, el analisis IA se desactiva automaticamente (el reporte sigue generandose) y el grafico de tendencia no se renderizara al abrir el HTML.

---

## 7. Validacion final post-instalacion

Una vez completados todos los pasos, ejecute esta lista de verificacion:

| # | Verificacion | Comando / Accion | Resultado esperado |
|---|-------------|-------------------|-------------------|
| 1 | Python instalado | `python --version` | Python 3.8+ |
| 2 | Venv activado | `which python` (Linux) o `where python` (Win) | Ruta dentro de venv/ |
| 3 | Dependencias OK | `pip list \| grep pandas` | pandas >= 1.5.0 |
| 4 | Archivo .env existe | `ls -la .env` | Archivo presente con permisos 600 |
| 5 | Conexion a DB | Test de seccion 3.1 | "Conexion exitosa!" |
| 6 | Carpeta output/ existe | `ls output/` | Directorio existe (puede estar vacio) |
| 7 | Ejecucion completa | `python wsr_generator_main.py` | Archivo .html generado en output/ |
| 8 | Reporte visualizable | Abrir .html en navegador | Reporte con datos y graficos |
| 9 | Tarea programada | Verificar en cron/Task Scheduler | Tarea configurada para lunes 8:00 AM |
| 10 | Log funcional | `cat wsr_generator.log` | Registros de la ultima ejecucion |

---

## 8. Desinstalacion

Si necesita desinstalar el sistema:

```bash
# 1. Remover la tarea programada
crontab -e    # Linux: eliminar la linea del WSR
# Windows: eliminar la tarea en Task Scheduler

# 2. (Opcional) Respaldar reportes generados
cp -r output/ /ruta/backup/wsr_reportes/

# 3. Eliminar el directorio del proyecto
rm -rf /opt/aplicaciones/wsr_generator_dym

# 4. (Opcional) Solicitar al DBA revocar credenciales de DB
```

> **Precaucion:** Antes de desinstalar, asegurese de respaldar los reportes historicos de la carpeta `output/` si son necesarios para referencia futura.

---

## 9. Contacto de soporte para instalacion

| Contacto | Rol | Email | Cuando contactar |
|----------|-----|-------|------------------|
| Fabiola Bowles | Desarrolladora del sistema | fbowles@theblankinc.com | Errores de instalacion, configuracion |
| Equipo DBA | Administrador de base de datos | (Consultar con IT) | Credenciales de DB, permisos, conectividad |
| Equipo de Redes | Infraestructura de red | (Consultar con IT) | Firewall, acceso a puertos |
