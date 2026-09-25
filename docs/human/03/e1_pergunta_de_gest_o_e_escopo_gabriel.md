# E1 - Coordenação: pergunta de gestão, escopo, cronograma, checklist e tag

## 1. Pergunta de gestão (fechada)

> **Quais imóveis rurais do CAR-DF tiveram focos de calor reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de Conservação entre 2015 e 2025?**

* **Quem pergunta:** analistas de fiscalização ambiental e órgãos de combate a incêndio do DF, como o CBMDF (atores da aba Identificação e da consulta 3 da aba Modelos).
* **Decisão que ela apoia:** quais imóveis priorizar em vistoria e prevenção antes da próxima seca.
* **Por que esta formulação:** tem sujeito (o imóvel do CAR), recorte espacial (DF), recorte temporal (2015-2025) e critério (reincidência em RL, APP ou entorno de UC). Ela usa só o núcleo de fontes da E1: focos do INPE, UCs, APPs e CAR-DF.

---

## 2. Definições operacionais

Cada termo da pergunta vira uma regra que a consulta consegue testar. Estas definições valem para toda a equipe na E1.

| Termo | Definição na E1 | O que exige do banco |
| :--- | :--- | :--- |
| **Imóvel rural do CAR-DF** | Polígono de imóvel do recorte do SICAR para o DF, identificado pelo código do CAR. | Chave pelo código do CAR; data do download registrada na carga. |
| **Foco de calor Reincidente** | Registro do BDQueimadas (INPE) dentro do DF. Focos na mesma área do imóvel em pelo menos 2 anos-calendário distintos do período. Conta anos distintos, não detecções. | Coluna de satélite em cada foco; hora do evento (passagem do satélite) separada da hora de ingestão. Extrair o ano da hora do evento, nunca da hora de ingestão. |
| **Dentro da reserva legal ou APP** | O ponto do foco intersecta o polígono de RL ou de APP do imóvel. | Interseção espacial com índice GIST nas duas camadas. |
| **A até 1 km de UC** | Foco dentro do imóvel e a no máximo 1.000 m do limite de uma UC (focos dentro da UC contam). | Distância em metros: SRID projetado ou *cast* para `geography`, conforme o SRID que a Modelagem Espacial fixar. |
| **Período** | 01/01/2015 a 31/12/2025, só anos completos. | Filtro pela hora do evento. |
| **Satélites** | Todos os satélites entram na reincidência. Comparações ano a ano usam o satélite de referência do INPE. | Satélite guardado por foco, nunca descartado na carga. |

* **Por que contar anos distintos:** o mesmo fogo pode ser detectado por vários satélites e em dias seguidos. Contando anos, duplicatas não inflam a reincidência, e dá para usar todos os satélites sem deduplicar na E1.
* **Limites do CAR:** a E1 responde com os limites do recorte baixado. Responder se o foco estava na reserva legal na época depende do histórico do CAR, que fica na declaração de histórico (Manoel e Elias).

---

## 3. Recorte de escopo da E1

**Decisão:** a E1 entrega o núcleo focos + UCs/APPs + CAR-DF num único banco PostGIS, subindo com um comando. Flora, vazão e as camadas de bucket e analítica da planilha ficam para entregas seguintes.

| Item | Na E1? | Motivo | Condição para entrar depois |
| :--- | :---: | :--- | :--- |
| **Focos de calor** (BDQueimadas, DF, 2015-2025, todos os satélites) | **Sim** | Tabela central da pergunta e a de maior volume. | — |
| **Unidades de Conservação** (IBRAM / Geoportal DF) | **Sim** | Base da faixa de 1 km. | — |
| **APPs** | **Sim** | Parte do critério da pergunta. | — |
| **Imóveis e reserva legal do CAR-DF** (SICAR) | **Sim** | Sujeito da pergunta. Se o download não automatizar, versiona-se o recorte do DF no repositório, se couber em 5 MB compactado. | — |
| **Hidrografia** | **Opcional** | Não entra na pergunta. Carrega se não atrasar o núcleo; não conta para fechar a E1. | Pergunta que use rios. |
| **Flora ameaçada** (SiBBr / JBRJ) | **Não** | O catálogo traz nomes de espécies, sem pontos de ocorrência com coordenadas. | Fonte de ocorrências georreferenciadas no DF. |
| **Pergunta da vazão** | **Não** | Exige séries hidrológicas, que não estão entre as fontes listadas. | Fonte de vazão incluída na aba 1 Fontes. |
| **Camada Bronze em bucket** (MinIO/S3) | **Não** | Aumenta o Compose e não ajuda a responder a pergunta. | Entrega que trate reprocessamento e auditoria. |
| **Camada analítica** (DuckDB/GeoParquet) e orquestrador | **Não** | A pergunta roda direto no PostGIS. | Gatilho já escrito no ADR: consulta acima de 500 ms ou carga acima de 1 h. |

