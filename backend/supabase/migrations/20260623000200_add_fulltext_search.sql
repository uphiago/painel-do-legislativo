-- =============================================================================
-- Migration 20260623000200: Full-text search em propositions + RLS refresh
-- =============================================================================
-- 1. Coluna tsvector gerada automaticamente para busca em portugues
-- 2. Indice GIN para queries rapidas
-- 3. Funcao PL/pgSQL para busca com ranking
-- 4. Refresh das materialized views no final (garante que existem)
-- =============================================================================

-- Coluna de busca gerada automaticamente a partir de ementa
ALTER TABLE propositions
    ADD COLUMN IF NOT EXISTS ementa_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('portuguese', COALESCE(ementa, ''))) STORED;

-- Indice GIN para full-text search
CREATE INDEX IF NOT EXISTS idx_propositions_ementa_tsv
    ON propositions USING GIN (ementa_tsv);


-- Funcao de busca com ranking (pode ser chamada via RPC do Supabase)
CREATE OR REPLACE FUNCTION search_proposicoes(
    search_term text,
    max_results integer DEFAULT 20
)
RETURNS TABLE(
    external_id text,
    sigla text,
    numero text,
    ano integer,
    ementa text,
    rank real
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        p.external_id,
        p.sigla,
        p.numero,
        p.ano,
        p.ementa,
        ts_rank(p.ementa_tsv, websearch_to_tsquery('portuguese', search_term)) AS rank
    FROM propositions p
    WHERE p.ementa_tsv @@ websearch_to_tsquery('portuguese', search_term)
    ORDER BY rank DESC, p.ano DESC
    LIMIT max_results;
$$;


-- Funcao auxiliar para o pipeline Python refrescar materialized views
-- (usada pelo supabase_client.refresh_materialized_views via RPC)
CREATE OR REPLACE FUNCTION refresh_view(view_name text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    EXECUTE 'REFRESH MATERIALIZED VIEW ' || quote_ident(view_name);
END $$;
