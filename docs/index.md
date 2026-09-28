# Corta-Fogo DF

Plataforma de engenharia de dados para cruzamento espacial e temporal de focos de calor, áreas públicas protegidas e imóveis rurais no Distrito Federal.

> Projeto desenvolvido para a disciplina [Sistemas de Bancos de Dados 2 (FCTE / UnB, Turma 03, Semestre 2026.2)](https://unb-bd2.github.io/PlanoEnsino/projeto/).

## Pergunta de Gestão

> Quais imóveis rurais do Distrito Federal tiveram focos de calor reincidentes em áreas de reserva legal, de preservação permanente ou a até 1 km de unidades de conservação entre 2015 e 2025?

## Equipe

> Grupo 5

| Integrante                                                                                    | Entrega 1                        | Entrega 2 | Entrega 3 | Entrega 4 |
| :-------------------------------------------------------------------------------------------- | :------------------------------- | :-------: | :-------: | :-------: |
| [Gabriel Souza](https://github.com/BeyondMagic/corta-fogo-df/commits?author=GabrielMS00)      | Coordenação e Pergunta de Gestão |     -     |     -     |     -     |
| [Manoel Fernando](https://github.com/BeyondMagic/corta-fogo-df/commits?author=Manoel835)      | Modelagem de Dados               |     -     |     -     |     -     |
| [Samuel Rodrigues](https://github.com/BeyondMagic/corta-fogo-df/commits?author=SamuelRicosta) | Migrações                        |     -     |     -     |     -     |
| [João V. Farias](https://github.com/BeyondMagic/corta-fogo-df/commits?author=beyondmagic)     | ADR e ingestão de dados de focos |     -     |     -     |     -     |
| [Gabriel Fernando](https://github.com/BeyondMagic/corta-fogo-df/commits?author=MMcLovin)      | Ingestão de camadas territoriais |     -     |     -     |     -     |
| [Cláudio Henrique](https://github.com/BeyondMagic/corta-fogo-df/commits?author=claudiohsc)    | Infraestrutura                   |     -     |     -     |     -     |
| [Elias F.](https://github.com/BeyondMagic/corta-fogo-df/commits?author=EliasOliver21)         | Caracterização e Métricas        |     -     |     -     |     -     |

<!--
## Entregas

- [Entrega 1](https://unb-bd2.github.io/PlanoEnsino/projeto/e1/);
- [Entrega 2](https://unb-bd2.github.io/PlanoEnsino/projeto/e2/);
- [Entrega 3](https://unb-bd2.github.io/PlanoEnsino/projeto/e3/);
- [Entrega 4](https://unb-bd2.github.io/PlanoEnsino/projeto/e4/).
-->

### Política de Inteligência Artificial

- Os [Registros de Decisões de Arquitetura](adr/README.md) servem como guia para assistentes de IA, que devem seguir as decisões de arquitetura e os padrões de modelagem do projeto;
- Para reduzir baboseiras, informações repetidas, irrelevantes ou incorretas, foi feito um [guia com instruções](https://github.com/BeyondMagic/corta-fogo-df/blob/main/AGENT.md) para assistentes e agentes, que devem ser seguidas rigorosamente.

<!--

## Estrutura

- SGBD principal: PostgreSQL 16 com extensão PostGIS 3.4.
- Projeção padronizada: SIRGAS 2000 / UTM zone 23S (EPSG:31983) em todas as tabelas.
- Total de focos de calor no DF (2015 a 2025): 38.945 registros de 20 satélites distintos.
- Imóveis rurais do CAR-DF: 21.047 feições com 13.499 polígonos de reserva legal.
- Unidades de Conservação e APPs: 84 UCs e 2.234 polígonos de preservação permanente do IBRAM. -->

<!--

## Seções

- **[Pergunta de Gestão e Escopo](entrega/01/gestao.md):** pergunta de gestão, definições operacionais e checklist de entregas da E1.
- **[Modelagem Espacial](modelagem/esquema_espacial.md):** DDL do PostGIS, tipos geométricos, chaves, restrições e regras de bitemporalidade.
- **[Declaração de Histórico](modelagem/declaracao_historico.md):** política de persistência temporal para focos (insert-only) e limites do CAR (snapshot).
- **[Decisões de Arquitetura (ADR)](adr/README.md):** registro formal das escolhas de banco, formatos e camadas.
- **[Diretrizes Técnicas](ai/CONTEXT.md):** contexto consolidado e regras para desenvolvedores e assistentes de IA. -->