### Texto pronto para a seção de escopo do README:

```markdown
## Escopo da E1

Pergunta de gestão: Quais imóveis rurais do CAR-DF tiveram focos de calor
reincidentes dentro da reserva legal, em APP ou a até 1 km de Unidades de
Conservação entre 2015 e 2025?

Incluído: focos de calor do INPE (DF, 2015-2025, todos os satélites),
Unidades de Conservação, APPs e imóveis/reserva legal do CAR-DF, em PostgreSQL +
PostGIS.

Fora da E1 (entregas seguintes):
- Flora ameaçada: o catálogo de espécies não traz pontos de ocorrência com coordenadas.
- Vazão: depende de dados hidrológicos, que não estão entre as fontes atuais.
- Camada Bronze (bucket) e camada analítica (DuckDB/GeoParquet): não são necessárias para responder à pergunta da E1.
```

---

## 4. Conferência de volume dos focos do DF

* **Resultado (24/09):** O DF tem 38.945 focos de 2015 a 2025 com todos os satélites, contra 2.350 só com o satélite de referência (`AQUA_M-T`), cerca de 17 vezes menos.
* **Decisão:** A E1 mantém 2015-2025 com todos os satélites. Não é preciso estender a série nem ampliar para o entorno.

| Ano | Todos os satélites (focos) | Satélite de referência AQUA_M-T (focos) | Satélites distintos |
| :---: | :---: | :---: | :---: |
| **2025** | 4.453 | 234 | 11 |
| **2024** | 6.190 | 349 | 12 |
| **2023** | 1.368 | 89 | 8 |
| **2022** | 5.741 | 251 | 13 |
| **2021** | 5.535 | 259 | 14 |
| **2020** | 3.258 | 196 | 13 |
| **2019** | 3.761 | 213 | 15 |
| **2018** | 948 | 88 | 13 |
| **2017** | 3.590 | 287 | 16 |
| **2016** | 2.269 | 229 | 12 |
| **2015** | 1.832 | 155 | 13 |
| **Total** | **38.945** | **2.350** | **20** |

Contagem feita sobre os CSVs do DF gerados pelo script abaixo, rodado por Gabriel Souza. A coluna de referência filtra `AQUA_M-T` nos mesmos arquivos. O volume oscila muito entre anos: 948 focos em 2018 e 6.190 em 2024.

### Script da contagem (`conta_focos_df.py`)
Python + pandas, já corrigido para UTF-8. Baixa os arquivos nacionais de 2015 a 2025, filtra o DF, conta por ano e grava os CSVs do DF em `focos_df/`.

```python
# conta_focos_df.py
# conferência de volume da E1
import os, zipfile, urllib.request
import pandas as pd

BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual"
ANOS = range(2015, 2026)
os.makedirs("focos_df", exist_ok=True)

def focos_do_df(url):
    caminho, _ = urllib.request.urlretrieve(url)
    partes = []
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as f:
            for bloco in pd.read_csv(f, chunksize=200_000, dtype=str, encoding="utf-8"):
                col = next((c for c in bloco.columns if c.lower() == "estado"), None)
                if col is None:
                    raise KeyError(f"Sem coluna 'estado' em {url}: {list(bloco.columns)}")
                partes.append(bloco[bloco[col].str.upper().str.contains("DISTRITO FEDERAL", na=False)])
    os.remove(caminho)
    return pd.concat(partes)

linhas = []
for ano in ANOS:
    todos = focos_do_df(f"{BASE}/Brasil_todos_sats/focos_br_todos-sats_{ano}.zip")
    ref = focos_do_df(f"{BASE}/Brasil_sat_ref/focos_br_ref_{ano}.zip")
    todos.to_csv(f"focos_df/focos_df_todos_sats_{ano}.csv", index=False)
    col_sat = next(c for c in todos.columns if c.lower().startswith("satelite"))
    linhas.append({
        "ano": ano,
        "todos_sats": len(todos),
        "sat_ref": len(ref),
        "satelites_distintos": todos[col_sat].nunique()
    })
    print(linhas[-1], flush=True)

res = pd.DataFrame(linhas)
print(res.to_string(index=False))
print("TOTAL 2015-2025 | todos os satélites:", res.todos_sats.sum(), "| referência:", res.sat_ref.sum())
```

