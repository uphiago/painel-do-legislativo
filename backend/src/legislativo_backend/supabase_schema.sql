-- Supabase SQL Schema for Painel do Legislativo
-- Estado REAL pos-migrations (colunas em portugues, apos align_column_names + fix_expense_columns).
-- Este arquivo e a referencia "create from scratch", nao uma migration.
-- Ultima atualizacao: 2026-06-23.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Sync runs log (rastreabilidade de execucoes do pipeline)
CREATE TABLE IF NOT EXISTS sync_runs (
  id BIGSERIAL PRIMARY KEY,
  job TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  records_count INTEGER NOT NULL DEFAULT 0,
  metadata_json JSONB NOT NULL DEFAULT '{}'
);

-- Raw API payloads (copia fiel da resposta original de cada endpoint)
CREATE TABLE IF NOT EXISTS raw_payloads (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  kind TEXT NOT NULL,
  external_id TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}',
  collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, kind, external_id)
);

-- Parliamentarians (deputies and senators, unified)
CREATE TABLE IF NOT EXISTS parlamentarians (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  nome TEXT NOT NULL,
  casa TEXT NOT NULL,
  partido TEXT,
  uf TEXT,
  email TEXT,
  foto_url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Propositions (bills, amendments, resolutions)
CREATE TABLE IF NOT EXISTS propositions (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  casa TEXT NOT NULL,
  sigla TEXT,
  numero TEXT,
  ano INTEGER,
  ementa TEXT,
  data_apresentacao TEXT,
  autor_principal BOOLEAN,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Expenses (CEAP - Cota para Exercicio da Atividade Parlamentar)
CREATE TABLE IF NOT EXISTS expenses (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  parlamentar_external_id TEXT,
  parlamentar_nome TEXT,
  ano INTEGER,
  mes INTEGER,
  categoria TEXT,
  fornecedor TEXT,
  documento TEXT,
  data TEXT,
  valor DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Political parties
CREATE TABLE IF NOT EXISTS parties (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'camara',
  external_id TEXT NOT NULL,
  sigla TEXT NOT NULL,
  nome TEXT,
  logo_url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Legislatures (congressional terms)
CREATE TABLE IF NOT EXISTS legislatures (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'camara',
  external_id TEXT NOT NULL,
  numero INTEGER,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Organs (commissions, committees, boards)
CREATE TABLE IF NOT EXISTS organs (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  sigla TEXT,
  nome TEXT,
  tipo TEXT,
  casa TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);

-- Parliamentarian mandates (links parliamentarians to legislatures)
CREATE TABLE IF NOT EXISTS parliamentarian_mandates (
  id BIGSERIAL PRIMARY KEY,
  parlamentar_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  legislature_id TEXT,
  party_sigla TEXT,
  uf TEXT,
  status TEXT,
  condition TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(parlamentar_external_id, source, legislature_id)
);

-- Organ memberships (parliamentarians in commissions)
CREATE TABLE IF NOT EXISTS organ_memberships (
  id BIGSERIAL PRIMARY KEY,
  parlamentar_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  organ_external_id TEXT NOT NULL,
  role TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(parlamentar_external_id, source, organ_external_id, data_inicio)
);

-- Parliamentary fronts (thematic caucuses)
CREATE TABLE IF NOT EXISTS parliamentary_fronts (
  id BIGSERIAL PRIMARY KEY,
  external_id TEXT NOT NULL UNIQUE,
  titulo TEXT,
  legislature_id INTEGER,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Front memberships
CREATE TABLE IF NOT EXISTS front_memberships (
  id BIGSERIAL PRIMARY KEY,
  front_external_id TEXT NOT NULL,
  parlamentar_external_id TEXT NOT NULL,
  legislature_id INTEGER,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(front_external_id, parlamentar_external_id)
);

-- Proposition types reference (544 types)
CREATE TABLE IF NOT EXISTS proposition_types (
  id BIGSERIAL PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  sigla TEXT,
  nome TEXT,
  descricao TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Proposition authors (many-to-many)
CREATE TABLE IF NOT EXISTS proposition_authors (
  id BIGSERIAL PRIMARY KEY,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  parlamentar_external_id TEXT,
  author_name TEXT,
  author_type TEXT,
  signature_order INTEGER,
  proponent BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(proposition_source, proposition_external_id, author_name, signature_order)
);

-- Proposition themes
CREATE TABLE IF NOT EXISTS proposition_themes (
  id BIGSERIAL PRIMARY KEY,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  theme_code TEXT,
  theme_name TEXT,
  relevance DOUBLE PRECISION DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(proposition_source, proposition_external_id, theme_code)
);

-- Proposition tracking history
CREATE TABLE IF NOT EXISTS proposition_trackings (
  id BIGSERIAL PRIMARY KEY,
  proposition_source TEXT NOT NULL,
  proposition_external_id TEXT NOT NULL,
  sequencia INTEGER,
  data_hora TEXT,
  orgao_sigla TEXT,
  orgao_id TEXT,
  descricao_tramitacao TEXT,
  codigo_tipo_tramitacao TEXT,
  descricao_situacao TEXT,
  codigo_situacao INTEGER,
  despacho TEXT,
  url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(proposition_source, proposition_external_id, sequencia)
);

-- Votacoes (voting sessions)
CREATE TABLE IF NOT EXISTS votacoes (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  proposicao_external_id TEXT,
  sigla_orgao TEXT,
  descricao TEXT,
  data TEXT,
  aprovada BOOLEAN,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_votacoes_proposicao ON votacoes(proposicao_external_id);
CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data);

-- Votos (individual parliamentarian votes)
CREATE TABLE IF NOT EXISTS votos (
  id BIGSERIAL PRIMARY KEY,
  votacao_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  parlamentar_external_id TEXT NOT NULL,
  parlamentar_nome TEXT,
  voto TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(votacao_external_id, source, parlamentar_external_id)
);
CREATE INDEX IF NOT EXISTS idx_votos_parlamentar ON votos(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_votos_votacao ON votos(votacao_external_id);

-- Senator speeches
CREATE TABLE IF NOT EXISTS discursos (
  id BIGSERIAL PRIMARY KEY,
  senador_codigo TEXT NOT NULL,
  senador_nome TEXT,
  data_discurso TEXT,
  casa TEXT DEFAULT 'senado',
  tipo TEXT,
  resumo TEXT,
  texto_url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(senador_codigo, data_discurso)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_parlamentarians_casa ON parlamentarians(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_casa ON propositions(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_ano ON propositions(ano);
CREATE INDEX IF NOT EXISTS idx_propositions_sigla ON propositions(sigla);
CREATE INDEX IF NOT EXISTS idx_propositions_sigla_ano ON propositions(sigla, ano);
CREATE INDEX IF NOT EXISTS idx_expenses_parlamentar ON expenses(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_expenses_ano_mes ON expenses(ano, mes);
CREATE INDEX IF NOT EXISTS idx_expenses_categoria ON expenses(categoria);
CREATE INDEX IF NOT EXISTS idx_expenses_parlamentar_valor ON expenses(parlamentar_external_id) INCLUDE (valor);
CREATE INDEX IF NOT EXISTS idx_organ_memberships_parlamentar ON organ_memberships(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_organ_memberships_source ON organ_memberships(source);
CREATE INDEX IF NOT EXISTS idx_proposition_authors_proposition ON proposition_authors(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_authors_parlamentar ON proposition_authors(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_themes_proposition ON proposition_themes(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_themes_name ON proposition_themes(theme_name);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_proposition ON proposition_trackings(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_prop_seq ON proposition_trackings(proposition_external_id, sequencia DESC);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_situacao ON proposition_trackings(descricao_situacao);
CREATE INDEX IF NOT EXISTS idx_mandates_parlamentar ON parliamentarian_mandates(parliamentarian_external_id);
CREATE INDEX IF NOT EXISTS idx_discursos_senador ON discursos(senador_codigo);
CREATE INDEX IF NOT EXISTS idx_discursos_data ON discursos(data_discurso);
CREATE INDEX IF NOT EXISTS idx_front_memberships_parlamentar ON front_memberships(parlamentar_external_id);

-- =============================================================================
-- MATERIALIZED VIEWS (eliminam N+1 queries do frontend)
-- =============================================================================

-- KPIs por parlamentar (proposicoes, orgaos, frentes, despesas)
CREATE MATERIALIZED VIEW IF NOT EXISTS parlamentar_kpis AS
SELECT
    p.external_id,
    p.nome,
    p.casa,
    p.partido,
    p.uf,
    COALESCE(pa.total_autorias, 0)       AS total_autorias,
    COALESCE(pa.autoria_principal, 0)    AS autoria_principal,
    COALESCE(om.total_orgaos, 0)         AS total_orgaos,
    COALESCE(fm.total_frentes, 0)        AS total_frentes,
    COALESCE(ex.total_despesa, 0)        AS despesa_total,
    COALESCE(ex.qtde_despesas, 0)        AS qtde_despesas
FROM parlamentarians p
LEFT JOIN (
    SELECT
        parliamentarian_external_id,
        COUNT(*)                                         AS total_autorias,
        COUNT(*) FILTER (WHERE proponent = TRUE)         AS autoria_principal
    FROM proposition_authors
    WHERE parliamentarian_external_id IS NOT NULL
    GROUP BY parliamentarian_external_id
) pa ON pa.parliamentarian_external_id = p.external_id
LEFT JOIN (
    SELECT
        parliamentarian_external_id,
        COUNT(DISTINCT organ_external_id) AS total_orgaos
    FROM organ_memberships
    GROUP BY parliamentarian_external_id
) om ON om.parliamentarian_external_id = p.external_id
LEFT JOIN (
    SELECT
        parliamentarian_external_id,
        COUNT(DISTINCT front_external_id) AS total_frentes
    FROM front_memberships
    GROUP BY parliamentarian_external_id
) fm ON fm.parliamentarian_external_id = p.external_id
LEFT JOIN (
    SELECT
        parlamentar_external_id,
        COALESCE(SUM(valor), 0)          AS total_despesa,
        COUNT(*)                         AS qtde_despesas
    FROM expenses
    WHERE parlamentar_external_id IS NOT NULL
    GROUP BY parlamentar_external_id
) ex ON ex.parlamentar_external_id = p.external_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_parlamentar_kpis_id ON parlamentar_kpis(external_id);

-- Despesas agregadas por categoria (grafico do dashboard)
CREATE MATERIALIZED VIEW IF NOT EXISTS despesas_por_categoria AS
SELECT
    categoria,
    SUM(valor)   AS total,
    COUNT(*)     AS qtde
FROM expenses
WHERE categoria IS NOT NULL
  AND categoria != 'Test'
  AND categoria != ''
GROUP BY categoria
ORDER BY total DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_despesas_categoria_cat ON despesas_por_categoria(categoria);

-- Ultimo status de tramitacao por proposicao
CREATE MATERIALIZED VIEW IF NOT EXISTS proposition_ultimo_status AS
SELECT DISTINCT ON (proposition_external_id)
    proposition_external_id,
    descricao_situacao,
    orgao_sigla,
    despacho,
    sequencia,
    data_hora
FROM proposition_trackings
ORDER BY proposition_external_id, sequencia DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_ultimo_status_prop ON proposition_ultimo_status(proposition_external_id);

-- =============================================================================
-- RLS: SELECT-only para anon/authenticated em TODAS as tabelas public
-- =============================================================================

DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format('DROP POLICY IF EXISTS public_select ON %I', tbl);
        EXECUTE format('CREATE POLICY public_select ON %I FOR SELECT USING (true)', tbl);
        EXECUTE format('REVOKE ALL ON TABLE %I FROM anon, authenticated', tbl);
        EXECUTE format('GRANT SELECT ON TABLE %I TO anon, authenticated', tbl);
    END LOOP;
END $$;
