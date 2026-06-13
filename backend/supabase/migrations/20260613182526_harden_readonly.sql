-- REVOKE all write permissions from anon and authenticated roles
-- This is the nuclear option - no INSERT/UPDATE/DELETE regardless of RLS

DO $$ 
DECLARE
    tbl text;
BEGIN
    FOR tbl IN 
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('REVOKE ALL ON TABLE %I FROM anon, authenticated', tbl);
        EXECUTE format('GRANT SELECT ON TABLE %I TO anon, authenticated', tbl);
    END LOOP;
END $$;

-- Ensure RLS is enabled on every table
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
        -- Drop existing policies and recreate SELECT-only
        EXECUTE format('DROP POLICY IF EXISTS public_select ON %I', tbl);
        EXECUTE format('CREATE POLICY public_select ON %I FOR SELECT USING (true)', tbl);
    END LOOP;
END $$;
