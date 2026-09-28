-- Benchmark minimo e reproduzivel da consulta central da pergunta de gestao (ADR 0001).
-- Roda a MESMA consulta, com dado real ja carregado pelo `docker compose up`, duas vezes:
--   B: comportamento padrao do PostgreSQL com PostGIS (usa o indice GiST das geometrias).
--   A: com enable_indexscan/enable_bitmapscan desligados nesta sessao, forcando varredura
--      sequencial. Aproxima a alternativa "PostgreSQL puro sem indice R-tree" descrita no
--      ADR, sem precisar de uma segunda infraestrutura: mede o efeito real de ter (ou nao)
--      um indice espacial sobre a mesma consulta e o mesmo dado.
--
-- Uso:
--   docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
--     -f /scripts/benchmark_pergunta_gestao.sql
--
-- (o docker-compose.yml usa POSTGRES_USER/POSTGRES_DB com valor padrao corta-fogo/corta-fogo-df)

\timing on

\echo '=== B: PostgreSQL + PostGIS, com indice GiST (alternativa escolhida) ==='

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

\echo '=== A: mesma consulta sem indice espacial (indexscan/bitmapscan desligados) ==='
\echo 'Limite de 5 minutos: sem indice a consulta nao terminou nesse tempo na medicao original.'

SET enable_indexscan = off;
SET enable_bitmapscan = off;
SET statement_timeout = '300s';

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

RESET enable_indexscan;
RESET enable_bitmapscan;
