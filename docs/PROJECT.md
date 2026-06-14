# Painel do Legislativo

> Documentação completa para consumo por IAs e desenvolvedores.
> Última atualização: Junho 2026

## Visão Geral

**Painel do Legislativo** é uma aplicação web que democratiza o acesso a informações legislativas brasileiras. Coleta dados oficiais da Câmara dos Deputados e Senado Federal via APIs públicas, normaliza, persiste no Supabase (PostgreSQL) e exibe em um dashboard Next.js com busca, comparação e exportação.

- **Objetivo:** Permitir que qualquer cidadão pesquise parlamentares, proposições e temas, entenda a tramitação e compare atuações.
- **Público:** Cidadãos, jornalistas, pesquisadores, gabinetes parlamentares.
- **Dados:** 594 parlamentares, 107k proposições (2025), 193k despesas CEAP, 154k autores, 40k temas, 1.626 órgãos.

---

## Arquitetura (3 camadas)

```
┌──────────────────────────────────────────────────────┐
│  Next.js 16 (Frontend)                                │
│  src/app/  src/data/  src/utils/supabase/             │
│  ↓ queries Supabase (publishable key, read-only)      │
├──────────────────────────────────────────────────────┤
│  Supabase (PostgreSQL + REST API)                     │
│  15 tabelas normalizadas, RLS SELECT-only público     │
│  ↑ escrita via service_role key                       │
├──────────────────────────────────────────────────────┤
│  Python CLI (Backend de coleta)                       │
│  legislativo pipeline → collectors → normalizers → DB │
│  Rate limiting: 4s/req (Câmara), 0.5s/req (Senado)   │
└──────────────────────────────────────────────────────┘
```

### Fluxo de dados

1. **Coleta:** Python CLI busca dados das APIs oficiais com rate limiting
2. **Normalização:** Pydantic models padronizam campos entre Câmara e Senado
3. **Persistência:** SQLite local (dev) + Supabase PostgreSQL (prod)
4. **Leitura:** Next.js consulta Supabase via REST API (publishable key)
5. **RLS:** Apenas SELECT público; INSERT/UPDATE/DELETE bloqueados

---

## Tech Stack

| Camada | Tecnologias |
|--------|------------|
| **Backend** | Python 3.12, Typer (CLI), httpx, Pydantic 2, tenacity, psycopg2-binary |
| **Banco** | SQLite (dev local), Supabase PostgreSQL (prod) |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Lucide Icons, jsPDF |
| **Infra** | Supabase CLI (migrations), uv (Python package manager), ruff (linter) |
| **Testes** | pytest (29 testes unitários backend) |

---

## Estrutura de Arquivos

```
painel-do-legislativo/
├── .gitignore
├── README.md
│
├── backend/                          # Python — pipeline de coleta
│   ├── pyproject.toml                # Dependências Python
│   ├── .env                          # Credenciais Supabase (gitignored)
│   ├── .env.example
│   ├── src/legislativo_backend/
│   │   ├── __init__.py
│   │   ├── cli.py                    # CLI principal (comando `legislativo`)
│   │   ├── db.py                     # SQLite schema + operações CRUD
│   │   ├── http.py                   # HTTP client com RateLimiter + retry
│   │   ├── normalizers.py            # Pydantic models de normalização
│   │   ├── pipeline.py               # Pipeline completo de coleta
│   │   ├── storage.py                # Snapshots raw JSON
│   │   ├── supabase_client.py        # Cliente Supabase (upsert com dedup)
│   │   ├── supabase_schema.sql       # Schema SQL para Supabase
│   │   └── collectors/
│   │       ├── camara.py             # Endpoints API Câmara dos Deputados
│   │       └── senado.py             # Endpoints API Senado Federal
│   ├── tests/                        # Testes pytest (29)
│   ├── docs/
│   │   ├── data-model.md             # Documentação do modelo de dados
│   │   └── source-inventory.md       # Inventário de fontes de dados
│   └── supabase/
│       └── migrations/               # Migrations SQL (5 arquivos)
│
├── next/                             # Frontend Next.js
│   ├── package.json
│   ├── .env.local                    # NEXT_PUBLIC_SUPABASE_* (gitignored)
│   ├── next.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout
│       │   ├── page.tsx              # Landing page (server component)
│       │   ├── globals.css           # Estilos globais (1745 linhas)
│       │   ├── dashboard/
│       │   │   └── page.tsx          # Dashboard principal (client component)
│       │   └── fontes/
│       │       └── page.tsx          # Fontes e metodologia
│       ├── data/
│       │   ├── mockLegislativo.ts    # Tipos + dados mock (fallback)
│       │   ├── supabase.ts           # Tipos TypeScript (14 interfaces)
│       │   ├── queries.ts            # Funções de query Supabase (15)
│       │   ├── liveData.ts           # Hook useLiveDashboard (dados reais)
│       │   ├── hooks.ts              # useRealData, useDashboardStats
│       │   ├── comparacao.ts         # useComparacao + downloadCSV
│       │   ├── pdfExport.ts          # Geração de PDF com jsPDF
│       │   └── toast.tsx             # Sistema de toast notifications
│       └── utils/supabase/
│           ├── server.ts             # Server client (@supabase/ssr)
│           └── client.ts             # Browser client (@supabase/ssr)
│
├── functions/                        # Cloudflare Pages Functions (legado)
├── index.html, app.js, styles.css    # SPA legada (produção atual)
└── data/                             # Dados locais (gitignored)
```

