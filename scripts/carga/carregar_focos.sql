-- Carrega data/processed/focos_df_2015_2025.csv (gerado por src/pipeline/extract_focos.py)
-- em satelite e foco_calor. Roda dentro do serviço `load` do docker-compose.
-- Reexecutável: esvazia foco_calor e a staging antes de recarregar, então
-- repetir o comando de subida não duplica focos.

TRUNCATE TABLE foco_calor RESTART IDENTITY;
TRUNCATE TABLE staging.foco_calor_raw;

\copy staging.foco_calor_raw FROM '/data/processed/focos_df_2015_2025.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

INSERT INTO satelite (nome, is_referencia)
SELECT DISTINCT satelite, (satelite = 'AQUA_M-T')
FROM staging.foco_calor_raw
ON CONFLICT (nome) DO NOTHING;

INSERT INTO foco_calor (id_satelite, data_hora_evento, data_hora_ingestao, municipio, bioma, risco_fogo, geom)
SELECT
    s.id_satelite,
    r.data_hora_evento,
    r.data_hora_ingestao,
    r.municipio,
    r.bioma,
    r.risco_fogo,
    ST_Transform(ST_SetSRID(ST_MakePoint(r.longitude, r.latitude), 4326), 31983)
FROM staging.foco_calor_raw r
JOIN satelite s ON s.nome = r.satelite;

ANALYZE foco_calor, satelite;

SELECT count(*) AS total_focos_carregados FROM foco_calor;
