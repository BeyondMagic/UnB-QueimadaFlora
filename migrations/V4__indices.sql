-- V4: índices. GiST em toda coluna de geometria, B-tree na data do evento dos focos
-- e nas chaves estrangeiras usadas nas junções.

CREATE INDEX ix_unidade_conservacao_geom         ON unidade_conservacao         USING gist (geom);
CREATE INDEX ix_area_preservacao_permanente_geom ON area_preservacao_permanente USING gist (geom);
CREATE INDEX ix_imovel_car_geom                  ON imovel_car                  USING gist (geom);
CREATE INDEX ix_reserva_legal_geom               ON reserva_legal               USING gist (geom);
CREATE INDEX ix_foco_calor_geom                  ON foco_calor                  USING gist (geom);

CREATE INDEX ix_foco_calor_data_hora_evento ON foco_calor (data_hora_evento);
CREATE INDEX ix_foco_calor_id_satelite      ON foco_calor (id_satelite);
CREATE INDEX ix_reserva_legal_cod_imovel    ON reserva_legal (cod_imovel);
