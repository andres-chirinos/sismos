#!/usr/bin/env python3
"""Extracción y actualización autónoma del catálogo de sismos del Observatorio San Calixto (Bolivia).

Este script opera como pipeline soberano de extracción para el repositorio federado `sismos`,
cumpliendo con la especificación de datos abiertos OKF / ODKF v0.2 del DataMesh.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from tqdm.auto import tqdm

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

REPO_ROOT = Path(__file__).resolve().parent

HEADERS = {
    "Host": "www.osc.org.bo",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

BASE_URL = "https://www.osc.org.bo/index.php/es/"

TARGET_COLUMNS = [
    'enlace_detalle',
    'magnitud',
    'region_base',
    'profundidad',
    'distancia_epicentral',
    'observaciones',
    'responsable',
    'referencias',
    'latitud',
    'longitud',
    'fecha_hora_registro',
    'fuente'
]


def fetch_html(url: str, retries: int = 3, delay_seconds: int = 2) -> bytes | None:
    """Descarga el HTML de una URL con reintentos y tolerancia a fallos."""
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, timeout=30, headers=HEADERS, verify=False)
            if res.status_code == 200:
                return res.content
        except Exception:
            pass
        time.sleep(delay_seconds)
    return None


def fetch_detail_page(url: str) -> dict[str, Any]:
    """Extrae la información complementaria de la página de detalle de un sismo."""
    if not url:
        return {}
    html_content = fetch_html(url)
    if not html_content:
        return {}

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        if not tables:
            return {}

        target_table = next((t for t in tables if 'Magnitud' in t.text or 'Región' in t.text), tables[0])
        df_list = pd.read_html(StringIO(str(target_table)))

        if not df_list:
            return {}
        df = df_list[0].dropna(subset=[0, 1])

        keys = df.iloc[:, 0].astype(str).tolist()
        values = df.iloc[:, 1].astype(str).tolist()

        detail_dict: dict[str, Any] = {'enlace_detalle': url}
        for k, v in zip(keys, values):
            if k != v and 'M - ' not in k:
                clean_key = k.strip().lower().replace(" ", "_").replace(":", "")
                detail_dict[clean_key] = v.strip()

        return detail_dict
    except Exception as e:
        logging.debug("Error procesando detalle %s: %s", url, e)
        return {}


def get_max_id() -> int:
    """Obtiene el ID máximo desde la primera página del listado."""
    url = f"{BASE_URL}?_pagi_pg=1"
    html_content = fetch_html(url)
    if not html_content:
        return 0
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return 0
    target_table = next((t for t in tables if 'Magnitud (M)' in t.text or 'Fecha' in t.text), tables[-1])
    rows = target_table.find_all('tr')
    for row in rows[1:]:
        link = row.get('data-href', '')
        if 'ID=' in link:
            try:
                return int(link.split('ID=')[1].split('&')[0])
            except ValueError:
                continue
    return 0


def fetch_page_data(page_num: int) -> tuple[list[dict[str, Any]] | None, str, int]:
    """Obtiene los eventos registrados en una página del listado."""
    url = f"{BASE_URL}?_pagi_pg={page_num}"
    html_content = fetch_html(url, retries=3, delay_seconds=3)

    if not html_content:
        logging.error("Fallo al obtener la página %d", page_num)
        return None, url, 500

    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')

    if not tables:
        return [], url, 200

    target_table = next((t for t in tables if 'Magnitud (M)' in t.text or 'Fecha' in t.text), tables[-1])
    rows = target_table.find_all('tr')

    if len(rows) <= 1:
        return [], url, 200

    headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]

    data: list[dict[str, Any]] = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if not cols:
            continue
        row_data = {headers[i]: col.text.strip() for i, col in enumerate(cols) if i < len(headers)}

        link = row.get('data-href', '')
        if link and link.startswith('http'):
            row_data['enlace_detalle'] = link
        elif link:
            row_data['enlace_detalle'] = "https://www.osc.org.bo" + (link if link.startswith('/') else '/' + link)
        else:
            row_data['enlace_detalle'] = None

        data.append(row_data)

    return data, url, 200


def enrich_with_details(data: list[dict[str, Any]], max_workers: int = 5) -> list[dict[str, Any]]:
    """Descarga en paralelo los enlaces de detalle para enriquecer atributos."""
    enriched_data: list[dict[str, Any]] = []

    def process_row(row: dict[str, Any]) -> dict[str, Any]:
        link = row.get('enlace_detalle')
        if link:
            details = fetch_detail_page(link)
            exclude_keys = [
                'latitud', 'longitud', 'profundidad', 'magnitud',
                'fecha', 'hora', 'fecha_y_hora', 'localización', 'enlace_detalle'
            ]
            filtered_details = {k: v for k, v in details.items() if k not in exclude_keys}
            return {**row, **filtered_details}
        return row

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_row, row): row for row in data}
        for future in as_completed(futures):
            try:
                enriched_data.append(future.result())
            except Exception:
                enriched_data.append(futures[future])

    return enriched_data


def clean_brute_force_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia los campos extraídos directamente por fuerza bruta."""
    if df.empty:
        return df

    if 'localización' in df.columns:
        locs = df['localización'].str.split(';', expand=True)
        if locs.shape[1] >= 2:
            df['latitud'] = locs[0]
            df['longitud'] = locs[1]

    if 'fecha_y_hora' in df.columns:
        df['fecha_hora_registro'] = df['fecha_y_hora'].str.replace(r'\(.*\)', '', regex=True).str.strip()
        df['fecha_hora_registro'] = pd.to_datetime(df['fecha_hora_registro'], errors='coerce')

    return df


