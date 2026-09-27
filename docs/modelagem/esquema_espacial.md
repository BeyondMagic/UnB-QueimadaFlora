# Modelagem espacial (E1)

Entrega de Manoel Fernando. Esquema PostGIS que responde à pergunta de gestão da E1.

DDL versionado em [`migrations/`](../../migrations/). Índices e extensão ficam com Samuel; a carga, com João e Gabriel Fernando.

## SRID fixo: 31983

Todas as colunas `geom` usam **EPSG:31983** (SIRGAS 2000 / UTM zone 23S).

- O DF fica na zona UTM 23S.
- Coordenadas em metros: `ST_DWithin(geom, geom, 1000)` mede 1 km sem cast para `geography`.
- Scripts de carga (`ogr2ogr`, `shp2pgsql`, GeoPandas) devem reprojetar para 31983 antes ou durante o insert.
- Conferência: `SELECT DISTINCT ST_SRID(geom) FROM <tabela>;` deve devolver só `31983`.

Focos do INPE chegam em lon/lat (EPSG:4326). Exemplo de conversão na carga:

```sql
ST_Transform(
  ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
  31983
)
```

## Diagrama lógico

```
satelite 1──* foco_calor
imovel_car 1──* reserva_legal
imovel_car 1──* area_preservacao_permanente   (FK opcional; NULL se APP for distrital)
unidade_conservacao                           (junção só espacial com foco)
hidrografia                                   (opcional na E1; fora da pergunta)
```

Relação foco ↔ imóvel / RL / APP / UC: junção espacial (`ST_Intersects`, `ST_DWithin`), não FK.

## Tabelas

| Tabela | Geometria | PK | FKs / restrições principais |
| :--- | :--- | :--- | :--- |
| `satelite` | — | `id_satelite` | `nome` UNIQUE; no máximo um `is_referencia = TRUE` |
| `unidade_conservacao` | `MultiPolygon, 31983` | `id_uc` | `ST_IsValid`, `NOT ST_IsEmpty`; `data_download` |
| `imovel_car` | `MultiPolygon, 31983` | `cod_imovel` (`DF-%`) | `ST_IsValid`; `data_download` (snapshot SICAR) |
| `area_preservacao_permanente` | `MultiPolygon, 31983` | `id_app` | FK opcional `cod_imovel` → `imovel_car`; `ST_IsValid` |
| `reserva_legal` | `MultiPolygon, 31983` | `id_reserva` | FK `cod_imovel` → `imovel_car` ON DELETE CASCADE |
| `hidrografia` | `MultiLineString, 31983` | `id_trecho` | Opcional na E1; `ST_IsValid` |
| `foco_calor` | `Point, 31983` | `id_foco` | FK `id_satelite`; `data_hora_evento` ≠ `data_hora_ingestao`; insert-only |

## Carimbos de tempo nos focos

| Coluna | Significado | Uso na reincidência |
| :--- | :--- | :--- |
| `data_hora_evento` | Passagem do satélite / detecção | Sim. Extrair o ano daqui. |
| `data_hora_ingestao` | Momento da carga no banco | Não. Só auditoria do pipeline. |

Constraint: `data_hora_ingestao >= data_hora_evento`.

Trigger `tg_foco_calor_imutavel`: bloqueia `UPDATE` e `DELETE`. `TRUNCATE` segue liberado para recarga em desenvolvimento.

## Satélite

- Todo foco guarda `id_satelite`. Nenhum satélite é descartado na carga.
- Reincidência da pergunta usa **todos** os satélites, contando **anos-calendário distintos** de `data_hora_evento`.
- Séries comparáveis ano a ano filtram `satelite.is_referencia = TRUE` (AQUA_M-T no INPE).
- Índice único parcial: no máximo uma linha com `is_referencia = TRUE`.

## Como a pergunta cai no esquema

> Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?

1. Foco no período: `data_hora_evento` entre 2015-01-01 e 2025-12-31.
2. Foco no imóvel: `ST_Intersects(foco.geom, imovel.geom)`.
3. Critério espacial (OR):
   - `ST_Intersects(foco.geom, reserva_legal.geom)` do mesmo `cod_imovel`, ou
   - `ST_Intersects(foco.geom, app.geom)` (APP do imóvel ou camada distrital que intersecta o imóvel), ou
   - `ST_DWithin(foco.geom, uc.geom, 1000)`.
4. Reincidência: `COUNT(DISTINCT date_part('year', data_hora_evento)) >= 2` por `cod_imovel`.

## Índices (V4)

GiST em toda `geom`. B-tree em `foco_calor(data_hora_evento)`, `foco_calor(id_satelite)`, `reserva_legal(cod_imovel)` e `area_preservacao_permanente(cod_imovel)` (parcial).

## Ordem de carga sugerida

1. `satelite` (seed com AQUA_M-T marcado como referência)
2. `imovel_car`
3. `reserva_legal`, `area_preservacao_permanente`
4. `unidade_conservacao` (e `hidrografia`, se entrar)
5. `foco_calor`

## Histórico

Ver [declaracao_historico.md](declaracao_historico.md). Na E1, CAR e camadas territoriais são snapshot com `data_download`. Focos são insert-only.

## Stack

PostgreSQL + PostGIS (Docker Compose local ou Supabase). O DDL usa tipos e funções padrão PostGIS; não depende de extensões exclusivas do Supabase.
