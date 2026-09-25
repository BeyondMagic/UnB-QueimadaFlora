# 1. Adotar PostgreSQL com extensão PostGIS como banco de dados principal (Camada Gold)

- **Status:** Aceito
- **Data:** 2026-09-09
- **Decisores:** Equipe de Engenharia de Dados G5 (Cláudio H., Elias F., Gabriel F., Gabriel S., João V., Manoel F., Samuel R.)
- **Disciplina:** Sistemas de Bancos de Dados 2 — FCTE / UnB (2026.2)

---

## Contexto

O projeto **Foco no Incêndio DF** necessita centralizar, estruturar e cruzar dados espaciais e temporais provenientes de múltiplas fontes públicas:
- Detecções de focos de calor por satélite (**INPE / BDQueimadas**);
- Unidades de Conservação (UCs), Áreas de Preservação Permanente (APPs) e hidrografia (**IBRAM-DF / Geoportal DF**);
- Limites de imóveis rurais e áreas de Reserva Legal (**SICAR / CAR-DF**);
- Ocorrências e catálogos taxonômicos de espécies de flora do Cerrado sob ameaça (**SiBBr / JBRJ**).

O objetivo central é responder a perguntas de inteligência ambiental e fiscalização (ex.: reincidência de queimadas em áreas protegidas e reservas legais de propriedades privadas). Tais análises demandam operações geométricas com alta precisão topológica (como interseções `ST_Intersects`, cálculo de distâncias com `ST_DWithin` e validação com `ST_IsValid`), associadas a restrições temporais e integridade referencial sólida entre as entidades.

---

## Requisitos e Restrições

- **Volumetria inicial estimada:** 3 GB a 5 GB (série histórica de focos no DF e geometrias vetoriais das malhas territoriais).
- **Latência:** Consultas espaciais e analíticas consumidas via API ou painel interativo devem responder em tempo inferior a 500 ms.
- **Garantias transacionais:** Forte integridade transacional (ACID) na ingestão de dados consolidados, garantindo que inconsistências nas geometrias ou falhas parciais não corrompam a camada Gold.
- **Validação topológica:** Capacidade de impor regras rígidas (ex.: polígonos fechados e válidos, verificação de SRID único nas colunas de geometria).
- **Competência da equipe:** Familiaridade ampla com SQL, comandos DDL/DML relacionais e manipulação de bancos de dados padrão de mercado.

---

## Padrões de Acesso Previstos

1. **Agregações geoespaciais com recorte temporal:**
   - Exemplo: *Quais UCs do DF registraram a maior densidade de focos de calor nos meses de seca?*
   - Execução rotineira de `ST_Intersects` entre pontos de focos de calor e polígonos de UCs, agrupando por período e área.
2. **Consultas de sobreposição fundiária e reincidência:**
   - Exemplo: *Quais propriedades rurais (CAR-DF) tiveram focos de calor reincidentes em áreas de reserva legal nos últimos 24 meses?*
   - Junção espacial de alta densidade entre pontos e geometrias poligonais complexas com filtros temporais de passagem do satélite.
3. **Leituras analíticas para dashboards:**
   - Contagens pontuais e filtros por satélite de referência, Região Administrativa e status de área de preservação.

---

## Decisão

**Centralizaremos a camada Gold (armazenamento consolidado e cruzamentos espaciais oficiais) no SGBD relacional PostgreSQL, utilizando a extensão espacial PostGIS.**

Todas as tabelas de geometrias consolidadas utilizarão colunas tipadas com SRID explícito e índices espaciais em árvore (GiST). A camada Gold será alimentada a partir da camada Bronze (Data Lake de arquivos brutos) por meio de pipelines de transformação e limpeza (ELT/ETL).

---

## Alternativas Consideradas

### Alternativa 1: Banco Orientado a Documentos (MongoDB com GeoJSON)

- **Prós:** 
  - Máxima flexibilidade de esquema para ingerir estruturas heterogêneas ou aninhadas (como metadados variáveis do Darwin Core e feeds de dados brutos) sem migrações formais de DDL.
- **Contras:** 
  - Suporte geoespacial rudimentar se comparado ao PostGIS;
  - Ausência de funções topológicas analíticas nativas ricas (ex.: cálculo diferencial de sobreposição de geometrias complexas, limpeza de feições);
  - Ineficiência expressiva no processamento em larga escala de junções espaciais (*spatial joins*) entre múltiplos conjuntos de polígonos densos;
  - Garantias transacionais e restrições de integridade mais frágeis para controle de malhas fundiárias.
- **Motivo de descarte:** 
  - A carência de funções analíticas geográficas nativas robustas e a complexidade de manter consistência e restrições de integridade topológica inviabilizaram a adoção do modelo orientado a documentos como banco principal.

### Alternativa 2: Data Lakehouse Puramente Colunar (GeoParquet + DuckDB)

