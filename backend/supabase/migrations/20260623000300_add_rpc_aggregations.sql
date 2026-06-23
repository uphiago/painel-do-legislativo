-- =============================================================================
-- Migration 20260623000300: Funcoes RPC para agregacao server-side
-- =============================================================================
-- Substituem consultas que puxam milhares de linhas pro cliente
-- (despesas por categoria e temas por parlamentar)
-- =============================================================================

-- Despesas agregadas por categoria para UM parlamentar (top 8)
CREATE OR REPLACE FUNCTION parlamentar_despesas_categoria(
    parl_id text,
    max_results integer DEFAULT 8
)
RETURNS TABLE(
    categoria text,
    total numeric,
    percentual integer
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    WITH agg AS (
        SELECT
            e.categoria,
            SUM(e.valor) AS total
        FROM expenses e
        WHERE e.parlamentar_external_id = parl_id
          AND e.categoria IS NOT NULL
          AND e.categoria != ''
        GROUP BY e.categoria
    ),
    ranked AS (
        SELECT
            categoria,
            total,
            ROUND((total / NULLIF(SUM(total) OVER (), 0)) * 100)::integer AS percentual
        FROM agg
    )
    SELECT categoria, total::numeric, percentual
    FROM ranked
    ORDER BY total DESC
    LIMIT max_results;
$$;


-- Temas mais frequentes para as proposicoes de UM parlamentar
CREATE OR REPLACE FUNCTION parlamentar_temas_frequentes(
    parl_id text,
    max_results integer DEFAULT 8
)
RETURNS TABLE(
    theme_name text,
    qtde bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        pt.theme_name,
        COUNT(*) AS qtde
    FROM proposition_authors pa
    JOIN proposition_themes pt
        ON pt.proposition_external_id = pa.proposition_external_id
       AND pt.proposition_source = pa.proposition_source
    WHERE pa.parliamentarian_external_id = parl_id
      AND pt.theme_name IS NOT NULL
    GROUP BY pt.theme_name
    ORDER BY qtde DESC
    LIMIT max_results;
$$;
