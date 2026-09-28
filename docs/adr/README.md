# Registros de Decisões de Arquitetura (ADR)

Estruturadas segundo o [Guia de ADR da disciplina](https://unb-bd2.github.io/PlanoEnsino/adr/).

O plano de ensino prevê cinco decisões estruturais ao longo do semestre, uma para cada etapa do ciclo de vida:

| ID       | Decisão                                                                                               |                        Etapa                        |   Status   |    Data    |
| :------- | :---------------------------------------------------------------------------------------------------- | :-------------------------------------------------: | :--------: | :--------: |
| **0001** | [Adotar PostgreSQL com PostGIS como banco principal](01-adotar-postgresql-com-postgis-camada-gold.md) | [E1](https://unb-bd2.github.io/PlanoEnsino/adr/01/) | **Aceito** | 2026-09-09 |
| **0002** | Mecanismo de ingestão: captura de mudanças (CDC) e formato aberto de tabela                           | [E2](https://unb-bd2.github.io/PlanoEnsino/adr/02/) | Planejado  | Semana 10  |
| **0003** | Modelagem dimensional da camada analítica e ferramenta declarativa de transformação                   | [E3](https://unb-bd2.github.io/PlanoEnsino/adr/03/) | Planejado  | Semana 13  |
| **0004** | Mecanismo de disponibilização de dados: camada semântica e consumo                                    | [E4](https://unb-bd2.github.io/PlanoEnsino/adr/04/) | Planejado  | Semana 16  |
| **0005** | Decisão arquitetural de maior impacto da equipe                                                       |                        Livre                        | Planejado  | A definir  |

## Método de Decisão aplicado

Cada registro segue os seis passos exigidos na avaliação no [formato _Nygar_](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions):

1. **Caracterização da carga:** métricas reais do Distrito Federal (38.945 focos, 21.047 imóveis, cardinalidades, padrão de acesso e latência);
2. **Restrições não funcionais:** requisitos de integridade topológica, projeção espacial métrica (EPSG:31983) e infraestrutura em contêineres;
3. **Candidatos avaliados:** no mínimo três opções, incluindo obrigatoriamente a opção nula (PostgreSQL padrão sem extensão espacial);
4. **Medição reproduzível:** benchmarks com dados do próprio domínio e scripts de reprodução no repositório;
5. **Compromisso explícito:** declaração do que se ganha, do que se perde e do que se torna irreversível;
6. **Gatilho de revisão:** métrica e limiar objetivos para revisão da arquitetura.
