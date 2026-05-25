-- ============================================================
-- sql/views.sql
-- Vistas en BigQuery que alimentan Power BI
-- Ejecutar en la consola de BigQuery o con bq CLI
-- ============================================================

-- -------------------------------------------------------
-- 1. Vista maestra: todos los indicadores mensuales juntos
--    Útil para cruzar IPC, IMACEC y desempleo en un solo gráfico
-- -------------------------------------------------------
CREATE OR REPLACE VIEW `indicadores_economicos.vw_resumen_mensual` AS
SELECT
    i.fecha,
    i.anio,
    i.mes,
    i.mes_nombre,
    i.variacion_mensual   AS ipc_variacion_mensual,
    i.variacion_anual     AS ipc_variacion_anual,
    im.indice_imacec,
    im.variacion_anual_pct AS imacec_variacion_anual,
    -- UF y dólar: último valor del mes
    uf.valor_uf           AS uf_fin_mes,
    d.valor_dolar         AS dolar_fin_mes
FROM
    `indicadores_economicos.ipc_mensual` i
LEFT JOIN
    `indicadores_economicos.imacec_mensual` im
    ON i.fecha = im.fecha
LEFT JOIN (
    -- Último valor de UF por mes
    SELECT anio, mes, valor_uf
    FROM `indicadores_economicos.uf_diario`
    WHERE es_fin_de_mes = TRUE
) uf ON i.anio = uf.anio AND i.mes = uf.mes
LEFT JOIN (
    -- Último valor de dólar por mes
    SELECT
        EXTRACT(YEAR  FROM fecha) AS anio,
        EXTRACT(MONTH FROM fecha) AS mes,
        valor_dolar
    FROM (
        SELECT
            fecha,
            valor_dolar,
            ROW_NUMBER() OVER (
                PARTITION BY EXTRACT(YEAR FROM fecha), EXTRACT(MONTH FROM fecha)
                ORDER BY fecha DESC
            ) AS rn
        FROM `indicadores_economicos.dolar_diario`
    )
    WHERE rn = 1
) d ON i.anio = d.anio AND i.mes = d.mes
ORDER BY i.fecha;


-- -------------------------------------------------------
-- 2. Vista: variación anual UF (comparativa año a año)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW `indicadores_economicos.vw_uf_anual` AS
SELECT
    anio,
    mes,
    AVG(valor_uf)     AS uf_promedio_mes,
    MIN(valor_uf)     AS uf_min_mes,
    MAX(valor_uf)     AS uf_max_mes,
    MAX(valor_uf) - MIN(valor_uf) AS uf_rango_mes
FROM
    `indicadores_economicos.uf_diario`
GROUP BY
    anio, mes
ORDER BY
    anio, mes;


-- -------------------------------------------------------
-- 3. Vista: IPC acumulado por año (inflación total del año)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW `indicadores_economicos.vw_ipc_acumulado_anual` AS
SELECT
    anio,
    ROUND(SUM(variacion_mensual), 2) AS inflacion_anual_pct,
    COUNT(*)                          AS meses_con_dato
FROM
    `indicadores_economicos.ipc_mensual`
GROUP BY
    anio
ORDER BY
    anio;


-- -------------------------------------------------------
-- 4. Vista: últimos 13 meses (para tarjetas KPI en Power BI)
-- -------------------------------------------------------
CREATE OR REPLACE VIEW `indicadores_economicos.vw_ultimos_13_meses` AS
SELECT *
FROM `indicadores_economicos.vw_resumen_mensual`
WHERE fecha >= DATE_SUB(
    DATE_TRUNC(CURRENT_DATE(), MONTH),
    INTERVAL 12 MONTH
)
ORDER BY fecha DESC;
