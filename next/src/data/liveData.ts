"use client";

import { createClient } from "@/utils/supabase/client";
import { useEffect, useState } from "react";
import {
  citizenQuestions,
  despesas as mockDespesas,
  legislativeHighlights,
  parlamentares as mockParlamentares,
  proposicoes as mockProposicoes,
  resumoCards as mockResumoCards,
  type Parlamentar,
  type ProposicaoDestaque,
} from "./mockLegislativo";
import type { ParlamentarRow, PropositionRow } from "./types";

export function useLiveDashboard() {
  const [parlamentares, setParlamentares] = useState(mockParlamentares);
  const [resumoCards, setResumoCards] = useState(mockResumoCards);
  const [proposicoes, setProposicoes] = useState(mockProposicoes);
  const [despesas, setDespesas] = useState(mockDespesas);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();

    async function load() {
      try {
        // KPIs
        const [parlCount, propCount, expCount] = await Promise.all([
          supabase.from("parlamentarians").select("*", { count: "exact", head: true }),
          supabase.from("propositions").select("*", { count: "exact", head: true }),
          supabase.from("expenses").select("*", { count: "exact", head: true }),
        ]);

        if (!cancelled) {
          setResumoCards([
            { ...mockResumoCards[0], value: (parlCount.count ?? 593).toString() },
            { ...mockResumoCards[1], value: `${((propCount.count ?? 0) / 1000).toFixed(0)} mil+` },
            { ...mockResumoCards[2], value: `${((expCount.count ?? 0) / 1000).toFixed(0)} mil+` },
          ]);
        }

        // Parliamentarians
        const { data: parlData } = await supabase
          .from("parlamentarians")
          .select("external_id, nome, casa, uf, partido, foto_url")
          .order("nome")
          .limit(100);

        if (!cancelled && parlData) {
          const enriched = await enrichParlamentares(supabase, parlData);
          if (!cancelled && enriched.length > 0) {
            setParlamentares(enriched);
          }
        }

        // Recent propositions
        const { data: propData } = await supabase
          .from("propositions")
          .select("external_id, sigla, numero, ano, ementa")
          .eq("source", "camara")
          .order("ano", { ascending: false })
          .limit(20);

        if (!cancelled && propData) {
          const enrichedProps = await enrichProposicoes(supabase, propData);
          if (!cancelled && enrichedProps.length > 0) {
            setProposicoes(enrichedProps);
          }
        }

        // Expenses
        const { data: expData } = await supabase
          .from("expenses")
          .select("categoria, valor")
          .not("categoria", "is", null)
          .neq("categoria", "Test")
          .limit(20000);

        if (!cancelled && expData) {
          const grouped: Record<string, number> = {};
          for (const e of expData) {
            const cat = e.categoria ?? "Outros";
            grouped[cat] = (grouped[cat] ?? 0) + (e.valor ?? 0);
          }
          const sorted = Object.entries(grouped)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5);
          const total = sorted.reduce((s, [, v]) => s + v, 0) || 1;
          const mapped = sorted.map(([cat, val]) => ({
            categoria: cat,
            valor: val.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
            percentual: Math.round((val / total) * 100),
          }));
          if (mapped.length > 0) setDespesas(mapped);
        }

        if (!cancelled) setConnected(true);
      } catch {
        // Silently keep mocks
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return {
    parlamentares,
    resumoCards,
    proposicoes,
    despesas,
    citizenQuestions,
    legislativeHighlights,
    connected,
    loading,
  };
}

function pluralOrgaos(n: number): string {
  return `${n} ${n === 1 ? "órgão" : "órgãos"}`;
}

function brl(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

type ParlamentarSel = Pick<ParlamentarRow, "external_id" | "nome" | "casa" | "uf" | "partido" | "foto_url">;
type PropositionSel = Pick<PropositionRow, "external_id" | "sigla" | "numero" | "ano" | "ementa">;

async function enrichParlamentares(
  supabase: ReturnType<typeof createClient>,
  rows: ParlamentarSel[],
): Promise<Parlamentar[]> {
  if (!rows.length) return [];

  const ids = rows.map((r) => r.external_id);

  // Contagens EXATAS por parlamentar (head-count). Evita o bug do fetch em
  // lote, que era truncado no limite default de 1000 linhas do PostgREST e
  // subcontava autores prolificos (ex.: 272 em vez de 2235). ~1.6s para 100.
  const [countsList, expRes] = await Promise.all([
    Promise.all(
      rows.map(async (r) => {
        const [pc, oc] = await Promise.all([
          supabase
            .from("proposition_authors")
            .select("*", { count: "exact", head: true })
            .eq("parliamentarian_external_id", r.external_id),
          supabase
            .from("organ_memberships")
            .select("*", { count: "exact", head: true })
            .eq("parliamentarian_external_id", r.external_id),
        ]);
        return { id: r.external_id, prop: pc.count ?? 0, org: oc.count ?? 0 };
      }),
    ),
    supabase
      .from("expenses")
      .select("parlamentar_external_id, valor")
      .in("parlamentar_external_id", ids)
      .limit(50000),
  ]);

  const propCounts: Record<string, number> = {};
  const orgCounts: Record<string, number> = {};
  const expTotals: Record<string, number> = {};

  for (const c of countsList) {
    propCounts[c.id] = c.prop;
    orgCounts[c.id] = c.org;
  }
  for (const e of expRes.data ?? []) {
    const key = e.parlamentar_external_id as string;
    expTotals[key] = (expTotals[key] ?? 0) + (e.valor ?? 0);
  }

  return rows.map((r, i) => {
    const orgaos = orgCounts[r.external_id] ?? 0;
    const total = expTotals[r.external_id] ?? 0;
    const isSenado = r.casa === "senado";
    return {
      id: r.external_id,
      nome: r.nome ?? `Parlamentar ${i}`,
      foto_url: r.foto_url ?? null,
      cargo: isSenado ? "Senador" : "Deputado Federal",
      casa: isSenado ? "Senado" : "Camara",
      uf: r.uf ?? "BR",
      partido: r.partido ?? "Sem partido",
      mandato: "2023-2027",
      temas: [],
      proposicoes: propCounts[r.external_id] ?? 0,
      autoriaPrincipal: 0, // contagem exata de autoria principal vem no detalhe do perfil
      despesas: total > 0 ? brl(total) : "Sem dados",
      despesasValor: total,
      presenca: pluralOrgaos(orgaos),
      snapshotLabel: "Supabase",
      destaque: "Perfil oficial da Câmara/Senado",
      coletaResumo: "Dados oficiais coletados via API",
      fontePrincipal: isSenado ? "Senado Federal" : "Câmara dos Deputados",
      leituraPublica: `Perfil oficial do ${isSenado ? "senador" : "deputado"} ${r.nome} (${r.partido}-${r.uf}).`,
      proximaAcao: "Acompanhar proposições e tramitações em andamento.",
      participacao: `${pluralOrgaos(orgaos)} identificado${orgaos === 1 ? "" : "s"}`,
    };
  });
}

async function enrichProposicoes(
  supabase: ReturnType<typeof createClient>,
  rows: PropositionSel[],
): Promise<ProposicaoDestaque[]> {
  if (!rows.length) return [];

  const ids = rows.map((r) => r.external_id);

  const { data: tracks } = await supabase
    .from("proposition_trackings")
    .select("proposition_external_id, descricao_situacao, orgao_sigla, despacho")
    .in("proposition_external_id", ids)
    .order("sequencia", { ascending: false });

  type TrackSel = {
    proposition_external_id: string;
    descricao_situacao: string | null;
    orgao_sigla: string | null;
    despacho: string | null;
  };
  const latestTrack: Record<string, TrackSel> = {};
  for (const t of (tracks ?? []) as TrackSel[]) {
    if (!latestTrack[t.proposition_external_id]) {
      latestTrack[t.proposition_external_id] = t;
    }
  }

  return rows.map((r) => ({
    sigla: r.sigla ?? "?",
    numero: r.numero ?? "0",
    ano: r.ano,
    tema: r.ementa?.slice(0, 60) ?? "",
    status: latestTrack[r.external_id]?.descricao_situacao ?? "Sem status",
    andamento: latestTrack[r.external_id]?.despacho?.slice(0, 80) ?? "Aguardando",
    responsavel: latestTrack[r.external_id]?.orgao_sigla ?? "MESA",
    impacto: "Acompanhamento público disponível",
  }));
}

export interface DespesaCategoria {
  categoria: string;
  valor: string;
  percentual: number;
}

export interface ParlamentarKpis {
  proposicoes: number;
  autoria: number;
  orgaos: number;
  despesaTotal: number;
}

export interface ParlamentarDetalhe {
  proposicoes: ProposicaoDestaque[];
  temas: string[];
  despesas: DespesaCategoria[];
  kpis: ParlamentarKpis;
}

// Busca os dados REAIS de um parlamentar selecionado (proposicoes de autoria,
// temas mais frequentes e despesas por categoria). Usado ao trocar de perfil.
export async function fetchParlamentarDetalhe(
  supabase: ReturnType<typeof createClient>,
  externalId: string,
): Promise<ParlamentarDetalhe> {
  // KPIs exatos via head-count (mesma base da comparacao).
  const [propCountRes, autoriaCountRes, orgCountRes, authList] = await Promise.all([
    supabase.from("proposition_authors").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", externalId),
    supabase.from("proposition_authors").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", externalId).eq("proponent", true),
    supabase.from("organ_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", externalId),
    supabase.from("proposition_authors").select("proposition_external_id").eq("parliamentarian_external_id", externalId).limit(400),
  ]);
  const auth = authList.data;

  const ids = [...new Set((auth ?? []).map((a) => a.proposition_external_id as string))].slice(0, 200);

  let proposicoes: ProposicaoDestaque[] = [];
  let temas: string[] = [];

  if (ids.length) {
    const { data: props } = await supabase
      .from("propositions")
      .select("external_id, sigla, numero, ano, ementa")
      .in("external_id", ids)
      .order("ano", { ascending: false })
      .limit(40);
    if (props?.length) proposicoes = await enrichProposicoes(supabase, props);

    const { data: th } = await supabase
      .from("proposition_themes")
      .select("theme_name")
      .in("proposition_external_id", ids)
      .limit(800);
    const counts: Record<string, number> = {};
    for (const t of th ?? []) {
      const name = t.theme_name as string | null;
      if (name) counts[name] = (counts[name] ?? 0) + 1;
    }
    temas = Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)
      .map(([k]) => k);
  }

  const { data: exp } = await supabase
    .from("expenses")
    .select("categoria, valor")
    .eq("parlamentar_external_id", externalId)
    .limit(5000);

  const grouped: Record<string, number> = {};
  let despesaTotal = 0;
  for (const e of exp ?? []) {
    const cat = (e.categoria as string | null) ?? "Outros";
    const v = (e.valor as number) ?? 0;
    grouped[cat] = (grouped[cat] ?? 0) + v;
    despesaTotal += v;
  }
  const sorted = Object.entries(grouped).sort(([, a], [, b]) => b - a).slice(0, 5);
  const maxCat = sorted.length ? sorted[0][1] : 1;
  const despesas: DespesaCategoria[] = sorted.map(([categoria, valor]) => ({
    categoria,
    valor: brl(valor),
    percentual: Math.round((valor / maxCat) * 100),
  }));

  const kpis: ParlamentarKpis = {
    proposicoes: propCountRes.count ?? 0,
    autoria: autoriaCountRes.count ?? 0,
    orgaos: orgCountRes.count ?? 0,
    despesaTotal,
  };

  return { proposicoes, temas, despesas, kpis };
}
