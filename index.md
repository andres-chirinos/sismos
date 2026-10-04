---
type: dataset
title: Sismología de Bolivia — Observatorio San Calixto
description: Catálogo oficial de eventos sísmicos registrados en Bolivia con magnitud, profundidad y coordenadas epicentrales.
spatial:
  country: BO
  regions: [BO-L, BO-P, BO-O, BO-C, BO-S, BO-H, BO-T, BO-B, BO-N]
  granularity: point
temporal:
  start: 2020-01-01T00:00:00Z
  end: 2026-06-30T23:59:59Z
  frequency: irregular
  timezone: America/La_Paz
quality:
  status: verified
  completeness: 0.99
contracts:
  - type: datapackage
    path: ./datapackage.yml
---

# sismology

---

type: DuckDB Table
title: "Registro Sísmico — Observatorio San Calixto"
description: "Catálogo de sismos registrados por el Observatorio San Calixto con magnitud, profundidad y coordenadas epicentrales."
resource: data/sismology/sismology.csv
tags: [sismologia, sismos, terremotos, san-calixto, geofisica]
timestamp: 2026-06-27T02:00:00Z

---

# Schema

| Column                 | Type      | Description                                                                                                                 |
| ---------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- |
| `fecha_hora_registro`  | TIMESTAMP | Fecha y hora del sismo. Dimensión temporal principal.                                                                       |
| `magnitud`             | DOUBLE    | Magnitud del sismo (escala logarítmica tipo Richter). **Nunca sumar ni promediar ingenuamente.** Usar `MAX()` o `COUNT(*)`. |
| `profundidad`          | DOUBLE    | Profundidad focal en km. **No sumar.** Usar `AVG()` para profundidad típica, `MIN()` para sismos superficiales.             |
| `region_base`          | VARCHAR   | Región geográfica del epicentro. Dimensión espacial categórica.                                                             |
| `latitud`              | DOUBLE    | Latitud del epicentro (WGS84). Usar para mapas de puntos.                                                                   |
| `longitud`             | DOUBLE    | Longitud del epicentro (WGS84). Usar para mapas de puntos.                                                                  |
| `distancia_epicentral` | VARCHAR   | Distancia del epicentro al punto de referencia. Texto descriptivo.                                                          |
| `observaciones`        | VARCHAR   | Notas del registro.                                                                                                         |
| `responsable`          | VARCHAR   | Responsable del registro en el observatorio.                                                                                |
| `referencias`          | VARCHAR   | Referencias bibliográficas del evento.                                                                                      |
| `enlace_detalle`       | VARCHAR   | URL al detalle del sismo en la web del observatorio.                                                                        |
| `fuente`               | VARCHAR   | Fuente de datos (ej. "Observatorio San Calixto").                                                                           |

# Uso Analítico

Este dataset es **espacio-temporal de eventos discretos**: cada fila es un sismo individual con su epicentro.

- **Análisis temporal**: Agrupar por `DATE_TRUNC('month', fecha_hora_registro)`. Usar `COUNT(*)` para frecuencia sísmica y `MAX(magnitud)` para el sismo más fuerte del periodo.
- **Análisis espacial**: Usar `latitud`, `longitud` para mapas de puntos epicentrales. Agrupar por `region_base` para comparar regiones.
- **Clasificación**: Filtrar por rangos de magnitud (`magnitud >= 4.0` para sismos significativos) o profundidad (`profundidad < 70` para superficiales).
- **Dashboard recomendado**: Mapa de epicentros (tamaño=magnitud) + Línea temporal de frecuencia mensual + Histograma de distribución de magnitudes.

# Indicadores Sísmicos Calculados

> **Nota:** Los datos sísmicos del Observatorio San Calixto están disponibles como CSV local. Cuando el backend los cargue, los siguientes gráficos se calcularán automáticamente.

```chart
{
  "type": "bar",
  "title": "Distribución de Sismos por Rango de Magnitud (M)",
  "subtitle": "Conteo acumulado de eventos sismológicos registrados en Bolivia",
  "source": "Observatorio San Calixto — Catálogo Oficial",
  "unit": "sismos",
  "sql": "SELECT CASE WHEN magnitud < 3.0 THEN '2.0-2.9 (Leve)' WHEN magnitud < 4.0 THEN '3.0-3.9 (Menor)' WHEN magnitud < 5.0 THEN '4.0-4.9 (Moderado)' WHEN magnitud < 6.0 THEN '5.0-5.9 (Fuerte)' ELSE '6.0+ (Mayor)' END AS rango, COUNT(*) AS sismos FROM sismology WHERE magnitud IS NOT NULL GROUP BY rango ORDER BY MIN(magnitud)",
  "xKey": "rango",
  "yKeys": ["sismos"],
  "colors": ["#2563eb"],
  "questions": [
    "¿Cuál es el sismo de mayor magnitud registrado en Bolivia?",
    "¿Por qué la mayoría de sismos en Bolivia tienen foco profundo (> 100 km)?"
  ]
}
```

```chart
{
  "type": "line",
  "title": "Frecuencia Sísmica Mensual y Magnitud Máxima",
  "subtitle": "Conteo mensual de eventos y magnitud pico reportada",
  "source": "Observatorio San Calixto — Red Sismológica Boliviana",
  "unit": "conteo",
  "sql": "SELECT STRFTIME(fecha_hora_registro, '%Y-%m') AS mes, COUNT(*) AS total_sismos, ROUND(MAX(magnitud), 1) AS magnitud_maxima FROM sismology GROUP BY mes ORDER BY mes DESC LIMIT 12",
  "xKey": "mes",
  "yKeys": ["total_sismos", "magnitud_maxima"],
  "colors": ["#059669", "#dc2626"],
  "questions": [
    "¿En qué mes ocurrieron más sismos en Bolivia?",
    "¿Qué estación detecta el mayor número de micro-sismos?"
  ]
}
```


# Conceptos Relacionados (SKOS)

Este dataset está enriquecido semánticamente vinculando variables sísmicas clave a vocabularios controlados. Puedes explorar las definiciones formales y sus relaciones aquí:

- [Terremoto / Sismo](concepts/earthquake.md) - [Q7944](https://www.wikidata.org/wiki/Q7944)
- [Escala de Richter (Magnitud)](concepts/richter_magnitude_scale.md) - [Q38053](https://www.wikidata.org/wiki/Q38053)

# Citations

[1] Observatorio San Calixto — https://www.osc.org.bo/
[2] Escala de Magnitud — https://earthquake.usgs.gov/learn/glossary/?term=magnitude
