-- Hardening consistente para discursos (criada apos o harden_readonly original)
-- e para qualquer tabela futura no schema public.
--
-- A tabela discursos ja estava protegida por RLS (politica apenas SELECT), mas
-- nao tinha o REVOKE ALL / GRANT SELECT em nivel de privilegio como as demais.
-- Esta migration aplica o mesmo padrao "nuclear" a TODAS as tabelas de public,
-- garantindo que anon/authenticated so possam ler.

DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('REVOKE ALL ON TABLE %I FROM anon, authenticated', tbl);
        EXECUTE format('GRANT SELECT ON TABLE %I TO anon, authenticated', tbl);
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format('DROP POLICY IF EXISTS public_select ON %I', tbl);
        EXECUTE format('CREATE POLICY public_select ON %I FOR SELECT USING (true)', tbl);
    END LOOP;
END $$;
