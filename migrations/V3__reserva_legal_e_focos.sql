-- V3: tabelas dependentes: reserva_legal (-> imovel_car) e foco_calor (-> satelite).
-- foco_calor é somente inserção: trigger bloqueia UPDATE e DELETE (TRUNCATE continua liberado para recarga).

CREATE TABLE reserva_legal (
    id_reserva      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_imovel      VARCHAR(60) NOT NULL REFERENCES imovel_car (cod_imovel) ON DELETE CASCADE,
    situacao        VARCHAR(40),
    area_ha         NUMERIC(14, 4) CHECK (area_ha > 0),
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

CREATE TABLE foco_calor (
    id_foco             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_satelite         SMALLINT NOT NULL REFERENCES satelite (id_satelite),
    data_hora_evento    TIMESTAMPTZ NOT NULL,
    data_hora_ingestao  TIMESTAMPTZ NOT NULL DEFAULT now(),
    municipio           VARCHAR(80),
    bioma               VARCHAR(40),
    risco_fogo          NUMERIC(4, 3) CHECK (risco_fogo BETWEEN 0 AND 1),
    geom                geometry(Point, 31983) NOT NULL
                        CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
    CONSTRAINT ck_foco_calor_ingestao_apos_evento CHECK (data_hora_ingestao >= data_hora_evento)
);

CREATE FUNCTION bloqueia_alteracao_foco() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'foco_calor é somente inserção (% bloqueado)', TG_OP;
END;
$$;

CREATE TRIGGER tg_foco_calor_imutavel
    BEFORE UPDATE OR DELETE ON foco_calor
    FOR EACH ROW EXECUTE FUNCTION bloqueia_alteracao_foco();
