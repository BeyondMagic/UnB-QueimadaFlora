# Entrega 1: Fonte Transacional e Sistema de Origem

## Visão Geral e Pergunta de Gestão

A Entrega 1 estabelece o sistema de origem transacional da plataforma, com esquema relacional versionado no PostgreSQL/PostGIS e carga automatizada a partir de dados abertos brasileiros.

A modelagem foi projetada para responder à seguinte pergunta central de gestão:

> **Quais imóveis rurais do Distrito Federal tiveram focos de calor reincidentes em áreas de reserva legal, de preservação permanente ou a até 1 km de unidades de conservação entre 2015 e 2025?**

- **Atores interessados:** analistas de fiscalização ambiental e órgãos de resposta a emergências do Distrito Federal (como o CBMDF).
- **Decisão apoiada:** priorização de imóveis rurais para vistorias em campo e ações preventivas antes do período anual de estiagem.
- **Estrutura da formulação:** define o sujeito cadastral (imóveis rurais do DF), o recorte geográfico (Distrito Federal), a série histórica completa (2015 a 2025) e critérios objetivos de sobreposição e proximidade a áreas protegidas, sem recorrer a siglas opacas.

## Definições Operacionais da Consulta

Cada termo da pergunta de gestão mapeia diretamente para regras e estruturas no banco de dados:

| Conceito | Regra de negócio | Implementação no PostGIS |
| :--- | :--- | :--- |
| **Imóveis rurais do Distrito Federal** | Polígonos de imóveis cadastrados no Cadastro Ambiental Rural (SICAR) para o DF. | Tabela `imovel_car` com chave primária `cod_imovel` (padrão `DF-%`) e carimbo `data_download`. |
| **Focos de calor reincidentes** | Registros de calor do INPE dentro do DF em pelo menos 2 anos-calendário distintos. | Tabela `foco_calor`, contando anos distintos de `data_hora_evento` por imóvel (não o número de detecções). |
| **Reserva legal e preservação permanente** | O foco intersecta área protegida declarada do imóvel ou mapeada no território. | Junção espacial (`ST_Intersects`) com `reserva_legal` e `area_preservacao_permanente` acelerada por índices GiST. |
| **Até 1 km de unidades de conservação** | O foco no imóvel está a no máximo 1.000 metros do limite de uma unidade de conservação. | Cálculo de distância métrica nativa (`ST_DWithin`) com `unidade_conservacao` no SRID 31983. |
| **Período de análise** | Anos completos entre 01/01/2015 e 31/12/2025. | Filtro temporal por intervalo em `data_hora_evento`. |
| **Sensores de satélite** | Todos os satélites entram no cálculo de reincidência. Séries comparáveis filtram o sensor de referência. | Coluna `id_satelite` com flag `is_referencia` (`AQUA_M-T`). |

## Volumetria Real do Distrito Federal

A carga foi dimensionada sobre a totalidade dos dados abertos do Distrito Federal:

| Camada / Tabela | Registros | Fonte pública | Tamanho aproximado |
| :--- | ---: | :--- | :--- |
| `foco_calor` | 38.945 | BDQueimadas (INPE), 2015 a 2025 | 4,5 MB (CSVs consolidados) |
| `imovel_car` | 21.047 | SICAR / Ministério da Agricultura | 21 MB compactado |
| `reserva_legal` | 13.499 | SICAR / Ministério da Agricultura | 10 MB compactado |
| `area_preservacao_permanente` | 2.234 | IBRAM / SISDIA | 8 MB |
| `unidade_conservacao` | 84 | IBRAM / SISDIA | 2 MB |

Detalhamento anual dos focos de calor no Distrito Federal:
- Total com todos os satélites: 38.945 registros de 20 sensores distintos (mínimo de 948 focos em 2018 e máximo de 6.190 em 2024).
- Total com o satélite de referência (`AQUA_M-T`): 2.350 registros no mesmo período (cerca de 17 vezes menos detecções).

## Artefatos e Documentos da Entrega

A documentação técnica detalhada da Entrega 1 está dividida nos seguintes documentos:

- **[Modelagem Espacial (PostGIS)](../../modelagem/esquema_espacial.md):** especificação técnica do DDL, projeção métrica EPSG:31983, constraints de integridade topológica (`ST_IsValid`) e índices GiST.
- **[Declaração de Histórico](../../modelagem/declaracao_historico.md):** diretrizes de persistência temporal para focos imutáveis (*insert-only*) e cadastros territoriais (*snapshot* com `data_download`).
- **[Decisão de Arquitetura (ADR 0001)](../../adr/01-adotar-postgresql-com-postgis-camada-gold.md):** justificativa da adoção do PostgreSQL com PostGIS, análise de alternativas (incluindo a opção nula) e benchmarks com dados do DF.
- **[Scripts de Migração](https://github.com/BeyondMagic/corta-fogo-df/tree/main/migrations):** scripts SQL versionados (`V1` a `V5`) gerenciados pelo Flyway.
- **[Pipelines de Ingestão](https://github.com/BeyondMagic/corta-fogo-df/tree/main/src/pipeline):** scripts automatizados para extração do INPE e ingestão com saneamento de geometrias via GeoPandas e GDAL.

## Como Reproduzir a Carga

A execução completa do banco e a carga dos dados são realizadas com um único comando na raiz do projeto:

```bash
docker compose up
```

O comando inicia o PostgreSQL com PostGIS, executa as migrações do Flyway em ordem e dispara em paralelo os serviços de ingestão de focos e camadas geográficas, garantindo idempotência e saneamento topológico.
