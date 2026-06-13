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
} from "./mockLegislativo";

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
          .select("external_id, nome, casa, uf, partido")
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

async function enrichParlamentares(
  supabase: ReturnType<typeof createClient>,
  rows: any[],
): Promise<any[]> {
  if (!rows.length) return [];

  const ids = rows.map((r) => r.external_id);

  const [propRes, orgRes] = await Promise.all([
    supabase
      .from("proposition_authors")
      .select("parliamentarian_external_id")
      .in("parliamentarian_external_id", ids)
      .eq("proposition_source", "camara"),
    supabase
      .from("organ_memberships")
      .select("parliamentarian_external_id")
      .in("parliamentarian_external_id", ids),
  ]);

  const propCounts: Record<string, number> = {};
  const orgCounts: Record<string, number> = {};

  for (const p of propRes.data ?? []) {
    propCounts[p.parliamentarian_external_id] = (propCounts[p.parliamentarian_external_id] ?? 0) + 1;
  }
  for (const o of orgRes.data ?? []) {
    orgCounts[o.parliamentarian_external_id] = (orgCounts[o.parliamentarian_external_id] ?? 0) + 1;
  }

  return rows.map((r, i) => ({
    id: r.external_id,
    nome: r.nome ?? `Parlamentar ${i}`,
    cargo: r.casa === "senado" ? "Senador" : "Deputado Federal",
    casa: r.casa === "senado" ? "Senado" : "Camara",
    uf: r.uf ?? "BR",
    partido: r.partido ?? "Sem partido",
    mandato: "2023-2027",
    temas: [],
    proposicoes: propCounts[r.external_id] ?? 0,
    autoriaPrincipal: 0,
    despesas: "CEAP 2025",
    presenca: `${orgCounts[r.external_id] ?? 0} órgãos`,
    snapshotLabel: "Supabase",
    destaque: "Perfil oficial da Câmara/Senado",
    coletaResumo: "Dados oficiais coletados via API",
    fontePrincipal: r.casa === "senado" ? "Senado Federal" : "Câmara dos Deputados",
    leituraPublica: `Perfil oficial do ${r.casa === "senado" ? "Senado" : "deputado"} ${r.nome} (${r.partido}-${r.uf})`,
    proximaAcao: "Acompanhar proposições e tramitações",
    participacao: `${orgCounts[r.external_id] ?? 0} órgãos identificados`,
  }));
}

async function enrichProposicoes(
  supabase: ReturnType<typeof createClient>,
  rows: any[],
): Promise<any[]> {
  if (!rows.length) return [];

  const ids = rows.map((r) => r.external_id);

  const { data: tracks } = await supabase
    .from("proposition_trackings")
    .select("proposition_external_id, descricao_situacao, orgao_sigla, despacho")
    .in("proposition_external_id", ids)
    .order("sequencia", { ascending: false });

  const latestTrack: Record<string, any> = {};
  for (const t of tracks ?? []) {
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
