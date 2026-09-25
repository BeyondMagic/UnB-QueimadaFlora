# Contexto do Projeto: Foco no Incêndio DF

Referência técnica para desenvolvedores e assistentes de IA no repositório UnB-QueimadaFlora (disciplina Sistemas de Bancos de Dados 2, FCTE / UnB, 2026.2, Grupo G5).

## 1. Pergunta de gestão da E1

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

- Quem pergunta: analistas ambientais e bombeiros militares do DF (CBMDF).
- Objetivo: priorizar imóveis rurais para fiscalização preventiva antes do período de seca.
- O que é reincidência: focos registrados na mesma área do imóvel em pelo menos 2 anos-calendário distintos dentro do período (2015 a 2025). Contam anos distintos, não o número de detecções.

## 2. Recorte de escopo da E1

O que entra no banco na E1:

- Focos de calor: BDQueimadas (INPE), recorte do DF, 2015 a 2025, todos os satélites.
- Unidades de Conservação e APPs: IBRAM / Geoportal DF.
- Imóveis rurais e reserva legal: SICAR / CAR-DF.

O que ficou para etapas seguintes:

- Flora ameaçada: o catálogo de espécies do SiBBr/JBRJ não traz pontos com coordenadas geográficas.
- Séries de vazão: dependem de dados hidrológicos que não estão nas fontes atuais.
- Camada analítica colunar (DuckDB / GeoParquet) e bucket de arquivos (MinIO): a consulta da E1 roda direto no PostGIS.

## 3. Dados reais do DF

Contagem feita sobre os CSVs do INPE de 2015 a 2025:

- Total de focos no DF (todos os satélites): 38.945 registros em 11 anos.
- Focos no satélite de referência (AQUA_M-T): 2.350 registros.
- Tamanho dos arquivos: cerca de 4,5 MB de CSVs compactados para todo o período.

Como o volume total cabe com folga em disco e memória, a E1 carrega todos os satélites de 2015 a 2025.

## 4. Banco e modelagem espacial

Banco escolhido: PostgreSQL com extensão PostGIS (rodando via Docker local ou serviço gerenciado/Supabase). Ver ADR 0001.

Regras de modelagem:
1. SRID explícito em todas as colunas de geometria (exemplo: EPSG:31983 para métrica local no DF ou EPSG:4326 geográfico). Nunca use `geometry` sem SRID.
2. Índice GiST obrigatório em toda coluna geométrica.
3. Validação topológica com `ST_IsValid` e saneamento de polígonos com `ST_MakeValid` na ingestão.
4. Focos de calor são imutáveis (apenas inserção).
5. Dois carimbos de data/hora nos focos:
   * `data_hora_evento`: hora em que o satélite passou e detectou o calor. O ano da reincidência sai obrigatoriamente deste campo.
   * `data_hora_ingestao`: momento em que o dado entrou no banco.
6. Guardar o satélite em cada linha de foco e sinalizar o satélite de referência (`AQUA_M-T`) para comparações históricas.
7. O CAR sofre retificações ao longo do tempo. Na E1 usamos o recorte atual do DF e registramos a data do download.

## 5. Divisão de tarefas da equipe (E1)

| Membro | Frente | Entrega |
| :--- | :--- | :--- |
| Gabriel Souza | Coordenação | Pergunta de gestão, corte de escopo, conferência de volume e tag e1 |
| Manoel | Modelagem espacial | Esquema PostGIS (tabelas, colunas geométricas tipadas, chaves e restrições) |
| Samuel | Migrações | Scripts SQL versionados (extensão PostGIS, tabelas, índices GiST e `ST_IsValid`) |
| João | Focos de calor | Download automatizado e carga dos focos do INPE (DF, 2015 a 2025) |
| Gabriel Fernando | Camadas geográficas | Ingestão e reprojeção de shapefiles/geopackages de UCs, APPs e CAR-DF |
| Cláudio | Docker e execução | Docker Compose do PostGIS, script de carga em um comando e teste em máquina limpa |
| Elias | Métricas e ADR | Números reais pós-carga, tempos de resposta e atualização do ADR |
