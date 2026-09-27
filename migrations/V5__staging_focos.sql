-- V5: tabela de staging para o CSV bruto dos focos de calor do INPE.
-- Recebe o dado como o pipeline de extração grava: coordenadas separadas e
-- texto sem conversão de tipo, antes da montagem da geometria em foco_calor.

CREATE TABLE staging.foco_calor_raw (
    latitude                NUMERIC,
    longitude               NUMERIC,
    data_hora_evento        TIMESTAMPTZ,
    data_hora_ingestao      TIMESTAMPTZ,
    satelite                VARCHAR(40),
    is_satelite_referencia  BOOLEAN,
    municipio               VARCHAR(80),
    bioma                   VARCHAR(40),
    risco_fogo              NUMERIC(4, 3)
);
