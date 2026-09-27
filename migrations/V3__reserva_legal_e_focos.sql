-- V3: tabelas dependentes (reserva_legal -> imovel_car; foco_calor -> satelite).
-- foco_calor é somente inserção: trigger bloqueia UPDATE e DELETE.
-- TRUNCATE continua liberado para recarga completa em ambiente de desenvolvimento.

CREATE TABLE reserva_legal (
    id_reserva      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_imovel      VARCHAR(60) NOT NULL REFERENCES imovel_car (cod_imovel) ON DELETE CASCADE,
    situacao        VARCHAR(40),
    area_ha         NUMERIC(14, 4) CHECK (area_ha IS NULL OR area_ha > 0),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

COMMENT ON TABLE reserva_legal IS
    'Polígono de reserva legal do imóvel CAR. Um imóvel pode ter uma ou mais feições de RL.';
COMMENT ON COLUMN reserva_legal.data_download IS
    'Data do recorte SICAR desta feição. Deve coincidir com data_download do imóvel na mesma carga.';

CREATE TABLE foco_calor (
    id_foco             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_satelite         SMALLINT NOT NULL REFERENCES satelite (id_satelite),
    data_hora_evento    TIMESTAMPTZ NOT NULL,
    data_hora_ingestao  TIMESTAMPTZ NOT NULL DEFAULT now(),
    municipio           VARCHAR(80),
    bioma               VARCHAR(40),
    risco_fogo          NUMERIC(4, 3) CHECK (risco_fogo IS NULL OR risco_fogo BETWEEN 0 AND 1),
    geom                geometry(Point, 31983) NOT NULL
                        CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
    CONSTRAINT ck_foco_calor_ingestao_apos_evento
        CHECK (data_hora_ingestao >= data_hora_evento)
);

COMMENT ON TABLE foco_calor IS
    'Foco de calor do BDQueimadas (INPE), recorte DF. Insert-only. Reincidência conta anos distintos de data_hora_evento.';
COMMENT ON COLUMN foco_calor.data_hora_evento IS
    'Passagem do satélite / detecção do calor. Ano da reincidência sai deste campo, nunca de data_hora_ingestao.';
COMMENT ON COLUMN foco_calor.data_hora_ingestao IS
    'Momento em que o registro entrou no banco (carga).';
COMMENT ON COLUMN foco_calor.id_satelite IS
    'Satélite que detectou o foco. Nunca descartar na carga. Todos entram na reincidência; séries comparáveis filtram is_referencia.';
COMMENT ON COLUMN foco_calor.geom IS
    'Ponto em EPSG:31983. Gerar a partir de lon/lat (4326) com ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 31983).';

CREATE FUNCTION bloqueia_alteracao_foco() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'foco_calor e somente insercao (operacao % bloqueada)', TG_OP;
END;
$$;

CREATE TRIGGER tg_foco_calor_imutavel
    BEFORE UPDATE OR DELETE ON foco_calor
    FOR EACH ROW EXECUTE FUNCTION bloqueia_alteracao_foco();
