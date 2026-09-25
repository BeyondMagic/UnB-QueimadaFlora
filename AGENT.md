# Instruções para Agentes de IA

Você está trabalhando no repositório UnB-QueimadaFlora (Foco no Incêndio DF), da disciplina Sistemas de Bancos de Dados 2 (FCTE / UnB, 2026.2).

## Onde ler o contexto antes de responder

Consulte sempre:
- `docs/ai/CONTEXT.md`: pergunta de gestão, números reais de focos no DF, regras de PostGIS e tarefas da equipe.
- `docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md`: decisão sobre PostgreSQL e PostGIS.
- `docs/human/03/e1_pergunta_de_gest_o_e_escopo_gabriel.md`: detalhamento de escopo da E1 feito pela coordenação.

## Pergunta de gestão da E1

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

## Regras obrigatórias de modelagem e código

1. Banco: PostgreSQL com PostGIS.
2. Geometrias: defina sempre SRID fixo em cada coluna geométrica (nunca use `geometry` genérico). Toda geometria precisa de índice GiST e validação com `ST_IsValid`.
3. Focos de calor: registros são imutáveis. Guarde o satélite e separe `data_hora_evento` de `data_hora_ingestao`. A reincidência conta anos distintos com base na hora do evento.
4. Escopo da E1: apenas focos do INPE, UCs, APPs e imóveis/reserva do CAR-DF. Flora ameaçada e dados de vazão ficaram para entregas seguintes.