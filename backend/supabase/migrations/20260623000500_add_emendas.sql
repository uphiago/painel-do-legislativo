-- Migration: emendas parlamentares do Portal da Transparencia
CREATE TABLE IF NOT EXISTS emendas (
    id BIGSERIAL PRIMARY KEY,
    codigo_emenda TEXT NOT NULL,
    ano INTEGER,
    numero TEXT,
    tipo TEXT,
    autor TEXT,
    valor DOUBLE PRECISION DEFAULT 0,
    objeto TEXT,
    uf TEXT,
    orgao_concedente TEXT,
    data_publicacao TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(codigo_emenda)
);
CREATE INDEX IF NOT EXISTS idx_emendas_ano ON emendas(ano);
CREATE INDEX IF NOT EXISTS idx_emendas_uf ON emendas(uf);

ALTER TABLE emendas ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_select ON emendas;
CREATE POLICY public_select ON emendas FOR SELECT USING (true);
REVOKE ALL ON TABLE emendas FROM anon, authenticated;
GRANT SELECT ON TABLE emendas TO anon, authenticated;
