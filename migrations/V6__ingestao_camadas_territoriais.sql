-- V6: separa a data de download da fonte (data_download) do momento em que a
-- linha entrou neste banco (data_hora_ingestao). Mesmo padrao bitemporal que
-- foco_calor ja tinha (data_hora_evento x data_hora_ingestao), agora extendido
-- as quatro tabelas territoriais: ate aqui so existia data_download, que a
-- carga vinha preenchendo com a data de execucao do script, nao com a data
-- real de obtencao do arquivo na fonte.

ALTER TABLE unidade_conservacao
    ADD COLUMN data_hora_ingestao TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE area_preservacao_permanente
    ADD COLUMN data_hora_ingestao TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE imovel_car
    ADD COLUMN data_hora_ingestao TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE reserva_legal
    ADD COLUMN data_hora_ingestao TIMESTAMPTZ NOT NULL DEFAULT now();

COMMENT ON COLUMN unidade_conservacao.data_download IS
    'Data em que o arquivo de origem (IBRAM/SISDIA) foi obtido. Nao e a data de carga no banco.';
COMMENT ON COLUMN unidade_conservacao.data_hora_ingestao IS
    'Momento em que esta linha foi inserida neste banco (carga). Pode ser bem posterior ao data_download.';

COMMENT ON COLUMN area_preservacao_permanente.data_download IS
    'Data em que o arquivo de origem (IBRAM/SISDIA) foi obtido. Nao e a data de carga no banco.';
COMMENT ON COLUMN area_preservacao_permanente.data_hora_ingestao IS
    'Momento em que esta linha foi inserida neste banco (carga). Pode ser bem posterior ao data_download.';

COMMENT ON COLUMN imovel_car.data_download IS
    'Data em que o recorte do SICAR foi obtido. Nao e a data de carga no banco.';
COMMENT ON COLUMN imovel_car.data_hora_ingestao IS
    'Momento em que esta linha foi inserida neste banco (carga). Pode ser bem posterior ao data_download.';

COMMENT ON COLUMN reserva_legal.data_download IS
    'Data em que o recorte do SICAR foi obtido. Nao e a data de carga no banco.';
COMMENT ON COLUMN reserva_legal.data_hora_ingestao IS
    'Momento em que esta linha foi inserida neste banco (carga). Pode ser bem posterior ao data_download.';
