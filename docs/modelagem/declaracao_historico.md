# Declaração de Tratamento Histórico e Temporal

Diretriz formal sobre como o banco de dados trata a evolução temporal das ocorrências de calor e dos limites territoriais na Entrega 1.

## 1. Princípios do Tratamento Histórico

O modelo do Corta-Fogo DF estabelece uma separação entre duas naturezas de dados:
- **Ocorrências físicas (focos de calor):** eventos pontuais discretos no tempo e no espaço, que representam fatos consumados do mundo real.
- **Cadastros territoriais (imóveis rurais e áreas protegidas):** dados regulatórios sujeitos a alterações administrativas, retificações de limites e revisões ao longo dos anos.

## 2. Focos de Calor: Semântica Imutável (Insert-Only)

Os registros de focos de calor capturados por sensores orbitais não sofrem alterações após a sua detecção pelo INPE. O banco implementa essa semântica de forma estrita:

1. **Operações permitidas:** apenas comandos `INSERT` são aceitos na tabela `foco_calor`. Comandos `UPDATE` e `DELETE` são interceptados e bloqueados pelo trigger `tg_foco_calor_imutavel`.
2. **Modelo bitemporal:**
   - `data_hora_evento`: carimbo temporal emitido pelo satélite no momento da passagem orbital. É o registro da ocorrência no mundo real e serve de base exclusiva para a extração do ano-calendário na métrica de reincidência.
   - `data_hora_ingestao`: carimbo registrado pelo pipeline de dados no momento da inserção na base. Serve para controle de linhagem, auditoria e identificação de recargas.
3. **Resolução de duplicatas e múltiplos sensores:** um mesmo incêndio florestal pode ser detectado por satélites distintos ou em passagens sucessivas em dias contíguos. O sistema preserva todas as detecções individuais sem deduplicação artificial na ingestão. A contagem de reincidência agrega os anos distintos de `data_hora_evento` por imóvel, impedindo distorções no indicador de recorrência.

## 3. Cadastros Territoriais: Semântica de Snapshot com Rastreabilidade

Os limites declarados de imóveis rurais no Cadastro Ambiental Rural (SICAR) e de áreas de preservação permanente sofrem retificações periódicas por parte dos proprietários e órgãos ambientais.

### Decisão adotada na Entrega 1

1. **Recorte único consolidado:** a base carrega um recorte estático oficial do SICAR e do IBRAM para o Distrito Federal.
2. **Rastreabilidade por data de extração:** as tabelas `imovel_car`, `reserva_legal`, `area_preservacao_permanente` e `unidade_conservacao` contêm a coluna obrigatória `data_download`, registrando o momento exato em que a geometria foi capturada da fonte oficial.
3. **Escopo analítico da consulta:** as consultas da E1 respondem se o foco de calor atingiu o perímetro do imóvel ou área protegida conforme a delimitação territorial vigente no snapshot baixado.

## 4. Evolução Futura: Versionamento com SCD Tipo 2

A Entrega 1 não implementa tabelas de dimensão de variação lenta (SCD Tipo 2) para preservar a simplicidade e a estabilidade da carga transacional. Caso análises de entregas futuras demandem saber se a área estava formalmente averbada como reserva legal na data exata da detecção, a modelagem prevê a seguinte expansão:

- Adição de colunas temporais de vigência nas tabelas cadastrais:
```text
cod_imovel + vigencia_inicio + vigencia_fim + geom
```
- Cada retificação cadastral recebida da fonte pública encerrará a vigência do registro anterior (`vigencia_fim = data_retificacao`) e inserirá uma nova linha com o novo polígono.
- A consulta temporal fará o cruzamento semiaberto entre a detecção e o período de vigência:
```sql
f.data_hora_evento::date >= r.vigencia_inicio
AND (r.vigencia_fim IS NULL OR f.data_hora_evento::date < r.vigencia_fim)
AND ST_Intersects(f.geom, r.geom)
```

## 5. Resumo da Capacidade Analítica Atual

| Tabela | Padrão temporal | O que o banco garante | O que a consulta responde |
| :--- | :--- | :--- | :--- |
| `foco_calor` | Imutável (*insert-only*) | Histórico preservado sem sobrescrita; distinção entre evento e ingestão. | Focos reais detectados no intervalo de 2015 a 2025. |
| `imovel_car` | *Snapshot* com `data_download` | Delimitação territorial cadastrada com data de extração auditável. | Localização do foco dentro do perímetro registrado do imóvel. |
| `reserva_legal` | *Snapshot* com `data_download` | Geometria da reserva associada ao imóvel na data de extração. | Ocorrência de fogo dentro da reserva legal do snapshot oficial. |
| `area_preservacao_permanente` | *Snapshot* com `data_download` | Mapeamento territorial de preservação permanente no DF. | Fogo em área protegida conforme a base distrital do IBRAM. |
| `unidade_conservacao` | *Snapshot* com `data_download` | Perímetro oficial das UCs distritais e federais no DF. | Fogo na faixa de amortecimento de 1.000 m do limite protegido. |
