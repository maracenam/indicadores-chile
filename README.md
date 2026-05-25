# 📊 Pipeline Indicadores Económicos Chile

Pipeline de datos automatizado que extrae, transforma y carga indicadores macroeconómicos de Chile (IPC, UF, Dólar, IMACEC) desde el Banco Central hacia BigQuery, con visualización en Power BI.

## 🏗️ Arquitectura

```
[API Banco Central] 
        ↓ Python (requests)
[Cloud Storage - raw/]     ← respaldo del dato crudo
        ↓
[Python - pandas]          ← limpieza y enriquecimiento
        ↓
[BigQuery]                 ← almacenamiento analítico
        ↓ SQL Views
[Power BI]                 ← dashboard interactivo
        ↑
[Cloud Scheduler]          ← automatización mensual
```

## 📁 Estructura del proyecto

```
indicadores-chile/
├── config/
│   └── settings.py         # Variables de configuración y series BCCH
├── extraction/
│   └── bcch_extractor.py   # Descarga desde API del Banco Central
├── transformation/
│   └── transformer.py      # Limpieza, enriquecimiento y validación
├── loading/
│   └── bq_loader.py        # Carga incremental a GCS y BigQuery
├── sql/
│   └── views.sql           # Vistas en BigQuery para Power BI
├── main.py                 # Orquestador del pipeline
├── requirements.txt
└── README.md
```

## 🚀 Setup local

### 1. Clonar y preparar entorno

```bash
git clone https://github.com/tu-usuario/indicadores-chile.git
cd indicadores-chile
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

Crear archivo `.env` en la raíz (nunca subir al repo):

```env
BCCH_USER=tu_email@ejemplo.com
BCCH_PASSWORD=tu_password_bcch
GCP_PROJECT_ID=indicadores-chile
GCP_BUCKET_NAME=indicadores-raw
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/service-account.json
```

### 3. Credenciales GCP

1. Ir a GCP Console → IAM → Service Accounts
2. Crear service account con roles: `BigQuery Admin`, `Storage Admin`
3. Descargar JSON de credenciales
4. Apuntar `GOOGLE_APPLICATION_CREDENTIALS` a ese archivo

### 4. Ejecutar el pipeline

```bash
# Prueba con últimos 3 meses
python main.py

# Carga histórica completa (editar fechas en main.py)
python main.py
```

## 📈 Indicadores incluidos

| Indicador | Fuente | Frecuencia | Tabla BQ |
|-----------|--------|------------|----------|
| IPC (variación mensual) | BCCH | Mensual | `ipc_mensual` |
| UF (valor diario) | BCCH | Diario | `uf_diario` |
| Dólar observado | BCCH | Diario | `dolar_diario` |
| IMACEC | BCCH | Mensual | `imacec_mensual` |

## ☁️ Deploy en GCP (automatización)

```bash
# Deploy como Cloud Function
gcloud functions deploy indicadores-pipeline \
  --runtime python311 \
  --trigger-http \
  --entry-point entry_point \
  --memory 512MB \
  --timeout 300s \
  --set-env-vars GCP_PROJECT_ID=indicadores-chile,...

# Crear scheduler mensual (día 5 de cada mes, 8am)
gcloud scheduler jobs create http indicadores-mensual \
  --schedule="0 8 5 * *" \
  --uri="https://REGION-PROJECT.cloudfunctions.net/indicadores-pipeline" \
  --time-zone="America/Santiago"
```

## 🔧 Decisiones técnicas

- **Carga incremental**: el pipeline solo sube fechas nuevas, evitando duplicados
- **Capa raw en GCS**: se preserva el dato original antes de cualquier transformación
- **Vistas en BigQuery**: Power BI consume vistas, no tablas directamente (más flexible)
- **Cloud Functions**: permite escalar a 0 cuando no hay ejecuciones (costo mínimo)

## 📊 Power BI

El dashboard se conecta a BigQuery usando el conector nativo de Power BI.
Vistas principales utilizadas:
- `vw_resumen_mensual` — página principal con todos los indicadores
- `vw_uf_anual` — análisis año a año de la UF
- `vw_ipc_acumulado_anual` — inflación anual histórica
- `vw_ultimos_13_meses` — KPIs del último año

---

*Proyecto desarrollado como práctica de ingeniería de datos. Datos públicos del [Banco Central de Chile](https://si.bcentral.cl).*
