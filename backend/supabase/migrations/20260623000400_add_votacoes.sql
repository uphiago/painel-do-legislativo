-- Migration: tabelas de votacoes e votos
-- Suporta Camara e Senado

CREATE TABLE IF NOT EXISTS votacoes (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,            -- 'camara' ou 'senado'
    external_id TEXT NOT NULL,       -- ID da votacao na API
    proposicao_external_id TEXT,     -- ID da proposicao relacionada
    sigla_orgao TEXT,                -- PLEN, CCJC...
    descricao TEXT,                  -- Texto da votacao
    data TEXT,                       -- Data da sessao
    aprovada BOOLEAN,                -- Resultado
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_votacoes_proposicao ON votacoes(proposicao_external_id);
CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data);

CREATE TABLE IF NOT EXISTS votos (
    id BIGSERIAL PRIMARY KEY,
    votacao_external_id TEXT NOT NULL,
    source TEXT NOT NULL,
    parlamentar_external_id TEXT NOT NULL,
    parlamentar_nome TEXT,
    voto TEXT NOT NULL,              -- 'Sim', 'Não', 'Abstenção', 'Obstrução', 'Ausente'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(votacao_external_id, source, parlamentar_external_id)
);

CREATE INDEX IF NOT EXISTS idx_votos_parlamentar ON votos(parlamentar_external_id);
CREATE INDEX IF NOT EXISTS idx_votos_votacao ON votos(votacao_external_id);

-- RLS SELECT-only
ALTER TABLE votacoes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_select ON votacoes;
CREATE POLICY public_select ON votacoes FOR SELECT USING (true);
REVOKE ALL ON TABLE votacoes FROM anon, authenticated;
GRANT SELECT ON TABLE votacoes TO anon, authenticated;

ALTER TABLE votos ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_select ON votos;
CREATE POLICY public_select ON votos FOR SELECT USING (true);
REVOKE ALL ON TABLE votos FROM anon, authenticated;
GRANT SELECT ON TABLE votos TO anon, authenticated;
