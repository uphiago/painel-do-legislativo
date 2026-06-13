import { createClient } from "@/utils/supabase/client";
import type {
  DashboardStats,
  Despesa,
  Organ,
  Parlamentar,
  PropositionAuthor,
  PropositionTheme,
  PropositionTracking,
  ProposicaoResumo,
} from "./supabase";

export async function getDashboardStats(): Promise<DashboardStats> {
  const supabase = createClient();

  const [parl, prop, exp, org] = await Promise.all([
    supabase.from("parlamentarians").select("*", { count: "exact", head: true }),
    supabase.from("propositions").select("*", { count: "exact", head: true }),
    supabase.from("expenses").select("*", { count: "exact", head: true }),
    supabase.from("organs").select("*", { count: "exact", head: true }),
  ]);

  return {
    total_parlamentarians: parl.count ?? 0,
    total_propositions: prop.count ?? 0,
    total_expenses: exp.count ?? 0,
    total_organs: org.count ?? 0,
  };
}

export async function getParlamentares(
  limit: number = 50,
  offset: number = 0,
): Promise<Parlamentar[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("parlamentarians")
    .select("*")
    .order("name")
    .range(offset, offset + limit - 1);
  return data ?? [];
}

export async function getParlamentarById(externalId: string): Promise<Parlamentar | null> {
  const supabase = createClient();
  const { data } = await supabase
    .from("parlamentarians")
    .select("*")
    .eq("external_id", externalId)
    .single();
  return data;
}

export async function getParlamentarStats(externalId: string) {
  const supabase = createClient();

  const [propCount, expSum, orgCount] = await Promise.all([
    supabase
      .from("proposition_authors")
      .select("*", { count: "exact", head: true })
      .eq("proposition_source", "camara")
      .eq("parliamentarian_external_id", externalId),

    supabase
      .from("expenses")
      .select("value")
      .eq("parliamentarian_external_id", externalId),

    supabase
      .from("organ_memberships")
      .select("*", { count: "exact", head: true })
      .eq("parliamentarian_external_id", externalId)
      .eq("source", "camara"),
  ]);

  return {
    proposition_count: propCount.count ?? 0,
    expense_total: expSum.data?.reduce((sum, e) => sum + e.value, 0) ?? 0,
    organs_count: orgCount.count ?? 0,
  };
}

export async function getProposicoes(
  limit: number = 50,
  offset: number = 0,
  sigla?: string,
): Promise<ProposicaoResumo[]> {
  const supabase = createClient();
  let query = supabase.from("propositions").select("*").order("ano", { ascending: false }).order("id", { ascending: false });

  if (sigla) {
    query = query.eq("sigla", sigla);
  }

  const { data } = await query.range(offset, offset + limit - 1);
  return data ?? [];
}

export async function getProposicaoById(externalId: string) {
  const supabase = createClient();
  const { data } = await supabase
    .from("propositions")
    .select("*")
    .eq("external_id", externalId)
    .single();
  return data;
}

export async function getProposicaoTrackings(externalId: string): Promise<PropositionTracking[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("proposition_trackings")
    .select("*")
    .eq("proposition_external_id", externalId)
    .order("sequencia", { ascending: false });
  return data ?? [];
}

export async function getProposicaoAutores(externalId: string): Promise<PropositionAuthor[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("proposition_authors")
    .select("*")
    .eq("proposition_external_id", externalId)
    .order("signature_order");
  return data ?? [];
}

export async function getProposicaoTemas(externalId: string): Promise<PropositionTheme[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("proposition_themes")
    .select("*")
    .eq("proposition_external_id", externalId);
  return data ?? [];
}

export async function getDespesasByParlamentar(
  externalId: string,
  limit: number = 20,
): Promise<Despesa[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("expenses")
    .select("*")
    .eq("parliamentarian_external_id", externalId)
    .order("value", { ascending: false })
    .limit(limit);
  return data ?? [];
}

export async function getDespesasSummary(externalId: string) {
  const supabase = createClient();
  const { data, error } = await supabase.rpc("get_expense_summary", {
    p_parliamentarian_id: externalId,
  });
  if (error) {
    const { data: rawData } = await supabase
      .from("expenses")
      .select("category, value")
      .eq("parliamentarian_external_id", externalId);

    if (!rawData) return [];

    const grouped: Record<string, number> = {};
    for (const e of rawData) {
      const cat = e.category ?? "Outros";
      grouped[cat] = (grouped[cat] ?? 0) + e.value;
    }
    return Object.entries(grouped)
      .map(([categoria, valor]) => ({ categoria, valor }))
      .sort((a, b) => b.valor - a.valor);
  }
  return data ?? [];
}

export async function getProposicoesByParlamentar(externalId: string): Promise<ProposicaoResumo[]> {
  const supabase = createClient();

  const { data: authData } = await supabase
    .from("proposition_authors")
    .select("proposition_external_id")
    .eq("parliamentarian_external_id", externalId)
    .eq("proposition_source", "camara");

  if (!authData?.length) return [];

  const propIds = authData.map((a) => a.proposition_external_id);
  const { data } = await supabase
    .from("propositions")
    .select("*")
    .in("external_id", propIds)
    .order("ano", { ascending: false })
    .limit(50);

  return data ?? [];
}

export async function getOrganByParliamentarian(externalId: string): Promise<Organ[]> {
  const supabase = createClient();

  const { data: memberships } = await supabase
    .from("organ_memberships")
    .select("organ_external_id")
    .eq("parliamentarian_external_id", externalId);

  if (!memberships?.length) return [];

  const organIds = memberships.map((m) => m.organ_external_id);
  const { data } = await supabase
    .from("organs")
    .select("*")
    .in("external_id", organIds);

  return data ?? [];
}

export async function searchProposicoes(
  termo: string,
  limit: number = 20,
): Promise<ProposicaoResumo[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("propositions")
    .select("*")
    .ilike("ementa", `%${termo}%`)
    .order("ano", { ascending: false })
    .limit(limit);
  return data ?? [];
}

export async function searchParlamentares(
  termo: string,
  limit: number = 20,
): Promise<Parlamentar[]> {
  const supabase = createClient();
  const { data } = await supabase
    .from("parlamentarians")
    .select("*")
    .or(`name.ilike.%${termo}%,party.ilike.%${termo}%,uf.ilike.%${termo}%`)
    .order("name")
    .limit(limit);
  return data ?? [];
}
