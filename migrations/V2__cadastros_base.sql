-- V2: cadastros base.
-- SRID fixo: 31983 (SIRGAS 2000 / UTM zone 23S).
-- Motivo: o DF fica na zona 23S; metros nativos permitem ST_DWithin(geom, geom, 1000)
-- sem cast para geography. Toda carga (ogr2ogr/shp2pgsql) deve reprojetar para 31983.

CREATE TABLE satelite (
    id_satelite     SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(40) NOT NULL UNIQUE CHECK (btrim(nome) <> ''),
    is_referencia   BOOLEAN NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE satelite IS
    'Catálogo de satélites do BDQueimadas. Comparações ano a ano usam o satélite de referência do INPE (AQUA_M-T).';
COMMENT ON COLUMN satelite.is_referencia IS
    'TRUE apenas no satélite de referência do INPE. Índice único parcial garante no máximo um.';

CREATE UNIQUE INDEX uq_satelite_referencia
    ON satelite (is_referencia)
    WHERE is_referencia;

CREATE TABLE unidade_conservacao (
    id_uc           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(200) NOT NULL CHECK (btrim(nome) <> ''),
    categoria       VARCHAR(100),
    grupo           VARCHAR(20) CHECK (grupo IS NULL OR grupo IN ('protecao_integral', 'uso_sustentavel')),
    area_ha         NUMERIC(14, 4) CHECK (area_ha IS NULL OR area_ha > 0),
    fonte           VARCHAR(80),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

COMMENT ON TABLE unidade_conservacao IS
    'Polígonos de Unidades de Conservação (IBRAM / Geoportal DF). Base da faixa de 1 km da pergunta de gestão.';
COMMENT ON COLUMN unidade_conservacao.geom IS
    'MultiPolygon em EPSG:31983. Distâncias em metros via ST_DWithin.';
COMMENT ON COLUMN unidade_conservacao.data_download IS
    'Data do download da camada. Carimbo da versão espacial usada na carga.';

CREATE TABLE imovel_car (
    cod_imovel      VARCHAR(60) PRIMARY KEY CHECK (cod_imovel LIKE 'DF-%'),
    situacao        VARCHAR(40),
    condicao        VARCHAR(200),
    area_ha         NUMERIC(14, 4) CHECK (area_ha IS NULL OR area_ha > 0),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

COMMENT ON TABLE imovel_car IS
    'Imóvel rural do SICAR no DF. Sujeito da pergunta de gestão. Snapshot da data_download (ver declaração de histórico).';
COMMENT ON COLUMN imovel_car.cod_imovel IS
    'Código do CAR no padrão DF-.... Chave natural do imóvel.';
COMMENT ON COLUMN imovel_car.data_download IS
    'Data do recorte SICAR carregado. Na E1 o banco guarda um snapshot; retificações futuras exigem versionamento.';

CREATE TABLE area_preservacao_permanente (
    id_app          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_imovel      VARCHAR(60) REFERENCES imovel_car (cod_imovel) ON DELETE SET NULL,
    tipo            VARCHAR(100),
    area_ha         NUMERIC(14, 4) CHECK (area_ha IS NULL OR area_ha > 0),
    fonte           VARCHAR(80),
    data_download   DATE NOT NULL,
    geom            geometry(MultiPolygon, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

COMMENT ON TABLE area_preservacao_permanente IS
    'Polígonos de APP (Geoportal DF e/ou camada APP do CAR). Interseção espacial com foco responde o critério da pergunta.';
COMMENT ON COLUMN area_preservacao_permanente.cod_imovel IS
    'Opcional. Preenchido quando a APP vem do pacote SICAR do imóvel; NULL quando a camada é distrital.';

CREATE TABLE hidrografia (
    id_trecho       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR(200),
    tipo            VARCHAR(80),
    fonte           VARCHAR(80),
    data_download   DATE NOT NULL,
    geom            geometry(MultiLineString, 31983) NOT NULL
                    CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

COMMENT ON TABLE hidrografia IS
    'Trechos hidrográficos do DF. Opcional na E1: não entra na pergunta de gestão; carrega se não atrasar o núcleo.';
