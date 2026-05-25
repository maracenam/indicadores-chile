# ============================================================
# extraction/bcch_extractor.py
# Extrae datos desde la API del Banco Central de Chile
# ============================================================

import requests
import pandas as pd
from datetime import datetime
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import BCCH_USER, BCCH_PASSWORD, BCCH_BASE_URL, BCCH_SERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def fetch_series(series_id: str, date_start: str, date_end: str) -> pd.DataFrame:
    """
    Descarga una serie del Banco Central de Chile.

    Args:
        series_id:   Código de la serie (ej: 'F073.IPC.IND...')
        date_start:  Fecha inicio en formato 'YYYY-MM-DD'
        date_end:    Fecha fin   en formato 'YYYY-MM-DD'

    Returns:
        DataFrame con columnas ['fecha', 'valor', 'serie_id']
    """
    params = {
        "user":          BCCH_USER,
        "pass":          BCCH_PASSWORD,
        "firstdate":     date_start,
        "lastdate":      date_end,
        "timeseries":    series_id,
        "function":      "GetSeries",
        "cbFunctionType": "GetSeries",
        "format":        "json",
    }

    logger.info(f"Descargando serie: {series_id} | {date_start} → {date_end}")

    try:
        response = requests.get(BCCH_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # La API retorna los datos dentro de 'Series' > 'Obs'
        obs = data["Series"]["Obs"]

        df = pd.DataFrame(obs)
        df = df.rename(columns={"indexDateString": "fecha", "value": "valor"})

        # Limpiar y tipar
        df["fecha"]    = pd.to_datetime(df["fecha"], format="%d-%m-%Y", errors="coerce")
        df["valor"]    = pd.to_numeric(df["valor"].str.replace(",", "."), errors="coerce")
        df["serie_id"] = series_id
        df["descargado_en"] = datetime.utcnow()

        # Eliminar filas sin valor
        df = df.dropna(subset=["fecha", "valor"])
        df = df[["fecha", "valor", "serie_id", "descargado_en"]]

        logger.info(f"  → {len(df)} registros obtenidos")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al descargar {series_id}: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Error parseando respuesta de {series_id}: {e}")
        raise


def extract_all_series(date_start: str, date_end: str) -> dict[str, pd.DataFrame]:
    """
    Descarga todas las series configuradas en settings.py.

    Returns:
        Diccionario {nombre_serie: DataFrame}
    """
    resultados = {}

    for nombre, serie_id in BCCH_SERIES.items():
        try:
            df = fetch_series(serie_id, date_start, date_end)
            df["indicador"] = nombre  # Columna legible con el nombre del indicador
            resultados[nombre] = df
            logger.info(f"✓ {nombre} descargado correctamente")
        except Exception as e:
            logger.warning(f"✗ {nombre} falló: {e} — continuando con el resto")

    return resultados


# -------------------------------------------------------
# Ejecución directa para pruebas
# python extraction/bcch_extractor.py
# -------------------------------------------------------
if __name__ == "__main__":
    from config.settings import DATE_START, DATE_END

    datos = extract_all_series(DATE_START, DATE_END)

    for nombre, df in datos.items():
        print(f"\n{'='*40}")
        print(f"Serie: {nombre}")
        print(df.head(3).to_string(index=False))
        print(f"Total filas: {len(df)}")
