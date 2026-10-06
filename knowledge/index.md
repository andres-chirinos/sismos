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
  end: 2026-10-06T13:55:10Z
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
  updated_at: '2026-10-06T21:05:19Z'
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

// Inyectar CSS de Leaflet si no existe
if (!document.getElementById("leaflet-css")) {
  const link = document.createElement("link");
  link.id = "leaflet-css";
  link.rel = "stylesheet";
  link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  document.head.appendChild(link);
}

// Cargar librería Leaflet de forma resiliente
let L = window.L;
if (!L) {
  try {
    L = await require("leaflet@1.9.4");
  } catch (e) {
    const mod = await import("https://esm.sh/leaflet@1.9.4");
    L = mod.default || mod;
  }
  if (!L && window.L) L = window.L;
}

const dateIdx = res.columns.indexOf("fecha_hora_registro");
const magIdx = res.columns.indexOf("magnitud");
const depthIdx = res.columns.indexOf("profundidad");
const latIdx = res.columns.indexOf("latitud");
const lonIdx = res.columns.indexOf("longitud");
const regIdx = res.columns.indexOf("region_base");
const linkIdx = res.columns.indexOf("enlace_detalle");
const distIdx = res.columns.indexOf("distancia_epicentral");

// Contenedor del mapa (evita colisión con parámetro formal 'container')
const mapDiv = document.createElement("div");
mapDiv.style.width = "100%";
mapDiv.style.height = "640px";
mapDiv.style.borderRadius = "10px";
mapDiv.style.overflow = "hidden";
mapDiv.style.border = "1px solid #cbd5e1";
mapDiv.style.boxShadow = "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)";
mapDiv.style.position = "relative";
mapDiv.style.zIndex = "1";

const map = L.map(mapDiv, {
  center: [-16.8, -64.8],
  zoom: 6,
  minZoom: 4,
  maxZoom: 14
});

// Capas base cartográficas
const positron = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; OpenStreetMap'
});

const darkMatter = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; OpenStreetMap'
});

const topo = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
  attribution: '&copy; Esri, USGS'
});

const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; OpenStreetMap contributors'
});

positron.addTo(map);

L.control.layers({
  "Mapa Claro (CartoDB)": positron,
  "Relieve Topográfico (Esri)": topo,
  "Mapa Oscuro (CartoDB)": darkMatter,
  "Calles (OpenStreetMap)": osm
}, null, { position: "topright" }).addTo(map);

L.control.scale({ metric: true, imperial: false, position: "bottomleft" }).addTo(map);

// Código de color por profundidad focal
function getDepthColor(depth) {
  if (isNaN(depth)) return "#94a3b8";
  if (depth < 70) return "#ef4444";      // Superficial (<70 km, rojo cortical)
  if (depth < 150) return "#f97316";     // Intermedio (70-150 km, naranja)
  if (depth < 300) return "#2563eb";     // Subducción (150-300 km, azul)
  return "#7c3aed";                      // Profundo (>300 km, púrpura)
}

function getDepthLabel(depth) {
  if (isNaN(depth)) return "No determinada";
  if (depth < 70) return "Superficial (< 70 km)";
  if (depth < 150) return "Intermedio (70–150 km)";
  if (depth < 300) return "Subducción (150–300 km)";
  return "Profundo (> 300 km)";
}

// Mayor profundidad = mayor transparencia (menor opacidad)
function getDepthOpacity(depth) {
  if (isNaN(depth)) return { fill: 0.5, stroke: 0.8 };
  const normalized = Math.min(1, Math.max(0, depth / 650));
  const fill = Math.max(0.15, +(0.90 - normalized * 0.75).toFixed(2));
  const stroke = Math.max(0.35, +(1.0 - normalized * 0.65).toFixed(2));
  return { fill, stroke };
}

// Escala exponencial que hace el tamaño notablemente mayor según la magnitud Richter
function getMarkerRadius(mag) {
  if (isNaN(mag) || mag <= 0) return 3;
  return Math.min(45, Math.round(Math.pow(1.85, mag - 2.0) * 2.2 + 2));
}

// Renderizador Canvas para rendimiento fluido con miles de sismos
const canvasRenderer = L.canvas({ padding: 0.5 });
const markersLayer = L.layerGroup().addTo(map);

// Parsear y ordenar sismos
const records = res.rows
  .map(r => ({
    lat: parseFloat(r[latIdx]),
    lon: parseFloat(r[lonIdx]),
    mag: parseFloat(r[magIdx]),
    depth: parseFloat(r[depthIdx]),
    region: r[regIdx] || "Sin registrar",
    fecha: r[dateIdx] || "",
    dist: distIdx >= 0 ? r[distIdx] : "",
    link: linkIdx >= 0 ? r[linkIdx] : ""
  }))
  .filter(d => !isNaN(d.lat) && !isNaN(d.lon) && !isNaN(d.mag))
  .sort((a, b) => a.mag - b.mag);