def transform_dataset(
    data: list[dict[str, Any]],
    url_source: str,
    status_code: int,
    add_metadata: bool = False,
    is_bruteforce: bool = False
) -> pd.DataFrame:
    """Estandariza los registros al esquema unificado del catálogo DataMesh."""
    if not data:
        return pd.DataFrame(columns=TARGET_COLUMNS)

    df = pd.DataFrame(data)

    if is_bruteforce:
        df = clean_brute_force_data(df)

    rename_map = {
        'Fecha': 'fecha',
        'Hora local': 'hora',
        'Latitud': 'latitud',
        'Longitud': 'longitud',
        'Profundidad (Km)': 'profundidad',
        'Magnitud (M)': 'magnitud',
        'Región': 'region_base',
        'región': 'region_base'
    }

    existing_rename = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_rename)

    if 'fecha_hora_registro' not in df.columns:
        if 'fecha' in df.columns and 'hora' in df.columns:
            try:
                df['fecha_hora_registro'] = pd.to_datetime(
                    df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
                    format='%d/%m/%Y %H:%M:%S',
                    errors='coerce'
                )
            except Exception:
                df['fecha_hora_registro'] = pd.to_datetime(
                    df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
                    errors='coerce'
                )
        else:
            df['fecha_hora_registro'] = pd.NaT

    if 'profundidad' in df.columns:
        df['profundidad_raw'] = df['profundidad'].astype(str).copy()

    numeric_cols = ['latitud', 'longitud', 'profundidad', 'magnitud']
    for col in numeric_cols:
        if col in df.columns:
            extracted = df[col].astype(str).str.extract(r'([-\d\.]+)')[0]
            df[col] = pd.to_numeric(extracted, errors='coerce')
        else:
            df[col] = float('nan')

    df['fuente'] = "observatorio_san_calixto"

    if 'observaciones' not in df.columns:
        df['observaciones'] = df.get('region_base', '')
    else:
        df['observaciones'] = df['observaciones'].fillna(df.get('region_base', ''))

    if 'profundidad_raw' in df.columns:
        mask = (
            (df['profundidad'].isna() & (df['profundidad_raw'] != 'nan') & (df['profundidad_raw'] != 'None') & (df['profundidad_raw'].str.strip() != ''))
            | df['profundidad_raw'].str.contains('intermedia|superficial|profund', case=False, na=False)
        )
        df.loc[mask, 'observaciones'] = (
            df.loc[mask, 'observaciones'].astype(str) + " | Profundidad: " + df.loc[mask, 'profundidad_raw'].astype(str)
        )
        df = df.drop(columns=['profundidad_raw'])

    if add_metadata:
        data_str = json.dumps(data, ensure_ascii=False)
        df['_metadata_source'] = url_source
        df['_metadata_request_status'] = status_code
        df['_metadata_timestamp'] = datetime.datetime.now().isoformat()
        df['_metadata_unix_timestamp'] = int(datetime.datetime.now().timestamp())
        df['_metadata_hash'] = hashlib.md5(data_str.encode("utf-8")).hexdigest()

    # Asegurar todas las columnas objetivo
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Formatear fecha_hora_registro a string ISO/SQL limpio
    if pd.api.types.is_datetime64_any_dtype(df['fecha_hora_registro']):
        df['fecha_hora_registro'] = df['fecha_hora_registro'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df[TARGET_COLUMNS]


def sync_okf_metadata(df: pd.DataFrame, repo_dir: Path) -> None:
    """Actualiza automáticamente los contratos OKF/ODKF v0.2 del repositorio con las métricas reales."""
    if df.empty or 'fecha_hora_registro' not in df.columns:
        return

    valid_dates = pd.to_datetime(df['fecha_hora_registro'], errors='coerce').dropna()
    if valid_dates.empty:
        return

    start_iso = valid_dates.min().strftime('%Y-%m-%dT%H:%M:%SZ')
    end_iso = valid_dates.max().strftime('%Y-%m-%dT%H:%M:%SZ')
    updated_at_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Métricas espaciales
    valid_lats = pd.to_numeric(df['latitud'], errors='coerce').dropna()
    valid_lons = pd.to_numeric(df['longitud'], errors='coerce').dropna()
    bbox = None
    if not valid_lats.empty and not valid_lons.empty:
        bbox = [
            round(float(valid_lons.min()), 2),
            round(float(valid_lats.min()), 2),
            round(float(valid_lons.max()), 2),
            round(float(valid_lats.max()), 2)
        ]

    # Completitud
    completeness = round(float(len(valid_dates)) / float(len(df)), 2)

    # Actualizar datapackage.yaml / datapackage.yml
    dp_paths = [
        repo_dir / "knowledge" / "datapackage.yaml",
        repo_dir / "datapackage.yml"
    ]
    for dp_path in dp_paths:
        if not dp_path.exists():
            continue
        try:
            with open(dp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Sustitución limpia de temporal.start y temporal.end preservando comentarios/formato
            content = re.sub(r'start:\s*[^\n]+', f'start: {start_iso}', content)
            content = re.sub(r'end:\s*[^\n]+', f'end: {end_iso}', content)
            content = re.sub(r'completeness:\s*[^\n]+', f'completeness: {completeness}', content)

            with open(dp_path, "w", encoding="utf-8") as f:
                f.write(content)
            logging.info("Metadatos actualizados en %s (cobertura: %s a %s)", dp_path.name, start_iso, end_iso)
        except Exception as e:
            logging.warning("No se pudo actualizar metadatos en %s: %s", dp_path, e)

    # Actualizar index.md en knowledge/ y raíz
    index_paths = [
        repo_dir / "knowledge" / "index.md",
        repo_dir / "index.md"
    ]
    for idx_path in index_paths:
        if not idx_path.exists():
            continue
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                content = f.read()

            content = re.sub(r'start:\s*[^\n]+', f'start: {start_iso}', content)
            content = re.sub(r'end:\s*[^\n]+', f'end: {end_iso}', content)
            content = re.sub(r'completeness:\s*[^\n]+', f'completeness: {completeness}', content)
            content = re.sub(r"updated_at:\s*'[^\n']+'", f"updated_at: '{updated_at_str}'", content)

            with open(idx_path, "w", encoding="utf-8") as f:
                f.write(content)
            logging.info("Frontmatter actualizado en %s", idx_path.name)
        except Exception as e:
            logging.warning("No se pudo actualizar index en %s: %s", idx_path, e)


def save_dataset(
    df: pd.DataFrame,
    output_dir: Path,
    base_name: str,
    output_formats: list[str]
) -> list[Path]:
    """Guarda el DataFrame en disco en los formatos solicitados (CSV, Parquet)."""
    saved_paths: list[Path] = []
    if df.empty:
        return saved_paths

    output_dir.mkdir(parents=True, exist_ok=True)

    for fmt in output_formats:
        fmt = fmt.strip().lower()
        filepath = output_dir / f"{base_name}.{fmt}"

        if fmt == 'csv':
            df.to_csv(filepath, index=False, encoding='utf-8')
        elif fmt == 'parquet':
            df.columns = df.columns.astype(str)
            df.to_parquet(filepath, index=False)
        logging.info("Guardado exitoso: %s (%d filas)", filepath, len(df))
        saved_paths.append(filepath)

    return saved_paths


def run_pipeline(
    mode: str = "incremental",
    max_pages: int = 0,
    output_dir: Path = REPO_ROOT,
    base_name: str = "sismology",
    output_formats: list[str] | None = None,
    workers: int = 6,
    update_metadata: bool = True
) -> pd.DataFrame:
    """Ejecuta el pipeline completo de extracción soberana e integración OKF."""
    if output_formats is None:
        output_formats = ["csv"]

    csv_path = output_dir / f"{base_name}.csv"
    existing_df = pd.DataFrame(columns=TARGET_COLUMNS)
    known_links: set[str] = set()

    if mode == "incremental" and csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path, dtype={'profundidad': float, 'magnitud': float})
            known_links = set(existing_df['enlace_detalle'].dropna().unique())
            logging.info("Modo incremental: %d registros previos cargados desde %s", len(existing_df), csv_path.name)
        except Exception as e:
            logging.warning("Error leyendo dataset existente %s, procediendo con refresh: %s", csv_path, e)

    new_dataframes: list[pd.DataFrame] = []
    page_num = 1
    consecutive_known_pages = 0
    pbar = tqdm(desc="Extrayendo páginas OSC")

    while True:
        data, url, status_code = fetch_page_data(page_num)

        if data is None or not data:
            logging.info("Fin de listado o error en página %d.", page_num)
            break

        # En modo incremental, filtrar solo enlaces no registrados
        if mode == "incremental" and known_links:
            unseen_data = [row for row in data if row.get('enlace_detalle') not in known_links]
            if len(unseen_data) == 0:
                consecutive_known_pages += 1
                logging.info("Página %d con todos los registros ya conocidos (%d/2)", page_num, consecutive_known_pages)
                if consecutive_known_pages >= 2:
                    logging.info("Corte anticipado: registros actualizados hasta la última fecha disponible.")
                    break
            else:
                consecutive_known_pages = 0
                data_to_enrich = unseen_data
        else:
            data_to_enrich = data

        if data_to_enrich:
            data_enriched = enrich_with_details(data_to_enrich, max_workers=workers)
            df_page = transform_dataset(data_enriched, url, status_code)
            if not df_page.empty:
                new_dataframes.append(df_page)

        pbar.update(1)
        pbar.set_postfix({"pág": page_num, "nuevos": sum(len(df) for df in new_dataframes)})

        if max_pages > 0 and page_num >= max_pages:
            logging.info("Límite alcanzado de %d páginas solicitadas.", max_pages)
            break
        page_num += 1

    pbar.close()

    # Combinar registros nuevos con existentes
    if new_dataframes:
        new_df = pd.concat(new_dataframes, ignore_index=True)
        logging.info("Total nuevos registros extraídos: %d", len(new_df))
        if not existing_df.empty:
            final_df = pd.concat([new_df, existing_df], ignore_index=True)
        else:
            final_df = new_df

        # Deduplicar por enlace de detalle o tríada espacio-temporal
        final_df = final_df.drop_duplicates(subset=['enlace_detalle'], keep='first')
        if 'fecha_hora_registro' in final_df.columns:
            final_df = final_df.sort_values(by='fecha_hora_registro', ascending=False)

        save_dataset(final_df, output_dir, base_name, output_formats)

        if update_metadata:
            sync_okf_metadata(final_df, output_dir)
    elif mode == "full-refresh" and not existing_df.empty:
        final_df = existing_df
        save_dataset(final_df, output_dir, base_name, output_formats)
        if update_metadata:
            sync_okf_metadata(final_df, output_dir)
    else:
        logging.info("Sin registros nuevos detectados. El catálogo ya se encuentra actualizado.")
        final_df = existing_df

    return final_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extractor soberano de sismología de Bolivia (Observatorio San Calixto) para DataMesh."
    )
    parser.add_argument(
        "--mode",
        choices=["incremental", "full-refresh", "brute-force"],
        default="incremental",
        help="Modo de ejecución: 'incremental' (por defecto, detecta registros nuevos), 'full-refresh', o 'brute-force'"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(REPO_ROOT),
        help="Directorio de destino para los artefactos de datos (por defecto la raíz del repositorio)."
    )
    parser.add_argument(
        "--base-name",
        type=str,
        default="sismology",
        help="Nombre base del archivo de salida (por defecto 'sismology')."
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv,parquet",
        help="Formatos de exportación separados por coma (ej. 'csv,parquet')."
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Límite máximo de páginas a procesar (0 para sin límite)."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Número de hilos concurrentes para descarga de detalles."
    )
    parser.add_argument(
        "--no-metadata-update",
        action="store_true",
        help="Desactivar sincronización automática de datapackage.yaml e index.md"
    )

    args = parser.parse_args()
    output_dir = Path(args.data_dir).resolve()
    formats = [f.strip() for f in args.format.split(",") if f.strip()]

    logging.info("Ejecutando pipeline en %s (Modo: %s, Salida: %s)...", REPO_ROOT, args.mode, output_dir)

    run_pipeline(
        mode=args.mode,
        max_pages=args.max_pages,
        output_dir=output_dir,
        base_name=args.base_name,
        output_formats=formats,
        workers=args.workers,
        update_metadata=not args.no_metadata_update
    )


if __name__ == "__main__":
    main()
