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
  const [error, setError] = useState<string | null>(null);
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

        // Parliamentarians — todos (593+), sem truncar
        const { data: parlData } = await supabase
          .from("parlamentarians")
          .select("external_id, nome, casa, uf, partido, foto_url")
          .order("nome")
          .limit(600);

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

        // Expenses aggregated server-side via materialized view
        const { data: expData } = await supabase
          .from("despesas_por_categoria")
          .select("categoria, total")
          .order("total", { ascending: false })
          .limit(5);

        if (!cancelled && expData && expData.length > 0) {
          const total = expData.reduce((s, e) => s + (e.total ?? 0), 0) || 1;
          const mapped = expData.map((e) => ({
            categoria: e.categoria ?? "Outros",
            valor: (e.total ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
            percentual: total > 0 ? Math.round(((e.total ?? 0) / total) * 100) : 0,
          }));
          if (mapped.length > 0) setDespesas(mapped);
        }

        if (!cancelled) setConnected(true);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.warn("Falha ao carregar dados do Supabase.", msg);
        if (!cancelled) setError(msg);
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
    error,
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

  // Usa a materialized view parlamentar_kpis (1 query em vez de 200+ N+1).
  // Inclui total_autorias, autoria_principal, total_orgaos, total_frentes, despesa_total.
  const { data: kpis } = await supabase
    .from("parlamentar_kpis")
    .select("external_id, total_autorias, autoria_principal, total_orgaos, total_frentes, despesa_total")
    .in("external_id", ids);

  const kpiMap: Record<string, {
    total_autorias: number;
    autoria_principal: number;
    total_orgaos: number;
    total_frentes: number;
    despesa_total: number;
  }> = {};
  for (const k of kpis ?? []) {
    kpiMap[k.external_id] = {
      total_autorias: k.total_autorias ?? 0,
      autoria_principal: k.autoria_principal ?? 0,
      total_orgaos: k.total_orgaos ?? 0,
      total_frentes: k.total_frentes ?? 0,
      despesa_total: k.despesa_total ?? 0,
    };
  }

  return rows.map((r, i) => {
    const kpi = kpiMap[r.external_id];
    const orgaos = kpi?.total_orgaos ?? 0;
    const total = kpi?.despesa_total ?? 0;
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
      proposicoes: kpi?.total_autorias ?? 0,
      autoriaPrincipal: kpi?.autoria_principal ?? 0,
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

  // Usa a materialized view com o ultimo status de cada proposicao.
  const { data: tracks } = await supabase
    .from("proposition_ultimo_status")
    .select("proposition_external_id, descricao_situacao, orgao_sigla, despacho")
    .in("proposition_external_id", ids);

  type TrackSel = {
    proposition_external_id: string;
    descricao_situacao: string | null;
    orgao_sigla: string | null;
    despacho: string | null;
  };
  const latestTrack: Record<string, TrackSel> = {};
  for (const t of (tracks ?? []) as TrackSel[]) {
    latestTrack[t.proposition_external_id] = t;
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
  // KPIs via materialized view (1 query em vez de 3 head-counts + 2 data queries).
  const [kpiRes, authList] = await Promise.all([
    supabase.from("parlamentar_kpis").select("total_autorias, autoria_principal, total_orgaos, despesa_total").eq("external_id", externalId).single(),
    supabase.from("proposition_authors").select("proposition_external_id").eq("parliamentarian_external_id", externalId).limit(400),
  ]);

  const kpi = kpiRes.data;
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

  // Despesas agregadas por categoria via aggregacao server-side
  const { data: exp } = await supabase
    .from("expenses")
    .select("categoria, valor")
    .eq("parlamentar_external_id", externalId)
    .limit(5000);

  const grouped: Record<string, number> = {};
  let despesaTotal = kpi?.despesa_total ?? 0;
  for (const e of exp ?? []) {
    const cat = (e.categoria as string | null) ?? "Outros";
    const v = (e.valor as number) ?? 0;
    grouped[cat] = (grouped[cat] ?? 0) + v;
  }
  const sorted = Object.entries(grouped).sort(([, a], [, b]) => b - a).slice(0, 5);
  const maxCat = sorted.length ? sorted[0][1] : 1;
  const despesas: DespesaCategoria[] = sorted.map(([categoria, valor]) => ({
    categoria,
    valor: brl(valor),
    percentual: Math.round((valor / maxCat) * 100),
  }));

  const kpis: ParlamentarKpis = {
    proposicoes: kpi?.total_autorias ?? 0,
    autoria: kpi?.autoria_principal ?? 0,
    orgaos: kpi?.total_orgaos ?? 0,
    despesaTotal,
  };

  return { proposicoes, temas, despesas, kpis };
}