---

## 5. Checklist da E1

Conferência feita pela coordenação antes da tag. Os itens saem das entregas do planejamento; se o enunciado da E1 tiver checklist oficial, cruzar com ele.

### Pergunta e escopo (Gabriel Souza)
- [ ] Pergunta de gestão, em uma frase, no README e na planilha
- [ ] Recorte de escopo escrito no README, com o que ficou fora e por quê
- [ ] Volume dos focos conferido e registrado na seção 4

### Modelagem espacial (Manoel)
- [ ] Tabelas de focos, satélite, UCs, APPs, imóveis do CAR e reserva legal (hidrografia, se entrar)
- [ ] Todas as colunas de geometria tipadas com o mesmo SRID fixo
- [ ] Chaves primárias, estrangeiras e restrições
- [ ] Foco com satélite e com hora do evento separada da hora de ingestão

### Migrações (Samuel)
- [ ] Migrações versionadas que rodam do zero, em ordem
- [ ] Criação da extensão PostGIS dentro das migrações
- [ ] Índices GIST nas geometrias
- [ ] Restrição `ST_IsValid` nas geometrias

### Focos de calor (João)
- [ ] Download automatizado, sem passo manual
- [ ] Anos completos, filtrados para o DF
- [ ] SICAR automatizado ou recorte do DF versionado (até 5 MB compactado)

### Camadas geográficas (Gabriel Fernando)
- [ ] UCs, APPs e CAR-DF carregados com `ogr2ogr` ou `shp2pgsql`
- [ ] Todas as camadas no SRID do esquema (conferir que só aparece um SRID por coluna de geometria)

### Docker Compose e README (Cláudio)
- [ ] Um comando sobe o PostGIS e roda a carga
- [ ] Serviço de carga com GDAL, se usar `ogr2ogr`
- [ ] README com pré-requisitos, o comando, a pergunta de gestão e o escopo
- [ ] Teste em máquina limpa feito e registrado (quem, quando, commit)

### Caracterização e ADR (Elias)
- [ ] Números reais: focos por ano e por mês de seca, feições por camada
- [ ] Consultas espaciais que importam e latência tolerada
- [ ] ADR cobre satélite por foco, hora do evento x hora de ingestão e histórico do CAR
- [ ] Declaração de histórico, com Manoel

---

### Planilha G5 - BD2: pendências encontradas

- [ ] **Aba Riscos não existe no arquivo:** O quadro de progresso marca "Falta preencher" (1 de 3 linhas) e o campo 20 do ADR manda trazer os riscos dela. Não há dono no planejamento; definir hoje. Riscos já identificados: captcha no download do SICAR, série magra do DF, SRID divergente entre camadas, limites do CAR que mudam.
- [ ] **Aba 2, coluna "Fonte de origem":** numeração deslocada. Focos aponta 1, mas o BDQueimadas é o nº 2 na aba 1; IBRAM $2 \rightarrow 3$; CAR $3 \rightarrow 4$; Flora $4 \rightarrow 5$.
- [ ] **Abas 1 e 2, volumes:** "milhares de focos/mês" e "~350 MB a 1 GB" não batem com o DF. Trocar pelos valores medidos em 24/09: 948 a 6.190 focos por ano no DF (todos os satélites) e cerca de 4,5 MB de CSV para os 11 anos.
- [ ] **Aba 3, consulta 3:** "últimos 24 meses" alinhar com o período da pergunta (2015-2025).
- [ ] **Identificação:** "o que o sistema faz" e "problema que resolve" falam de corredores de vegetação. Alinhar com a pergunta de gestão e subir a versão (hoje 0.01).
- [ ] **ADR, campo 4 ("Quem decidiu"):** trocar "Equipe de Engenharia de Dados G5" pelos nomes.
- [ ] **Aba 5, "Responsável na equipe":** trocar "Engenharia de Dados" pelos nomes.
- [ ] **Itens fora da E1 na planilha (SiBBr, bucket, DuckDB):** marcar como entrega futura, para não parecer que estão na E1.

---

## 6. Stack

Utilizaremos o banco de dados **Supabase (PostgreSQL)** para fazer a implementação necessária do nosso banco de dados.