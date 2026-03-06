---
titulo: Manual de Uso
subtitulo: WSR Generator DyM — Guia completa para ejecutar el sistema e interpretar el reporte
version: 3.0
fecha: Marzo 2026
audiencia: Gerencia de IT / Usuarios finales
---

# Manual de Uso — WSR Generator DyM

## 1. Introduccion

### 1.1 Que es el WSR Generator

El **WSR Generator** (Weekly Sales Report Generator) es un sistema automatizado que genera el reporte semanal de ventas de DyM. El sistema se conecta al Data Warehouse corporativo (`dwh_saiv`), extrae informacion de ventas, presupuestos, proyecciones de gerentes, stock e indicadores de eficiencia comercial, y produce un **reporte HTML interactivo** listo para ser compartido por correo o presentado en reuniones gerenciales.

### 1.2 Que produce el sistema

El WSR Generator produce un **archivo HTML unico y autocontenido** que incluye:

- **Resumen ejecutivo** con KPIs nacionales y analisis de comentarios de gerentes
- **Performance por Marca** con drill-down a nivel subfamilia (BOB y C9L)
- **Performance por Ciudad** con drill-down a nivel marca
- **Performance por Canal** (Mayoreo, Detalle, etc.)
- **Grafico de tendencia interactivo** con selector multi-ciudad
- **Proyeccion Objetiva Triple Pilar** (Gerente, Estadistico, Operativo)
- **Analisis de Stock y Cobertura** con semaforizacion
- **Hit Rate y Eficiencia** de la fuerza de ventas

El archivo se nombra automaticamente con el patron:

```
WSR_DYM_{AÑO}_{MES}_{YYYYMMDD_HHMMSS}.html
```

Por ejemplo: `WSR_DYM_2025_10_20251028_143022.html`

### 1.3 Frecuencia de ejecucion

El sistema esta disenado para ejecutarse **cada lunes** al inicio de la jornada laboral, generando el reporte de la semana anterior. Sin embargo, puede ejecutarse en cualquier momento para obtener datos actualizados al dia.

> **Nota:** El reporte refleja los datos disponibles en el DWH al momento de la ejecucion. Si el DWH no ha sido actualizado con los datos del viernes/sabado, el reporte mostrara informacion incompleta para esa semana.

---

## 2. Ejecucion del sistema

### 2.1 Ejecucion manual (paso a paso)

Para ejecutar el sistema manualmente, siga estos pasos:

**Paso 1:** Abra una terminal (CMD o PowerShell en Windows, Terminal en Linux)

**Paso 2:** Navegue al directorio del proyecto:

```bash
cd /ruta/al/proyecto/aa_v3_dym_wsr_proyecto_2209_sia
```

**Paso 3:** Active el entorno virtual de Python:

```bash
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

**Paso 4:** Ejecute el generador:

```bash
python wsr_generator_main.py
```

Alternativamente, puede usar el script simplificado:

```bash
python generate_report.py
```

> **Nota:** `generate_report.py` es un wrapper que maneja la codificacion UTF-8 y proporciona logging sin emojis. Ambos scripts producen el mismo reporte.

### 2.2 Que esperar en consola

Durante la ejecucion, vera mensajes de progreso en la consola:

```
[INFO] Iniciando WSR Generator DyM v3.0...
[INFO] Conectando a base de datos dwh_saiv...
[INFO] Conexion exitosa.
[INFO] Obteniendo datos de ventas historicas...
[INFO] Obteniendo presupuesto general...
[INFO] Obteniendo SOP mensual...
[INFO] Obteniendo proyecciones de gerentes...
[INFO] Obteniendo datos de stock...
[INFO] Obteniendo ventas semanales...
[INFO] Procesando datos por marca...
[INFO] Procesando datos por ciudad...
[INFO] Procesando datos por canal...
[INFO] Generando analisis con IA...
[INFO] Generando grafico de tendencia...
[INFO] Generando Proyeccion Objetiva...
[INFO] Generando reporte HTML...
[INFO] Reporte guardado: output/WSR_DYM_2025_10_20251028_143022.html
[INFO] Abriendo reporte en navegador...
```

**Tiempos esperados:**
- Extraccion de datos: 30-60 segundos
- Procesamiento y calculo de KPIs: 10-20 segundos
- Analisis LLM (si esta habilitado): 15-30 segundos
- Generacion HTML: 5-10 segundos
- **Total estimado: 2-5 minutos**

### 2.3 Donde encontrar el reporte generado

El reporte se guarda en la carpeta `output/` dentro del directorio del proyecto:

```
proyecto/
└── output/
    ├── WSR_DYM_2025_09_20250929_091522.html
    ├── WSR_DYM_2025_10_20251028_143022.html
    └── WSR_DYM_2025_11_20251125_090115.html
