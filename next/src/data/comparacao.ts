"use client";

import { createClient } from "@/utils/supabase/client";
import { useState, useCallback } from "react";

export interface ComparacaoParlamentar {
  id: string;
  nome: string;
  partido: string;
  uf: string;
  proposicoes: number;
  despesasTotal: number;
  orgaos: number;
  frentes: number;
}

export function useComparacao() {
  const [a, setA] = useState<any>(null);
  const [b, setB] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const comparar = useCallback(async (idA: string, idB: string) => {
    setLoading(true);
    const supabase = createClient();

    const [resA, resB] = await Promise.all([
      loadStats(supabase, idA),
      loadStats(supabase, idB),
    ]);

    setA(resA);
    setB(resB);
    setLoading(false);
  }, []);

  const limpar = useCallback(() => {
    setA(null);
    setB(null);
  }, []);

  return { a, b, loading, comparar, limpar };
}

async function loadStats(supabase: ReturnType<typeof createClient>, extId: string): Promise<ComparacaoParlamentar> {
  const [parl, propCount, expSum, orgCount, frontCount] = await Promise.all([
    supabase.from("parlamentarians").select("nome,partido,uf,casa").eq("external_id", extId).single(),
    supabase.from("proposition_authors").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
    supabase.from("expenses").select("valor").eq("parlamentar_external_id", extId).limit(1000),
    supabase.from("organ_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
    supabase.from("front_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
  ]);

  const p = parl.data;
  return {
    id: extId,
    nome: p?.nome ?? extId,
    partido: p?.partido ?? "?",
    uf: p?.uf ?? "?",
    proposicoes: propCount.count ?? 0,
    despesasTotal: (expSum.data ?? []).reduce((s: number, e: any) => s + (e.valor ?? 0), 0),
    orgaos: orgCount.count ?? 0,
    frentes: frontCount.count ?? 0,
  };
}

export function downloadCSV(filename: string, rows: Record<string, any>[]) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const csv = [headers.join(","), ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
