# 1. Adotar PostgreSQL com PostGIS como banco principal

- **Status:** Aceito
- **Data:** 2026-09-09 - 2026-09-27
- **Decisores:** Cláudio H., Elias F., Gabriel F., Gabriel S., João V., Manoel F., Samuel R.
- **Disciplina:** Sistemas de Bancos de Dados 2 (FCTE / UnB, 2026.2)

## Contexto

## Contexto e pergunta de gestão

O projeto cruza pontos de calor do INPE com polígonos de Unidades de Conservação do IBRAM e áreas de reserva legal do CAR-DF. A consulta central exige testes de interseção espacial e cálculo de distâncias até limites protegidos no Distrito Federal.
O projeto cruza detecções de calor por satélite com polígonos de proteção ambiental e imóveis rurais no Distrito Federal. A pergunta central de gestão da Entrega 1 (E1) é:

A equipe precisa de um banco que valide geometrias na entrada, processe consultas espaciais abaixo de 500 ms e mantenha integridade referencial entre cadastros e ocorrências.

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

## Requisitos e restrições

- Atores: analistas de fiscalização ambiental e bombeiros militares (CBMDF).
- Objetivo: priorizar imóveis rurais para vistorias preventivas antes do período de seca.

- Volume real do DF: 38.945 focos entre 2015 e 2025 (cerca de 4,5 MB em CSVs) mais os polígonos distritais do CAR e das UCs.
- Latência: consultas espaciais na camada consolidada abaixo de 500 ms.
- Integridade: garantia de geometrias válidas (polígonos fechados e sem autointerseção) e tipos geométricos com SRID fixo.
- Conhecimento prévio: a equipe domina SQL e bancos relacionais.
  ## Definições operacionais da consulta

## Padrões de acesso

| Conceito            | Regra de negócio                                                                                            | Exigência no banco                                                     |
| :------------------ | :---------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| Imóvel rural        | Polígono cadastrado no SICAR para o DF.                                                                     | Chave primária `cod_imovel` (padrão `DF-%`) e `data_download`.         |
| Reincidência        | Focos na mesma área do imóvel em pelo menos 2 anos-calendário distintos.                                    | Contar anos distintos de `data_hora_evento`, nunca a data de ingestão. |
| Dentro de RL ou APP | Foco intersecta a reserva legal ou APP do imóvel.                                                           | Interseção espacial (`ST_Intersects`) com índice GiST.                 |
| A até 1 km de UC    | Foco no imóvel a no máximo 1.000 m do limite de uma UC.                                                     | `ST_DWithin` com coordenadas métricas no SRID 31983.                   |
| Período             | 01/01/2015 a 31/12/2025 (anos completos).                                                                   | Filtro temporal em `data_hora_evento`.                                 |
| Satélites           | Todos os sensores entram na reincidência. Séries comparáveis filtram o satélite de referência (`AQUA_M-T`). | Coluna `id_satelite` com flag `is_referencia`.                         |

1. Interseção espacial (`ST_Intersects`) entre pontos de focos e polígonos de reserva legal e APP.
2. Cálculo de raio (`ST_DWithin`) de 1 km a partir do limite de Unidades de Conservação.
3. Agrupamento por imóvel e contagem de anos distintos com focos para medir reincidência.
   ## Recorte de escopo da E1

O núcleo da E1 entrega o cruzamento em um único banco PostGIS. Dados auxiliares e camadas analíticas adicionais ficam para etapas posteriores:

- Focos de calor (INPE, DF, 2015 a 2025, todos os satélites): Sim. Tabela central de eventos.
- Unidades de Conservação e APPs (IBRAM): Sim. Delimitação das áreas protegidas e base da faixa de 1 km.
- Imóveis e reserva legal (SICAR / CAR-DF): Sim. Sujeito e critério de reincidência da pergunta.
- Flora ameaçada (SiBBr / JBRJ): Não na E1. O catálogo traz nomes taxonômicos sem coordenadas geográficas no DF.
- Séries de vazão: Não na E1. Demanda dados hidrológicos ausentes nas fontes atuais.
- Camada Bronze em bucket (MinIO/S3): Não na E1. Adiciona serviços ao Compose sem ganho para responder à pergunta.
- Camada analítica colunar (DuckDB / GeoParquet): Não na E1. A consulta da E1 roda direto no PostGIS. Fica mantida como alternativa futura se o tempo de carga passar de 1 h.

## Volumetria real do DF

Medição sobre os dados consolidados:
* Focos de calor (2015 a 2025): 38.945 registros de 20 satélites (2.350 com o satélite de referência `AQUA_M-T`). O volume oscila entre 948 focos em 2018 e 6.190 em 2024. Tamanho: 3,6 MB em CSV.
* Imóveis rurais do CAR-DF: 21.047 feições.
* Reserva legal: 13.499 feições.
* Áreas de Preservação Permanente (APPs): 2.234 feições.
* Unidades de Conservação: 84 feições.

Como o volume total cabe com folga na memória e disco de uma máquina padrão, a camada Gold opera sem particionamento distribuído na E1.

## Decisão

