# Instruções para GitHub Copilot - UnB-QueimadaFlora

Projeto de Engenharia de Dados Foco no Incêndio DF (disciplina Sistemas de Bancos de Dados 2, FCTE / UnB, 2026.2).

## Documentos de referência

- `docs/ai/CONTEXT.md`: contexto geral, números reais de focos no DF, regras PostGIS e tarefas da equipe.
- `docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md`: decisão sobre PostgreSQL e PostGIS.

## Regras técnicas

1. Banco: PostgreSQL com PostGIS.
2. Geometrias: colunas com SRID fixo, índices GiST e validação via `ST_IsValid`.
3. Focos de calor: tabela imutável, com distinção entre `data_hora_evento` e `data_hora_ingestao`. A reincidência conta anos distintos com base na data do evento.
4. Escopo da E1: restrito a focos do INPE (DF, 2015 a 2025), UCs/APPs do IBRAM e imóveis/reserva do CAR-DF.
