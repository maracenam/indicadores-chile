# 📊 Pipeline de Indicadores Económicos — Chile

Pipeline de datos **end-to-end** que extrae indicadores macroeconómicos chilenos desde la API del Banco Central, los transforma y carga automáticamente en Google BigQuery, y los visualiza en un dashboard interactivo de Power BI.

> Proyecto de portafolio orientado a roles de **Analista / Ingeniero de Datos**.

---

## 🏗️ Arquitectura

```
[API Banco Central de Chile]
        │  bcchapi (Python)
        ▼
┌─────────────────────────────────┐
│         Python ETL              │
│  bcch_extractor.py              │  ◄── Cloud Scheduler (mensual)
│  transformer.py                 │         via main.py
│  bq_loader.py                   │
└────────┬──────────────┬─────────┘
         │              │
         ▼              ▼
 [Cloud Storage]    [BigQuery]
  Capa raw JSON    uf · dolar · imacec
                        │
                        ▼
                  [Vistas SQL]
              vw_resumen_mensual
              vw_dolar_mensual
              vw_uf_mensual
              vw_kpis_actuales
                        │
                        ▼
                  [Power BI]
               Dashboard interactivo
```

---

## 📦 Stack tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Extracción | `bcchapi` (librería oficial del Banco Central) |
| Transformación | `pandas`, `numpy` |
| Almacenamiento raw | Google Cloud Storage |
| Almacenamiento analítico | Google BigQuery |
| Orquestación | Google Cloud Scheduler + Cloud Functions |
| Visualización | Microsoft Power BI Desktop |
| Control de versiones | Git / GitHub |

---

## 📈 Indicadores incluidos

| Indicador | Fuente | Frecuencia | Tabla BigQuery |
|---|---|---|---|
| UF (valor diario) | Banco Central | Diaria | `uf_diario` |
| Dólar observado | Banco Central | Diaria | `dolar_diario` |
| IMACEC | Banco Central | Mensual | `imacec_mensual` |

---

## 📁 Estructura del proyecto

```
indicadores-chile/
├── config/
│   └── settings.py          # Configuración central: series, IDs de GCP, tablas BQ
├── extraction/
│   └── bcch_extractor.py    # Descarga series desde API del Banco Central con bcchapi
├── transformation/
│   └── transformer.py       # Limpieza, enriquecimiento y validación de datos
├── loading/
│   └── bq_loader.py         # Carga incremental a GCS (raw) y BigQuery
├── sql/
│   └── views.sql            # Vistas en BigQuery que alimentan Power BI
├── main.py                  # Orquestador del pipeline (ETL completo)
├── requirements.txt
├── .gitignore               # Excluye credenciales y venv
└── README.md
```

---

## 🚀 Configuración local

### 1. Clonar el repositorio

```bash
git clone https://github.com/maracenam/indicadores-chile.git
cd indicadores-chile
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Crear archivo `.env`

Crea un archivo `.env` en la raíz del proyecto (nunca se sube al repo):

```env
BCCH_USER=tu_email@ejemplo.com
BCCH_PASSWORD=tu_password_bcch
GCP_PROJECT_ID=tu-project-id
GCP_BUCKET_NAME=nombre-de-tu-bucket
GOOGLE_APPLICATION_CREDENTIALS=C:\ruta\a\service-account.json
```

**Credenciales necesarias:**
- **Banco Central:** Registro gratuito en [si.bcentral.cl](https://si.bcentral.cl)
- **GCP:** Service account con roles `BigQuery Admin` y `Storage Admin`

### 4. Ejecutar el pipeline

```bash
# Prueba con los últimos 90 días
python main.py