```

Cada ejecucion genera un archivo nuevo (no sobreescribe anteriores), lo que permite mantener un historial de reportes.

### 2.4 Apertura automatica en navegador

Al finalizar la generacion, el sistema **abre automaticamente** el reporte en el navegador predeterminado del sistema. Si esto no ocurre, puede abrir manualmente el archivo `.html` con cualquier navegador moderno (Chrome, Firefox, Edge).

> **Importante:** El archivo HTML es **autocontenido** — no requiere conexion a internet para visualizarse, excepto para el grafico de tendencia que carga la libreria Chart.js desde CDN. Si necesita visualizacion completamente offline, contacte al equipo de desarrollo.

---

## 3. Interpretacion del reporte — Seccion por seccion

### 3.1 Resumen Ejecutivo

El resumen ejecutivo es la primera seccion del reporte y presenta una vision consolidada nacional.

#### KPIs nacionales

Se muestran como tarjetas (cards) en la parte superior:

| KPI | Descripcion | Formula |
|-----|-------------|---------|
| **Vendido (BOB)** | Venta acumulada del mes en bolivianos | Suma de ingresos netos del mes actual |
| **Presupuesto General (PG)** | Presupuesto anual prorrateado al mes | Del plan anual aprobado por directorio |
| **SOP** | Sales & Operations Plan mensual | Presupuesto mensual ajustado por operaciones |
| **Avance (AV)** | Porcentaje de avance vs SOP | `(Vendido / SOP) × 100` |
| **Proyeccion (PY)** | Proyeccion de cierre del mes | Hibrida: semanas cerradas (real) + futuras (gerente/SOP) |
| **Prior Year (PY ant.)** | Venta del mismo mes del ano anterior | Para comparacion interanual |

#### Semaforo de colores

Todos los KPIs porcentuales usan el siguiente semaforo de colores:

| Color | Condicion | Significado |
|-------|-----------|-------------|
| Verde | >= 95% (o desviacion >= -5%) | En linea o superando el objetivo |
| Amarillo | >= 85% (o desviacion >= -15%) | Atencion — por debajo pero recuperable |
| Rojo | < 85% (o desviacion < -15%) | Critico — requiere accion correctiva |

#### Dias laborales y progreso del mes

El resumen muestra:
- **Dias laborales transcurridos** vs **dias laborales totales del mes**
- **Porcentaje de avance del mes** (util para contextualizar si la venta va "a ritmo")
- Los dias laborales excluyen domingos y feriados bolivianos (sabados SI son laborales)

#### Analisis de comentarios

Debajo de los KPIs, el sistema presenta un analisis consolidado de los comentarios ingresados por los gerentes regionales en el sistema de proyecciones. Este analisis:

- Se genera automaticamente mediante **inteligencia artificial** (Claude via OpenRouter)
- Agrupa comentarios por region y tema
- Identifica patrones recurrentes: quiebres de stock, cupeos, contrabando, competencia, ferias
- Resalta marcas con desempeno critico (`AV/SOP < -30%`) y marcas estrella (`AV/SOP > +10%`)

> **Nota:** Si la API de OpenRouter no esta disponible, el sistema genera un analisis basico sin IA, agrupando comentarios por region y extrayendo palabras clave.

### 3.2 Performance por Marca

Esta seccion contiene **4 tablas** organizadas en pestanas:

#### Tabla BOB (Bolivianos) — Columnas y significado

| Columna | Descripcion |
|---------|-------------|
| **Marca** | Nombre de la marca (Havana, Casa Real, Gran Reserva, etc.) |
| **Vendido {ano anterior}** | Venta total del mismo mes del ano previo en BOB |
| **Ppto General** | Presupuesto general anual asignado a esta marca para el mes |
| **SOP** | Sales & Operations Plan mensual para esta marca |
| **Avance {ano}** | Venta acumulada del mes actual en BOB |
| **Proyeccion Cierre** | Proyeccion hibrida de cierre del mes |
| **PY/SOP** | `(Proyeccion / SOP) - 1` — Variacion proyeccion vs plan |
| **AV/PG** | `(Avance / Ppto General) - 1` — Variacion avance vs presupuesto |
| **AV/SOP** | `(Avance / SOP) - 1` — Variacion avance vs plan mensual |
| **PY/V** | `(Proyeccion / Vendido anterior) - 1` — Crecimiento interanual |
| **PY Est. (HW)** | Proyeccion estadistica Holt-Winters (si disponible) |
| **IngNeto/C9L {anterior}** | Precio promedio por C9L del ano anterior |
| **IngNeto/C9L {actual}** | Precio promedio por C9L del ano actual |
| **%Inc Precio** | Incremento de precio YoY: `(Precio actual / Precio anterior) - 1` |
| **Stock C9L** | Stock disponible en cajas de 9 litros |
| **Cobertura** | Dias de cobertura: `Stock C9L / Venta promedio diaria` |

La **fila Total** al final muestra los agregados nacionales.

#### Tabla C9L (Cajas de 9 Litros)

Misma estructura que la tabla BOB pero en **unidades fisicas** (C9L). Es util para analizar el volumen real movido, independiente de variaciones de precio.

> **Nota:** La formula de conversion a C9L es: `Stock disponible (unidades) × Volumen (litros) / 9`

#### Tabla Semanal

Desglosa la venta del mes en **hasta 5 semanas calendario** (Lunes a Domingo). Muestra:

- Venta real por semana (S1 a S5)
- Total acumulado
- SOP del mes para referencia

Las semanas futuras (aun sin datos) se muestran vacias o como "Pendiente".

#### Drill-down por subfamilia

En las tablas BOB y C9L, cada marca tiene un **icono expandible** `[+]` a la izquierda. Al hacer clic, se despliegan las **subfamilias** de esa marca con el mismo desglose de columnas.

Esto permite analizar, por ejemplo, que subfamilia de Havana esta impulsando o frenando el desempeno.

### 3.3 Performance por Ciudad

Estructura identica a Performance por Marca, pero agrupada por **ciudad**.

#### Orden fijo de ciudades

Las ciudades siempre aparecen en este orden (de mayor a menor relevancia comercial):

1. Santa Cruz (SCZ)
2. Cochabamba (CBB)
3. La Paz (LPZ)
4. El Alto (EA)
5. Tarija (TJA)
6. Sucre (SUC)
7. Oruro (ORU)
8. Potosi (POT)
9. Trinidad (TDD)

#### Drill-down por marca

En la tabla de ciudades, el drill-down muestra las **marcas** dentro de cada ciudad, permitiendo ver que marcas lideran o rezagan en cada region.

### 3.4 Performance por Canal

Agrupa los resultados por **canal de distribucion** (Mayoreo, Detalle, etc.). Misma estructura de tablas BOB, C9L y semanal, pero sin drill-down.

> **Nota:** La proyeccion del canal usa una formula especial de ponderacion: 80% del peso viene del avance actual (T), 10% del vendido del ano anterior (R), 6% del SOP (S), y 4% del presupuesto general (Q).

### 3.5 Grafico de Tendencia

El grafico de tendencia es una visualizacion interactiva que muestra la **venta semanal vs la proyeccion** a lo largo del mes.

#### Como leer el grafico

- **Barras azules**: Venta real de la semana
- **Barras grises**: Proyeccion de la semana (para semanas futuras)
- **Tabla resumen debajo del grafico**: Muestra el cumplimiento porcentual por semana

Semanas futuras aparecen con el texto "Pendiente" y un icono de reloj de arena.

#### Selector multi-ciudad

En la parte superior del grafico hay **botones de seleccion** para cada ciudad:

- **General-Nacional**: Vista consolidada de todas las ciudades
- **Santa Cruz, Cochabamba, La Paz**, etc.: Vista individual por ciudad

Al hacer clic en un boton, el grafico y la tabla se actualizan mostrando los datos de esa ciudad.

#### Colores del cumplimiento

| Color | Condicion | Significado |
|-------|-----------|-------------|
| Verde (#10B981) | Cumplimiento >= 95% | En linea con el plan |
| Amarillo (#F59E0B) | Cumplimiento >= 85% | Atencion |
| Rojo (#EF4444) | Cumplimiento < 85% | Critico |

### 3.6 Proyeccion Objetiva (Triple Pilar)

Esta seccion presenta tres perspectivas independientes de proyeccion para reducir el sesgo de una sola fuente:

#### Los 3 pilares

| Pilar | Fuente | Metodo |
|-------|--------|--------|
| **PY Gerente** | Gerentes regionales (ingresado manualmente) | Juicio experto basado en conocimiento del terreno |
| **PY Estadistica** | Datos historicos de venta | Modelo Holt-Winters (suavizacion exponencial triple) con ajuste de eventos moviles |
| **PY Operativa** | Cobertura, Hit Rate, Drop Size | Arbol de ingresos: `Cobertura × Hit Rate × Drop Size` proyectado con WMA |

#### Diagnostico de spread

El sistema calcula la **dispersion (spread)** entre los 3 pilares y clasifica la situacion:

| Diagnostico | Condicion | Significado |
|-------------|-----------|-------------|
| **Optimista** | Spread > +10% | Los pilares sugieren que las proyecciones son conservadoras |
| **Consenso** | Spread entre -5% y +5% | Los 3 pilares convergen — alta confianza |
| **Conservador** | Spread < -10% | Las proyecciones podrian estar optimistas |

> **Nota:** Oruro y Trinidad pueden no tener Proyeccion de Gerente si no cuentan con gerente regional asignado. En ese caso, solo se muestran los pilares Estadistico y Operativo.

### 3.7 Stock y Cobertura

Esta seccion muestra el inventario actual por marca/ciudad y calcula la **cobertura en dias** (cuantos dias de venta cubre el stock actual al ritmo actual).

#### Umbrales de cobertura

| Rango | Estado | Color | Accion recomendada |
|-------|--------|-------|--------------------|
| 0 dias | Sin stock | Rojo | Reposicion urgente |
| < 15 dias | Critico | Rojo | Reposicion prioritaria |
| 15-30 dias | Optimo | Verde | Nivel ideal de inventario |
| 30-60 dias | Alto (monitorear) | Amarillo | Revisar rotacion, posible exceso |
| > 60 dias | Exceso | Naranja | Accion comercial para mover stock |

#### Formula de cobertura

```
Cobertura (dias) = Stock en C9L / Venta promedio diaria en C9L
```

Donde:
- `Stock en C9L = Unidades disponibles × Volumen por unidad / 9`
- `Venta promedio diaria = Venta C9L del mes / Dias laborales transcurridos`

### 3.8 Hit Rate y Eficiencia

Esta seccion evalua la **productividad de la fuerza de ventas** basada en datos del sistema de visitas.

#### Definiciones

| Metrica | Formula | Descripcion |
|---------|---------|-------------|
| **Eficiencia** | `Clientes contactados / Total clientes` × 100 | Que porcentaje de la cartera fue visitada o atendida |
| **Hit Rate** | `Clientes con venta / Clientes contactados` × 100 | De los contactados, que porcentaje compro |
| **Efectividad Total** | `(Eficiencia × Hit Rate) / 100` | Combinacion de ambas metricas |

Un cliente se considera "contactado" si tiene al menos un registro de tipo "Ventas" o "Visita" en el mes. Los clientes con tipo "No Visita" no se cuentan como contactados.

#### Clasificacion de desempeno

| Metrica | Alto | Medio | Bajo |
|---------|------|-------|------|
| **Hit Rate** | >= 70% | >= 50% | < 50% |
| **Eficiencia** | >= 80% | >= 60% | < 60% |

---

## 4. Glosario de terminos

| Termino | Definicion |
|---------|-----------|
| **BOB** | Bolivianos — moneda nacional de Bolivia |
| **C9L** | Cajas de 9 Litros — unidad estandar de volumen en la industria de bebidas |
| **SOP** | Sales & Operations Plan — presupuesto mensual ajustado por operaciones |
| **PG** | Presupuesto General — presupuesto anual aprobado por directorio |
| **PY** | Proyeccion — estimacion de cierre del mes basada en datos reales + proyecciones |
| **AV** | Avance — venta acumulada del mes en curso |
| **AV/PG** | Avance vs Presupuesto General: `(AV/PG) - 1` |
| **AV/SOP** | Avance vs SOP: `(AV/SOP) - 1` |
| **PY/V** | Proyeccion vs Vendido del ano anterior: `(PY/V anterior) - 1` |
| **Hit Rate** | Tasa de exito comercial: porcentaje de clientes contactados que compraron |
| **Cobertura** | Dias de stock disponible al ritmo de venta actual |
| **Spread** | Dispersion entre los 3 pilares de proyeccion |
| **Holt-Winters** | Modelo estadistico de suavizacion exponencial triple con estacionalidad |
| **WMA** | Weighted Moving Average — promedio movil ponderado |
| **DWH** | Data Warehouse — base de datos consolidada para analisis |
| **Subfamilia** | Subgrupo de productos dentro de una marca |
| **Tipo de cambio** | Conversion BOB/USD utilizada: 6.96 |
| **Drill-down** | Funcionalidad para expandir y ver detalle dentro de una fila |
| **Markup** | Incremento de precio ano sobre ano |
| **Drop Size** | Tamano promedio de pedido por cliente (en BOB o C9L) |
| **Ingreso Neto** | Venta neta despues de descuentos y devoluciones |

---

## 5. Preguntas frecuentes (FAQ)

### Por que Oruro y Trinidad no siempre tienen proyeccion de gerente?

Historicamente, estas ciudades no contaban con gerente regional dedicado. En esos casos, el sistema usa el **SOP** como proyeccion, distribuido semanalmente con patrones especificos:

- **Oruro**: Patron back-loaded (8%, 12%, 20%, 28%, 32%) — la venta se concentra al final del mes
- **Trinidad**: Patron front-loaded (25%, 18%, 22%, 20%, 15%) — la venta se concentra al inicio

A partir de **2026**, Oruro cuenta con gerente regional, por lo que solo Trinidad sigue usando SOP como proxy.

### Que marcas y ciudades se excluyen del reporte?

Las siguientes exclusiones se aplican automaticamente en todas las consultas:

| Tipo | Exclusion | Razon |
|------|-----------|-------|
| Ciudad | Turismo | No es una ciudad geografica, es un canal especial |
| Canal | Turismo | Se excluye como canal de distribucion |
| Marca | "Ninguna" | Registros sin marca asignada |
| Marca | "Sin marca asignada" | Registros pendientes de clasificacion |

### Que tipo de cambio se usa?

El sistema usa un tipo de cambio fijo de **6.96 BOB/USD** para todas las conversiones. Este valor esta configurado en el sistema y se muestra en el pie de pagina del reporte.

> **Importante:** Si el tipo de cambio oficial cambia, este parametro debe ser actualizado por el equipo de sistemas. Ver Manual de Mantenimiento para instrucciones.

### Por que los datos del lunes pueden parecer incompletos?

Los datos dependen de la actualizacion del Data Warehouse (`dwh_saiv`). Si la carga ETL no se ha completado antes de la ejecucion del WSR, los datos del viernes y sabado pueden no estar reflejados. Se recomienda ejecutar el WSR despues de las **9:00 AM del lunes** para asegurar que la carga nocturna se haya completado.

### Puedo ejecutar el reporte para un mes diferente al actual?

El sistema genera el reporte para el mes y ano definidos en las variables de entorno `CURRENT_YEAR` y la fecha actual del sistema. Para generar un reporte de un mes anterior, seria necesario modificar la logica de consultas (tarea del equipo de desarrollo).

### Que navegadores son compatibles?

El reporte HTML funciona en cualquier navegador moderno:

- Google Chrome (recomendado)
- Mozilla Firefox
- Microsoft Edge
- Safari

No se garantiza compatibilidad con Internet Explorer.

### Que tan grande es el archivo del reporte?

El archivo HTML pesa entre **500 KB y 2 MB**, dependiendo de la cantidad de marcas, ciudades y semanas con datos. Es lo suficientemente ligero para enviar por correo electronico.

### Que pasa si la IA (OpenRouter) no esta disponible?

El sistema tiene un mecanismo de fallback:

1. Intenta con el modelo principal (`claude-opus-4.1`)
2. Si falla (rate limit o error), intenta con el modelo secundario (`claude-sonnet-4`)
3. Si ambos fallan, genera un analisis basico sin IA, agrupando comentarios por region

El reporte siempre se genera, con o sin analisis de IA.

### Como se cuentan los dias laborales?

- **Sabados** son laborales
- **Domingos** NO son laborales
- **Feriados bolivianos** NO son laborales (7 fijos + 3 moviles por ano)
- Los feriados moviles (Carnaval, Viernes Santo, Corpus Christi) se actualizan anualmente

---

## 6. Contacto y soporte

Para consultas sobre el uso del reporte o problemas de interpretacion:

| Contacto | Rol | Email |
|----------|-----|-------|
| Fabiola Bowles | Desarrolladora del sistema | fbowles@theblankinc.com |
| Equipo DBA | Soporte base de datos / DWH | (Consultar con IT) |
| Gerencia Comercial DyM | Reglas de negocio y definiciones | (Consultar con Comercial) |

Para problemas tecnicos de instalacion o mantenimiento, consultar el **Manual de Instalacion** y el **Manual de Mantenimiento**.
