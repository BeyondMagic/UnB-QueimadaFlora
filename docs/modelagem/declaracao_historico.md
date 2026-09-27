# Declaração de histórico (E1)

Documento conjunto Modelagem Espacial (Manoel) e Caracterização/ADR (Elias).
Define o que o banco preserva no tempo e o que a E1 deliberadamente não versiona.

## Focos de calor: insert-only

Um foco é um evento de detecção. Não se corrige geometria nem satélite depois da carga.

- `INSERT` permitido.
- `UPDATE` e `DELETE` bloqueados pelo trigger `tg_foco_calor_imutavel`.
- Recarga completa em desenvolvimento: `TRUNCATE foco_calor` (o trigger não cobre TRUNCATE).

Dois carimbos:

| Campo | Origem | Papel histórico |
| :--- | :--- | :--- |
| `data_hora_evento` | CSV do INPE (`data_pas` / equivalente) | Tempo do mundo real. Ano da reincidência. |
| `data_hora_ingestao` | Pipeline no momento do insert | Tempo do sistema. Auditoria da carga. |

O mesmo fogo físico pode gerar várias linhas (vários satélites, dias seguidos). A E1 não deduplica: conta anos distintos de `data_hora_evento` por imóvel.

## CAR (imóvel, reserva legal, APP do SICAR): snapshot

Imóveis do CAR são retificados. Limites de reserva legal e APP mudam. Se a carga sobrescrever o polígono atual, deixa de ser possível perguntar se o foco estava dentro da RL **na época do evento**.

### Decisão da E1

- Carregar **um** recorte do SICAR para o DF.
- Registrar `data_download` em `imovel_car`, `reserva_legal` e `area_preservacao_permanente`.
- Responder a pergunta de gestão com os limites desse recorte.
- Documentar no README/ADR: a resposta é "dentro da RL/APP do snapshot baixado", não "dentro da RL vigente em 2017".

### O que não fazer na E1

- Não implementar SCD Type 2 ainda (evita atrasar migrações e carga).
- Não apagar `data_download` nem misturar recortes de datas diferentes na mesma tabela sem marcar a origem.

### Caminho pós-E1 (quando precisar de "na época")

Versionar `imovel_car` e `reserva_legal` com vigência:

```text
cod_imovel + vigencia_inicio + vigencia_fim + geom + ...
```

Consulta temporal típica:

```sql
-- esboço futuro: RL vigente na data do foco
f.data_hora_evento::date >= r.vigencia_inicio
AND (r.vigencia_fim IS NULL OR f.data_hora_evento::date < r.vigencia_fim)
AND ST_Intersects(f.geom, r.geom)
```

Cada nova retificação do SICAR vira linha nova (fecha a vigência anterior, abre outra). Focos continuam insert-only.

## UCs, APP distrital e hidrografia

Camadas de referência territorial. Na E1 também são snapshot com `data_download`.
Mudança de limite de UC é rara no prazo da disciplina; o mesmo padrão de vigência serve depois se precisar.

## Resumo para o ADR

1. Foco: imutável; satélite preservado; evento ≠ ingestão.
2. CAR: snapshot com `data_download`; sobrescrita impede análise temporal da RL.
3. Pós-E1: SCD Type 2 em imóvel/RL se a pergunta exigir "na época do foco".
