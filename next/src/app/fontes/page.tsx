"use client";

import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  PauseCircle,
  ServerCog,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/utils/supabase/client";
import { graphEdges, graphNodes } from "@/data/mockLegislativo";

interface SyncRun {
  job: string;
  source: string;
  status: string;
  records_count: number;
  started_at: string;
}

interface TableCount {
  table: string;
  count: number;
}

export default function FontesPage() {
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [tables, setTables] = useState<TableCount[]>([]);
  const [ultimaColeta, setUltimaColeta] = useState<string | null>(null);
  const [totalRegistros, setTotalRegistros] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();

    async function load() {
      try {
        const [syncRunsRes, parlRes, propRes, expRes, discRes, rawRes] = await Promise.all([
          supabase.from("sync_runs").select("job,source,status,records_count,started_at").order("started_at", { ascending: false }).limit(5),
          supabase.from("parlamentarians").select("*", { count: "exact", head: true }),
          supabase.from("propositions").select("*", { count: "exact", head: true }),
          supabase.from("expenses").select("*", { count: "exact", head: true }),
          supabase.from("discursos").select("*", { count: "exact", head: true }),
          supabase.from("raw_payloads").select("*", { count: "exact", head: true }),
        ]);

        if (cancelled) return;

        const runs: SyncRun[] = (syncRunsRes.data ?? []) as SyncRun[];
        const tbls: TableCount[] = [
          { table: "Parlamentares", count: parlRes.count ?? 0 },
          { table: "Proposições", count: propRes.count ?? 0 },
          { table: "Despesas", count: expRes.count ?? 0 },
          { table: "Discursos", count: discRes.count ?? 0 },
          { table: "Payloads brutos", count: rawRes.count ?? 0 },
        ];

        setSyncRuns(runs);
        setTables(tbls);
        setUltimaColeta(runs.length > 0
          ? new Date(runs[0].started_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
          : null);
        setTotalRegistros(tbls.reduce((s, t) => s + t.count, 0));
        setErro(null);
      } catch (err) {
        if (!cancelled) setErro(String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="page-shell">
      <header className="dashboard-header">
        <div>
          <div className="hero-ribbon">
            <span className="hero-chip">Fontes e metodologia</span>
            {loading && <span className="hero-chip hero-chip--loading">⏳ Carregando...</span>}
            {ultimaColeta && <span className="hero-chip hero-chip--ok">● Última coleta: {ultimaColeta}</span>}
            {erro && <span className="hero-chip hero-chip--error">⚠ Erro ao carregar</span>}
          </div>
          <p className="eyebrow">Bastidor do projeto</p>
          <h1>Como os dados entram no painel</h1>
          <p>
            Esta página mostra a cobertura real das fontes oficiais e o histórico
            de coletas que alimentam o banco do projeto.
          </p>
        </div>
        <Link className="secondary-button" href="/dashboard">
          <ArrowLeft aria-hidden="true" size={16} />
          Voltar ao dashboard
        </Link>
      </header>

      <section className="collector-board" aria-label="Cobertura dos coletores">
        <div className="section-head collector-board-head">
          <div>
            <p className="eyebrow">Banco de dados</p>
            <h2>Cobertura atual</h2>
            <p>
              {totalRegistros > 0
                ? `${totalRegistros.toLocaleString("pt-BR")} registros em ${tables.length} tabelas.`
                : "Execute o pipeline Python com --supabase para popular o banco."}
            </p>
          </div>
          <span className="collector-badge">
            <ServerCog aria-hidden="true" size={16} />
            supabase
          </span>
        </div>

        <div className="collector-grid">
          {tables.length > 0 ? tables.map((t) => (
            <article className="collector-card" key={t.table}>
              <div className="collector-card-top">
                <ServerCog aria-hidden="true" size={21} />
                <span>ativo</span>
              </div>
              <h3>{t.table}</h3>
              <strong>{t.count.toLocaleString("pt-BR")} registros</strong>
            </article>
          )) : (
            <article className="collector-card">
              <div className="collector-card-top">
                <PauseCircle aria-hidden="true" size={21} />
                <span>pendente</span>
              </div>
              <h3>Banco vazio</h3>
              <p>Execute o pipeline Python com a flag --supabase.</p>
              <strong>0 registros</strong>
            </article>
          )}
        </div>
      </section>

      <section className="data-map-grid" aria-label="Histórico e grafo">
        <article className="data-map-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Grafo de dados</p>
              <h2>Da fonte oficial ao perfil</h2>
            </div>
          </div>
          <svg className="data-graph" viewBox="0 0 700 300" role="img" aria-label="Grafo das fontes">
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M 0 0 L 8 4 L 0 8 z" />
              </marker>
            </defs>
            {graphEdges.map(([from, to]) => {
              const fn = graphNodes.find((n) => n.id === from);
              const tn = graphNodes.find((n) => n.id === to);
              if (!fn || !tn) return null;
              return <line className="graph-edge" key={`${from}-${to}`}
                x1={fn.x} x2={tn.x} y1={fn.y} y2={tn.y} />;
            })}
            {graphNodes.map((n) => (
              <g className={`graph-node ${n.tone}`} key={n.id}>
                <rect x={n.x - 58} y={n.y - 24} width="116" height="48" rx="8" />
                <text x={n.x} y={n.y + 4}>{n.label}</text>
              </g>
            ))}
          </svg>
        </article>

        <article className="collector-queue-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Histórico de coletas</p>
              <h2>Últimas execuções do pipeline</h2>
            </div>
          </div>
          <div className="collector-run-list">
            {syncRuns.length > 0 ? syncRuns.map((run, i) => (
              <article key={`${run.job}-${run.started_at}-${i}`}>
                <CheckCircle2 aria-hidden="true" size={18}
                  color={run.status === "success" ? "#166534" : run.status === "partial" ? "#d97706" : "#b91c1c"} />
                <div>
                  <strong>{run.job}</strong>
                  <span>{run.source}</span>
                </div>
                <p>{run.records_count.toLocaleString("pt-BR")} registros</p>
                <small>{new Date(run.started_at).toLocaleString("pt-BR")}</small>
              </article>
            )) : (
              <article>
                <Clock aria-hidden="true" size={18} />
                <div>
                  <strong>Nenhuma coleta registrada</strong>
                  <span>Execute o pipeline Python para popular o banco.</span>
                </div>
              </article>
            )}
          </div>
        </article>
      </section>

      <section className="source-health-card" aria-label="Status das fontes oficiais">
        <div className="section-head compact">
          <div>
            <p className="eyebrow">Fontes oficiais</p>
            <h2>Status de coleta</h2>
          </div>
        </div>
        <div className="source-health-table">
          {[
            { source: "Câmara — parlamentares", coverage: tables.find(t => t.table === "Parlamentares")?.count.toLocaleString("pt-BR") ?? "—", use: "Perfis, despesas, proposições, órgãos, frentes.", status: "respondendo" as const },
            { source: "Câmara — proposições", coverage: tables.find(t => t.table === "Proposições")?.count.toLocaleString("pt-BR") ?? "—", use: "Arquivos anuais JSON + API por deputado.", status: "respondendo" as const },
            { source: "Câmara — CEAP", coverage: tables.find(t => t.table === "Despesas")?.count.toLocaleString("pt-BR") ?? "—", use: "CSV ZIP anual + API por deputado.", status: "respondendo" as const },
            { source: "Senado — discursos", coverage: tables.find(t => t.table === "Discursos")?.count.toLocaleString("pt-BR") ?? "—", use: "Pronunciamentos em plenário.", status: "respondendo" as const },
            { source: "Portal CGU", coverage: "pendente", use: "Requer chave de API. Emendas e transferências.", status: "pendente" as const },
          ].map((s) => (
            <article key={s.source}>
              {s.status === "respondendo"
                ? <CheckCircle2 aria-hidden="true" size={18} color="#166534" />
                : <PauseCircle aria-hidden="true" size={18} color="#d97706" />}
              <strong>{s.source}</strong>
              <span>{s.coverage}</span>
              <p>{s.use}</p>
              <small className={s.status === "respondendo" ? "ok" : "pending"}>{s.status}</small>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
