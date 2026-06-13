-- Supabase SQL Schema for Painel do Legislativo
-- This mirrors the SQLite schema but uses PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sync runs log
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

-- Parliamentarians (deputies and senators)
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

-- Propositions (bills, amendments, etc.)
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
  parliamentarian_external_id TEXT,
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
  parliamentarian_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  legislature_id TEXT,
  party_sigla TEXT,
  uf TEXT,
  status TEXT,
  condition TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(parliamentarian_external_id, source, legislature_id)
);

-- Organ memberships (parliamentarians in commissions)
CREATE TABLE IF NOT EXISTS organ_memberships (
  id BIGSERIAL PRIMARY KEY,
  parliamentarian_external_id TEXT NOT NULL,
  source TEXT NOT NULL,
  organ_external_id TEXT NOT NULL,
  role TEXT,
  data_inicio TEXT,
  data_fim TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(parliamentarian_external_id, source, organ_external_id, data_inicio)
);

-- Parliamentary fronts
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
  parliamentarian_external_id TEXT NOT NULL,
  legislature_id INTEGER,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(front_external_id, parliamentarian_external_id)
);

-- Proposition types reference
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
  parliamentarian_external_id TEXT,
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_parlamentarians_house ON parlamentarians(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_house ON propositions(casa);
CREATE INDEX IF NOT EXISTS idx_propositions_year ON propositions(ano);
CREATE INDEX IF NOT EXISTS idx_propositions_sigla ON propositions(sigla);
CREATE INDEX IF NOT EXISTS idx_expenses_parliamentarian ON expenses(parliamentarian_external_id);
CREATE INDEX IF NOT EXISTS idx_expenses_year_month ON expenses(ano, mes);
CREATE INDEX IF NOT EXISTS idx_organ_memberships_parlamentarian ON organ_memberships(parliamentarian_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_authors_proposition ON proposition_authors(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_themes_proposition ON proposition_themes(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_proposition ON proposition_trackings(proposition_external_id);
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_situacao ON proposition_trackings(descricao_situacao);
CREATE INDEX IF NOT EXISTS idx_mandates_parliamentarian ON parliamentarian_mandates(parliamentarian_external_id);
