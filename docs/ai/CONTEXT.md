# Contexto do Projeto: Foco no Incêndio DF

# Contexto do Projeto: Corta-Fogo DF

Referência técnica para desenvolvedores e assistentes de IA no repositório [corta-fogo-df](https://github.com/BeyondMagic/corta-fogo-df) (disciplina Sistemas de Bancos de Dados 2, FCTE / UnB, 2026.2, Grupo G5).

## 1. Pergunta de gestão da E1

> Quais imóveis rurais do Distrito Federal tiveram focos de calor reincidentes em áreas de reserva legal, de preservação permanente ou a até 1 km de unidades de conservação entre 2015 e 2025?

- Quem pergunta: analistas ambientais e bombeiros militares do DF (CBMDF).
- Objetivo: priorizar imóveis rurais para fiscalização preventiva antes do período de seca.
- O que é reincidência: focos registrados na mesma área do imóvel em pelo menos 2 anos-calendário distintos dentro do período (2015 a 2025). Contam anos distintos, não o número de detecções.

## 2. Recorte de escopo da E1

O que entra no banco na E1:

- Focos de calor: BDQueimadas (INPE), recorte do DF, 2015 a 2025, todos os satélites.
- Unidades de conservação e áreas de preservação permanente: IBRAM / Geoportal DF.
- Imóveis rurais e reserva legal: Cadastro Ambiental Rural (SICAR).

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

Banco escolhido: PostgreSQL com extensão PostGIS (Docker local ou Supabase). Ver [ADR 01](../adr/01-adotar-postgresql-com-postgis-camada-gold.md).
Esquema fechado: [`docs/modelagem/esquema_espacial.md`](../modelagem/esquema_espacial.md).
Histórico: [`docs/modelagem/declaracao_historico.md`](../modelagem/declaracao_historico.md).

Regras de modelagem:
1. SRID fixo **EPSG:31983** em toda coluna `geom`. Nunca use `geometry` sem SRID.
2. Índice GiST obrigatório em toda coluna geométrica.
3. Validação com `ST_IsValid` (e `ST_MakeValid` na ingestão se o shapefile vier inválido).
4. Focos imutáveis (apenas inserção).
5. Dois carimbos nos focos: `data_hora_evento` (reincidência) e `data_hora_ingestao` (auditoria).
6. Satélite por foco; `is_referencia` para AQUA_M-T.
7. CAR na E1: snapshot com `data_download`. Sem versionamento temporal ainda.
8. Tabelas: `satelite`, `foco_calor`, `unidade_conservacao`, `area_preservacao_permanente`, `imovel_car`, `reserva_legal`, `hidrografia` (opcional).

## 5. Divisão de tarefas da equipe (E1)

| Membro           | Frente              | Entrega                                                                           |
| :--------------- | :------------------ | :-------------------------------------------------------------------------------- |
| Gabriel Souza    | Coordenação         | Pergunta de gestão, corte de escopo, conferência de volume e tag e1               |
| Manoel           | Modelagem espacial  | Esquema PostGIS (tabelas, colunas geométricas tipadas, chaves e restrições)       |
| Samuel           | Migrações           | Scripts SQL versionados (extensão PostGIS, tabelas, índices GiST e `ST_IsValid`)  |
| João             | Focos de calor      | Download automatizado e carga dos focos do INPE (DF, 2015 a 2025)                 |
| Gabriel Fernando | Camadas geográficas | Ingestão e reprojeção de shapefiles/geopackages de UCs, APPs e CAR-DF             |
| Cláudio          | Docker e execução   | Docker Compose do PostGIS, script de carga em um comando e teste em máquina limpa |
| Elias            | Métricas e ADR      | Números reais pós-carga, tempos de resposta e atualização do ADR                  |
