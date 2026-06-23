-- =============================================================================
-- Migration 20260623000100: raw_payloads + indexes + materialized views
-- =============================================================================
-- 1. Cria tabela raw_payloads (rastreabilidade de payloads brutos da API)
-- 2. Adiciona UNIQUE constraint em discursos
-- 3. Cria indexes faltantes para queries do dashboard
-- 4. Cria materialized views para eliminar N+1 queries do frontend
-- =============================================================================

-- 1. raw_payloads ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_payloads (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    external_id TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}',
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source, kind, external_id)
);

ALTER TABLE raw_payloads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_select" ON raw_payloads FOR SELECT USING (true);

REVOKE ALL ON TABLE raw_payloads FROM anon, authenticated;
GRANT SELECT ON TABLE raw_payloads TO anon, authenticated;


-- 2. discursos UNIQUE constraint ------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'discursos_senador_codigo_data_discurso_key'
          AND conrelid = 'discursos'::regclass
    ) THEN
        ALTER TABLE discursos
            ADD CONSTRAINT discursos_senador_codigo_data_discurso_key
            UNIQUE (senador_codigo, data_discurso);
    END IF;
END $$;


-- 3. Missing indexes -------------------------------------------------------

-- proposition_authors.parliamentarian_external_id
-- Usado pelo dashboard para contar proposicoes por parlamentar (head-count).
CREATE INDEX IF NOT EXISTS idx_proposition_authors_parlamentarian
    ON proposition_authors(parliamentarian_external_id);

-- proposition_trackings para busca do ultimo status (ordenado por sequencia DESC)
CREATE INDEX IF NOT EXISTS idx_proposition_trackings_prop_seq
    ON proposition_trackings(proposition_external_id, sequencia DESC);

-- expenses.categoria para agregacoes por categoria
CREATE INDEX IF NOT EXISTS idx_expenses_categoria
    ON expenses(categoria);

-- expenses para busca por parlamentar com valor (dashboard KPIs)
CREATE INDEX IF NOT EXISTS idx_expenses_parlamentar_valor
    ON expenses(parlamentar_external_id) INCLUDE (valor);

-- propositions para busca por sigla + ano (filtros comuns)
CREATE INDEX IF NOT EXISTS idx_propositions_sigla_ano
    ON propositions(sigla, ano);

-- organ_memberships.source para filtro combinado
CREATE INDEX IF NOT EXISTS idx_organ_memberships_source
    ON organ_memberships(source);

-- proposition_themes.theme_name para agrupamento
CREATE INDEX IF NOT EXISTS idx_proposition_themes_name
    ON proposition_themes(theme_name);

-- front_memberships.parliamentarian_external_id para contagem por parlamentar
CREATE INDEX IF NOT EXISTS idx_front_memberships_parlamentarian
    ON front_memberships(parliamentarian_external_id);


-- 4. Materialized views ----------------------------------------------------
-- Eliminam centenas de chamadas N+1 do frontend para o dashboard.
-- Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY <nome>;

-- 4a. Contagens por parlamentar (proposicoes, orgaos, frentes, despesa total)
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


-- 4b. Despesas agregadas por categoria (top 20 para o grafico)
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


-- 4c. Ultimos status de tramitacao por proposicao
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


-- Todas as views com RLS SELECT-only (padrao do projeto)
ALTER MATERIALIZED VIEW parlamentar_kpis OWNER TO authenticated;
ALTER MATERIALIZED VIEW despesas_por_categoria OWNER TO authenticated;
ALTER MATERIALIZED VIEW proposition_ultimo_status OWNER TO authenticated;
