# ============================================================
# main.py
# Orquestador principal del pipeline
# Ejecutar localmente:   python main.py
# En Cloud Function:     la función entry_point() es el handler
# ============================================================

import logging
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from extraction.bcch_extractor import extract_all_series
from transformation.transformer import transform_all
from loading.bq_loader import load_all
from config.settings import DATE_START

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_pipeline(date_start: str = None, date_end: str = None):
    """
    Ejecuta el pipeline completo: Extract → Transform → Load.

    Args:
        date_start: Fecha inicio (default: DATE_START en settings)
        date_end:   Fecha fin    (default: hoy)
    """
    start_time = datetime.now(datetime.UTC)

    # Si no se pasan fechas, usar configuración por defecto
    if not date_start:
        date_start = DATE_START
    if not date_end:
        date_end = datetime.today().strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE — Indicadores Económicos Chile")
    logger.info(f"Rango de fechas: {date_start} → {date_end}")
    logger.info("=" * 60)

    # -------------------------------------------------------
    # PASO 1: EXTRACCIÓN
    # -------------------------------------------------------
    logger.info("\n[1/3] EXTRACCIÓN — Descargando desde BCCH...")
    try:
        raw_data = extract_all_series(date_start, date_end)
        logger.info(f"  → {len(raw_data)} series extraídas")
    except Exception as e:
        logger.error(f"Fallo en extracción: {e}")
        raise

    # -------------------------------------------------------
    # PASO 2: TRANSFORMACIÓN
    # -------------------------------------------------------
    logger.info("\n[2/3] TRANSFORMACIÓN — Limpiando y enriqueciendo datos...")
    try:
        transformed_data = transform_all(raw_data)
        logger.info(f"  → {len(transformed_data)} series transformadas")
    except Exception as e:
        logger.error(f"Fallo en transformación: {e}")
        raise

    # -------------------------------------------------------
    # PASO 3: CARGA
    # -------------------------------------------------------
    logger.info("\n[3/3] CARGA — Subiendo a GCS y BigQuery...")
    try:
        load_all(transformed_data)
        logger.info("  → Carga completada")
    except Exception as e:
        logger.error(f"Fallo en carga: {e}")
        raise

    # -------------------------------------------------------
    # RESUMEN
    # -------------------------------------------------------
    elapsed = (datetime.now(datetime.UTC) - start_time).seconds
    logger.info("\n" + "=" * 60)
    logger.info(f"✓ PIPELINE COMPLETADO en {elapsed} segundos")
    for nombre, df in transformed_data.items():
        logger.info(f"  • {nombre}: {len(df)} filas procesadas")
    logger.info("=" * 60)


# -------------------------------------------------------
# Entry point para Google Cloud Functions
# En GCP configuras esta función como handler HTTP
# -------------------------------------------------------
def entry_point(request):
    """Handler para Cloud Functions (trigger HTTP o Pub/Sub)."""
    try:
        run_pipeline()
        return {"status": "ok", "message": "Pipeline ejecutado correctamente"}, 200
    except Exception as e:
        logger.error(f"Pipeline falló: {e}")
        return {"status": "error", "message": str(e)}, 500


# -------------------------------------------------------
# Ejecución local
# -------------------------------------------------------
if __name__ == "__main__":
    # Modo de prueba: últimos 3 meses solamente
    # Cuando quieras carga completa, elimina estos argumentos
    fecha_fin   = datetime.today().strftime("%Y-%m-%d")
    fecha_inicio = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")

    run_pipeline(date_start=fecha_inicio, date_end=fecha_fin)