Adotamos PostgreSQL com a extensão PostGIS como banco de dados da camada consolidada (Gold). O banco pode rodar via Docker ou instância Supabase/PostgreSQL gerenciada.
Centralizamos a camada Gold no PostgreSQL 16 com a extensão PostGIS 3.4, subindo via Docker Compose local ou serviço gerenciado/Supabase.

Toda tabela geográfica terá SRID explicitado na coluna de geometria, índice espacial GiST e validação de consistência via `ST_IsValid`.
Padrões fixados:
1. SRID único: EPSG:31983 (SIRGAS 2000 / UTM zone 23S) em todas as tabelas. O DF fica na zona 23S, permitindo cálculos de distância em metros nativos sem conversão para `geography`.
2. Validação topológica: colunas geométricas com restrições `CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))` e saneamento na ingestão via `ST_MakeValid`.
3. Índices espaciais: índice GiST em todas as colunas de geometria e B-tree em chaves e datas de evento.

## Alternativas consideradas

### 1. MongoDB com GeoJSON

- Prós: flexibilidade de esquema para formatos semiestruturados sem migrações de DDL.
- Contras: recursos espaciais limitados em comparação ao PostGIS, sem suporte a junções espaciais densas entre camadas de polígonos.
- Motivo de descarte: consultas de sobreposição topológica são o centro do projeto; o MongoDB não atende esse tipo de operação com a mesma precisão e velocidade.

- Prós: flexibilidade de esquema para receber formatos semiestruturados sem migrações de DDL.
- Contras: recursos espaciais limitados em comparação ao PostGIS, sem suporte maduro a junções espaciais densas entre camadas de polígonos.
- Motivo de descarte: consultas de sobreposição topológica entre imóveis e áreas de proteção são o centro do projeto, e o MongoDB não atende esse tipo de operação com a mesma precisão e velocidade.

### 2. DuckDB lendo GeoParquet

- Prós: leitura colunar rápida, compressão alta e dispensa processo de banco de dados sempre ativo.
- Contras: atualizações pontuais difíceis, falta de restrições relacionais de integridade e ausência de índices espaciais persistentes para consultas transacionais.
- Motivo de descarte: o núcleo da E1 precisa de validação de dados na carga e suporte a chaves estrangeiras. DuckDB com GeoParquet segue como alternativa para relatórios futuros, mas não como base operacional.
- Motivo de descarte: o núcleo da E1 precisa de validação de dados na carga e suporte a chaves estrangeiras.

## Consequências

## Consequências e custos aceitos

### Positivas

- Suporte nativo a funções espaciais consagradas (`ST_Intersects`, `ST_DWithin`, `ST_MakeValid`).
- Índices GiST que aceleram as buscas espaciais para milissegundos.
- Compatibilidade com ferramentas padrão de carga, como `ogr2ogr`, `shp2pgsql` e GeoPandas.
- Compatibilidade com ferramentas padrão de carga (`ogr2ogr`, `shp2pgsql`, GeoPandas).

### Negativas e custos aceitos

- Exige padronizar projeções (reprojeção obrigatória para o SRID escolhido antes ou durante a carga).
- Polígonos corrompidos da base pública precisam ser tratados na ingestão para não quebrarem restrições do banco.
- Reprojeção obrigatória para o SRID 31983 na ingestão.
- Polígonos corrompidos da base pública precisam de correção prévia para não quebrarem constraints.
- Desempenho da consulta: polígonos da reserva legal do SICAR possuem alta densidade de vértices (até 54.373 em uma feição) e imóveis do CAR se sobrepõem no DF (38.945 focos geram 76.116 pares foco-imóvel). A junção completa sem simplificação ultrapassa 30 segundos, superando a meta teórica de 500 ms.

## Pontos de modelagem definidos

## Políticas de modelagem e histórico

Detalhe do DDL: [`docs/modelagem/esquema_espacial.md`](../modelagem/esquema_espacial.md). Histórico: [`docs/modelagem/declaracao_historico.md`](../modelagem/declaracao_historico.md).

- SRID único: EPSG:31983 (SIRGAS 2000 / UTM 23S) em todas as geometrias.
- Dois carimbos nos focos: `data_hora_evento` (passagem do satélite) e `data_hora_ingestao` (carga). A reincidência usa só o ano do evento.
- Satélite em cada foco; flag `is_referencia` para AQUA_M-T. Todos os satélites entram na reincidência; séries comparáveis filtram a referência.
- Focos insert-only (trigger bloqueia UPDATE/DELETE).
- CAR na E1: snapshot com `data_download`. Retificações do SICAR sobrescritas impediriam perguntar se o foco estava na RL na época. Versionamento temporal (SCD Type 2) fica para depois da E1.
- Dois carimbos nos focos: `data_hora_evento` (detecção do satélite) e `data_hora_ingestao` (momento da carga). A reincidência usa apenas o ano do evento.
- Focos são imutáveis: trigger `tg_foco_calor_imutavel` bloqueia `UPDATE` e `DELETE`.
- Snapshot do CAR: imóveis e reservas usam o recorte do SICAR com registro de `data_download`. Versionamento temporal fino (SCD Type 2) fica para entregas posteriores.
- Detalhes de DDL em [`docs/modelagem/esquema_espacial.md`](../modelagem/esquema_espacial.md) e justificativa histórica em [`docs/modelagem/declaracao_historico.md`](../modelagem/declaracao_historico.md).
