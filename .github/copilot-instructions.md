# Instruções para GitHub Copilot - UnB-QueimadaFlora

Projeto Foco no Incêndio DF (disciplina Sistemas de Bancos de Dados 2, FCTE / UnB, 2026.2).

## Escrita e estilo

- Leia e siga a skill em `.agents/skills/writing/SKILL.md`.
- Tom técnico, direto e preciso para programadores.
- Sem adjetivos vazios ou floreios de marketing.
- Não repita informações já documentadas; utilize referências e links diretos com parcimônia.
- Sem em dashes ou double hyphens.

## Documentos de referência

- `docs/ai/CONTEXT.md`: contexto geral, dados do DF, regras PostGIS e tarefas.
- `docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md`: decisão sobre PostgreSQL e PostGIS.

## Regras técnicas

1. PostgreSQL com PostGIS.
2. Geometrias com SRID fixo, índices GiST e validação via `ST_IsValid`.
3. Focos imutáveis, com satélite de referência e carimbos separados de evento e ingestão.
4. Escopo E1: focos do INPE (DF, 2015 a 2025), UCs/APPs do IBRAM e imóveis/reserva do CAR-DF.
