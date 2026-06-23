"use client";

import {
  ArrowUpRight,
  BarChart3,
  Download,
  Filter,
  Home as HomeIcon,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useLiveDashboard, fetchParlamentarDetalhe, type ParlamentarDetalhe } from "@/data/liveData";
import { createClient } from "@/utils/supabase/client";
import { downloadCSV } from "@/data/comparacao";
import { generateParlamentarPDF } from "@/data/pdfExport";
import { useToast } from "@/data/toast";
import type { BuscaProposicao, ComparacaoStats } from "@/data/types";

const tabs = ["Resumo", "Projetos", "Participacao", "Transparencia", "Tramitacao"];
const tabLabels: Record<string, string> = {
  Resumo: "Resumo",
  Projetos: "Projetos",
  Participacao: "Participação",
  Transparencia: "Transparência",
  Tramitacao: "Tramitação",
};
const UFS = ["Todas","AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
const ORDENACOES = ["Proposições", "Cota usada", "Nome"] as const;
type Ordenacao = (typeof ORDENACOES)[number];

// Limite de itens na lista "Leitura do recorte" para não criar scroll gigante.
const RECORTE_LIMIT = 6;

export default function Home() {
  const { parlamentares, resumoCards, proposicoes,
          connected, error, loading } = useLiveDashboard();

  const [activeId, setActiveId] = useState(parlamentares[0]?.id ?? "");
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const { show, ToastContainer } = useToast();

  // Search state
  const [searchNome, setSearchNome] = useState("");
  const [searchTema, setSearchTema] = useState("");
  const [searchCasa, setSearchCasa] = useState("Ambas");
  const [searchUf, setSearchUf] = useState("Todas");
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("Proposições");
  const [searchProposicoes, setSearchProposicoes] = useState<BuscaProposicao[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buscarTema = useCallback(async (tema: string) => {
    if (!tema || tema.length < 2) return;
    setSearching(true);
    const supabase = createClient();
    // Full-text search em portugues via funcao PostgreSQL
    const { data, error } = await supabase
      .rpc("search_proposicoes", { search_term: tema, max_results: 20 });
    if (error) {
      // Fallback para ILIKE se a funcao RPC nao existir (migration nao aplicada)
      const fallback = await supabase
        .from("propositions")
        .select("external_id, sigla, numero, ano, ementa")
        .ilike("ementa", `%${tema}%`)
        .order("ano", { ascending: false })
        .limit(20);
      setSearchProposicoes(fallback.data ?? []);
    } else {
      setSearchProposicoes((data ?? []) as BuscaProposicao[]);
    }
    setSearching(false);
  }, []);

  const handleTemaInput = (val: string) => {
    setSearchTema(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.length >= 2) {
      debounceRef.current = setTimeout(() => buscarTema(val), 400);
    }
  };

  // Comparison
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  const [compareData, setCompareData] = useState<{ a: ComparacaoStats; b: ComparacaoStats } | null>(null);
  const [comparing, setComparing] = useState(false);

  const toggleCompare = async (id: string) => {
    if (compareA === id) { setCompareA(null); return; }
    if (compareB === id) { setCompareB(null); return; }
    if (!compareA) { setCompareA(id); return; }
    if (!compareB) {
      setCompareB(id);
      setComparing(true);
      const supabase = createClient();
      const [rA, rB] = await Promise.all([loadStatsFn(supabase, compareA), loadStatsFn(supabase, id)]);
      setCompareData({ a: rA, b: rB });
      setComparing(false);
    }
  };

  const clearCompare = () => { setCompareA(null); setCompareB(null); setCompareData(null); };

  const loadStatsFn = async (supabase: ReturnType<typeof createClient>, extId: string): Promise<ComparacaoStats> => {
    const [parl, kpi] = await Promise.all([
      supabase.from("parlamentarians").select("nome,partido,uf").eq("external_id", extId).single(),
      supabase.from("parlamentar_kpis").select("total_autorias,total_orgaos,total_frentes,despesa_total").eq("external_id", extId).single(),
    ]);
    const p = parl.data;
    const k = kpi.data;
    return {
      nome: p?.nome ?? extId,
      partido: p?.partido ?? "?",
      uf: p?.uf ?? "?",
      proposicoes: k?.total_autorias ?? 0,
      orgaos: k?.total_orgaos ?? 0,
      frentes: k?.total_frentes ?? 0,
      despesas: k?.despesa_total ?? 0,
    };
  };

  // Filter + sort parliamentarians based on search controls
  const filteredParlamentares = useMemo(() => {
    const filtered = parlamentares.filter((p) => {
      if (searchNome && !p.nome.toLowerCase().includes(searchNome.toLowerCase())) return false;
      if (searchCasa !== "Ambas" && p.casa !== searchCasa) return false;
      if (searchUf !== "Todas" && p.uf !== searchUf) return false;
      return true;
    });
    const sorted = [...filtered];
    if (ordenacao === "Proposições") {
      sorted.sort((a, b) => b.proposicoes - a.proposicoes);
    } else if (ordenacao === "Cota usada") {
      sorted.sort((a, b) => (b.despesasValor ?? 0) - (a.despesasValor ?? 0));
    } else {
      sorted.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    }
    return sorted;
  }, [parlamentares, searchNome, searchCasa, searchUf, ordenacao]);

  // Seleção derivada durante o render (sem setState em effect): se o id ativo
  // não estiver na lista filtrada, cai para o primeiro resultado.
  const activeParlamentar = useMemo(
    () => filteredParlamentares.find((item) => item.id === activeId) ?? filteredParlamentares[0],
    [activeId, filteredParlamentares],
  );

  // Detalhe real do parlamentar selecionado (proposicoes, temas, despesas).
  // Guardamos junto o id ao qual o detalhe pertence, para derivar "loading"
  // sem precisar de setState sincrono dentro do effect.
  const [detalhe, setDetalhe] = useState<{ forId: string; data: ParlamentarDetalhe } | null>(null);
  const activeExtId = activeParlamentar?.id;

  useEffect(() => {
    if (!activeExtId) return;
    let cancelled = false;
    const supabase = createClient();
    fetchParlamentarDetalhe(supabase, activeExtId)
      .then((d) => { if (!cancelled) setDetalhe({ forId: activeExtId, data: d }); })
      .catch(() => {
        if (!cancelled) setDetalhe({ forId: activeExtId, data: { proposicoes: [], temas: [], despesas: [], kpis: { proposicoes: 0, autoria: 0, orgaos: 0, despesaTotal: 0 } } });
      });
    return () => { cancelled = true; };
  }, [activeExtId]);

  const detalheReady = !!activeExtId && detalhe?.forId === activeExtId;
  const detalheLoading = !detalheReady;
  const perfilProps = detalheReady ? detalhe!.data.proposicoes : [];
  const perfilTemas = detalheReady ? detalhe!.data.temas : [];
  const perfilDespesas = detalheReady ? detalhe!.data.despesas : [];

  // KPIs exatos do perfil (consistentes com diretorio e comparacao). Enquanto
  // o detalhe carrega, usa o valor aproximado do diretorio como fallback.
  const k = detalhe?.data.kpis;
  const kpiProps = detalheReady && k ? k.proposicoes : (activeParlamentar?.proposicoes ?? 0);
  const kpiAutoria = detalheReady && k ? k.autoria : (activeParlamentar?.autoriaPrincipal ?? 0);
  const kpiOrgaos = detalheReady && k ? k.orgaos : 0;
  const kpiCota = detalheReady && k
    ? (k.despesaTotal > 0 ? k.despesaTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "Sem dados")
    : (activeParlamentar?.despesas ?? "—");
  const kpiOrgaosLabel = `${kpiOrgaos} ${kpiOrgaos === 1 ? "órgão" : "órgãos"}`;

  return (
    <>
    <main className="page-shell">
      <header className="dashboard-header">
        <div>
          <div className="hero-ribbon">
            <span className="hero-chip">Painel do Legislativo</span>
            {loading && <span className="hero-chip hero-chip--loading">⏳ Carregando...</span>}
            {connected && <span className="hero-chip hero-chip--ok">● Dados oficiais</span>}
            {error && <span className="hero-chip hero-chip--error">⚠ Desconectado — dados mock</span>}
          </div>
          <p className="eyebrow">Acompanhamento público</p>
          <h1>Atuação parlamentar em linguagem clara</h1>
          <p>
            Pesquise deputados, senadores, projetos e temas para enxergar o que
            foi proposto, onde a matéria está, quem participa da tramitação e
            quais informações públicas ajudam o cidadão a acompanhar o mandato.
          </p>
        </div>
        <div className="header-actions">
          <Link className="secondary-button" href="/">
            <HomeIcon aria-hidden="true" size={16} />
            Voltar ao front
          </Link>
          <Link className="secondary-button" href="/fontes">
            Fontes e metodologia
            <ArrowUpRight aria-hidden="true" size={16} />
          </Link>
        </div>
      </header>

      <section className="search-card">
        <div className="workbench-head">
          <p className="eyebrow">Busca principal</p>
          <h2>Encontre parlamentar, tema ou projeto</h2>
          <p>
            Comece por nome, palavra-chave ou recorte de interesse público. O
            painel organiza resultados oficiais para leitura rápida, comparação
            e geração de relatório.
          </p>
        </div>

        <div className="search-form">
          <label className="field field-wide">
            <span>Nome do parlamentar</span>
            <div className="input-shell">
              <Search aria-hidden="true" size={18} />
              <input placeholder="Ex.: Acácio Favacho, Alan Rick..."
                     value={searchNome} onChange={(e) => setSearchNome(e.target.value)} />
            </div>
          </label>

          <label className="field field-wide">
            <span>Tema ou palavra-chave</span>
            <div className="input-shell">
              <Filter aria-hidden="true" size={18} />
              <input placeholder="Ex.: segurança pública, saúde, educação..."
                     value={searchTema} onChange={(e) => handleTemaInput(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && buscarTema(searchTema)} />
            </div>
          </label>

          <label className="field">
            <span>Casa</span>
            <select value={searchCasa} onChange={(e) => setSearchCasa(e.target.value)}>
              <option value="Ambas">Ambas</option>
              <option value="Camara">Câmara</option>
              <option value="Senado">Senado</option>
            </select>
          </label>

          <label className="field">
            <span>UF</span>
            <select value={searchUf} onChange={(e) => setSearchUf(e.target.value)}>
              {UFS.map((uf) => <option key={uf}>{uf}</option>)}
            </select>
          </label>

          <label className="field">
            <span>Ordenar</span>
            <select value={ordenacao} onChange={(e) => setOrdenacao(e.target.value as Ordenacao)}>
              {ORDENACOES.map((o) => <option key={o}>{o}</option>)}
            </select>
          </label>

          <button className="primary-button" type="button" onClick={() => buscarTema(searchTema)}>
            <SlidersHorizontal aria-hidden="true" size={18} />
            Filtrar
          </button>
        </div>

        <div className="quick-pills">
          {["Segurança pública", "Saúde", "Educação", "Meio ambiente", "Economia", "Direitos"].map(
            (item) => (
              <button className="quick-pill" type="button" key={item}
                      onClick={() => { setSearchTema(item); buscarTema(item); }}>
                {item}
              </button>
            ),
          )}
        </div>
      </section>

      <section className="summary-grid" aria-label="Resumo do painel legislativo">
        {resumoCards.map((card) => {
          const Icon = card.icon;
          return (
            <article className="summary-card" key={card.title}>
              <Icon aria-hidden="true" size={22} />
              <span>{card.title}</span>
              <strong>{card.value}</strong>
              <small>{card.label}</small>
            </article>
          );
        })}
      </section>

      <section className="data-map-grid" aria-label="Resultados de busca">
        <article className="collector-queue-card civic-queue-card" style={{ gridColumn: "1 / -1" }}>
          <div className="section-head compact">
            <div>
              <p className="eyebrow">{searchTema ? `Busca: "${searchTema}"` : "Proposições recentes"}</p>
              <h2>{searchTema
                ? `${searchProposicoes.length} resultados` + (searching ? " (buscando...)" : "")
                : "Últimas proposições na Câmara"}</h2>
            </div>
          </div>
          <div className="collector-run-list">
            {(searchTema ? searchProposicoes : proposicoes).slice(0, RECORTE_LIMIT).map((item, idx) => {
              const sigla = "sigla" in item ? item.sigla : undefined;
              const numero = "numero" in item ? item.numero : undefined;
              const ano = "ano" in item ? item.ano : undefined;
              const ementa = "ementa" in item ? item.ementa : undefined;
              const status = "status" in item ? item.status : undefined;
              const responsavel = "responsavel" in item ? item.responsavel : undefined;
              return (
                <article key={`${sigla}-${numero}-${idx}`}>
                  <Search aria-hidden="true" size={18} />
                  <div>
                    <strong>{sigla} {numero}{ano ? `/${ano}` : ""}</strong>
                    <span>{status ?? ementa?.slice(0, 60)}</span>
                  </div>
                  <p>{responsavel ?? ementa?.slice(0, 80)}</p>
                  <small>Proposição legislativa</small>
                </article>
              );
            })}
            {searchTema && !searching && searchProposicoes.length === 0 && (
              <p style={{ padding: 12, color: "#64748b" }}>
                Nenhuma proposição encontrada para &ldquo;{searchTema}&rdquo;.
              </p>
            )}
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <aside className="directory-card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Para acompanhar parlamentares</p>
              <h2>Diretório público</h2>
            </div>
            <button className="mini-button" type="button"
                    onClick={() => { downloadCSV("parlamentares.csv", filteredParlamentares.map(p => ({
                      nome: p.nome, cargo: p.cargo, partido: p.partido, uf: p.uf,
                      proposicoes: p.proposicoes, despesas: p.despesas, participacao: p.participacao,
                    }))); show("CSV exportado!"); }}>
              <Download aria-hidden="true" size={16} />
              CSV
            </button>
          </div>

          <div className="parlamentar-list">
            {(loading && !connected) ? (
              [...Array(5)].map((_, i) => (
                <div className="skeleton-row" key={i}>
                  <div className="skeleton skeleton-avatar" />
                  <div className="skeleton skeleton-text" style={{width:"60%"}} />
                  <div className="skeleton skeleton-metric" />
                </div>
              ))
            ) : filteredParlamentares.length === 0 ? (
              <p className="muted-note" style={{ padding: 24, textAlign: "center" }}>
                Nenhum parlamentar encontrado com os filtros atuais.
              </p>
            ) : (
              filteredParlamentares.map((parlamentar) => (
              <button
                className={`parlamentar-row ${
                  parlamentar.id === activeParlamentar.id ? "is-active" : ""
                }`}
                key={parlamentar.id}
                onClick={() => setActiveId(parlamentar.id)}
                type="button"
              >
                <span className="avatar" aria-hidden="true"
                      style={parlamentar.foto_url ? { backgroundImage: `url(${parlamentar.foto_url})`, backgroundSize: "cover", backgroundPosition: "center", color: "transparent" } : {}}>
                  {parlamentar.nome
                    .split(" ")
                    .slice(0, 2)
                    .map((part) => part[0])
                    .join("")}
                </span>
                <span className="parlamentar-copy">
                  <strong>{parlamentar.nome}</strong>
                  <small>
                    {parlamentar.cargo} - {parlamentar.uf} - {parlamentar.partido}
                  </small>
                  <em>{parlamentar.participacao}</em>
                </span>
                <span className="row-metrics">
                  <b>{parlamentar.proposicoes}</b>
                  <small>projetos</small>
                </span>
                <span
                  className={`row-compare${compareA === parlamentar.id || compareB === parlamentar.id ? " is-selected" : ""}`}
                  onClick={(e) => { e.stopPropagation(); toggleCompare(parlamentar.id); }}
                  title="Selecionar para comparar">
                  {compareA === parlamentar.id ? "❶" : compareB === parlamentar.id ? "❷" : "⇆"}
                </span>
              </button>
            )))}
          </div>
        </aside>

        {activeParlamentar ? (
        <article className="profile-card">
          <div className="profile-hero">
            <div className="profile-photo" aria-hidden="true"
                 style={activeParlamentar.foto_url ? { backgroundImage: `url(${activeParlamentar.foto_url})`, backgroundSize: "cover", backgroundPosition: "center top", color: "transparent" } : {}}>
              {activeParlamentar.nome
                .split(" ")
                .slice(0, 2)
                .map((part) => part[0])
                .join("")}
            </div>
            <div className="profile-title">
              <p className="eyebrow">Perfil parlamentar</p>
              <h2>{activeParlamentar.nome}</h2>
              <p>
                {activeParlamentar.cargo} - {activeParlamentar.uf} -{" "}
                {activeParlamentar.partido}
                <br />
                Mandato {activeParlamentar.mandato}
              </p>
              <div className="profile-badges">
                <span>{activeParlamentar.casa === "Camara" ? "Câmara" : "Senado"}</span>
                <span>{activeParlamentar.uf}</span>
                {perfilTemas[0] && <span>{perfilTemas[0]}</span>}
                <span>{activeParlamentar.participacao}</span>
              </div>
            </div>
          </div>

          <div className="profile-kpis">
            <div>
              <strong>{kpiProps}</strong>
              <span>proposições</span>
            </div>
            <div>
              <strong>{kpiAutoria}</strong>
              <span>como autor</span>
            </div>
            <div>
              <strong>{kpiCota}</strong>
              <span>cota usada</span>
            </div>
            <div>
              <strong>{kpiOrgaosLabel}</strong>
              <span>participação</span>
            </div>
          </div>

          <div className="tabs" role="tablist" aria-label="Seções do perfil">
            {tabs.map((tab) => (
              <button
                className={tab === activeTab ? "is-active" : ""}
                key={tab}
                onClick={() => setActiveTab(tab)}
                type="button"
              >
                {tabLabels[tab] ?? tab}
              </button>
            ))}
          </div>

          <div className="profile-content">
            {activeTab === "Resumo" && (
              <>
                <section className="detail-card wide">
                  <h3>Temas recorrentes</h3>
                  {perfilTemas.length > 0 ? (
                    <div className="tag-list">
                      {perfilTemas.map((tema) => (
                        <span key={tema}>{tema}</span>
                      ))}
                    </div>
                  ) : (
                    <p className="muted-note">
                      {detalheLoading ? "Carregando temas…" : "Sem temas classificados."}
                    </p>
                  )}
                </section>
                <section className="detail-card wide">
                  <h3>Atuação parlamentar</h3>
                  <p>
                    {activeParlamentar.nome} ({activeParlamentar.partido}-{activeParlamentar.uf})
                    exerce o mandato como {activeParlamentar.cargo.toLowerCase()} na legislatura {activeParlamentar.mandato}.
                    {detalhe?.data.kpis && ` Possui ${detalhe.data.kpis.proposicoes} proposições registradas (${detalhe.data.kpis.autoria} como autor principal) e participação em ${detalhe.data.kpis.orgaos} órgãos legislativos.`}
                  </p>
                </section>
              </>
            )}

            {activeTab === "Projetos" && (
              <section className="detail-card wide">
                <h3>Proposições de autoria</h3>
                {detalheLoading ? (
                  <p className="muted-note">Carregando proposições…</p>
                ) : perfilProps.length > 0 ? (
                  <div className="proposal-list">
                    {perfilProps.slice(0, 12).map((proposicao, i) => (
                      <article key={`${proposicao.sigla}-${proposicao.numero}-${i}`}>
                        <strong>
                          {proposicao.sigla} {proposicao.numero}{proposicao.ano ? `/${proposicao.ano}` : ""}
                        </strong>
                        <span>{proposicao.tema}</span>
                        <p>{proposicao.andamento}</p>
                        <small>{proposicao.responsavel}</small>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="muted-note">Nenhuma proposição de autoria encontrada para este parlamentar.</p>
                )}
              </section>
            )}

            {activeTab === "Participacao" && (
              <section className="detail-card wide">
                <h3>Comissões, órgãos e frentes</h3>
                <div className="proposal-list">
                  <article>
                    <strong>Participação institucional</strong>
                    <span>{activeParlamentar.participacao}</span>
                  </article>
                  <article>
                    <strong>Temas de atuação</strong>
                    <span>{perfilTemas.length > 0 ? perfilTemas.join(", ") : "Sem temas classificados"}</span>
                  </article>
                </div>
              </section>
            )}

            {activeTab === "Transparencia" && (
              <section className="detail-card wide">
                <h3>Despesas (CEAP) por categoria</h3>
                {detalheLoading ? (
                  <p className="muted-note">Carregando despesas…</p>
                ) : perfilDespesas.length > 0 ? (
                  <div className="expense-list">
                    {perfilDespesas.map((item) => (
                      <div className="expense-row" key={item.categoria}>
                        <div>
                          <strong>{item.categoria}</strong>
                          <span>{item.valor}</span>
                        </div>
                        <div className="bar-track">
                          <span style={{ width: `${item.percentual}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted-note">Sem despesas CEAP registradas para este parlamentar no período coletado.</p>
                )}
              </section>
            )}

            {activeTab === "Tramitacao" && (
              <section className="detail-card wide">
                <h3>Tramitação das proposições</h3>
                {detalheLoading ? (
                  <p className="muted-note">Carregando tramitação…</p>
                ) : perfilProps.length > 0 ? (
                  <div className="timeline-list">
                    {perfilProps.slice(0, 12).map((proposicao, i) => (
                      <article key={`${proposicao.numero}-${i}`}>
                        <BarChart3 aria-hidden="true" size={18} />
                        <div>
                          <strong>
                            {proposicao.sigla} {proposicao.numero} — {proposicao.status}
                          </strong>
                          <p>{proposicao.andamento}</p>
                          <small>{proposicao.responsavel}</small>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="muted-note">Sem proposições com tramitação registrada para este parlamentar.</p>
                )}
              </section>
            )}
          </div>

          <div className="profile-actions">
            <a className="secondary-button" href={
                activeParlamentar.casa === "Senado"
                  ? `https://www25.senado.leg.br/web/senadores/senador/-/perfil/${activeParlamentar.id}`
                  : `https://www.camara.leg.br/deputados/${activeParlamentar.id}`
              } target="_blank" rel="noopener noreferrer">
              Abrir página pública
              <ArrowUpRight aria-hidden="true" size={16} />
            </a>
            <button className="secondary-button" type="button"
                    onClick={() => { generateParlamentarPDF(activeParlamentar); show("PDF gerado!"); }}>
              Gerar relatório PDF
              <Download aria-hidden="true" size={16} />
            </button>
          </div>
        </article>
        ) : (
          <article className="profile-card">
            <p style={{ padding: 24, color: "#64748b" }}>
              Nenhum parlamentar corresponde aos filtros atuais. Ajuste a busca por
              nome, casa ou UF para visualizar um perfil.
            </p>
          </article>
        )}
      </section>

      {compareA && compareB && (
        <section className="dashboard-grid comparison-section">
          <article className="profile-card comparison-card">
            <div className="profile-hero">
              <div className="profile-title">
                <p className="eyebrow">Comparação</p>
                <h2>{compareData?.a?.nome ?? "..."} vs {compareData?.b?.nome ?? "..."}</h2>
                <button className="secondary-button comparison-clear" onClick={clearCompare}>Limpar comparação</button>
              </div>
            </div>
            {comparing && <p className="muted-note" style={{padding: 16}}>Carregando comparação...</p>}
            {compareData && (
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Indicador</th>
                    <th>{compareData.a.nome}</th>
                    <th>{compareData.b.nome}</th>
                  </tr>
                </thead>
                <tbody>
                  {([
                    ["Partido", "partido"],
                    ["UF", "uf"],
                    ["Proposições", "proposicoes"],
                    ["Órgãos", "orgaos"],
                    ["Frentes", "frentes"],
                    ["Despesas", "despesas"],
                  ] as [string, keyof ComparacaoStats][]).map(([label, key]) => {
                    const valA = compareData.a[key];
                    const valB = compareData.b[key];
                    const fmt = key === "despesas"
                      ? (v: number | string) => (v as number).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
                      : (v: number | string) => String(v);
                    return (
                    <tr key={key}>
                      <td className="comp-label">{label}</td>
                      <td className="comp-val-a">{fmt(valA)}</td>
                      <td className="comp-val-b">{fmt(valB)}</td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </article>
        </section>
      )}

    </main>
      {ToastContainer}
    </>
  );
}