let counterEl;

function renderMarkers(minMag = 2.0, depthFilter = "all") {
  markersLayer.clearLayers();

  const filtered = records.filter(d => {
    if (d.mag < minMag) return false;
    if (depthFilter === "superficial" && (isNaN(d.depth) || d.depth >= 70)) return false;
    if (depthFilter === "intermedio" && (isNaN(d.depth) || d.depth < 70 || d.depth >= 150)) return false;
    if (depthFilter === "subduccion" && (isNaN(d.depth) || d.depth < 150 || d.depth >= 300)) return false;
    if (depthFilter === "profundo" && (isNaN(d.depth) || d.depth < 300)) return false;
    return true;
  });

  for (const d of filtered) {
    const radius = getMarkerRadius(d.mag);
    const color = getDepthColor(d.depth);
    const opacities = getDepthOpacity(d.depth);
    const depthLabel = getDepthLabel(d.depth);

    const marker = L.circleMarker([d.lat, d.lon], {
      renderer: canvasRenderer,
      radius: radius,
      fillColor: color,
      color: color,
      weight: 1,
      opacity: opacities.stroke,
      fillOpacity: opacities.fill
    });

    const popupHtml = `
      <div style="font-family:system-ui,-apple-system,sans-serif;font-size:12px;line-height:1.45;min-width:210px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;">
          <span style="font-size:15px;font-weight:700;color:${color};">
            ${d.mag.toFixed(1)} M
          </span>
          <span style="font-size:11px;background:#f1f5f9;color:#475569;padding:2px 6px;border-radius:4px;font-weight:600;">
            ${depthLabel}
          </span>
        </div>
        <div style="color:#64748b;font-size:11px;margin-bottom:6px;">${d.fecha}</div>
        <div style="margin-bottom:3px;"><strong>Región:</strong> ${d.region}</div>
        <div style="margin-bottom:3px;"><strong>Profundidad:</strong> ${isNaN(d.depth) ? "N/D" : d.depth + " km"} (opacidad ${(opacities.fill * 100).toFixed(0)}%)</div>
        <div style="margin-bottom:4px;"><strong>Epicentro:</strong> ${d.lat.toFixed(3)}°S, ${Math.abs(d.lon).toFixed(3)}°W</div>
        ${d.dist ? `<div style="color:#64748b;font-size:11px;margin-bottom:4px;">${d.dist}</div>` : ''}
        ${d.link ? `<div style="margin-top:6px;"><a href="${d.link}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;font-weight:600;">Ver boletín oficial OSC &rarr;</a></div>` : ''}
      </div>
    `;

    marker.bindPopup(popupHtml);
    marker.bindTooltip(`<b>${d.mag.toFixed(1)} M</b> — ${d.region} (${isNaN(d.depth) ? 'N/D' : d.depth + ' km'})`, {
      direction: "top",
      opacity: 0.95
    });

    marker.addTo(markersLayer);
  }

  if (counterEl) {
    counterEl.textContent = `${filtered.length.toLocaleString()} sismos`;
  }
}

