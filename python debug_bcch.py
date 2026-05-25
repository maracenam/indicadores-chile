# debug_bcch.py — pon esto en la raíz del proyecto y ejecútalo
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

params = {
    "user":           os.getenv("BCCH_USER"),
    "pass":           os.getenv("BCCH_PASSWORD"),
    "firstdate":      "2026-02-01",
    "lastdate":       "2026-05-25",
    "timeseries":     "F073.TCO.PRE.Z.Z.EP17.TUF.N.D",  # UF
    "function":       "GetSeries",
    "cbFunctionType": "GetSeries",
    "format":         "json",
}

r = requests.get("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx", params=params)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))