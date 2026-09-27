---
icon: lucide/rocket
---

# Corta-Fogo DF

Plataforma de engenharia de dados para cruzamento espacial e temporal de focos de calor, áreas públicas protegidas e imóveis rurais no Distrito Federal.

Projeto desenvolvido para a disciplina Sistemas de Bancos de Dados 2 (FCTE / UnB, Turma 03, Semestre 2026.2).

## Equipe: Grupo G5

| Integrante       | Frente de Trabalho (E1)                           |
| :--------------- | :------------------------------------------------ |
| Gabriel Souza    | Coordenação e Pergunta de Gestão                  |
| Manoel Fernando  | Modelagem Espacial PostGIS                        |
| Samuel Rodrigues | Migrações Versionadas (Flyway)                    |
| João Victor      | Ingestão de Focos de Calor (INPE)                 |
| Gabriel Fernando | Ingestão de Camadas Territoriais (IBRAM / CAR-DF) |
| Cláudio Henrique | Infraestrutura Docker e Execução                  |
| Elias F.         | Caracterização, Métricas e ADR                    |

## Pergunta de gestão (Entrega 1 - E1)

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

## Estrutura

- SGBD principal: PostgreSQL 16 com extensão PostGIS 3.4.
- Projeção padronizada: SIRGAS 2000 / UTM zone 23S (EPSG:31983) em todas as tabelas.
- Total de focos de calor no DF (2015 a 2025): 38.945 registros de 20 satélites distintos.
- Imóveis rurais do CAR-DF: 21.047 feições com 13.499 polígonos de reserva legal.
- Unidades de Conservação e APPs: 84 UCs e 2.234 polígonos de preservação permanente do IBRAM.

## Seções

- **[Pergunta de Gestão e Escopo](entrega/01/gestao.md):** pergunta de gestão, definições operacionais e checklist de entregas da E1.
- **[Modelagem Espacial](modelagem/esquema_espacial.md):** DDL do PostGIS, tipos geométricos, chaves, restrições e regras de bitemporalidade.
- **[Declaração de Histórico](modelagem/declaracao_historico.md):** política de persistência temporal para focos (insert-only) e limites do CAR (snapshot).
- **[Decisões de Arquitetura (ADR)](adr/README.md):** registro formal das escolhas de banco, formatos e camadas.
- **[Diretrizes Técnicas](ai/CONTEXT.md):** contexto consolidado e regras para desenvolvedores e assistentes de IA.
