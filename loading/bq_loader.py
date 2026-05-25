# ============================================================
# loading/bq_loader.py
# Carga los datos transformados a BigQuery (carga incremental)
# ============================================================

import pandas as pd
from google.cloud import bigquery, storage
from google.api_core.exceptions import NotFound
import logging
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import GCP_PROJECT_ID, GCP_BUCKET_NAME, BQ_DATASET, BQ_TABLES

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Schemas de BigQuery por tabla
# Definir explícitamente evita errores de tipo en producción
# -------------------------------------------------------
BQ_SCHEMAS = {
    "ipc_mensual": [
        bigquery.SchemaField("fecha",              "DATE"),
        bigquery.SchemaField("anio",               "INTEGER"),
        bigquery.SchemaField("mes",                "INTEGER"),
        bigquery.SchemaField("mes_nombre",         "STRING"),
        bigquery.SchemaField("variacion_mensual",  "FLOAT"),
        bigquery.SchemaField("variacion_anual",    "FLOAT"),
    ],
    "uf_diario": [
        bigquery.SchemaField("fecha",              "DATE"),
        bigquery.SchemaField("anio",               "INTEGER"),
        bigquery.SchemaField("mes",                "INTEGER"),
        bigquery.SchemaField("valor_uf",           "FLOAT"),
        bigquery.SchemaField("variacion_diaria_pct", "FLOAT"),
        bigquery.SchemaField("es_fin_de_mes",      "BOOLEAN"),
    ],
    "dolar_diario": [
        bigquery.SchemaField("fecha",              "DATE"),
        bigquery.SchemaField("anio",               "INTEGER"),
        bigquery.SchemaField("mes",                "INTEGER"),
        bigquery.SchemaField("valor_dolar",        "FLOAT"),
        bigquery.SchemaField("variacion_diaria_pct", "FLOAT"),
        bigquery.SchemaField("promedio_30d",       "FLOAT"),
    ],
    "imacec_mensual": [
        bigquery.SchemaField("fecha",              "DATE"),
        bigquery.SchemaField("anio",               "INTEGER"),
        bigquery.SchemaField("mes",                "INTEGER"),
        bigquery.SchemaField("mes_nombre",         "STRING"),
        bigquery.SchemaField("indice_imacec",      "FLOAT"),
        bigquery.SchemaField("variacion_anual_pct", "FLOAT"),
    ],
}

# Mapa entre nombre de serie y nombre de tabla BQ
SERIE_TO_TABLE = {
    "ipc_variacion_mensual": "ipc_mensual",
    "uf_diario":             "uf_diario",
    "dolar_observado":       "dolar_diario",
    "imacec_mensual":        "imacec_mensual",
}


def get_bq_client() -> bigquery.Client:
    """Retorna cliente de BigQuery autenticado."""
    # Localmente: apunta a tu service account con la variable de entorno
    # GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credentials.json
    return bigquery.Client(project=GCP_PROJECT_ID)


def get_storage_client() -> storage.Client:
    """Retorna cliente de Cloud Storage autenticado."""
    return storage.Client(project=GCP_PROJECT_ID)


def create_dataset_if_not_exists(client: bigquery.Client):
    """Crea el dataset en BigQuery si no existe."""
    dataset_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}"
    try:
        client.get_dataset(dataset_ref)
        logger.info(f"Dataset '{BQ_DATASET}' ya existe")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        logger.info(f"Dataset '{BQ_DATASET}' creado")


def get_max_fecha(client: bigquery.Client, table_name: str) -> str | None:
    """
    Retorna la fecha máxima existente en la tabla.
    Sirve para hacer carga incremental (solo subir datos nuevos).
    """
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}"
    query = f"SELECT MAX(fecha) as max_fecha FROM `{table_id}`"
    try:
        result = client.query(query).result()
        for row in result:
            if row.max_fecha:
                return str(row.max_fecha)
    except NotFound:
        pass  # La tabla no existe aún, carga completa
    return None


def upload_to_gcs(df: pd.DataFrame, nombre: str) -> str:
    """
    Sube el DataFrame como JSON a Cloud Storage (capa raw).
    Esto preserva el dato original antes de cargar a BQ.

    Returns:
        URI del archivo en GCS (gs://bucket/path)
    """
    from datetime import datetime
    client = get_storage_client()
    bucket = client.bucket(GCP_BUCKET_NAME)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"raw/{nombre}/{timestamp}.json"
    blob = bucket.blob(blob_name)

    json_data = df.to_json(orient="records", date_format="iso", force_ascii=False)
    blob.upload_from_string(json_data, content_type="application/json")

    uri = f"gs://{GCP_BUCKET_NAME}/{blob_name}"
    logger.info(f"Raw guardado en GCS: {uri}")
    return uri


def load_to_bigquery(df: pd.DataFrame, table_name: str, client: bigquery.Client):
    """
    Carga un DataFrame a BigQuery con carga incremental.
    Solo sube filas con fecha > max_fecha existente en la tabla.
    """
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}"

    # Carga incremental: filtrar solo fechas nuevas
    max_fecha = get_max_fecha(client, table_name)
    if max_fecha:
        df_new = df[df["fecha"] > pd.Timestamp(max_fecha)]
        logger.info(f"Carga incremental: {len(df_new)} filas nuevas "
                    f"(desde {max_fecha})")
    else:
        df_new = df
        logger.info(f"Primera carga: {len(df_new)} filas totales")

    if df_new.empty:
        logger.info(f"  → Sin datos nuevos para {table_name}, se omite carga")
        return

    # Configurar el job de carga
    job_config = bigquery.LoadJobConfig(
        schema=BQ_SCHEMAS.get(table_name, []),
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # Agrega, no reemplaza
    )

    # Convertir columna fecha a string para compatibilidad
    df_new = df_new.copy()
    df_new["fecha"] = pd.to_datetime(df_new["fecha"])

    job = client.load_table_from_dataframe(df_new, table_id, job_config=job_config)
    job.result()  # Esperar que termine

    logger.info(f"✓ {len(df_new)} filas cargadas a {table_id}")


def load_all(transformed_data: dict):
    """
    Orquesta la carga completa:
    1. Sube raw a GCS
    2. Carga transformado a BigQuery

    Args:
        transformed_data: Dict {nombre_serie: DataFrame transformado}
    """
    client = get_bq_client()
    create_dataset_if_not_exists(client)

    for nombre, df in transformed_data.items():
        table_name = SERIE_TO_TABLE.get(nombre)
        if not table_name:
            logger.warning(f"No hay tabla mapeada para '{nombre}'")
            continue

        try:
            # 1. Guardar raw en GCS
            upload_to_gcs(df, nombre)

            # 2. Cargar a BigQuery
            load_to_bigquery(df, table_name, client)

        except Exception as e:
            logger.error(f"Error cargando {nombre} a BigQuery: {e}")
            raise
