-- V1: habilita o PostGIS e cria o schema staging.
-- staging recebe o dado bruto gravado pelos scripts de carga, antes da validação
-- e da transformação para as tabelas do schema public.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS staging;
