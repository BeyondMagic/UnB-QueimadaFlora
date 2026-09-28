# Esquema Espacial e Relacional (PostGIS)

Especificação técnica do modelo de dados transacional da Entrega 1, implementado no PostgreSQL 16 com a extensão PostGIS 3.4.

## 1. Padrão de Projeção Espacial (SRID 31983)

Todas as colunas geométricas do banco utilizam obrigatoriamente a projeção métrica **EPSG:31983** (SIRGAS 2000 / UTM zone 23S).

- **Justificativa geográfica:** o território do Distrito Federal está situado integralmente no fuso UTM 23S.
- **Eficiência computacional:** coordenadas projetadas em metros permitem calcular distâncias e buffers (como a faixa de 1.000 metros em torno de unidades de conservação via `ST_DWithin`) diretamente no plano cartesiano, sem conversão computacional para o tipo `geography`.
- **Validação de esquema:** nenhuma coluna pode ser definida como tipo genérico `geometry` sem SRID declarado. A conferência é garantida pelo catálogo do PostGIS.

As detecções de focos de calor chegam na base do INPE em coordenadas geográficas WGS84 (EPSG:4326). A conversão métrica é executada na ingestão:

```sql
ST_Transform(
  ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
  31983
)
```

## 2. Modelo Lógico e Relacionamentos

A estrutura conjuga integridade relacional clássica (chaves estrangeiras) com relacionamentos topológicos espaciais:

```text
satelite (1) ──< foco_calor (N)
imovel_car (1) ──< reserva_legal (N)
imovel_car (1) ──< area_preservacao_permanente (N) [relacional opcional]

foco_calor ──[ junção espacial: ST_Intersects ]──> imovel_car
foco_calor ──[ junção espacial: ST_Intersects ]──> reserva_legal
foco_calor ──[ junção espacial: ST_Intersects ]──> area_preservacao_permanente
foco_calor ──[ junção espacial: ST_DWithin    ]──> unidade_conservacao
```

- **Relações relacionais:** chaves estrangeiras formais vinculam cada foco de calor ao seu sensor na tabela `satelite`, e cada polígono de reserva legal ao seu respectivo cadastro em `imovel_car`.
- **Relações espaciais:** o vínculo entre ocorrências de calor e os perímetros territoriais é dinâmico e avaliado no plano geométrico por operadores topológicos (`ST_Intersects` e `ST_DWithin`), sem colunas de chave estrangeira nas ocorrências.

## 3. Especificação das Tabelas

O DDL das tabelas físicas é gerenciado por migrações versionadas do Flyway (diretório `migrations/`).

| Tabela | Tipo geométrico | Chave primária | Restrições de integridade e regras |
| :--- | :--- | :--- | :--- |
| `satelite` | Sem geometria | `id_satelite` | Nome único; no máximo um registro com flag `is_referencia = TRUE`. |
| `imovel_car` | `MultiPolygon, 31983` | `cod_imovel` | Formato padrão `DF-%`; restrição `CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))`; metadado `data_download`. |
| `reserva_legal` | `MultiPolygon, 31983` | `id_reserva` | Chave estrangeira `cod_imovel` referenciando `imovel_car` com `ON DELETE CASCADE`; restrição `ST_IsValid`. |
| `area_preservacao_permanente` | `MultiPolygon, 31983` | `id_app` | Chave estrangeira opcional para `imovel_car`; restrição `ST_IsValid`. |
| `unidade_conservacao` | `MultiPolygon, 31983` | `id_uc` | Restrição `CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))`; metadado `data_download`. |
| `foco_calor` | `Point, 31983` | `id_foco` | Chave estrangeira para `satelite`; constraint `data_hora_ingestao >= data_hora_evento`; trigger de imutabilidade. |
| `hidrografia` | `MultiLineString, 31983` | `id_trecho` | Tabela auxiliar opcional na E1; restrição `ST_IsValid`. |

### Carimbos temporais nos focos

A tabela `foco_calor` implementa modelo bitemporal:
- `data_hora_evento`: momento exato da detecção na passagem do satélite. O ano da reincidência é extraído exclusivamente deste campo.
- `data_hora_ingestao`: momento da carga no banco pelo pipeline, utilizado para auditoria e controle de recargas.

A imutabilidade das detecções é garantida pelo trigger `tg_foco_calor_imutavel`, que rejeita comandos `UPDATE` e `DELETE`. O recarregamento em desenvolvimento é feito via `TRUNCATE`.

## 4. Estratégia de Indexação

A aceleração de consultas combina índices espaciais GiST com índices relacionais B-tree:

1. **Índices GiST (R-Tree):** aplicados em todas as colunas `geom` das tabelas `foco_calor`, `imovel_car`, `reserva_legal`, `area_preservacao_permanente` e `unidade_conservacao`. Reduzem a complexidade do teste de sobreposição de $O(N \times M)$ para varredura de caixas mínimas envolventes indexadas.
2. **Índices B-tree:**
   - `foco_calor(data_hora_evento)` para filtragem do intervalo de 2015 a 2025.
   - `foco_calor(id_satelite)` para filtros pelo satélite de referência.
   - `reserva_legal(cod_imovel)` para junções diretas com o imóvel rural.
   - Índice parcial único em `satelite(is_referencia)` onde `is_referencia = TRUE`.

## 5. Mapeamento da Consulta da Pergunta de Gestão

A consulta central é avaliada em quatro etapas espaciais e temporais:

1. **Recorte temporal:** `f.data_hora_evento BETWEEN '2015-01-01' AND '2025-12-31'`.
2. **Interseção com o imóvel rural:** `ST_Intersects(f.geom, i.geom)`.
3. **Critérios de proximidade ou sobreposição ambiental (cláusula OR):**
   - Foco intersecta reserva legal do mesmo imóvel: `ST_Intersects(f.geom, r.geom) AND r.cod_imovel = i.cod_imovel`.
   - Foco intersecta área de preservação permanente: `ST_Intersects(f.geom, a.geom)`.
   - Foco está no raio de 1 km de uma unidade de conservação: `ST_DWithin(f.geom, u.geom, 1000)`.
4. **Agrupamento e reincidência:** `COUNT(DISTINCT date_part('year', f.data_hora_evento)) >= 2` agrupado por `i.cod_imovel`.

## 6. Ordem de Carga e Dependências

Para preservar a integridade referencial das chaves estrangeiras, a carga de dados obedece à seguinte ordem determinística:

1. `satelite` (inserção inicial com definição do satélite de referência `AQUA_M-T`).
2. `imovel_car` (base territorial dos imóveis do DF).
3. `reserva_legal` e `area_preservacao_permanente` (dependem dos códigos de imóveis cadastrados).
4. `unidade_conservacao` e `hidrografia` (camadas independentes de referência distrital).
5. `foco_calor` (camada de eventos que referencia a tabela de satélites).
