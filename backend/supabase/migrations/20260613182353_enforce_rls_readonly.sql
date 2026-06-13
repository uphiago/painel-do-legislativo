-- Drop all existing policies and re-create with SELECT ONLY

DO $$ 
DECLARE
    r record;
BEGIN
    FOR r IN (SELECT policyname, tablename FROM pg_policies WHERE schemaname = 'public') LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', r.policyname, r.tablename);
    END LOOP;
END $$;

-- Ensure RLS is enabled on all tables
ALTER TABLE IF EXISTS parlamentarians ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS propositions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS legislatures ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS organs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS parliamentarian_mandates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS organ_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS parliamentary_fronts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS front_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS proposition_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS proposition_authors ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS proposition_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS proposition_trackings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sync_runs ENABLE ROW LEVEL SECURITY;

-- Public read-only access on all tables (anon + authenticated can SELECT only)
CREATE POLICY "public_select" ON parlamentarians FOR SELECT USING (true);
CREATE POLICY "public_select" ON propositions FOR SELECT USING (true);
CREATE POLICY "public_select" ON expenses FOR SELECT USING (true);
CREATE POLICY "public_select" ON parties FOR SELECT USING (true);
CREATE POLICY "public_select" ON legislatures FOR SELECT USING (true);
CREATE POLICY "public_select" ON organs FOR SELECT USING (true);
CREATE POLICY "public_select" ON parliamentarian_mandates FOR SELECT USING (true);
CREATE POLICY "public_select" ON organ_memberships FOR SELECT USING (true);
CREATE POLICY "public_select" ON parliamentary_fronts FOR SELECT USING (true);
CREATE POLICY "public_select" ON front_memberships FOR SELECT USING (true);
CREATE POLICY "public_select" ON proposition_types FOR SELECT USING (true);
CREATE POLICY "public_select" ON proposition_authors FOR SELECT USING (true);
CREATE POLICY "public_select" ON proposition_themes FOR SELECT USING (true);
CREATE POLICY "public_select" ON proposition_trackings FOR SELECT USING (true);
CREATE POLICY "public_select" ON sync_runs FOR SELECT USING (true);

-- Service role bypass (implicit - Supabase service_role always bypasses RLS)
-- No INSERT/UPDATE/DELETE policies = denied for anon/authenticated users