- **Prós:** 
  - Altíssima taxa de compressão colunar;
  - Baixo custo de armazenamento prolongado;
  - Velocidade excelente em varreduras sequenciais brutas (*scans*) com *projection and filter pushdown* direto em arquivos estáticos sem depender de um daemon de banco sempre ligado.
- **Contras:** 
  - Dificuldade operacional para atualizações pontuais e correções incrementais (UPSERTs geográficos) de registros com anomalias;
  - Ausência de camada transacional rígida nativa na borda para rejeitar dados corrompidos antes da gravação;
  - Desempenho subótimo para acessos concorrentes pontuais e APIs transacionais de baixa latência contínua.
- **Motivo de descarte:** 
  - O projeto necessita de uma base operacional "viva", com suporte a chaves estrangeiras, restrições DDL (`CHECK`, `ST_IsValid`), índices GiST e latência estável < 500 ms em consultas concorrentes. O DuckDB com GeoParquet foi reservado para a camada de cubos analíticos históricos, e não como repositório mestre de serviço.

---

## Evidência que Sustenta a Decisão

- **Padrão OGC:** PostGIS é a implementação de referência certificada pela *Open Geospatial Consortium (OGC)* para SQL espacial.
- **Performance de Indexação:** Benchmarks da indústria e documentação oficial apontam que índices GiST (*Generalized Search Tree*) e R-Tree reduzem consultas de interseção espacial sobre polígonos complexos de varreduras lineares completas ($O(N)$) para buscas logarítmicas ($O(\log N)$), entregando respostas em escala de poucos milissegundos.
- **Ecossistema:** Compatibilidade nativa com ferramentas geoespaciais e de ETL (GDAL/OGR, QGIS, GeoPandas, `shp2pgsql`, SQLAlchemy com GeoAlchemy2).

---

## Consequências

### Positivas
- **Integridade de Dados:** Garantia de integridade referencial relacional estrita e suporte a constraints de validação geográfica (`CHECK (ST_IsValid(geom))`).
- **Poder Expressivo:** Acesso imediato a centenas de funções espaciais consagradas (`ST_Intersects`, `ST_Area`, `ST_DWithin`, `ST_Transform`, `ST_Buffer`).
- **Curva de Aprendizado:** Alinhamento técnico direto com o conhecimento da equipe em SQL, modelagem relacional e migrações versionadas.

### Negativas e Custos Aceitos
- **Complexidade de Infraestrutura:** Requer provisionamento e manutenção de serviço contínuo de banco de dados (PostgreSQL + PostGIS via Docker), com consumo de memória e CPU dedicado superior a soluções de arquivos estáticos.
- **Rigor na Ingestão:** Exige padronização estrita de projeções (conversão obrigatória de CRS/SRID antes da carga) e saneamento prévio de feições inválidas (polígonos com auto-interseção precisam ser corrigidos via `ST_MakeValid` ou rejeitados).

---

## Riscos Assumidos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| **Picos de I/O em temporadas de seca** | Sobrecarga de gravação no banco durante picos massivos de focos diários do INPE. | Ingestão em lote (*batch*) fora dos horários de pico; uso de `COPY` binário/bulk load nas cargas. |
| **Fragmentação de índices espaciais GiST** | Degradação de performance em buscas após inserções/atualizações recorrentes. | Agendamento de rotinas de manutenção (`VACUUM ANALYZE` periódico e eventual `REINDEX`). |
| **Retificação histórica de polígonos do CAR** | Sobrescrita de limites territoriais passados impedir cruzar focos antigos com a área de reserva da época. | Tratar dados de propriedades rurais com rastreabilidade temporal/versionamento (SCD Tipo 2 ou carimbos de vigência). |

---

## Pontos Especiais de Modelagem Incorporados

1. **Multi-satélite e Satélite de Referência:**
   - O mesmo incêndio pode ser capturado em horários próximos por sensores distintos (Aqua, Terra, NOAA, etc.). Para permitir séries temporais estatisticamente consistentes, a tabela de focos armazena explicitamente o identificador do satélite e uma flag indicando se pertence ao *satélite de referência oficial do INPE* (satélite padrão para comparações históricas).
2. **Dualidade Temporal (Bitemporalidade):**
   - Distinção explícita entre `data_hora_evento` (instante real de passagem do satélite e captura térmica) e `data_hora_ingestao` (momento de entrada do registro no pipeline do projeto).
3. **Focos Insert-Only:**
   - Registros de focos de calor são estritamente imutáveis (*append-only*), garantindo auditabilidade das detecções históricas.

---

## Como e Quando Revisitar

Esta decisão será formalmente reavaliada caso ocorra algum dos seguintes gatilhos:
1. O tempo de execução da janela diária de carga em lote ultrapassar 1 hora contínua de processamento ou travar a disponibilidade do banco;
2. A latência mediana de resposta das consultas espaciais na API analítica exceder o teto acordado de 500 ms;
3. O volume de geometrias do DF e entorno crescer para além da capacidade operacional de memória do servidor alocado, justificando a migração para armazenamento analítico distribuído ou partição federada via GeoParquet/DuckDB.
