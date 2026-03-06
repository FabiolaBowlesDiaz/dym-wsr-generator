---
titulo: Manual de Mantenimiento
subtitulo: WSR Generator DyM — Arquitectura, diagnostico, actualizaciones y soporte
version: 3.0
fecha: Marzo 2026
audiencia: Gerencia de IT / Administrador del sistema
---

# Manual de Mantenimiento — WSR Generator DyM

## 1. Arquitectura del sistema

### 1.1 Diagrama de modulos

El sistema esta compuesto por **3 capas principales** y un modulo especializado de proyeccion:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE ORQUESTACION                          │
│                                                                  │
│  wsr_generator_main.py ─── Punto de entrada principal           │
│  generate_report.py ────── Runner simplificado (wrapper)        │
│  setup.py ──────────────── Scaffolding inicial del proyecto     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   CAPA CORE      │ │   CAPA UTILS     │ │  MODULO PROYECCION   │
│                  │ │                  │ │  OBJETIVA            │
│ database.py      │ │ business_days.py │ │                      │
│  └ DatabaseMgr   │ │  └ BusinessDays  │ │ config.py            │
│  └ SQL queries   │ │  └ Feriados BOL  │ │ projection_          │
│  └ Conexion PG   │ │                  │ │  processor.py        │
│                  │ │ llm_processor.py │ │ data_fetcher.py      │
│ data_processor   │ │  └ OpenRouter    │ │                      │
│  .py             │ │  └ Fallback      │ │ pilar2_estadistica/  │
│  └ KPI calcs     │ │                  │ │  └ statistical_      │
│  └ Consolidacion │ │ html_tables.py   │ │    engine.py         │
│  └ Hit Rate      │ │  └ Tablas perf.  │ │  └ event_calendar.py │
│                  │ │  └ Drill-down    │ │                      │
│ html_generator   │ │  └ Semanal       │ │ pilar3_operativa/    │
│  .py             │ │                  │ │  └ decomposition_    │
│  └ CSS/Layout    │ └──────────────────┘ │    engine.py         │
│  └ Ensamblado    │                      │                      │
│  └ Footer        │                      │ visualizacion/       │
│                  │                      │  └ Charts + HTML     │
│ trend_chart_     │                      │                      │
│  generator.py    │                      │ tests/               │
│  └ Chart.js      │                      │  └ Unit tests        │
│  └ Multi-ciudad  │                      └──────────────────────┘
└──────────────────┘
```

### 1.2 Flujo de datos completo

El flujo de ejecucion sigue este orden estricto:

```
 INICIO
   │
   ▼
 1. Cargar configuracion (.env)
   │
   ▼
 2. Conectar a PostgreSQL (dwh_saiv)
   │
   ▼
 3. Fetch de datos (5 dimensiones × 8 sub-queries cada una)
   │  ├── Marca (+ subfamilia drill-down)
   │  ├── Ciudad (+ marca drill-down)
   │  ├── Canal
   │  ├── Ventas semanales (semanas calendario Lun-Dom)
   │  └── Stock y promedio diario
   │
   ▼
 4. Procesamiento de datos
   │  ├── Calcular KPIs: AV/PG, AV/SOP, PY/V, inc_precio, cobertura
   │  ├── Consolidar jerarquias: marca→subfamilia, ciudad→marca
   │  ├── Normalizar claves (.strip().title())
   │  └── Ordenar ciudades (orden fijo: SCZ→CBB→LPZ→...→TDD)
   │
   ▼
 5. Resumen ejecutivo
   │  ├── Agregar KPIs nacionales
   │  └── Calcular dias laborales (excluir domingos + feriados)
   │
   ▼
 6. Analisis de comentarios (opcional - requiere OpenRouter API)
   │  ├── Extraer comentarios de gerentes de fact_proyecciones
   │  ├── Enviar a Claude para analisis consolidado
   │  └── Fallback: agrupacion por region + keywords
   │
   ▼
 7. Grafico de tendencia (Chart.js)
   │  ├── Datos semanales reales + proyecciones
   │  ├── Multi-ciudad con selector de tabs
   │  └── SOP distribuido para ciudades sin gerente
   │
   ▼
 8. Proyeccion Objetiva Triple Pilar (opcional)
   │  ├── Pilar 1: PY Gerente (de fact_proyecciones)
   │  ├── Pilar 2: PY Estadistica (Holt-Winters)
   │  ├── Pilar 3: PY Operativa (Revenue Tree: Cob × HR × DS)
   │  └── Calculo de spread y diagnostico
   │
   ▼
 9. Hit Rate y Eficiencia
   │  ├── Consultar fact_eficiencia_hitrate
   │  └── Calcular metricas por ciudad/marca
   │
   ▼
 10. Generacion HTML
   │   ├── CSS inline (estilo DyM azul #1e3a8a)
   │   ├── Tablas interactivas con drill-down JS
   │   ├── Graficos Chart.js embebidos
   │   └── Footer con notas metodologicas
   │
   ▼
 11. Guardar en output/WSR_DYM_{YEAR}_{MONTH}_{TIMESTAMP}.html
   │
   ▼
 12. Abrir en navegador (webbrowser.open)
   │
   ▼
 FIN
```

### 1.3 Dependencias entre modulos

| Modulo | Depende de | Es usado por |
|--------|-----------|-------------|
| `database.py` | psycopg2, dotenv, pandas | wsr_generator_main.py |
| `data_processor.py` | pandas, numpy | wsr_generator_main.py |
| `html_generator.py` | (ninguno externo) | wsr_generator_main.py |
| `trend_chart_generator.py` | (ninguno externo) | wsr_generator_main.py |
| `business_days.py` | datetime | database.py, event_calendar.py |
| `llm_processor.py` | openai, requests | wsr_generator_main.py |
| `html_tables.py` | (ninguno externo) | html_generator.py |
| `statistical_engine.py` | statsmodels, scipy, numpy | projection_processor.py |
| `event_calendar.py` | business_days.py | statistical_engine.py |
| `decomposition_engine.py` | pandas, numpy | projection_processor.py |
| `projection_processor.py` | Pilar 2 + Pilar 3 + data_fetcher | wsr_generator_main.py |

---

## 2. Logs y monitoreo

### 2.1 Ubicacion del log

El archivo de log principal se encuentra en la **raiz del proyecto**:

```
wsr_generator.log
```

Adicionalmente, si se usa ejecucion automatica con BAT o cron, los logs de ejecucion se guardan en:

```
logs/cron_output.log        # Linux (cron)
logs/bat_execution.log      # Windows (BAT)
```

### 2.2 Niveles de log

El sistema usa 4 niveles de logging, configurables via la variable `LOG_LEVEL` en `.env`:

| Nivel | Cuando se usa | Ejemplo |
|-------|--------------|---------|
| **DEBUG** | Informacion detallada de depuracion | `Query ejecutada: SELECT ... (1.2s)` |
| **INFO** | Progreso normal de ejecucion | `Obteniendo datos de ventas historicas...` |
| **WARNING** | Situacion inesperada pero no critica | `API OpenRouter no responde, usando fallback` |
| **ERROR** | Error que impide completar una seccion | `Error de conexion a DB: Connection refused` |

> **Recomendacion:** En produccion, usar `LOG_LEVEL=INFO`. Solo cambiar a `DEBUG` cuando se este diagnosticando un problema especifico.

### 2.3 Que buscar: mensajes de exito vs error

**Ejecucion exitosa** — buscar estos mensajes en el log:

```
[INFO] Conexion exitosa.
[INFO] Reporte guardado: output/WSR_DYM_...html
[INFO] Abriendo reporte en navegador...
```

**Ejecucion con problemas** — buscar estos patrones:

```
[ERROR] Error de conexion a base de datos: ...
[ERROR] ModuleNotFoundError: No module named '...'
[WARNING] API OpenRouter: rate limit exceeded, switching to fallback
[WARNING] Sin datos de proyeccion para ...
[ERROR] Error generando Proyeccion Objetiva: ...
```

### 2.4 Comandos de diagnostico rapido

```bash
# Ver las ultimas 50 lineas del log
tail -50 wsr_generator.log

# Buscar errores en el log
grep -i "error" wsr_generator.log

# Buscar warnings
grep -i "warning" wsr_generator.log

# Ver log en tiempo real durante ejecucion
tail -f wsr_generator.log

# Contar errores por tipo
grep -c "ERROR" wsr_generator.log

# Ver la ultima ejecucion completa (desde "Iniciando" hasta "Reporte guardado")
grep -A 100 "Iniciando WSR" wsr_generator.log | head -100
```

---

## 3. Actualizaciones periodicas requeridas

### 3.1 Actualizacion anual (obligatoria — cada enero)

Al inicio de cada ano fiscal, se deben actualizar las siguientes configuraciones:

#### 3.1.1 Variables de entorno (.env)

Editar el archivo `.env`:

```ini
# Cambiar de:
CURRENT_YEAR=2025
PREVIOUS_YEAR=2024

# A:
CURRENT_YEAR=2026
PREVIOUS_YEAR=2025
```

#### 3.1.2 Verificar presupuestos del nuevo ano en la base de datos

Confirmar con el equipo de DWH/BI que las tablas de presupuesto estan cargadas:

```sql
-- Verificar presupuesto general del nuevo ano
SELECT COUNT(*), SUM(ingreso_neto_sus)
FROM auto.factpresupuesto_general
WHERE tiempo_key LIKE '2026%';

-- Verificar SOP mensual
SELECT COUNT(*), SUM(ingreso_neto_sus)
FROM auto.factpresupuesto_mensual
WHERE tiempo_key LIKE '2026%';
```

Si estas consultas devuelven 0 registros, el reporte no mostrara datos de presupuesto/SOP.

#### 3.1.3 Agregar feriados moviles en business_days.py

Los feriados moviles de Bolivia (Carnaval, Viernes Santo, Corpus Christi) cambian cada ano. Se deben agregar manualmente en el archivo `utils/business_days.py`.

**Ubicacion en el codigo:**

```python
# utils/business_days.py - buscar la seccion de feriados moviles
self.mobile_holidays = {
    2024: [(2, 12), (2, 13), (3, 29), (5, 30)],   # Carnaval, Viernes Santo, Corpus
    2025: [(3, 3), (3, 4), (4, 18), (6, 19)],
    2026: [(2, 16), (2, 17), (4, 3), (6, 4)],
    # Agregar aqui el nuevo ano:
    # 2027: [(mes, dia), (mes, dia), (mes, dia), (mes, dia)],
}
```

**Formato:** `(mes, dia)` — cada ano tiene 4 entradas:
1. Lunes de Carnaval
2. Martes de Carnaval
3. Viernes Santo
4. Corpus Christi

> **Importante:** Estos feriados se calculan basandose en la fecha de Pascua. Consultar el calendario oficial de Bolivia para el ano correspondiente. Carnaval es 47 dias antes de Pascua, Corpus Christi es 60 dias despues.

#### 3.1.4 Verificar ciudades sin gerente

Revisar en `core/database.py` el metodo `_get_ciudades_sin_gerente()`:

```python
def _get_ciudades_sin_gerente(self, year: int) -> tuple:
    if year >= 2026:
        return ('TRINIDAD',)  # Oruro tiene gerente desde 2026
    else:
        return ('ORURO', 'TRINIDAD')
```

Si alguna ciudad nueva obtiene (o pierde) un gerente regional, actualizar esta logica.

### 3.2 Actualizacion de API Key OpenRouter

Las API keys de OpenRouter pueden expirar o ser revocadas. Para renovar:

1. Ir a [openrouter.ai](https://openrouter.ai) y generar una nueva API key
2. Actualizar en `.env`:

```ini
OPENROUTER_API_KEY=sk-or-v1-NUEVA_KEY_AQUI
```

3. Verificar que la key funciona:

```bash
python -c "
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(
    base_url=os.getenv('OPENROUTER_BASE_URL'),
    api_key=os.getenv('OPENROUTER_API_KEY')
)
response = client.chat.completions.create(
    model='anthropic/claude-sonnet-4',
    messages=[{'role': 'user', 'content': 'Responde solo: OK'}],
    max_tokens=10
)
print(f'API Key valida. Respuesta: {response.choices[0].message.content}')
"
```

> **Nota:** Verifique tambien que la cuenta de OpenRouter tenga creditos disponibles. El consumo promedio del WSR es de 1-2 llamadas por ejecucion, con ~1000 tokens por llamada.

### 3.3 Actualizacion de dependencias Python

Periodicamente (cada 6 meses recomendado), actualizar las dependencias a versiones con parches de seguridad:

```bash
# Activar venv
source venv/bin/activate    # Linux
venv\Scripts\activate       # Windows

# Actualizar pip
pip install --upgrade pip

# Actualizar dependencias (respetando los minimos de requirements.txt)
pip install --upgrade -r requirements.txt

# Verificar que no hay conflictos
pip check

# Ejecutar tests para validar
python -m pytest tests/ -v
```

> **Precaucion:** Antes de actualizar en produccion, probar en un entorno de desarrollo. Las actualizaciones mayores de `pandas` o `statsmodels` podrian cambiar comportamientos.

### 3.4 Cambios en logica de negocio

Los siguientes cambios de negocio requieren modificacion de codigo:

#### 3.4.1 Ciudad nueva obtiene/pierde gerente

**Archivo:** `core/database.py` → metodo `_get_ciudades_sin_gerente()`

**Tambien actualizar:** `core/trend_chart_generator.py` → distribucion SOP semanal (si la ciudad usaba SOP y ahora tiene gerente, se puede remover su distribucion personalizada).

#### 3.4.2 Cambio en distribucion SOP por semana

**Archivos a modificar:**

En `core/database.py`:
```python
# Buscar las distribuciones porcentuales
# ORURO: S1=8%, S2=12%, S3=20%, S4=28%, S5=32%
# TRINIDAD: S1=25%, S2=18%, S3=22%, S4=20%, S5=15%
```

En `core/trend_chart_generator.py`:
```python
# Nota: Trinidad tiene distribucion DIFERENTE en el grafico
# TRINIDAD (chart): S1=25%, S2=45%, S3=20%, S4=10%, S5=0%
```

> **Advertencia:** La distribucion SOP en el grafico de tendencia (`trend_chart_generator.py`) es DIFERENTE a la del modulo de base de datos (`database.py`) para Trinidad. Si se cambia una, considerar si la otra tambien debe cambiar.

#### 3.4.3 Exclusiones de marcas, ciudades o canales

**Archivo:** `core/database.py` — Las exclusiones estan hardcodeadas en TODAS las consultas SQL:

```sql
WHERE UPPER(ciudad) != 'TURISMO'
  AND UPPER(canal) != 'TURISMO'
  AND UPPER(marcadir) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
```

Si se necesita agregar o quitar exclusiones, se deben modificar **todas las consultas** en `database.py`.

#### 3.4.4 Cambio de tipo de cambio

**Archivos a modificar:**

1. `core/database.py` — variable `self.tipo_cambio = 6.96`
2. Verificar tambien en el footer del reporte (`core/html_generator.py`)

---

## 4. Solucion de problemas

### 4.1 Tabla de errores comunes

| Error | Causa probable | Solucion |
|-------|---------------|----------|
| `ConnectionRefusedError: [Errno 111] Connection refused` | Servidor DWH apagado o inaccesible | 1. Verificar que el servidor 192.168.80.85 esta encendido. 2. Ejecutar `ping 192.168.80.85`. 3. Verificar que el puerto 5432 esta abierto: `telnet 192.168.80.85 5432`. 4. Contactar al DBA |
| `psycopg2.OperationalError: FATAL: password authentication failed` | Credenciales incorrectas en .env | Verificar DB_USER y DB_PASSWORD en .env. Contactar al DBA si la contrasena fue cambiada |
| `psycopg2.OperationalError: FATAL: database "dwh_saiv" does not exist` | Nombre de base de datos incorrecto | Verificar DB_NAME en .env |
| `ModuleNotFoundError: No module named 'pandas'` | Entorno virtual no activado o dependencias no instaladas | 1. Activar venv: `source venv/bin/activate`. 2. Reinstalar: `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'statsmodels'` | Dependencia de proyeccion no instalada | `pip install statsmodels scipy` |
| `openai.AuthenticationError: Invalid API key` | API key de OpenRouter invalida o expirada | Actualizar OPENROUTER_API_KEY en .env. Ver seccion 3.2 |
| `openai.RateLimitError: Rate limit exceeded` | Demasiadas peticiones a OpenRouter | El sistema hace fallback automatico al modelo secundario. Si persiste, esperar 1 minuto y reintentar |
| Reporte generado pero sin datos (tablas vacias) | DWH no tiene datos del periodo actual | 1. Verificar que el ETL diario se ejecuto. 2. Confirmar CURRENT_YEAR en .env. 3. Ejecutar: `SELECT COUNT(*) FROM auto.td_ventas_bob_historico WHERE anio = 2026 AND mes = 3` |
| Reporte generado pero sin grafico | Navegador sin acceso a Internet (Chart.js CDN) | El grafico requiere cargar Chart.js desde CDN. Abrir el reporte en un equipo con acceso a Internet |
| Cron no ejecuta en Linux | Rutas relativas, venv no activado, permisos | 1. Usar rutas absolutas. 2. Llamar Python del venv directamente: `/path/venv/bin/python`. 3. Verificar permisos: `chmod +x wsr_generator_main.py` |
| Task Scheduler no ejecuta en Windows | Usuario sin permiso "Log on as batch job" | En GPO local, agregar el usuario a "Log on as a batch job". Verificar que la tarea usa la ruta correcta al .bat |
| `PermissionError: [Errno 13] Permission denied: 'output/...'` | Sin permisos de escritura en output/ | `chmod 775 output/` (Linux) o verificar permisos NTFS (Windows) |
| `UnicodeEncodeError` en consola Windows | Consola no soporta caracteres especiales | Usar `generate_report.py` en lugar de `wsr_generator_main.py` (maneja encoding) |

### 4.2 Procedimiento de diagnostico paso a paso

Ante cualquier fallo, seguir este flujo:

**Paso 1: Verificar el log**

```bash
tail -30 wsr_generator.log
grep -i "error\|warning" wsr_generator.log | tail -20
```

**Paso 2: Verificar conectividad de red**

```bash
# Ping al servidor DWH
ping 192.168.80.85

# Verificar puerto PostgreSQL
# Linux:
nc -zv 192.168.80.85 5432
# Windows:
Test-NetConnection -ComputerName 192.168.80.85 -Port 5432
```

**Paso 3: Verificar entorno Python**

```bash
# Verificar que el venv esta activo
which python    # Linux: debe mostrar ruta dentro de venv/
where python    # Windows: debe mostrar ruta dentro de venv\

# Verificar dependencias
pip check
```

**Paso 4: Verificar configuracion**

```bash
# Verificar que .env existe y tiene contenido
cat .env | grep -v PASSWORD    # No mostrar contrasenas en pantalla

# Verificar que las variables se cargan
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DB_HOST'))"
```

**Paso 5: Ejecucion con log DEBUG**

Cambiar temporalmente en `.env`:

```ini
LOG_LEVEL=DEBUG
```

Ejecutar y revisar el log detallado. Restaurar a `INFO` despues del diagnostico.

**Paso 6: Test de conexion aislado**

```bash
python -c "
import psycopg2
conn = psycopg2.connect(host='192.168.80.85', port=5432, dbname='dwh_saiv', user='automatizacion', password='SU_PASSWORD')
cur = conn.cursor()
cur.execute('SELECT 1')
print('DB OK:', cur.fetchone())
conn.close()
"
```

**Paso 7: Escalamiento**

Si despues de los pasos anteriores el problema persiste, recopilar:
- Ultimo fragmento del log con el error
- Resultado de los tests de conectividad
- Version de Python (`python --version`)
- Lista de paquetes (`pip list`)

Enviar esta informacion a fbowles@theblankinc.com.

---

## 5. Backup y recuperacion

### 5.1 Backup de configuracion

Los archivos criticos que deben respaldarse son:

| Archivo | Contenido | Frecuencia de backup |
|---------|-----------|---------------------|
| `.env` | Credenciales y configuracion | Despues de cada cambio |
| `utils/business_days.py` | Feriados bolivianos | Despues de actualizacion anual |
| `core/database.py` | Si se modificaron queries | Despues de cada cambio |

**Comando de backup:**

```bash
# Crear backup con fecha
FECHA=$(date +%Y%m%d)
mkdir -p backups/
cp .env backups/.env_$FECHA
cp utils/business_days.py backups/business_days_$FECHA.py
```

### 5.2 Backup de reportes generados

Los reportes en `output/` son el producto final del sistema. Se recomienda:

```bash
# Copiar reportes a ubicacion de backup
cp -r output/ /ruta/backup/wsr_reportes/

# O comprimir por mes
tar czf backups/reportes_$(date +%Y%m).tar.gz output/WSR_DYM_$(date +%Y)_*.html
```

### 5.3 Limpieza de archivos antiguos

Para evitar acumulacion excesiva de reportes, se recomienda eliminar reportes de mas de 90 dias:

```bash
# Linux: eliminar reportes de mas de 90 dias
find output/ -name "WSR_DYM_*.html" -mtime +90 -delete

# Windows (PowerShell):
Get-ChildItem output\WSR_DYM_*.html | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } | Remove-Item
```

> **Precaucion:** Antes de eliminar, considere si los reportes historicos son necesarios para auditorias o comparaciones. Se recomienda respaldar antes de limpiar.

### 5.4 Rotacion de logs

El archivo de log puede crecer significativamente con el tiempo. Para rotar:

```bash
# Linux: configurar logrotate
# Crear /etc/logrotate.d/wsr_generator:
/opt/aplicaciones/wsr_generator_dym/wsr_generator.log {
    weekly
    rotate 12
    compress
    missingok
    notifempty
}

