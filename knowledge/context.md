---
type: DuckDB Table
title: "Registro Sísmico — Observatorio San Calixto"
description: "Catálogo de sismos registrados por el Observatorio San Calixto con magnitud, profundidad y coordenadas epicentrales."
resource: data/sismology/sismology.csv
tags: [sismologia, sismos, terremotos, san-calixto, geofisica]
timestamp: 2026-06-27T02:00:00Z
---

# Schema

| Column | Type | Description |
|--------|------|-------------|
| `fecha_hora_registro` | TIMESTAMP | Fecha y hora del sismo. Dimensión temporal principal. |
| `magnitud` | DOUBLE | Magnitud del sismo (escala logarítmica tipo Richter). **Nunca sumar ni promediar ingenuamente.** Usar `MAX()` o `COUNT(*)`. |
| `profundidad` | DOUBLE | Profundidad focal en km. **No sumar.** Usar `AVG()` para profundidad típica, `MIN()` para sismos superficiales. |
| `region_base` | VARCHAR | Región geográfica del epicentro. Dimensión espacial categórica. |
| `latitud` | DOUBLE | Latitud del epicentro (WGS84). Usar para mapas de puntos. |
| `longitud` | DOUBLE | Longitud del epicentro (WGS84). Usar para mapas de puntos. |
| `distancia_epicentral` | VARCHAR | Distancia del epicentro al punto de referencia. Texto descriptivo. |
| `observaciones` | VARCHAR | Notas del registro. |
| `responsable` | VARCHAR | Responsable del registro en el observatorio. |
| `referencias` | VARCHAR | Referencias bibliográficas del evento. |
| `enlace_detalle` | VARCHAR | URL al detalle del sismo en la web del observatorio. |
| `fuente` | VARCHAR | Fuente de datos (ej. "Observatorio San Calixto"). |

# Uso Analítico

Este dataset es **espacio-temporal de eventos discretos**: cada fila es un sismo individual con su epicentro.

- **Análisis temporal**: Agrupar por `DATE_TRUNC('month', fecha_hora_registro)`. Usar `COUNT(*)` para frecuencia sísmica y `MAX(magnitud)` para el sismo más fuerte del periodo.
- **Análisis espacial**: Usar `latitud`, `longitud` para mapas de puntos epicentrales. Agrupar por `region_base` para comparar regiones.
- **Clasificación**: Filtrar por rangos de magnitud (`magnitud >= 4.0` para sismos significativos) o profundidad (`profundidad < 70` para superficiales).
- **Dashboard recomendado**: Mapa de epicentros (tamaño=magnitud) + Línea temporal de frecuencia mensual + Histograma de distribución de magnitudes.

# Citations

[1] Observatorio San Calixto — https://www.osc.org.bo/
[2] Escala de Magnitud — https://earthquake.usgs.gov/learn/glossary/?term=magnitude