---

## Modelo de Dados

### Tabelas principais (15 no Supabase + SQLite)

```
parlamentarians          — 594 deputados + senadores (fonte: source, external_id)
propositions             — 107k+ proposições legislativas (PL, PEC, PLP, etc.)
expenses                 — 193k+ despesas CEAP (Cota Parlamentar)
proposition_authors      — 154k+ vínculos proposição ↔ autor
proposition_themes       — 40k+ temas por proposição
proposition_trackings    — Histórico de tramitação (sequencia, órgão, situação)
organs                   — 1.626 órgãos/comissões da Câmara
parties                  — 21 partidos políticos
legislatures             — 57 legislaturas históricas
proposition_types        — 544 tipos de proposição (PL, PEC, REQ...)
parliamentarian_mandates — Mandatos (parlamentar ↔ legislatura)
organ_memberships        — Participação em órgãos (titular/suplente)
parliamentary_fronts     — Frentes parlamentares
front_memberships        — Membros de frentes
discursos                — Discursos de senadores (em coleta)
sync_runs                — Log de execuções do pipeline
```

### Colunas chave (parlamentarians)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `source` | text | `"camara"` ou `"senado"` |
| `external_id` | text | ID na API de origem |
| `nome` | text | Nome parlamentar |
| `casa` | text | `"camara"` ou `"senado"` |
| `partido` | text | Sigla (MDB, PL, PT...) |
| `uf` | text | Estado (SP, RJ...) |
| `foto_url` | text | URL da foto oficial |

### Colunas chave (propositions)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `sigla` | text | PL, PEC, PLP, REQ... |
| `numero` | text | Número |
| `ano` | int | Ano de apresentação |
| `ementa` | text | Resumo/ementa |
| `casa` | text | `"camara"` ou `"senado"` |
| `data_apresentacao` | text | Data ISO |

### Relacionamentos

```
PARTIDO 1──N PARLAMENTAR (via mandatos)
LEGISLATURA 1──N PARLAMENTAR (via mandatos)
ORGAO N──N PARLAMENTAR (via organ_memberships)
FRENTE N──N PARLAMENTAR (via front_memberships)
PARLAMENTAR 1──N PROPOSICAO (via proposition_authors)
PROPOSICAO N──N TEMA (via proposition_themes)
PROPOSICAO 1──N TRAMITACAO (via proposition_trackings)
PARLAMENTAR 1──N DESPESA
```

---

## APIs de Origem

### Câmara dos Deputados (Dados Abertos)

- **Base URL:** `https://dadosabertos.camara.leg.br/api/v2`
- **Rate limit:** ~15 req/min (aplicamos 4s entre requests)
- **Endpoints usados:** deputados, deputados/{id}, proposicoes, orgaos, partidos, legislaturas, frentes, eventos, votacoes, referencias/tiposProposicao
- **Arquivos bulk:** `http://dadosabertos.camara.leg.br/arquivos/proposicoes/json/proposicoes-{ano}.json`
- **CEAP CSV:** `http://www.camara.leg.br/cotas/Ano-{ano}.csv.zip`

