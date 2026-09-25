# 1. Adotar PostgreSQL com PostGIS como banco principal

* Status: Aceito
* Data: 2026-09-09
* Decisores: Cláudio H., Elias F., Gabriel F., Gabriel S., João V., Manoel F., Samuel R.
* Disciplina: Sistemas de Bancos de Dados 2 (FCTE / UnB, 2026.2)

## Contexto

O projeto cruza pontos de calor do INPE com polígonos de Unidades de Conservação do IBRAM e áreas de reserva legal do CAR-DF. A consulta central exige testes de interseção espacial e cálculo de distâncias até limites protegidos no Distrito Federal.

A equipe precisa de um banco que valide geometrias na entrada, processe consultas espaciais abaixo de 500 ms e mantenha integridade referencial entre cadastros e ocorrências.

## Requisitos e restrições

* Volume real do DF: 38.945 focos entre 2015 e 2025 (cerca de 4,5 MB em CSVs) mais os polígonos distritais do CAR e das UCs.
* Latência: consultas espaciais na camada consolidada abaixo de 500 ms.
* Integridade: garantia de geometrias válidas (polígonos fechados e sem autointerseção) e tipos geométricos com SRID fixo.
* Conhecimento prévio: a equipe domina SQL e bancos relacionais.

## Padrões de acesso

1. Interseção espacial (`ST_Intersects`) entre pontos de focos e polígonos de reserva legal e APP.
2. Cálculo de raio (`ST_DWithin`) de 1 km a partir do limite de Unidades de Conservação.
3. Agrupamento por imóvel e contagem de anos distintos com focos para medir reincidência.

## Decisão

Adotamos PostgreSQL com a extensão PostGIS como banco de dados da camada consolidada (Gold). O banco pode rodar via Docker ou instância Supabase/PostgreSQL gerenciada.

Toda tabela geográfica terá SRID explicitado na coluna de geometria, índice espacial GiST e validação de consistência via `ST_IsValid`.

## Alternativas consideradas

### 1. MongoDB com GeoJSON

* Prós: flexibilidade de esquema para receber formatos semiestruturados sem migrações de DDL.
* Contras: recursos espaciais limitados em comparação ao PostGIS, sem suporte maduro a junções espaciais densas entre camadas de polígonos.
* Motivo de descarte: consultas de sobreposição topológica entre imóveis e áreas de proteção são o centro do projeto, e o MongoDB não atende esse tipo de operação com a mesma precisão e velocidade.

### 2. DuckDB lendo GeoParquet

* Prós: leitura colunar rápida, compressão alta e dispensa processo de banco de dados sempre ativo.
* Contras: atualizações pontuais difíceis, falta de restrições relacionais de integridade e ausência de índices espaciais persistentes para consultas transacionais.
* Motivo de descarte: o núcleo da E1 precisa de validação de dados na carga e suporte a chaves estrangeiras. DuckDB com GeoParquet segue como alternativa para relatórios futuros, mas não como base operacional.

## Consequências

### Positivas
* Suporte nativo a funções espaciais consagradas (`ST_Intersects`, `ST_DWithin`, `ST_MakeValid`).
* Índices GiST que aceleram as buscas espaciais para milissegundos.
* Compatibilidade com ferramentas padrão de carga, como `ogr2ogr`, `shp2pgsql` e GeoPandas.

### Negativas e custos aceitos
* Exige padronizar projeções (reprojeção obrigatória para o SRID escolhido antes ou durante a carga).
* Polígonos corrompidos da base pública precisam ser tratados na ingestão para não quebrarem restrições do banco.

## Pontos de modelagem definidos

* Dois carimbos de data/hora nos focos: `data_hora_evento` (leitura do sensor) e `data_hora_ingestao` (momento da carga). A reincidência usa a data do evento.
* Preservação do satélite em cada foco, com marcação do satélite de referência do INPE (`AQUA_M-T`).
* Focos são imutáveis (apenas inserção).
* Limites do CAR sofrem retificações ao longo do tempo. Na E1 usamos o recorte atual do DF, mantendo a data de coleta documentada.
