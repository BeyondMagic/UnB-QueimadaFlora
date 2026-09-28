# UnB-QueimadaFlora (Foco no Incêndio DF)

Projeto de Engenharia de Dados para análise de focos de calor, áreas protegidas e imóveis rurais no Distrito Federal.

Disciplina Sistemas de Bancos de Dados 2 (FCTE / UnB, semestre 2026.2, Grupo G5).

## Escopo da E1

### Pergunta de gestão

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

### O que entra na E1

- Focos de calor: BDQueimadas (INPE), recorte do DF de 2015 a 2025, todos os satélites (38.945 focos no total).
- Unidades de Conservação e APPs: IBRAM / Geoportal DF.
- Imóveis rurais e reserva legal: SICAR / CAR-DF.
- Banco de dados: PostgreSQL com extensão PostGIS (ver [ADR 0001](docs/adr/01-adotar-postgresql-com-postgis-camada-gold.md)).

### O que ficou para entregas seguintes

- Flora ameaçada: o catálogo do SiBBr/JBRJ lista espécies, mas não fornece coordenadas das ocorrências.
- Vazão de bacias: exige dados hidrológicos que não constam nas fontes atuais.
- Bucket de arquivos brutos e camada analítica colunar: a consulta da E1 roda direto no PostGIS.

### Status da carga

Todas as tabelas da E1 têm dado carregado pelo comando abaixo, com geometrias 100% válidas e no SRID 31983:

| Tabela | Registros | Fonte |
| :--- | ---: | :--- |
| `foco_calor` | 38.945 | BDQueimadas (INPE), DF, 2015-2025, todos os satélites |
| `imovel_car` | 21.047 | SICAR (`data/raw/AREA_IMOVEL.zip`, versionado no repo) |
| `reserva_legal` | 13.499 | SICAR (`data/raw/RESERVA_LEGAL.zip`, versionado no repo) |
| `area_preservacao_permanente` | 2.234 | IBRAM/SISDIA (nascente, borda de chapada, reservatório) |
| `unidade_conservacao` | 84 | IBRAM/SISDIA |

## Como rodar

### Pré-requisitos

- Docker e Docker Compose v2 (comando `docker compose`, não o script antigo `docker-compose`).
- Rede liberada para `sisdia.df.gov.br` (download das UCs e APPs do IBRAM a cada carga).

### Um comando

```bash
docker compose up
```

Isso faz, em ordem:

1. `db`: sobe PostgreSQL 16 com PostGIS 3.4 na porta 5434 do host e espera o banco responder (`pg_isready`).
2. `migrate`: aplica as migrações do Flyway em `migrations/` (extensão PostGIS, tabelas, índices GiST, schema de staging).
3. `load`: carrega `data/processed/focos_df_2015_2025.csv` em `satelite` e `foco_calor`, reprojetando as coordenadas para o SRID 31983.
4. `load_camadas`: baixa UCs e APPs do IBRAM/SISDIA e carrega os zips do SICAR já versionados em `data/raw/`, saneando geometrias inválidas e reprojetando para 31983.

`load` e `load_camadas` rodam em paralelo (dependem só do `migrate`) e cada um esvazia suas próprias tabelas antes de recarregar, então repetir `docker compose up` não duplica dado. Para derrubar tudo e apagar o volume do banco:

```bash
docker compose down -v
```

Variáveis de ambiente aceitas (todas opcionais, com valor padrão): `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`.

### Conferir a carga

```bash
docker compose exec db psql -U queimada -d queimadaflora -c "
SELECT 'foco_calor', count(*) FROM foco_calor
UNION ALL SELECT 'imovel_car', count(*) FROM imovel_car
UNION ALL SELECT 'reserva_legal', count(*) FROM reserva_legal
UNION ALL SELECT 'area_preservacao_permanente', count(*) FROM area_preservacao_permanente
UNION ALL SELECT 'unidade_conservacao', count(*) FROM unidade_conservacao;"
```

Resultado esperado: os números da tabela em "Status da carga".

### Desempenho da consulta da pergunta de gestão

A junção espacial completa (focos dentro de imóvel, com interseção em reserva legal ou APP, ou a até 1 km de UC, agrupando por imóvel) não fica abaixo dos 500 ms previstos no ADR: sem otimização ela passa de 30 segundos. A causa não é falta de índice GiST (todos existem e são usados), é a complexidade real dos polígonos do SICAR: `reserva_legal` chega a 54.373 vértices numa única geometria, e o join `foco_calor` x `imovel_car` sozinho já leva ~4 s porque muitos imóveis do CAR-DF se sobrepõem (38.945 focos geram 76.116 pares foco-imóvel).

### Teste em máquina limpa

- Quem: Cláudio Henrique.
- Quando: 27/09/2026.
- Commit: o que adiciona os serviços `load` e `load_camadas`, a migração de staging dos focos e o `Dockerfile` de `src/pipeline` (mensagem "feat: adicionar serviços de carga em um comando").
- Ambiente: macOS, runtime Docker via Colima, Docker Compose v2, a partir de `docker compose down -v` seguido de `docker compose up`, sem estado anterior.
- Resultado: banco saudável e 5 migrações aplicadas em cerca de 25 segundos; as 5 tabelas da E1 carregadas com os números da seção "Status da carga"; satélite de referência único (`AQUA_M-T`); todas as geometrias válidas em SRID 31983; trigger de imutabilidade de `foco_calor` bloqueou um `UPDATE` de teste; segunda execução de `load` e `load_camadas` não duplicou linhas.

## Equipe e entregas da E1

| Integrante | Frente | Entrega |
| :--- | :--- | :--- |
| Gabriel Souza | Coordenação | Pergunta de gestão, escopo, contagem de focos e tag e1 |
| Manoel Fernando | Modelagem espacial | Esquema PostGIS com colunas geométricas tipadas e restrições |
| Samuel Rodrigues | Migrações | Scripts versionados de criação do banco, extensão e índices GiST |
| João Victor | Focos de calor | Download automatizado e carga dos focos do INPE (DF, 2015 a 2025) |
| Gabriel Fernando | Camadas geográficas | Carga e reprojeção de shapefiles/geopackages do IBRAM e CAR-DF |
| Cláudio Henrique | Docker e execução | Compose do PostGIS, script de carga em um comando e teste em máquina limpa |
| Elias F. | Métricas e ADR | Números reais pós-carga e documentação no ADR |

## Onde encontrar mais detalhes

- [docs/ai/CONTEXT.md](docs/ai/CONTEXT.md): contexto completo, regras técnicas de PostGIS e dados reais de volume.
- [docs/modelagem/esquema_espacial.md](docs/modelagem/esquema_espacial.md): esquema PostGIS da E1 (SRID 31983, tabelas, chaves, carimbos).
- [docs/modelagem/declaracao_historico.md](docs/modelagem/declaracao_historico.md): focos insert-only e snapshot do CAR.
- [docs/adr/](docs/adr/): registros formais de decisões de arquitetura.
- [docs/entrega/01/README.md](docs/entrega/01/README.md): visão geral, definições operacionais e volumetria da E1.