### Senado Federal (Dados Abertos)

- **Base URL:** `https://legis.senado.leg.br/dadosabertos`
- **ADM URL (CEAP):** `https://adm.senado.gov.br/adm-dadosabertos/api/v1`
- **Rate limit:** ~10 req/s (aplicamos 0.5s buffer)
- **Endpoints usados:** senador/lista/atual, senador/{codigo}, processo, comissao
- **IMPORTANTE:** `/senador/{codigo}/autorias` está **depreciado** (desde 2025-03-18). Usar `/processo?codigoParlamentarAutor={codigo}`.
- **IMPORTANTE:** `/relatorias` e `/liderancas` também depreciados. Substituir por `/composicao/`.

---

## Comandos CLI (Python Backend)

```bash
cd backend
uv sync                          # Instalar dependências
uv run legislativo --help        # Listar comandos

# Status
uv run legislativo status        # Visão completa do banco (cobertura, pendências)

# Schema
uv run legislativo supabase-schema  # Gerar SQL para Supabase

# Pipeline (comandos principais)
uv run legislativo pipeline reference              # 544 tipos, 57 legislaturas, 21 partidos, 1626 órgãos
uv run legislativo pipeline parlamentares           # 513 dep + 81 sen (≈30min com rate limit)
uv run legislativo pipeline bulk-year --anos "2025" # 107k props + 40k temas + 154k autores (≈30s)
uv run legislativo pipeline bulk-ceap --anos "2025" # 193k despesas (≈30s)
uv run legislativo pipeline full --supabase         # Pipeline completo orquestrado

# Enriquecimento individual
uv run legislativo pipeline deputado --deputado-id 204379
uv run legislativo pipeline senador --codigo 5995
uv run legislativo pipeline proposicao --proposicao-id 2626629
uv run legislativo pipeline enrich-props-incr --min-ano 2024

# Com --supabase sincroniza com o Supabase
uv run legislativo pipeline reference --supabase
```

### Migrations Supabase

```bash
cd backend
SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase link --project-ref xvccxrtrwgxcllofdzls
SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase db push
```

### Testes

```bash
cd backend
uv run pytest                    # 29 testes
uv run ruff check src/ tests/    # Lint
```

---

## Frontend (Next.js)

### Rotas

| Rota | Tipo | Descrição |
|------|------|-----------|
| `/` | Server Component | Landing page com stats, fotos, preview |
| `/dashboard` | Client Component | Dashboard interativo completo |
| `/fontes` | Server Component | Fontes e metodologia |

### Funcionalidades do Dashboard

- **Busca:** Nome do parlamentar, tema/palavra-chave, filtro por UF e Casa
- **Quick-pills:** Segurança pública, Saúde, Educação, Meio ambiente
- **Debounce:** 400ms na busca por tema (evita excesso de chamadas)
- **Resultados:** Exibidos no painel "Leitura do recorte" com contagem
- **Diretório:** Lista de parlamentares com foto real (fallback: iniciais)
- **Perfil:** Foto, partido, UF, mandato, KPIs (proposições, órgãos)
- **Tabs:** Resumo, Projetos, Participação, Transparência, Tramitação
- **Comparação:** Selecionar 2 parlamentares, tabela lado a lado
- **CSV:** Download da lista de parlamentares visível
- **PDF:** Relatório completo com perfil + proposições + despesas (jsPDF)
- **Link oficial:** Abre página do parlamentar na Câmara ou Senado
- **Skeletons:** Animação de loading enquanto carrega dados reais
- **Toast:** Feedback visual ao exportar CSV/PDF
- **Empty state:** Mensagem amigável quando filtro não acha resultados
- **Dados oficiais:** Badge verde quando conectado ao Supabase

### Como rodar

```bash
cd next
npm install
cp .env.local.example .env.local   # Configurar NEXT_PUBLIC_SUPABASE_*
npm run dev                         # http://localhost:3000
npm run build                       # Build de produção
```

### Variáveis de ambiente (next/.env.local)

