# Instruções para Agentes de IA

Você está trabalhando no repositório UnB-QueimadaFlora (Foco no Incêndio DF), da disciplina Sistemas de Bancos de Dados 2 (FCTE / UnB, 2026.2).

## 1. Diretriz de escrita e comunicação (Obrigatório)

Antes de produzir qualquer texto, documentação ou resposta, leia e siga estritamente a skill [`.agents/skills/writing/SKILL.md`](.agents/skills/writing/SKILL.md).

- O público é composto exclusivamente por programadores. Seja direto, técnico e preciso.
- Elimine adjetivos vazios (como robusto, crucial, vital, inovador).
- Não repita informações. Em vez de reescrever dados já documentados, apenas aponte o link para o arquivo correspondente quando indispensável.
- Proibido o uso de travessoes (em dashes) e double hyphens. Use ponto, virgula, dois-pontos ou parenteses.
- Sem preâmbulos, conclusões de resumo ou frases de chatbot.

## 2. Onde ler o contexto técnico

Consulte sempre:

- [`docs/ai/CONTEXT.md`](docs/ai/CONTEXT.md): pergunta de gestão, dados do DF, regras de PostGIS e frentes da equipe.
- [`docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md`](docs/adr/0001-adotar-postgresql-com-postgis-camada-gold.md): decisão de arquitetura da camada Gold.
- [`docs/human/03/e1_pergunta_de_gest_o_e_escopo_gabriel.md`](docs/human/03/e1_pergunta_de_gest_o_e_escopo_gabriel.md): escopo e checklist da E1.

## 3. Regras inegociáveis de código e modelagem

1. PostgreSQL com PostGIS.
2. Colunas de geometria sempre com SRID fixo, índice GiST e validação `ST_IsValid`.
3. Focos imutáveis, com satélite, flag do satélite de referência e carimbos separados de `data_hora_evento` e `data_hora_ingestao`.
4. Escopo E1: apenas focos do INPE, UCs, APPs e imóveis/reserva do CAR-DF. Flora e vazão estão fora da E1.