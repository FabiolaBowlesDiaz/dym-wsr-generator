# Pilar 3: Drivers de Performance (PY Operativa / Revenue Tree)

## Que es

Descomposicion de la venta en sus 3 palancas operativas:

```
Venta = Cobertura x Hit Rate x Drop Size
```

| Driver | Definicion | Mide | Ejemplo |
|--------|-----------|------|---------|
| Cobertura | Clientes unicos que compraron | Alcance de la fuerza de ventas | 450 clientes |
| Hit Rate | Pedidos por cliente (frecuencia) | Intensidad de compra | 2.1 ped/cli |
| Drop Size | BOB por pedido (ticket promedio) | Valor por transaccion | $1,460/ped |

**Check matematico**: 450 x 2.1 x $1,460 = $1,379,700 (exacto)

---

## Fuente de datos

**Tabla**: `fact_ventas_detallado` (DWH PostgreSQL, schema `auto`)

| Columna | Tipo | Uso |
|---------|------|-----|
| `cod_cliente` | varchar | Cobertura: COUNT(DISTINCT) |
| `cuf_factura` | varchar | Hit Rate: COUNT(DISTINCT) / Cobertura |
| `marca` | varchar | Nivel marca (UPPER CASE) |
| `submarca` | varchar | Nivel submarca/subfamilia |
| `ciudad` | varchar | Nivel ciudad (Title Case) |
| `fecha` | date | Temporal (EXTRACT year/month) |
| `ingreso_neto_bob` | numeric | Drop Size: SUM / pedidos |

**Rango temporal**: Desde Ene 2025. IT carga datos 2026 de forma continua.

**Diferencias de nomenclatura vs td_ventas_bob_historico**:
- `marca` (no `marcadir`)
- `submarca` (no `subfamilia`)
- `ingreso_neto_bob` (no `fin_01_ingreso`)
- `fecha` (no `anio`/`mes` separados)
- TIENE `cod_cliente` y `cuf_factura` (que historico NO tiene)

---

## Niveles de calculo

| Nivel | Agrupacion | Acompana a |
|-------|-----------|------------|
| 1 | Por marca | Tabla Performance por Marca |
| 2 | Por marca + submarca | Drilldown de Tabla 1 |
| 3 | Por ciudad | Tabla Performance por Ciudad |
| 4 | Por ciudad + marca | Drilldown de Tabla 2 |

---

## Queries SQL

### Query base (parametrizada por GROUP BY)

```sql
SELECT
    {group_cols},
    EXTRACT(YEAR FROM fecha)::INT AS anio,
    EXTRACT(MONTH FROM fecha)::INT AS mes,
    COUNT(DISTINCT cod_cliente) AS cobertura,
    COUNT(DISTINCT cuf_factura) AS pedidos,
    ROUND(
        COUNT(DISTINCT cuf_factura)::NUMERIC /
        NULLIF(COUNT(DISTINCT cod_cliente), 0), 2
    ) AS hit_rate,
    ROUND(
        SUM(ingreso_neto_bob) /
        NULLIF(COUNT(DISTINCT cuf_factura), 0), 2
    ) AS drop_size,
    SUM(ingreso_neto_bob) AS venta_total
FROM auto.fact_ventas_detallado
WHERE UPPER(marca) NOT IN ('NINGUNA', 'SIN MARCA ASIGNADA')
  AND UPPER(ciudad) NOT IN ('TURISMO')
GROUP BY {group_cols}, EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha)
ORDER BY {group_cols}, anio, mes
```

**Nivel 1**: `group_cols = marca`
**Nivel 2**: `group_cols = marca, submarca`
**Nivel 3**: `group_cols = ciudad`
**Nivel 4**: `group_cols = ciudad, marca`

---

## Calculo de tendencias

Para cada grupo y cada variable (Cob, HR, DS):

```
Tendencia = (Promedio ultimos 3 meses / Promedio 3 meses anteriores) - 1
```

Ejemplo:
- Cobertura Casa Real Oct-Dic 2025 avg: 420 clientes
- Cobertura Casa Real Jul-Sep 2025 avg: 455 clientes
- Tendencia: (420/455) - 1 = -7.7%

**Umbral de estabilidad**: +/-2% se considera estable.

---

## Logica de diagnostico automatico

| Cobertura | Hit Rate | Drop Size | Diagnostico |
|-----------|----------|-----------|-------------|
| baja | estable | estable | Problema de ruta/cobertura |
| estable | baja | estable | Problema de conversion/selling |
| estable | estable | baja | Problema de mix/precio |
| baja | baja | baja | Problema sistemico |
| baja | baja | estable | Problema de cobertura + conversion |
| baja | estable | baja | Problema de cobertura + mix |
| estable | baja | baja | Problema de conversion + mix |
| estable/sube | estable/sube | estable/sube | Estable |

---

## Narrativa IA (diagnostico)

- **Modelo**: `anthropic/claude-opus-4.6` via OpenRouter (fallback: `claude-sonnet-4`)
- **Input**: Tabla de drivers por marca con tendencias
- **Output**: 4-6 bullet points identificando marcas con senales criticas y la palanca que falla
- **Ubicacion en WSR**: Despues de la narrativa PY Sistema, antes de la tabla semanal

---

## Flujo de datos completo

```
fact_ventas_detallado (DWH)
  |
  v
DriversEngine._fetch_monthly()        -- 4 queries (1 por nivel)
  |
  v
DriversEngine._compute_trends()       -- Calcula Cob/HR/DS + tendencias
  |
  v
projection_processor.generate_projections()  -- Retorna drivers_data en el dict
  |
  v
wsr_generator_main.py                 -- Extrae drivers, pasa a HTML
  |
  +---> html_tables.generate_drivers_table()    -- Tabla visual
  +---> DriversNarrativeGenerator               -- Diagnostico IA (Claude)
  |
  v
WSR HTML (seccion Drivers de Performance)
```

---

## Archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `pilar3_operativa/drivers_engine.py` | Motor de calculo: queries + tendencias |
| `pilar3_operativa/drivers_narrative.py` | Narrativa IA del diagnostico |
| `pilar3_operativa/DRIVERS.md` | Esta documentacion |

---

## Limitaciones conocidas

1. **Hit Rate NO es tasa de conversion clasica**: Es frecuencia de compra (pedidos/cliente), no "visitados que compraron". Para la conversion clasica se necesita data de visitas por marca, que no existe en fact_ventas_detallado.
2. **Nombres de marca en UPPER**: fact_ventas_detallado usa `marca` en UPPER CASE. El WSR usa Title Case. El merge requiere normalizacion.
3. **Submarca vs Subfamilia**: fact_ventas_detallado usa `submarca`, el WSR usa `subfamilia`. Son equivalentes pero con nombres distintos.
