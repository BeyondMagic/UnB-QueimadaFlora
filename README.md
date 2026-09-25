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
- Banco de dados: PostgreSQL com extensão PostGIS (ver [ADR 0001](docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md)).

### O que ficou para entregas seguintes

- Flora ameaçada: o catálogo do SiBBr/JBRJ lista espécies, mas não fornece coordenadas das ocorrências.
- Vazão de bacias: exige dados hidrológicos que não constam nas fontes atuais.
- Bucket de arquivos brutos e camada analítica colunar: a consulta da E1 roda direto no PostGIS.

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
- [docs/adr/](docs/adr/): registros formais de decisões de arquitetura.
- [docs/human/03/e1_pergunta_de_gest_o_e_escopo_gabriel.md](docs/human/03/e1_pergunta_de_gest_o_e_escopo_gabriel.md): relatório de coordenação, checklist da entrega e script de conferência de volume.