```
NEXT_PUBLIC_SUPABASE_URL=https://xvccxrtrwgxcllofdzls.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

### Variáveis de ambiente (backend/.env)

```
SUPABASE_URL=https://xvccxrtrwgxcllofdzls.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_ACCESS_TOKEN=sbp_...
```

---

## Segurança (RLS)

Todas as 15 tabelas têm Row Level Security habilitado:

| Operação | Publishable Key (anon) | Service Role Key |
|----------|----------------------|------------------|
| SELECT   | ✅ Permitido          | ✅               |
| INSERT   | ❌ Bloqueado          | ✅               |
| UPDATE   | ❌ Bloqueado          | ✅               |
| DELETE   | ❌ Bloqueado          | ✅               |

Implementado via `REVOKE ALL ... FROM anon, authenticated; GRANT SELECT ... TO anon, authenticated;`

---

## Rate Limiting

O backend implementa limitadores por fonte:

- **Câmara:** 4 segundos entre requests (~15 requisições/minuto)
- **Senado:** 0.5 segundos entre requests (buffer generoso para 10 req/s)

Além disso, usa retry com backoff exponencial (até 3 tentativas) em caso de timeout ou erro de transporte.

---

## Normalizadores Pydantic

Modelos que padronizam dados das duas casas legislativas:

| Modelo | Campos | Uso |
|--------|--------|-----|
| `ParlamentarResumo` | source, external_id, nome, casa, partido, uf, email, foto_url | Deputados e senadores |
| `ProposicaoResumo` | source, external_id, casa, sigla, numero, ano, ementa, data_apresentacao | PL, PEC, etc. |
| `DespesaResumo` | source, external_id, parlamentar_external_id, parlamentar_nome, ano, mes, categoria, fornecedor, documento, data, valor | CEAP |

---

## Git (Repositório)

- **URL:** https://github.com/uphiago/painel-do-legislativo
- **Branch:** main
- **Commits recentes:**
  - `dd02e88` fix(landing): corrigir NaN no contador de parlamentares
  - `adf3d39` feat(ui): landing page com dados reais, fotos oficiais
  - `8e36500` feat(ux): skeletons, toast, debounce, hover, fade-in
  - `d5419a5` fix(frontend): mobile responsiveness
  - `273bc43` feat: PDF export + Senado discursos collection
  - `8497bfa` feat(frontend): busca funcional, comparação
  - `9d27b93` feat(frontend): CSV export, loading indicator
  - `18a66d9` feat(frontend): Next.js dashboard com Supabase live data
  - `e88adb8` feat(backend): pipeline de coleta, schema Supabase

---

## Fluxo de deploy

### 1. Schema no Supabase

```bash
cd backend
SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase link --project-ref xvccxrtrwgxcllofdzls
SUPABASE_ACCESS_TOKEN="sbp_..." npx supabase db push
```

### 2. Popular dados

```bash
cd backend
uv run legislativo pipeline reference --supabase
uv run legislativo pipeline parlamentares --supabase
uv run legislativo pipeline bulk-year --anos "2020,2021,2022,2023,2024,2025" --supabase
uv run legislativo pipeline bulk-ceap --anos "2020,2021,2022,2023,2024,2025" --supabase
```

### 3. Deploy frontend

```bash
cd next
npm run build
# Deploy na Vercel ou similar
```

---

## Pendências / Roadmap

| Item | Prioridade |
|------|-----------|
| Popular anos anteriores (2020-2024) no Supabase | Alta |
| Enriquecer proposições recentes com tramitação | Alta |
| Coletar votos (como cada parlamentar votou) | Média |
| Gráficos de evolução temporal no dashboard | Média |
| Autenticação (login para salvar favoritos) | Baixa |
| PWA / offline support | Baixa |

---

## Notas para IAs

- O projeto usa **Next.js 16 com Turbopack** — APIs e convenções podem diferir de versões anteriores.
- As **migrations Supabase** estão em `backend/supabase/migrations/` e devem ser aplicadas na ordem (timestamps nos nomes).
- O **schema SQLite** (dev) espelha o **schema Supabase** (prod). Mudanças de coluna devem ser sincronizadas nos dois.
- Os **normalizadores Pydantic** usam nomes de campo em português (ex: `casa`, `nome`, `partido`) que correspondem às colunas do banco.
- O **supabase_client.py** faz dedup automático baseado nas colunas de `on_conflict` antes do upsert.
- O frontend carrega **mock data** inicialmente como fallback e substitui por dados reais do Supabase quando a conexão é estabelecida.
