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



```ojs
const resourcePath = "sismos:sismology";
const res = await datamesh.query({ resource_uri: resourcePath });

const dateIdx = res.columns.indexOf("fecha_hora_registro");
const magIdx = res.columns.indexOf("magnitud");
const depthIdx = res.columns.indexOf("profundidad");
const latIdx = res.columns.indexOf("latitud");
const lonIdx = res.columns.indexOf("longitud");
const regIdx = res.columns.indexOf("region_base");

const data = res.rows
  .map(r => {
    const lat = parseFloat(r[latIdx]);
    const lon = parseFloat(r[lonIdx]);
    const mag = parseFloat(r[magIdx]);
    const depth = parseFloat(r[depthIdx]);
    const region = r[regIdx] || "Sin registrar";
    const fecha = r[dateIdx] || "";

    let tipoProfundidad = "Sin datos";
    if (!isNaN(depth)) {
      if (depth < 70) tipoProfundidad = "Superficial (< 70 km)";
      else if (depth < 150) tipoProfundidad = "Intermedio (70–150 km)";
      else if (depth < 300) tipoProfundidad = "Subducción (150–300 km)";
      else tipoProfundidad = "Profundo (> 300 km)";
    }

    return {
      fecha,
      magnitud: mag,
      profundidad: depth,
      latitud: lat,
      longitud: lon,
      region,
      tipoProfundidad
    };
  })
  .filter(d => 
    !isNaN(d.latitud) && 
    !isNaN(d.longitud) && 
    !isNaN(d.magnitud) &&
    d.longitud >= -71 && d.longitud <= -57 &&
    d.latitud >= -24 && d.latitud <= -9
  );

return Plot.plot({
  title: "Mapa de Epicentros Sísmicos en Bolivia — Observatorio San Calixto",
  subtitle: "Distribución geográfica de eventos según profundidad focal y magnitud Richter",
  width: 760,
  height: 600,
  aspectRatio: 1,
  grid: true,
  x: {
    label: "Longitud (°W)",
    domain: [-70.5, -57.5],
    tickFormat: d => `${Math.abs(d)}°W`
  },
  y: {
    label: "Latitud (°S)",
    domain: [-23.5, -9.5],
    tickFormat: d => `${Math.abs(d)}°S`
  },
  color: {
    domain: [
      "Superficial (< 70 km)",
      "Intermedio (70–150 km)",
      "Subducción (150–300 km)",
      "Profundo (> 300 km)"
    ],
    range: ["#ef4444", "#f97316", "#2563eb", "#7c3aed"],
    legend: true,
    label: "Profundidad Focal"
  },
  r: {
    range: [2.5, 9],
    legend: true,
    label: "Magnitud (M)"
  },
  marks: [
    Plot.frame({ stroke: "#cbd5e1" }),
    Plot.dot(data, {
      x: "longitud",
      y: "latitud",
      r: "magnitud",
      fill: "tipoProfundidad",
      fillOpacity: 0.65,
      stroke: "tipoProfundidad",
      strokeWidth: 0.6,
      channels: {
        Fecha: "fecha",
        "Región": "region",
        "Magnitud (M)": d => `${d.magnitud.toFixed(1)} M`,
        "Profundidad": d => isNaN(d.profundidad) ? "N/D" : `${d.profundidad} km`
      },
      tip: {
        format: {
          x: false,
          y: false,
          fill: false,
          r: false
        }
      }
    })
  ]
});
```