# Manual: rotar y comprimir
mv wsr_generator.log wsr_generator_$(date +%Y%m%d).log
gzip wsr_generator_$(date +%Y%m%d).log
```

En Windows, puede agregar al script `.bat` de ejecucion:

```bat
REM Rotar log si supera 10MB
for %%F in (wsr_generator.log) do if %%~zF GTR 10485760 (
    move wsr_generator.log logs\wsr_generator_%date:~-4%%date:~3,2%%date:~0,2%.log
)
```

---

## 6. Seguridad

### 6.1 Proteccion del archivo .env

El archivo `.env` contiene credenciales de base de datos y API keys. Debe estar protegido:

**Linux:**

```bash
# Solo el propietario puede leer/escribir
chmod 600 .env

# Verificar
ls -la .env
# -rw------- 1 usuario grupo 512 mar  5 10:00 .env
```

**Windows:**
- Click derecho en `.env` → Propiedades → Seguridad
- Remover acceso de "Usuarios" y "Todos"
- Solo mantener acceso para el usuario de servicio y Administradores

### 6.2 Usuario de base de datos con permisos minimos

El usuario `automatizacion` debe tener **solo permisos de lectura (SELECT)** en el esquema `auto`:

```sql
-- Verificar permisos (ejecutar como DBA)
SELECT privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'automatizacion'
  AND table_schema = 'auto';

