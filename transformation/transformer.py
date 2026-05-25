# ============================================================
# transformation/transformer.py
# Limpia y transforma los datos crudos antes de cargar a BigQuery
# ============================================================

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def transform_ipc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma datos del IPC (variación mensual).
    Agrega variación acumulada 12 meses (inflación anual).
    """
    df = df.copy()
    df = df.sort_values("fecha").reset_index(drop=True)

    # Variación acumulada 12 meses (suma rolling de variaciones mensuales)
    df["variacion_anual"] = df["valor"].rolling(window=12).sum().round(2)

    # Columnas de tiempo útiles para Power BI
    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month
    df["mes_nombre"] = df["fecha"].dt.strftime("%B")

    df = df.rename(columns={"valor": "variacion_mensual"})

    logger.info(f"IPC transformado: {len(df)} filas")
    return df[["fecha", "anio", "mes", "mes_nombre", "variacion_mensual", "variacion_anual"]]


def transform_uf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma datos de la UF.
    Agrega variación porcentual diaria y valor fin de mes.
    """
    df = df.copy()
    df = df.sort_values("fecha").reset_index(drop=True)

    df["variacion_diaria_pct"] = df["valor"].pct_change().mul(100).round(4)

    # Valor al último día de cada mes (útil para reportes)
    df["es_fin_de_mes"] = ~df["fecha"].dt.to_period("M").duplicated(keep="last")

    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month

    df = df.rename(columns={"valor": "valor_uf"})

    logger.info(f"UF transformada: {len(df)} filas")
    return df[["fecha", "anio", "mes", "valor_uf", "variacion_diaria_pct", "es_fin_de_mes"]]


def transform_dolar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma datos del Dólar Observado.
    Similar a UF pero agrega promedio mensual.
    """
    df = df.copy()
    df = df.sort_values("fecha").reset_index(drop=True)

    df["variacion_diaria_pct"] = df["valor"].pct_change().mul(100).round(4)

    # Promedio móvil 30 días
    df["promedio_30d"] = df["valor"].rolling(window=30).mean().round(2)

    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month

    df = df.rename(columns={"valor": "valor_dolar"})

    logger.info(f"Dólar transformado: {len(df)} filas")
    return df[["fecha", "anio", "mes", "valor_dolar", "variacion_diaria_pct", "promedio_30d"]]


def transform_imacec(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma datos del IMACEC.
    Agrega variación anual (mismo mes año anterior).
    """
    df = df.copy()
    df = df.sort_values("fecha").reset_index(drop=True)

    # Variación respecto al mismo mes del año anterior
    df["variacion_anual_pct"] = df["valor"].pct_change(periods=12).mul(100).round(2)

    df["anio"] = df["fecha"].dt.year
    df["mes"]  = df["fecha"].dt.month
    df["mes_nombre"] = df["fecha"].dt.strftime("%B")

    df = df.rename(columns={"valor": "indice_imacec"})

    logger.info(f"IMACEC transformado: {len(df)} filas")
    return df[["fecha", "anio", "mes", "mes_nombre", "indice_imacec", "variacion_anual_pct"]]


def validate_dataframe(df: pd.DataFrame, nombre: str) -> bool:
    """
    Validaciones básicas antes de cargar a BigQuery.
    Retorna True si pasa, False si hay problemas.
    """
    errores = []

    if df.empty:
        errores.append("DataFrame vacío")

    nulos_criticos = df[["fecha"]].isnull().sum()
    if nulos_criticos.any():
        errores.append(f"Nulos en columna fecha: {nulos_criticos.to_dict()}")

    # Verificar que no haya fechas futuras
    if df["fecha"].max() > pd.Timestamp.today():
        errores.append("Hay fechas futuras en los datos")

    if errores:
        for err in errores:
            logger.warning(f"[{nombre}] Validación fallida: {err}")
        return False

    logger.info(f"[{nombre}] ✓ Validación OK — {len(df)} filas, "
                f"rango: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    return True


# Mapa de funciones de transformación por indicador
TRANSFORMERS = {
    "ipc_variacion_mensual": transform_ipc,
    "uf_diario":             transform_uf,
    "dolar_observado":       transform_dolar,
    "imacec_mensual":        transform_imacec,
}


def transform_all(raw_data: dict) -> dict[str, pd.DataFrame]:
    """
    Aplica la transformación correcta a cada indicador.

    Args:
        raw_data: Dict {nombre_serie: DataFrame crudo}

    Returns:
        Dict {nombre_serie: DataFrame transformado y validado}
    """
    transformados = {}

    for nombre, df in raw_data.items():
        if nombre not in TRANSFORMERS:
            logger.warning(f"No hay transformer para '{nombre}', se omite")
            continue

        try:
            df_transformed = TRANSFORMERS[nombre](df)
            if validate_dataframe(df_transformed, nombre):
                transformados[nombre] = df_transformed
        except Exception as e:
            logger.error(f"Error transformando {nombre}: {e}")

    return transformados
