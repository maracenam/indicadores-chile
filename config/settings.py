# ============================================================
# config/settings.py
# Configuración central del proyecto
# ============================================================

import os

# --- Banco Central de Chile ---
# Regístrate en https://si.bcentral.cl para obtener estas credenciales
BCCH_USER     = os.getenv("BCCH_USER", "tu_email@ejemplo.com")
BCCH_PASSWORD = os.getenv("BCCH_PASSWORD", "tu_password")
BCCH_BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

# Códigos de series del Banco Central
# Puedes encontrar más en: https://si.bcentral.cl/siete/
BCCH_SERIES = {
    "ipc_variacion_mensual": "F073.IPC.IND.Z.Z.EP18.Z.N.M",   # Nota: Este es un Índice (IND). Si quieres la variación en %, revisa tu CSV o script.
    "uf_diario":             "F073.UFF.PRE.Z.D",              # UF valor diario (Código oficial corregido)
    "dolar_observado":       "F073.TCO.PRE.Z.D",              # Dólar observado (Código oficial corregido)
    "imacec_mensual":        "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M", # IMACEC mensual base 2018 (Confirmado en tu CSV)
}

# --- INE (desempleo) ---
# El INE tiene archivos Excel descargables, no requiere API key
INE_DESEMPLEO_URL = (
    "https://www.ine.gob.cl/docs/default-source/ocupacion-y-desempleo/"
    "bbdd/2024/trimestral/nacional/ene-2024-trimestre-movil.xlsx"
)

# --- Google Cloud Platform ---
GCP_PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "indicadores-chile-497405")  # Tu project ID en GCP
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME", "indicadores-raw")   # Nombre del bucket GCS
BQ_DATASET      = "indicadores_economicos"                           # Dataset en BigQuery

# Tablas en BigQuery
BQ_TABLES = {
    "ipc":       "ipc_mensual",
    "uf":        "uf_diario",
    "dolar":     "dolar_diario",
    "imacec":    "imacec_mensual",
    "desempleo": "desempleo_trimestral",
}

# --- Rango de fechas para carga inicial ---
DATE_START = "2015-01-01"   # Cambia según cuánto histórico quieras
DATE_END   = "2024-12-31"   # En producción esto será dinámico