-- Solo debe mostrar: SELECT
-- Si muestra INSERT, UPDATE, DELETE → contactar al DBA para revocar
```

> **Importante:** El WSR Generator **nunca escribe** en la base de datos. Si el usuario tiene permisos de escritura, es un riesgo innecesario.

### 6.3 Rotacion de API keys

Se recomienda rotar la API key de OpenRouter cada **6 meses**:

1. Generar nueva key en openrouter.ai
2. Actualizar en `.env`
3. Verificar funcionamiento (ver seccion 3.2)
4. Revocar la key anterior en OpenRouter

### 6.4 Permisos de directorio recomendados

| Directorio/Archivo | Permiso Linux | Descripcion |
|--------------------|--------------|-------------|
| Raiz del proyecto | 755 | Lectura y ejecucion para todos, escritura solo propietario |
| `.env` | 600 | Solo propietario lee/escribe |
| `output/` | 775 | Escritura para propietario y grupo |
| `logs/` | 775 | Escritura para propietario y grupo |
| `core/`, `utils/` | 755 | Lectura y ejecucion |
| `venv/` | 755 | Lectura y ejecucion |
| `*.py` (scripts) | 644 | Lectura para todos, escritura solo propietario |

### 6.5 Consideraciones de red

- El servidor WSR solo necesita acceso **saliente** al puerto 5432 (PostgreSQL) y 443 (HTTPS para OpenRouter)
- **No exponer** el servidor WSR a Internet
- Si es posible, colocar el servidor en la misma VLAN que el DWH para minimizar latencia y exposicion

---

## 7. Estructura de archivos del proyecto

### 7.1 Tabla completa de archivos

| Archivo | Proposito | Cuando modificar |
|---------|-----------|-----------------|
| `wsr_generator_main.py` | Punto de entrada principal, orquesta todo el flujo | Rara vez — solo si cambia el flujo general |
| `generate_report.py` | Runner alternativo con manejo de encoding | Nunca en condiciones normales |
| `setup.py` | Script de scaffolding inicial | Nunca despues de la instalacion inicial |
| `.env` | Variables de configuracion y credenciales | Anualmente (ano fiscal) o cuando cambian credenciales |
| `requirements.txt` | Dependencias Python | Al agregar nuevas dependencias |
| `core/database.py` | Todas las consultas SQL, conexion a DB | Al cambiar exclusiones, agregar queries, cambiar tipo de cambio |
| `core/data_processor.py` | Calculo de KPIs, consolidacion | Al cambiar formulas de KPIs o orden de ciudades |
| `core/html_generator.py` | CSS, estructura del reporte HTML, footer | Al cambiar estilo visual o notas del footer |
| `core/trend_chart_generator.py` | Grafico de tendencia Chart.js | Al cambiar distribucion SOP o colores del grafico |
| `utils/business_days.py` | Feriados bolivianos, calculo dias laborales | **Anualmente** — agregar feriados moviles del nuevo ano |
| `utils/llm_processor.py` | Integracion con OpenRouter (analisis IA) | Al cambiar modelo LLM o prompt de analisis |
| `utils/html_tables.py` | Generacion de todas las tablas del reporte | Al cambiar columnas, formato o drill-down |
| `proyeccion_objetiva/config.py` | Parametros del modulo de proyeccion | Al ajustar umbrales de HW, impacto de eventos, o WMA |
| `proyeccion_objetiva/projection_processor.py` | Orquestador de los 3 pilares | Rara vez |
| `proyeccion_objetiva/data_fetcher.py` | Queries SQL del modulo de proyeccion | Al cambiar tablas fuente de proyeccion |
| `proyeccion_objetiva/pilar2_estadistica/statistical_engine.py` | Modelo Holt-Winters | Al ajustar parametros estadisticos |
| `proyeccion_objetiva/pilar2_estadistica/event_calendar.py` | Ajuste de eventos moviles en forecast | Al agregar nuevos tipos de eventos |
| `proyeccion_objetiva/pilar3_operativa/decomposition_engine.py` | Arbol de ingresos (Cob × HR × DS) | Al cambiar pesos WMA o logica de proyeccion |
| `wsr_generator.log` | Log de ejecucion | No modificar — se genera automaticamente |
| `output/*.html` | Reportes generados | No modificar — son el producto final |

### 7.2 Archivos que NUNCA se deben modificar manualmente

| Archivo | Razon |
|---------|-------|
| `output/*.html` | Son el producto final generado automaticamente |
| `wsr_generator.log` | Log generado por el sistema |
| `venv/` (todo el directorio) | Gestionado por pip, no editar manualmente |
| `__pycache__/` | Cache de Python, se regenera automaticamente |
| `*.pyc` | Bytecode compilado de Python |

### 7.3 Archivos configurables por el administrador

| Archivo | Que se puede cambiar | Frecuencia |
|---------|---------------------|------------|
| `.env` | Credenciales, ano fiscal, nivel de log | Segun necesidad |
| `utils/business_days.py` | Feriados moviles | Anualmente |
| `core/database.py` | Tipo de cambio, exclusiones, ciudades sin gerente | Segun cambios de negocio |
| `proyeccion_objetiva/config.py` | Umbrales, pesos, impactos de eventos | Segun ajuste fino |

---

## 8. Reglas de negocio embebidas en el codigo

Esta seccion documenta todas las reglas de negocio que estan **hardcodeadas** en el codigo fuente, para referencia rapida del equipo de IT.

### 8.1 Tabla de referencia rapida

| Regla | Valor | Ubicacion en el codigo | Notas |
|-------|-------|----------------------|-------|
| **Tipo de cambio** | 6.96 BOB/USD | `database.py` linea ~31, footer del HTML | Se muestra en el pie de pagina de cada reporte |
| **Semanas calendario** | Lunes a Domingo, max 5 por mes | `database.py` metodo `get_calendar_week_ranges()` | Define como se segmentan las ventas semanales |
| **Dia no laboral** | Domingo (weekday == 6) | `business_days.py` | Sabados SI son laborales |
| **Feriados fijos** | 7: Ano Nuevo, Est. Plurinacional, Trabajo, Aymara, Independencia, Difuntos, Navidad | `business_days.py` | No cambian nunca |
| **Feriados moviles** | 4 por ano: 2 dias Carnaval + Viernes Santo + Corpus Christi | `business_days.py` | Actualizar anualmente |
| **Exclusion: ciudad** | TURISMO | Todas las queries en `database.py` | Se excluye de todo analisis |
| **Exclusion: canal** | TURISMO | Todas las queries en `database.py` | Se excluye de todo analisis |
| **Exclusion: marcas** | NINGUNA, SIN MARCA ASIGNADA | Todas las queries en `database.py` | Registros sin clasificar |
| **Orden de ciudades** | SCZ, CBB, LPZ, EA, TJA, SUC, ORU, POT, TDD | `data_processor.py` linea ~311 | Orden fijo en todas las tablas |
| **Ciudades sin gerente (<=2025)** | Oruro, Trinidad | `database.py` | Ambas usan SOP como proxy |
| **Ciudades sin gerente (>=2026)** | Trinidad | `database.py` | Solo Trinidad usa SOP |
| **SOP Oruro** | S1=8%, S2=12%, S3=20%, S4=28%, S5=32% | `database.py`, `trend_chart_generator.py` | Patron back-loaded |
| **SOP Trinidad (DB)** | S1=25%, S2=18%, S3=22%, S4=20%, S5=15% | `database.py` | Para calculo de proyeccion |
| **SOP Trinidad (Chart)** | S1=25%, S2=45%, S3=20%, S4=10%, S5=0% | `trend_chart_generator.py` | Para grafico visual (difiere de DB) |
| **Canal PY pesos** | R=10%, Q=4%, S=6%, T=80% | `database.py` linea ~1354 | T = avance actual domina la ponderacion |
| **Stock C9L formula** | `disponible × volumen / 9` | `database.py` | Conversion a cajas de 9 litros |
| **Cobertura: Critico** | < 15 dias | `html_generator.py` | Rojo |
| **Cobertura: Optimo** | 15-30 dias | `html_generator.py` | Verde |
| **Cobertura: Alto** | 30-60 dias | `html_generator.py` | Amarillo |
| **Cobertura: Exceso** | > 60 dias | `html_generator.py` | Naranja |
| **KPI positivo** | >= -5% (desviacion) | `html_tables.py` | CSS verde |
| **KPI neutral** | >= -15% (desviacion) | `html_tables.py` | CSS gris |
| **KPI negativo** | < -15% (desviacion) | `html_tables.py` | CSS rojo |
| **Cumplimiento alto** | >= 95% | `trend_chart_generator.py` | Verde en grafico |
| **Cumplimiento medio** | >= 85% | `trend_chart_generator.py` | Amarillo en grafico |
| **Cumplimiento bajo** | < 85% | `trend_chart_generator.py` | Rojo en grafico |
| **Hit Rate alto** | >= 70% | `data_processor.py` | — |
| **Hit Rate medio** | >= 50% | `data_processor.py` | — |
| **Eficiencia alta** | >= 80% | `data_processor.py` | — |
| **Eficiencia media** | >= 60% | `data_processor.py` | — |
| **LLM modelo principal** | anthropic/claude-opus-4.1 | `llm_processor.py` / `.env` | Via OpenRouter |
| **LLM fallback** | anthropic/claude-sonnet-4 | `llm_processor.py` / `.env` | Ante rate limit |
| **LLM temperatura** | 0.3 | `llm_processor.py` | Respuestas conservadoras |
| **LLM max tokens** | 1000 | `llm_processor.py` | Limita extension del analisis |
| **LLM timeout** | 30 segundos | `llm_processor.py` | Evita bloqueo prolongado |

### 8.2 Holt-Winters (Proyeccion Estadistica)

| Parametro | Valor | Ubicacion |
|-----------|-------|-----------|
| Meses minimos (triple) | 25 | `proyeccion_objetiva/config.py` |
| Meses minimos (doble) | 12 | `proyeccion_objetiva/config.py` |
| Meses minimos (absoluto) | 12 | `proyeccion_objetiva/config.py` |
| Umbral de zeros | 70% | `proyeccion_objetiva/config.py` |
| Ventana outlier | 5 meses | `proyeccion_objetiva/config.py` |
| Z-threshold outlier | 2.5 | `proyeccion_objetiva/config.py` |
| Periodo estacional | 12 meses | `proyeccion_objetiva/config.py` |

### 8.3 Revenue Tree (Proyeccion Operativa)

| Parametro | Valor | Ubicacion |
|-----------|-------|-----------|
| Pesos WMA | [0.5, 0.3, 0.2] | `proyeccion_objetiva/config.py` |
| Factor de dampening estacional | 0.7 + 0.3 × factor | `decomposition_engine.py` |
| Cap estacional | [0.5, 2.0] | `decomposition_engine.py` |

### 8.4 Spread y diagnostico

| Diagnostico | Condicion | Ubicacion |
|-------------|-----------|-----------|
| Optimista | Spread > +10% | `proyeccion_objetiva/config.py` |
| Conservador | Spread < -10% | `proyeccion_objetiva/config.py` |
| Consenso | Spread absoluto < 5% | `proyeccion_objetiva/config.py` |

### 8.5 Impacto de eventos moviles

| Evento | Factor | Efecto |
|--------|--------|--------|
| Carnaval | +15% | Incrementa venta del mes con carnaval |
| Viernes Santo | -2% | Efecto minimo negativo |
| Corpus Christi | 0% | Sin efecto significativo |

---

## 9. Contactos de soporte

| Contacto | Rol | Email | Cuando contactar |
|----------|-----|-------|------------------|
| **Fabiola Bowles** | Desarrolladora del sistema (The Blank Inc.) | fbowles@theblankinc.com | Bugs, cambios de logica, actualizaciones mayores del sistema |
| **DBA / Data Warehouse** | Administrador de base de datos | (Consultar con IT) | Problemas de conexion, datos faltantes en DWH, permisos |
| **Equipo de Sistemas/IT** | Infraestructura | (Consultar con IT) | Red, firewalls, Task Scheduler, servidores |
| **Analisis Comercial DyM** | Reglas de negocio | (Consultar con Comercial) | Cambios en exclusiones, umbrales, marcas, ciudades |

---

## 10. Historial de versiones del sistema

| Version | Fecha | Cambios principales |
|---------|-------|---------------------|
| **v1.0** | Sep 2025 | Version inicial: ventas por marca, ciudad, canal |
| **v2.0** | Oct 2025 | Agregar grafico de tendencia, hit rate, multi-ciudad |
| **v3.0** | Nov 2025 | Proyeccion Objetiva Triple Pilar (Holt-Winters + Revenue Tree), analisis LLM con fallback, drill-down subfamilia, SOP distribuido |

> **Nota:** Para cambios especificos entre versiones, consultar el historial de Git del repositorio.
