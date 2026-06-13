# Modelo de Dados - Painel do Legislativo

## Visao Geral

O modelo de dados unifica informacoes da **Camara dos Deputados** e do **Senado Federal**
em um conjunto de tabelas normalizadas. Os dados sao coletados pelas APIs oficiais
(`dadosabertos.camara.leg.br` e `legis.senado.leg.br/dadosabertos`), normalizados
para um schema comum, e persistidos no SQLite (dev) e Supabase (prod).

## Entidades Principais

### 1. Parlamentares (`parlamentarians`)

Unifica deputados e senadores.

| Coluna | Tipo | Origem Camara | Origem Senado |
|--------|------|---------------|---------------|
| `source` | text | `"camara"` | `"senado"` |
| `external_id` | text | `deputado.id` | `IdentificacaoParlamentar.CodigoParlamentar` |
| `name` | text | `nome` | `NomeParlamentar` |
| `house` | text | `"camara"` | `"senado"` |
| `party` | text | `siglaPartido` | `SiglaPartidoParlamentar` |
| `uf` | text | `siglaUf` | `UfParlamentar` |
| `email` | text | `email` | `EmailParlamentar` |
| `photo_url` | text | `urlFoto` | `UrlFotoParlamentar` |

### 2. Partidos (`parties`)

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `external_id` | text | ID do partido na Camara |
| `sigla` | text | Sigla (MDB, PL, PT...) |
| `nome` | text | Nome completo |
| `logo_url` | text | URL da logo |

### 3. Legislaturas (`legislatures`)

Periodos de trabalho da Camara (4 anos desde 1988).

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `external_id` | text | Numero da legislatura |
| `numero` | int | 57 = atual (2023-2027) |
| `data_inicio` | text | Inicio do periodo |
| `data_fim` | text | Fim do periodo |

### 4. Orgaos (`organs`)

Comissoes, Mesas, Conselhos e demais orgaos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `source` | text | `"camara"` ou `"senado"` |
| `external_id` | text | ID do orgao |
| `sigla` | text | Sigla (CCJC, CMADS, PLEN...) |
| `nome` | text | Nome completo |
| `tipo` | text | Tipo (Permanente, Temporaria, CPI...) |
| `casa` | text | `"camara"`, `"senado"` ou `"congresso"` |

### 5. Mandatos (`parliamentarian_mandates`)

Vincula parlamentar a uma legislatura com partido e UF.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `parliamentarian_external_id` | text | ID do parlamentar |
| `source` | text | `"camara"` ou `"senado"` |
| `legislature_id` | text | Legislatura |
| `party_sigla` | text | Partido no periodo |
| `uf` | text | UF no periodo |
| `status` | text | "Exercicio", "Licenca"... |
| `condition` | text | "Titular", "Suplente" |

### 6. Membros de Orgaos (`organ_memberships`)

Parlamentares em comissoes e outros orgaos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `parliamentarian_external_id` | text | ID do parlamentar |
| `organ_external_id` | text | ID do orgao |
| `role` | text | "Titular", "Suplente", "Presidente" |
| `data_inicio` | text | Inicio da participacao |
| `data_fim` | text | Fim da participacao (null = atual) |

### 7. Frentes Parlamentares (`parliamentary_fronts`)

Grupos de parlamentares em torno de temas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `external_id` | text | ID da frente |
| `titulo` | text | Nome da frente |
| `legislature_id` | int | Legislatura de criacao |

### 8. Proposicoes (`propositions`)

Todas as proposicoes legislativas (PL, PEC, PLP, etc.).

| Coluna | Tipo | Origem Camara | Origem Senado |
|--------|------|---------------|---------------|
| `source` | text | `"camara"` | `"senado_processo"` |
| `external_id` | text | `proposicao.id` | `processo.id` |
| `house` | text | `"camara"` | `"senado"` |
| `type_sigla` | text | `siglaTipo` (PL, PEC...) | `sigla` (RQS, PLS...) |
| `numero` | text | `numero` | `numero` |
| `ano` | int | `ano` | `ano` |
| `ementa` | text | `ementa` | `ementa` |
| `data_apresentacao` | text | `dataApresentacao` | `dataApresentacao` |
| `status_descricao` | text | `statusProposicao.descricaoSituacao` | via tramitacao |
| `status_situacao_code` | int | `statusProposicao.codSituacao` | via tramitacao |
| `status_orgao_sigla` | text | `statusProposicao.siglaOrgao` | via tramitacao |
| `tipo_apreciacao` | text | `statusProposicao.apreciacao` | - |
| `keywords` | text | `keywords` | `indexacao` |
| `url_inteiro_teor` | text | `urlInteiroTeor` | - |

### 9. Tipos de Proposicao (`proposition_types`)