# Carga histórica completa (editar fechas en main.py)
# Cambiar: run_pipeline(date_start="2020-01-01", ...)
```

---

## ☁️ Automatización en GCP

El pipeline está desplegado como **Cloud Function** y se ejecuta automáticamente mediante **Cloud Scheduler**.

### Deploy de la Cloud Function

```bash
gcloud functions deploy indicadores-pipeline \
  --runtime python311 \
  --trigger-http \
  --entry-point entry_point \
  --memory 512MB \
  --timeout 300s \
  --set-env-vars GCP_PROJECT_ID=tu-project-id,GCP_BUCKET_NAME=tu-bucket,...
```

### Crear el job de Cloud Scheduler

```bash
# Ejecuta el día 5 de cada mes a las 8:00 AM hora de Santiago
gcloud scheduler jobs create http indicadores-mensual \
  --schedule="0 8 5 * *" \
  --uri="https://REGION-PROJECT.cloudfunctions.net/indicadores-pipeline" \
  --time-zone="America/Santiago"
```

---

## 🗄️ Vistas SQL en BigQuery

Las vistas centralizan la lógica de negocio y separan el modelo de datos del dashboard.

| Vista | Descripción | Uso en Power BI |
|---|---|---|
| `vw_resumen_mensual` | IMACEC + UF fin de mes + Dólar fin de mes | Página principal |
| `vw_dolar_mensual` | Promedio, mínimo y máximo del dólar por mes | Página dólar |
| `vw_uf_mensual` | Valor UF al último día de cada mes | Página UF |
| `vw_kpis_actuales` | Últimos valores de todos los indicadores | Tarjetas KPI |

---

## 📊 Dashboard Power BI

El dashboard se conecta directamente a BigQuery mediante el conector nativo de Power BI.

**Páginas del dashboard:**
- **Resumen general** — Tarjetas KPI con los valores actuales de UF, Dólar e IMACEC
- **Dólar** — Evolución diaria y promedios mensuales con variaciones
- **UF** — Evolución mensual del valor de la UF desde 2020
- **IMACEC** — Índice mensual de actividad económica con variación anual

**Medidas DAX utilizadas:**
```dax
-- Variación dólar mes a mes
Variación Dólar MoM =
VAR dolar_actual   = CALCULATE(MAX(vw_dolar_mensual[dolar_promedio]))
VAR dolar_anterior = CALCULATE(
    MAX(vw_dolar_mensual[dolar_promedio]),
    DATEADD(vw_dolar_mensual[fecha], -1, MONTH)
)
RETURN DIVIDE(dolar_actual - dolar_anterior, dolar_anterior) * 100
```

---

## 🔧 Decisiones de diseño

- **Carga incremental:** el pipeline consulta la fecha máxima existente en BigQuery y solo sube registros nuevos, evitando duplicados y reduciendo costos de procesamiento.
- **Capa raw en GCS:** se preserva el dato original antes de cualquier transformación, permitiendo reprocesar sin volver a llamar a la API.
- **Vistas en lugar de tablas:** Power BI consume vistas SQL en vez de tablas directamente, lo que permite modificar la lógica de negocio sin tocar el dashboard.
- **Cloud Function vs VM:** se eligió Cloud Function porque el pipeline es de corta duración y ejecución mensual, lo que reduce el costo a prácticamente cero en el free tier.
- **Validaciones en transformación:** cada DataFrame pasa por validaciones de nulos, tipos de datos y rangos de fechas antes de ser cargado, evitando datos corruptos en BigQuery.

---

## 📋 Requisitos previos

- Python 3.11+
- Cuenta en [si.bcentral.cl](https://si.bcentral.cl) (gratuita)
- Proyecto en Google Cloud Platform con BigQuery y Cloud Storage habilitados
- Power BI Desktop (gratuito)

---

## 🗺️ Próximos pasos

- [ ] Agregar IPC (índice de precios al consumidor)
- [ ] Tests unitarios con `pytest` para las funciones de transformación
- [ ] Notificación por email si el pipeline falla (Cloud Monitoring)
- [ ] Incorporar datos del INE (tasa de desempleo trimestral)

---

*Datos públicos del [Banco Central de Chile](https://si.bcentral.cl) — uso educativo y de portafolio.*
