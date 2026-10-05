---
type: dataset
title: Sismología de Bolivia — Observatorio San Calixto
description: Catálogo oficial de eventos sísmicos registrados en Bolivia con coordenadas epicentrales, profundidad y magnitud Richter.
spatial:
  country: BO
  regions: [BO-L, BO-P, BO-O, BO-C, BO-S, BO-H, BO-T, BO-B, BO-N]
  granularity: point
temporal:
  start: 2009-04-18T11:29:00Z
  end: 2026-10-04T08:07:55Z
  frequency: irregular
  timezone: America/La_Paz
quality:
  status: verified
  completeness: 1.0
contracts:
  - type: datapackage
    path: ./datapackage.yaml
lineage:
  source:
    - name: Observatorio San Calixto
      url: http://www.sancalixto.org.bo
  version: 1.0.0
  updated_at: '2026-10-05T03:09:21Z'
---

# Sismología de Bolivia — Observatorio San Calixto

Catálogo oficial de eventos sísmicos registrados en Bolivia por el **Observatorio San Calixto (OSC)**, entidad privada sin fines de lucro de la Compañía de Jesús y centro oficial de monitoreo sismológico en Bolivia.

## Contenido del Conjunto de Datos

- **`data/sismology.csv`**: Registro completo de eventos sísmicos con fecha, hora local y UTC, coordenadas geográficas del epicentro (WGS84), profundidad focal en kilómetros, magnitud estimada en escala Richter y enlaces al reporte oficial de registro.
- **`data/sismology.parquet`**: Versión columnar optimizada con tipado estricto para análisis analíticos de alto rendimiento.

## Análisis Espacio-Temporal Recomendado

- **Distribución de Magnitudes**: Filtrar por magnitud $\ge 4.0$ para sismos perceptibles y de relevancia estructural.
- **Frecuencia Mensual**: Agrupación por `DATE_TRUNC('month', fecha_hora_registro)` para evaluar actividad sísmica acumulada.
- **Profundidad Focal**: Clasificación entre sismos superficiales ($< 70$ km, mayor riesgo destructivo) e intermedios/profundos ($> 70$ km, comunes en la placa de Nazca subducida bajo los Andes bolivianos).