Tabela de referencia com todos os tipos (544 na Camara).

| Codigo | Sigla | Nome |
|--------|-------|------|
| 139 | PL | Projeto de Lei |
| 136 | PEC | Proposta de Emenda a Constituicao |
| 140 | PLP | Projeto de Lei Complementar |
| 135 | PDC | Projeto de Decreto Legislativo |
| 141 | PRC | Projeto de Resolucao |
| 147 | REQ | Requerimento |

### 10. Autores (`proposition_authors`)

Liga proposicoes a seus autores (parlamentares ou outros).

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `proposition_source` | text | `"camara"` ou `"senado_processo"` |
| `proposition_external_id` | text | ID da proposicao |
| `parliamentarian_external_id` | text | ID do autor (se for parlamentar) |
| `author_name` | text | Nome do autor |
| `author_type` | text | "Deputado(a)", "Comissao"... |
| `signature_order` | int | Ordem de assinatura (1 = primeiro) |
| `proponent` | bool | Se e proponente (true) ou apoiador |

### 11. Temas (`proposition_themes`)

Areas tematicas associadas as proposicoes.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `proposition_external_id` | text | ID da proposicao |
| `theme_code` | text | Codigo do tema |
| `theme_name` | text | Nome (Direito Civil, Saude, Educacao...) |
| `relevance` | real | Relevancia (0 = secundario) |

### 12. Tramitacoes (`proposition_trackings`)

Historico completo de tramitacao de cada proposicao.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `proposition_external_id` | text | ID da proposicao |
| `sequencia` | int | Ordem na tramitacao |
| `data_hora` | text | Data e hora do evento |
| `orgao_sigla` | text | Orgao responsavel (MESA, CCJC, PLEN...) |
| `descricao_tramitacao` | text | "Apresentacao de Proposicao" |
| `descricao_situacao` | text | Situacao resultante |
| `codigo_situacao` | int | Codigo da situacao |
| `despacho` | text | Texto completo do despacho |
| `url` | text | Link para o ato publicado |

### 13. Despesas (`expenses`)

CEAP (Cota para Exercicio da Atividade Parlamentar).

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `source` | text | `"camara_ceap"`, `"senado_ceaps"` |
| `parliamentarian_external_id` | text | ID do parlamentar |
| `ano` | int | Ano |
| `mes` | int | Mes |
| `category` | text | Categoria (Passagens, Divulgacao...) |
| `supplier` | text | Fornecedor |
| `value` | real | Valor liquido |
| `receipt_url` | text | URL do comprovante (Camara) |

## Relacionamentos

```
PARTIDO 1---N PARLAMENTAR (via mandatos)
LEGISLATURA 1---N PARLAMENTAR (via mandatos)
ORGAO N---N PARLAMENTAR (via organ_memberships)
FRENTE N---N PARLAMENTAR (via front_memberships)
PARLAMENTAR 1---N PROPOSICAO (via autores, proponente)
PROPOSICAO N---N TEMA (via proposition_themes)
PROPOSICAO 1---N TRAMITACAO (via proposition_trackings)
PARLAMENTAR 1---N DESPESA
```

## Fontes

### Camara dos Deputados
- **API Base:** `https://dadosabertos.camara.leg.br/api/v2`
- **Rate Limit:** ~15 req/min (4s intervalo)
- **Docs:** https://dadosabertos.camara.leg.br/swagger/api.html
- **Download:** http://dadosabertos.camara.leg.br/arquivos/

### Senado Federal
- **API Base:** `https://legis.senado.leg.br/dadosabertos`
- **Rate Limit:** 10 req/s (0.5s buffer)
- **Docs:** https://legis.senado.leg.br/dadosabertos/docs/
- **ADM API (CEAP):** `https://adm.senado.gov.br/adm-dadosabertos/api/v1`
- **Nota:** Endpoint `/senador/{codigo}/autorias` depreciado desde 2025-03-18.
  Substituir por `/processo?codigoParlamentarAutor={codigo}`.

## Pipeline de Coleta

```
1. collect reference data
   ├── tipos de proposicao (referencias/tiposProposicao)
   ├── legislaturas
   └── partidos

2. collect all parliamentarians
   ├── deputados (list_all_deputados)
   └── senadores (list_senadores_atual)

3. enrich each parliamentarian
   ├── perfil completo (detail, orgaos, frentes, mandato)
   ├── proposicoes como autor
   └── despesas CEAP

4. enrich each proposition
   ├── detalhe (status completo)
   ├── autores
   ├── temas
   └── tramitacoes (historico completo)

5. sync to Supabase (upsert)
```

O schema SQLite local (data/local/painel.db) espelha exatamente as tabelas do
Supabase, permitindo validacao antes da sincronia.
