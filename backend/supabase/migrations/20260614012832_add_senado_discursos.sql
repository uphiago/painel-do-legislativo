-- Table for senator speeches
CREATE TABLE IF NOT EXISTS discursos (
  id BIGSERIAL PRIMARY KEY,
  senador_codigo TEXT NOT NULL,
  senador_nome TEXT,
  data_discurso TEXT,
  casa TEXT DEFAULT 'senado',
  tipo TEXT,
  resumo TEXT,
  texto_url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discursos_senador ON discursos(senador_codigo);
CREATE INDEX IF NOT EXISTS idx_discursos_data ON discursos(data_discurso);

ALTER TABLE discursos ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'public_select' AND tablename = 'discursos') THEN
    CREATE POLICY "public_select" ON discursos FOR SELECT USING (true);
  END IF;
END $$;
