# 0001. Adotar PostgreSQL com PostGIS como banco principal

- **Status:** Aceito
- **Data:** 2026-09-25
- **Decisores:** Cláudio H., Elias F., Gabriel F., Gabriel S., João V., Manoel F., Samuel R.

## Contexto

O projeto Corta-Fogo DF cruza detecções de calor por satélite do [BDQueimadas](../glossario.md#bdqueimadas-inpe) com polígonos de proteção ambiental e imóveis rurais no Distrito Federal. A pergunta central de gestão é:

> Quais imóveis rurais do Distrito Federal tiveram focos de calor reincidentes em áreas de reserva legal, de preservação permanente ou a até 1 km de unidades de conservação entre 2015 e 2025?

A equipe precisa de um banco transacional que valide geometrias na carga, processe cruzamentos espaciais métricos e garanta integridade referencial.

### Caracterização da carga

- **Volume de focos:** 38.945 registros de 20 satélites entre 2015 e 2025 (2.350 com o satélite de referência AQUA_M-T). Tamanho bruto em CSV: 4,5 MB.
- **Camadas territoriais do DF:** 21.047 imóveis rurais no [SICAR](../glossario.md#sicar-car-sistema-nacional-de-cadastro-ambiental-rural), 13.499 [reservas legais](../glossario.md#reserva-legal), 2.234 polígonos de [preservação permanente](../glossario.md#app-area-de-preservacao-permanente) do IBRAM/SISDIA e 84 [unidades de conservação](../glossario.md#uc-unidade-de-conservacao).
- **Complexidade geométrica:** feições de reserva legal alcançam até 54.373 vértices em um único polígono. Imóveis rurais do SICAR possuem sobreposições no DF, gerando 76.116 pares foco-imóvel no cruzamento espacial bruto.
- **Taxa de escrita:** ingestão em lote periódica ou anual. Focos de calor são imutáveis (apenas inserção).
- **Taxa de leitura:** consultas analíticas espaciais com filtros por ano do evento e identificador do imóvel.
- **Latência:** consultas interativas de fiscalização devem responder em tempo hábil para triagem de vistorias.

### Restrições não funcionais

- **Integridade topológica:** restrição no esquema para impedir geometrias vazias (`NOT ST_IsEmpty`) ou com autointerseção (`ST_IsValid`).
- **Projeção padronizada:** coordenadas no sistema métrico SIRGAS 2000 / [UTM zone 23S](../glossario.md#utm-zone-23s-universal-transversa-de-mercator-fuso-23-sul), identificado pelo código [EPSG:31983](../glossario.md#epsg31983-sirgas-2000-utm-zone-23s), para permitir buffers de 1.000 m nativos sem conversão para `geography`.
- **Competência técnica:** a equipe domina modelagem relacional e SQL.
- **Custo e ambiente:** execução local em contêineres Docker Compose e suporte a instâncias gerenciadas (Supabase/PostgreSQL).

## Alternativas consideradas

### A. Opção nula: PostgreSQL puro sem extensão espacial

Manter apenas o PostgreSQL relacional, guardando coordenadas pontuais em colunas numéricas (`latitude`, `longitude` do tipo `double precision`) e limites territoriais em colunas `text` ou `jsonb` em formato GeoJSON. Consultas de proximidade usariam a fórmula de Haversine em SQL puro e caixas envolventes (Bounding Box) indexadas por B-tree.

- **Por que é viável:** dispensa extensões externas, utiliza a imagem oficial padrão do PostgreSQL e elimina dependências binárias no servidor.
- **Por que não foi escolhida:** testar interseção ponto-polígono contra 13.499 polígonos de reserva legal (alguns com mais de 50 mil vértices) exige algoritmos de varredura topológica como Point-in-Polygon (PIP). Em SQL puro ou funções procedurais sem indexação R-tree via [índice GiST](../glossario.md#indice-gist-generalized-search-tree-r-tree), o custo computacional seria muito pesado ao banco. A aproximação por caixas envolventes gera excesso de falsos positivos em geometrias sinuosas.

### B. PostgreSQL 16 com extensão PostGIS 3.4

Adotar o PostgreSQL com a extensão [PostGIS](../glossario.md#postgis) habilitada, utilizando tipos nativos `geometry(MultiPolygon, 31983)` e `geometry(Point, 31983)`.

- **O que oferece:** funções espaciais consagradas via biblioteca [GEOS](../glossario.md#geos-geometry-engine-open-source) (`ST_Intersects`, `ST_DWithin`, `ST_MakeValid`), suporte a [índices espaciais GiST](../glossario.md#indice-gist-generalized-search-tree-r-tree) baseados em R-tree, projeção métrica nativa no [EPSG:31983](../glossario.md#epsg31983-sirgas-2000-utm-zone-23s) e integração direta com ferramentas de ecossistema geográfico (GDAL, GeoPandas, QGIS).
- **O que cobra:** dependência de imagem com binários compilados (`postgis/postgis`), consumo adicional de memória para os índices espaciais e necessidade de reprojetar fontes públicas que chegam em EPSG:4674 ou [EPSG:4326](../glossario.md#epsg4326-wgs-84-coordenadas-geograficas).

### C. MongoDB com índices 2dsphere e GeoJSON

Armazenar ocorrências e cadastros territoriais como coleções de documentos JSON/BSON no MongoDB, criando índices espaciais `2dsphere`.

- **O que oferece:** esquema flexível para receber atributos divergentes de satélites e dispensar scripts de migração de tabelas.
- **O que cobra:** o índice `2dsphere` opera exclusivamente com base na esfera WGS84 ([EPSG:4326](../glossario.md#epsg4326-wgs-84-coordenadas-geograficas)), impedindo operações métricas nativas em [UTM zone 23S](../glossario.md#utm-zone-23s-universal-transversa-de-mercator-fuso-23-sul). O MongoDB não possui operadores eficientes de junção espacial entre coleções poligonais densas (`$lookup` espacial limitado), transferindo a carga do cruzamento para o código da aplicação.

## Medição

Benchmark mínimo com o dado real do Distrito Federal (38.945 focos, 21.047 imóveis, 13.499 reservas legais, 2.234 APPs, 84 UCs), já carregado pelo `docker compose up`. Nenhum dado sintético.

Script, comando de reprodução e detalhe da medição: [`scripts/benchmark/`](../../scripts/benchmark/README.md).

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT i.cod_imovel, count(DISTINCT date_part('year', f.data_hora_evento)) AS anos_foco
FROM foco_calor f
JOIN imovel_car i ON ST_Intersects(f.geom, i.geom)
LEFT JOIN reserva_legal r ON r.cod_imovel = i.cod_imovel AND ST_Intersects(f.geom, r.geom)
LEFT JOIN area_preservacao_permanente a ON ST_Intersects(f.geom, a.geom)
LEFT JOIN unidade_conservacao u ON ST_DWithin(f.geom, u.geom, 1000)
WHERE f.data_hora_evento BETWEEN '2015-01-01' AND '2025-12-31'
  AND (r.id_reserva IS NOT NULL OR a.id_app IS NOT NULL OR u.id_uc IS NOT NULL)
GROUP BY i.cod_imovel
HAVING count(DISTINCT date_part('year', f.data_hora_evento)) >= 2;
```

A mesma consulta roda duas vezes na mesma sessão: uma com o comportamento padrão do PostgreSQL (usa o índice GiST das geometrias), outra com `enable_indexscan`/`enable_bitmapscan` desligados, forçando varredura sequencial. Essa segunda execução isola o efeito do índice espacial sobre o mesmo dado, sem depender de uma segunda infraestrutura: aproxima a alternativa A ("PostgreSQL puro sem índice R-tree"), já que a ausência desse índice é exatamente o que a distingue da alternativa escolhida.

| Alternativa | Tempo da consulta central |
| :--- | :---: |
| A. Sem índice espacial (varredura sequencial forçada) | > 5 min (timeout aplicado no script, não terminou) |
| B. PostgreSQL + PostGIS, com índice GiST (escolhida) | 41,8 s (38.945 focos × 21.047 imóveis) |
| C. MongoDB | não medido |

A alternativa C não foi implementada nem medida: exigiria uma segunda pipeline completa de ingestão duplicando o mesmo dado real em coleções GeoJSON com índice `2dsphere`, fora do escopo de um benchmark mínimo. A justificativa técnica para descartá-la sem essa medição está na seção "Alternativas consideradas": o índice `2dsphere` só opera na esfera WGS84 (EPSG:4326), o que impede o cálculo métrico nativo em UTM 23S que a pergunta de gestão exige (`ST_DWithin` de 1.000 m), e o MongoDB não tem um operador de junção espacial entre coleções poligonais equivalente ao `ST_Intersects` acelerado por GiST.

## Decisão

Adotamos **PostgreSQL 16 com extensão [PostGIS 3.4](../glossario.md#postgis)** como banco de dados principal do sistema de origem e camada consolidada.

Padrões obrigatórios:

1. [SRID](../glossario.md#srid-spatial-reference-system-identifier) fixo [EPSG:31983](../glossario.md#epsg31983-sirgas-2000-utm-zone-23s) em projeção [UTM zone 23S](../glossario.md#utm-zone-23s-universal-transversa-de-mercator-fuso-23-sul) em todas as colunas geométricas.
2. Restrição `CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))` em todas as tabelas espaciais.
3. [Índice GiST](../glossario.md#indice-gist-generalized-search-tree-r-tree) em todas as colunas `geom`.
4. [Modelo temporal bitemporal](../glossario.md#modelo-temporal-bitemporal) nos focos de calor: `data_hora_evento` (detecção do satélite para reincidência) e `data_hora_ingestao` (auditoria do pipeline). Focos são imutáveis via trigger.
5. [Snapshot de limites territoriais](../glossario.md#snapshot-de-limites-territoriais): `data_download` registrado para controle de versão do CAR e UCs.

## Consequências

**O que ganhamos:**

- Cruzamento espacial direto em SQL via `ST_Intersects` e `ST_DWithin` com coordenadas métricas exatas.
- Rejeição imediata de dados com erro topológico no momento da carga pelo motor relacional.
- Compatibilidade nativa com ferramentas padrão de engenharia de dados espaciais (`GDAL`, `GeoPandas`, `QGIS`).

**O que perdemos:**

- A imagem Docker e instâncias gerenciadas exigem a extensão PostGIS instalada.
- Reprojeção obrigatória de fontes em EPSG:4674 ou [EPSG:4326](../glossario.md#epsg4326-wgs-84-coordenadas-geograficas) durante o pipeline de carga.
- A consulta da pergunta de gestão sem simplificação de vértices leva 41,8 segundos (medição real, seção "Medição") devido à sobreposição de imóveis do CAR e polígonos densos de reserva legal, ultrapassando a meta de 500 ms sem a aplicação de pré-simplificação topológica (`ST_SimplifyPreserveTopology`).

**O que se torna irreversível:**

- Os dados geométricos passam a ser armazenados na estrutura binária interna do PostGIS (formato [EWKB](../glossario.md#ewkb-extended-well-known-binary)) indexados por [GiST](../glossario.md#indice-gist-generalized-search-tree-r-tree). Reverter para outro banco exigirá dump e reexportação via ferramentas GIS externas, além da reescrita de todas as regras topológicas.

## Gatilho de revisão

Esta decisão será revisada caso o tempo de carga completa ultrapasse 1 hora ou caso as consultas analíticas continuem acima de 5 segundos mesmo após a simplificação e pré-agregação dos polígonos, disparando a migração do processamento analítico para [DuckDB](../glossario.md#duckdb) com arquivos [GeoParquet](../glossario.md#geoparquet).