// Panel de Filtros interactivo en la esquina superior izquierda
const filterControl = L.control({ position: "topleft" });
filterControl.onAdd = function() {
  const div = L.DomUtil.create("div", "info filter-panel");
  L.DomEvent.disableClickPropagation(div);
  L.DomEvent.disableScrollPropagation(div);

  div.style.backgroundColor = "rgba(255, 255, 255, 0.95)";
  div.style.padding = "10px 14px";
  div.style.borderRadius = "8px";
  div.style.boxShadow = "0 2px 8px rgba(0,0,0,0.18)";
  div.style.fontSize = "12px";
  div.style.color = "#1e293b";
  div.style.backdropFilter = "blur(6px)";
  div.style.minWidth = "220px";
  div.style.maxWidth = "280px";

  div.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="font-weight:700;font-size:12px;color:#0f172a;">Filtros de Sismicidad</span>
      <span id="sismo-counter" style="font-size:11px;font-weight:700;color:#2563eb;background:#eff6ff;padding:2px 8px;border-radius:10px;">${records.length.toLocaleString()} sismos</span>
    </div>
    <div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
        <label for="sismo-mag-range" style="font-size:11px;font-weight:600;color:#475569;">Magnitud mínima:</label>
        <span id="sismo-mag-val" style="font-size:11px;font-weight:700;color:#0f172a;">≥ 2.0 M</span>
      </div>
      <input id="sismo-mag-range" type="range" min="2.0" max="6.5" step="0.1" value="2.0" style="width:100%;cursor:pointer;accent-color:#2563eb;">
    </div>
    <div style="margin-bottom:6px;">
      <label for="sismo-depth-select" style="font-size:11px;font-weight:600;color:#475569;display:block;margin-bottom:3px;">Profundidad focal:</label>
      <select id="sismo-depth-select" style="width:100%;padding:4px 6px;border:1px solid #cbd5e1;border-radius:6px;font-size:11px;background:#fff;cursor:pointer;">
        <option value="all">Todas las profundidades</option>
        <option value="superficial">Superficial (&lt; 70 km)</option>
        <option value="intermedio">Intermedio (70–150 km)</option>
        <option value="subduccion">Subducción (150–300 km)</option>
        <option value="profundo">Profundo (&gt; 300 km)</option>
      </select>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:6px;">
      <button id="sismo-reset-btn" style="background:#f1f5f9;border:1px solid #cbd5e1;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:600;color:#475569;cursor:pointer;">
        Restablecer
      </button>
    </div>
  `;

  counterEl = div.querySelector("#sismo-counter");
  const magSlider = div.querySelector("#sismo-mag-range");
  const magVal = div.querySelector("#sismo-mag-val");
  const depthSelect = div.querySelector("#sismo-depth-select");
  const resetBtn = div.querySelector("#sismo-reset-btn");

  const onFilterChange = () => {
    const minMag = parseFloat(magSlider.value);
    magVal.textContent = `≥ ${minMag.toFixed(1)} M`;
    renderMarkers(minMag, depthSelect.value);
  };

  magSlider.addEventListener("input", onFilterChange);
  depthSelect.addEventListener("change", onFilterChange);
  resetBtn.addEventListener("click", () => {
    magSlider.value = "2.0";
    magVal.textContent = "≥ 2.0 M";
    depthSelect.value = "all";
    renderMarkers(2.0, "all");
  });

  return div;
};

filterControl.addTo(map);

// Render inicial con todos los sismos
renderMarkers(2.0, "all");

// Leyenda informativa fija en el mapa con escala de opacidad y radio
const legend = L.control({ position: "bottomright" });
legend.onAdd = function() {
  const div = L.DomUtil.create("div", "info legend");
  div.style.backgroundColor = "rgba(255, 255, 255, 0.94)";
  div.style.padding = "10px 14px";
  div.style.borderRadius = "8px";
  div.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
  div.style.fontSize = "12px";
  div.style.lineHeight = "19px";
  div.style.color = "#1e293b";
  div.style.backdropFilter = "blur(4px)";
  div.innerHTML = `
    <div style="font-weight:700;font-size:12px;margin-bottom:4px;color:#0f172a;">Profundidad Focal (Color y Opacidad)</div>
    <div><i style="background:#ef4444;opacity:0.9;width:10px;height:10px;display:inline-block;border-radius:50%;margin-right:6px;"></i> Superficial (&lt; 70 km, sólida)</div>
    <div><i style="background:#f97316;opacity:0.75;width:10px;height:10px;display:inline-block;border-radius:50%;margin-right:6px;"></i> Intermedio (70–150 km)</div>
    <div><i style="background:#2563eb;opacity:0.55;width:10px;height:10px;display:inline-block;border-radius:50%;margin-right:6px;"></i> Subducción (150–300 km)</div>
    <div><i style="background:#7c3aed;opacity:0.3;width:10px;height:10px;display:inline-block;border-radius:50%;margin-right:6px;border:1px solid #7c3aed;"></i> Profundo (&gt; 300 km, translúcida)</div>
    <div style="font-size:10px;color:#64748b;margin-top:2px;">* A mayor profundidad, mayor transparencia</div>
    <hr style="margin:8px 0;border:0;border-top:1px solid #e2e8f0;">
    <div style="font-weight:700;font-size:12px;margin-bottom:4px;color:#0f172a;">Escala de Magnitud (Radio)</div>
    <div style="display:flex;align-items:center;gap:6px;margin-top:2px;">
      <span style="display:inline-block;width:6px;height:6px;background:#64748b;border-radius:50%;"></span> <span style="font-size:11px;">M3 (6px)</span>
      <span style="display:inline-block;width:10px;height:10px;background:#64748b;border-radius:50%;margin-left:4px;"></span> <span style="font-size:11px;">M4 (10px)</span>
      <span style="display:inline-block;width:16px;height:16px;background:#64748b;border-radius:50%;margin-left:4px;"></span> <span style="font-size:11px;">M5 (16px)</span>
      <span style="display:inline-block;width:28px;height:28px;background:#64748b;border-radius:50%;margin-left:4px;"></span> <span style="font-size:11px;font-weight:600;">M6+ (28px+)</span>
    </div>
  `;
  return div;
};
legend.addTo(map);

// Si el entorno ya provee 'container' como elemento DOM, adjuntar directamente
if (typeof container !== "undefined" && container && container.appendChild) {
  container.appendChild(mapDiv);
}

// Invalidate size tras montaje en el DOM para ajuste perfecto de teselas
requestAnimationFrame(() => map.invalidateSize());
setTimeout(() => map.invalidateSize(), 300);

return mapDiv;
```

