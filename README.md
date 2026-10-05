# Sismología de Bolivia — Catálogo Oficial y Pipeline Autónomo

[![Update Sismología Bolivia](https://github.com/datosbolivia/sismos/actions/workflows/update-sismos.yml/badge.svg)](https://github.com/datosbolivia/sismos/actions/workflows/update-sismos.yml)
[![DataMesh OKF v0.2](https://img.shields.io/badge/DataMesh-OKF%20v0.2-blue)](https://datosbolivia.org)
[![Licencia: Abierta](https://img.shields.io/badge/License-ODbL%20%2F%20CC--BY--4.0-green.svg)](https://opendatacommons.org/licenses/odbl/)

Catálogo abierto y soberano de eventos sísmicos registrados en Bolivia por el **[Observatorio San Calixto (OSC)](https://www.osc.org.bo)** (entidad oficial de monitoreo sismológico en Bolivia y obra de la Compañía de Jesús). Este repositorio incluye la pipeline autónoma de extracción incremental, contratos de datos estandarizados bajo la especificación **OKF / ODKF v0.2 (Open Knowledge Foundation)** y persistencia optimizada en formatos tabular y columnar.

---

## Estructura del Repositorio

La organización del proyecto sigue una estricta separación entre datos procesados, especificación semántica y lógica del pipeline:

```text
├── data/                               # Artefactos de datos (exclusivo para conjuntos de datos)
│   ├── sismology.csv                   # Registro tabular completo de sismos
│   └── sismology.parquet               # Formato columnar de alto rendimiento y tipado estricto
├── knowledge/                          # Capa semántica y contratos OKF (exclusivo para metadatos)
│   ├── datapackage.yaml                # Contrato de datos OKF v0.2 (schema, tipos, calidad, bbox)
│   ├── index.md                        # Catálogo y linaje con frontmatter estandarizado
│   ├── context.md                      # Contexto del dominio sismológico y glosario
│   └── concepts/                       # Ontología y conceptos canónicos del catálogo
│       ├── earthquake.md               # Definición semántica de evento sísmico
│       └── richter_magnitude_scale.md  # Definición de la escala de magnitud Richter
├── notebooks/                          # Cuadernos de análisis exploratorio
├── .github/workflows/
│   └── update-sismos.yml               # GitHub Actions: actualización incremental y sincronización OKF
├── obs_san_calixto_extract.py          # Extractor soberano y sincronizador de contratos
└── requirements.txt                    # Dependencias del proyecto (Python 3.12+)
```

> **Regla de organización**:
> - Todos los artefactos de datos residen exclusivamente en `data/`.
> - Todos los contratos, metadatos, conceptos semánticos y documentación técnica residen exclusivamente en `knowledge/`.

---

## Esquema del Conjunto de Datos (`TARGET_COLUMNS`)

Tanto `data/sismology.csv` como `data/sismology.parquet` contienen las siguientes columnas unificadas:

| Campo | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `fecha_hora_registro` | `datetime` | Fecha y hora local normalizada (`YYYY-MM-DD HH:MM:SS`) | `2026-06-24 18:59:34` |
| `magnitud` | `float` | Magnitud estimada en escala de Richter | `4.2` |
| `profundidad` | `float` | Profundidad del foco o hipocentro en kilómetros (km) | `171.4` |
| `latitud` | `float` | Latitud del epicentro en coordenadas decimales (WGS84) | `-17.443` |
| `longitud` | `float` | Longitud del epicentro en coordenadas decimales (WGS84) | `-69.309` |
| `region_base` | `string` | Departamento y provincia del epicentro | `Prov. Pacajes, La Paz` |
| `distancia_epicentral` | `string` | Referencias espaciales relativas a localidades cercanas | `A 44 km SSW de SANTIAGO DE MACHACA...` |
| `observaciones` | `string` | Notas técnicas del sismo (perceptibilidad, fallas, etc.) | `Debido a la profundidad > 100 km...` |
| `responsable` | `string` | Sismólogo o analista responsable del reporte | `Ing. Walter Arce` |
| `referencias` | `string` | Cita formal del boletín emitido por el OSC | `OSC (2026). Boletín diario OSC...` |
| `enlace_detalle` | `string` | Identificador único y URL al reporte individual | `https://www.osc.org.bo/...&ID=5337` |
| `fuente` | `string` | Identificador canónico de la fuente | `observatorio_san_calixto` |

---

## Pipeline de Extracción y Actualización Autónoma

El script `obs_san_calixto_extract.py` extrae eventos de forma robusta, normaliza el esquema y actualiza automáticamente los contratos en `knowledge/`.

### Modos de Ejecución

1. **Modo Incremental (por defecto)**:
   Lee los registros existentes en `data/sismology.csv`, identifica enlaces ya conocidos y descarga únicamente los eventos nuevos. Si detecta 2 páginas consecutivas con datos existentes, realiza un corte anticipado (*early stopping*).
   ```bash
   python obs_san_calixto_extract.py --mode incremental --data-dir data --format csv,parquet
   ```

2. **Modo Full Refresh**:
   Recorre todo el historial disponible en el portal del Observatorio San Calixto hasta la página final:
   ```bash
   python obs_san_calixto_extract.py --mode full-refresh --data-dir data --format csv,parquet
   ```

3. **Modo Fuerza Bruta**:
   Consulta por rango continuo de identificadores numéricos directos (`ID=1` hasta `ID_MAX`):
   ```bash
   python obs_san_calixto_extract.py --mode brute-force --data-dir data --format csv,parquet
   ```

### Parámetros de la CLI

| Argumento | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--mode` | `choice` | `incremental` | Modo de extracción (`incremental`, `full-refresh`, `brute-force`) |
| `--data-dir` | `path` | `data/` | Directorio de destino para los artefactos de datos |
| `--base-name` | `string` | `sismology` | Nombre base de los archivos generados |
| `--format` | `string` | `csv,parquet` | Formatos de salida separados por comas |
| `--max-pages` | `int` | `0` (ilimitado) | Máximo de páginas del listado a procesar |
| `--workers` | `int` | `6` | Hilos concurrentes para la descarga de páginas de detalle |
| `--no-metadata-update` | `flag` | `False` | Desactiva la sincronización automática en `knowledge/` |

---

## Sincronización Automática de Contratos OKF (`knowledge/`)

Cada vez que el pipeline finaliza una ejecución exitosa, la función `sync_okf_metadata()` recalcula las métricas del conjunto de datos y actualiza automáticamente los archivos en `knowledge/`:

- **Cobertura temporal**: Actualiza `temporal.start` y `temporal.end` con las marcas de tiempo ISO 8601 extremas.
- **Bounding Box espacial**: Calcula el rectángulo envolvente `spatial.bbox: [min_lon, min_lat, max_lon, max_lat]` de Bolivia.
- **Completitud y calidad**: Actualiza el ratio `quality.completeness` y la marca de auditoría `updated_at`.
- **Archivos sincronizados**:
  - `knowledge/datapackage.yaml`: Contrato de esquema y recursos hacia `../data/sismology.csv` y `../data/sismology.parquet`.
  - `knowledge/index.md`: Frontmatter YAML del catálogo DataMesh.

---

## Automatización en GitHub Actions

El flujo de trabajo [`.github/workflows/update-sismos.yml`](.github/workflows/update-sismos.yml) mantiene el repositorio actualizado sin intervención manual:

- **Frecuencia programada**: Se ejecuta automáticamente dos veces al día (`04:30` y `16:30` UTC / `00:30` y `12:30` BOT).
- **Ejecución manual**: Permite lanzamiento inmediato mediante `workflow_dispatch`.
- **Entorno**: Configurado sobre Python 3.12 con caché de dependencias `pip`.
- **Persistencia**: Si detecta nuevos sismos, realiza commit y push automático sobre la rama `main` afectando exclusivamente `data/` y `knowledge/`.

---

## Ejemplos de Uso y Carga de Datos

### Con Python y Pandas
```python
import pandas as pd

# Lectura eficiente desde Parquet
df = pd.read_parquet("data/sismology.parquet")

# Filtrar sismos perceptibles (Magnitud >= 4.0) en La Paz
sismos_lp = df[(df['magnitud'] >= 4.0) & (df['region_base'].str.contains("La Paz", na=False))]
print(sismos_lp[['fecha_hora_registro', 'magnitud', 'profundidad', 'region_base']])
```

### Con DuckDB (SQL analítico directo)
```python
import duckdb

# Consulta analítica de sismos por año
query = """
SELECT 
    EXTRACT(YEAR FROM fecha_hora_registro::TIMESTAMP) AS anio,
    COUNT(*) AS total_sismos,
    ROUND(AVG(magnitud), 2) AS magnitud_promedio,
    ROUND(MAX(magnitud), 2) AS magnitud_maxima
FROM 'data/sismology.parquet'
WHERE fecha_hora_registro IS NOT NULL
GROUP BY anio
ORDER BY anio DESC;
"""
print(duckdb.query(query).df())
```

---

## Créditos y Fuente de Información

- **Fuente oficial**: [Observatorio San Calixto (OSC)](https://www.osc.org.bo) — La Paz, Bolivia.
- **Coordinación e integración**: [DataMesh Bolivia](https://datosbolivia.org) — Iniciativa de datos abiertos soberanos.
