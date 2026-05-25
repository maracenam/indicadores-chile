# buscar_series.py — pégalo en la raíz y ejecútalo
import bcchapi
from dotenv import load_dotenv
import os

load_dotenv()

siete = bcchapi.Siete(os.getenv("BCCH_USER"), os.getenv("BCCH_PASSWORD"))

# Busca cada indicador y muéstrame el output completo
for termino in ["IPC", "UF", "dólar observado", "IMACEC"]:
    print(f"\n{'='*60}")
    print(f"Buscando: {termino}")
    print('='*60)
    resultado = siete.buscar(termino)
    print(resultado[["seriesId", "frequencyCode", "spanishTitle"]].to_string())