-- V2: tabelas sem dependências: satelite, unidade_conservacao, area_preservacao_permanente e imovel_car.
-- Rascunho provisório até o esquema da Modelagem Espacial ser fechado.
-- SRID 31983 (SIRGAS 2000 / UTM 23S): métrico, permite ST_DWithin(geom, geom, 1000) sem cast para geography.

CREATE TABLE satelite (
    id_satelite     SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(40) NOT NULL UNIQUE CHECK (btrim(nome) <> ''),
    is_referencia   BOOLEAN NOT NULL DEFAULT FALSE
);

-- Garante um único satélite de referência (AQUA_M-T no INPE).
CREATE UNIQUE INDEX uq_satelite_referencia ON satelite (is_referencia) WHERE is_referencia;

CREATE TABLE unidade_conservacao (
    id_uc           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(200) NOT NULL CHECK (btrim(nome) <> ''),
    categoria       VARCHAR(100),
    grupo           VARCHAR(20) CHECK (grupo IN ('protecao_integral', 'uso_sustentavel')),
    area_ha         NUMERIC(14, 4) CHECK (area_ha > 0),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

CREATE TABLE area_preservacao_permanente (
    id_app          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo            VARCHAR(100),
    area_ha         NUMERIC(14, 4) CHECK (area_ha > 0),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

CREATE TABLE imovel_car (
    cod_imovel      VARCHAR(60) PRIMARY KEY CHECK (cod_imovel LIKE 'DF-%'),
    situacao        VARCHAR(40),
    condicao        VARCHAR(200),
    area_ha         NUMERIC(14, 4) CHECK (area_ha > 0),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);
