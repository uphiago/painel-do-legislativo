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
  const { parlamentares, resumoCards, proposicoes, citizenQuestions,
          legislativeHighlights, connected, loading } = useLiveDashboard();

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
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const buscarTema = useCallback(async (tema: string) => {
    if (!tema || tema.length < 2) return;
    setSearching(true);
    const supabase = createClient();
    const { data } = await supabase
      .from("propositions")
      .select("external_id, sigla, numero, ano, ementa")
      .ilike("ementa", `%${tema}%`)
      .order("ano", { ascending: false })
      .limit(20);
    setSearchProposicoes(data ?? []);
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
    const [parl, propC, orgC, frtC] = await Promise.all([
      supabase.from("parlamentarians").select("nome,partido,uf").eq("external_id", extId).single(),
      supabase.from("proposition_authors").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
      supabase.from("organ_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
      supabase.from("front_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
    ]);
    const p = parl.data;
    return { nome: p?.nome ?? extId, partido: p?.partido ?? "?", uf: p?.uf ?? "?", proposicoes: propC.count ?? 0, orgaos: orgC.count ?? 0, frentes: frtC.count ?? 0 };
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
        if (!cancelled) setDetalhe({ forId: activeExtId, data: { proposicoes: [], temas: [], despesas: [] } });
      });
    return () => { cancelled = true; };
  }, [activeExtId]);

  const detalheReady = !!activeExtId && detalhe?.forId === activeExtId;
  const detalheLoading = !detalheReady;
  const perfilProps = detalheReady ? detalhe!.data.proposicoes : [];
  const perfilTemas = detalheReady ? detalhe!.data.temas : [];
  const perfilDespesas = detalheReady ? detalhe!.data.despesas : [];

  return (
    <>
    <main className="page-shell">
      <header className="dashboard-header">
        <div>
          <div className="hero-ribbon">
            <span className="hero-chip">Painel do Legislativo</span>
            {loading && <span className="hero-chip" style={{background:"#d97706",marginLeft:8}}>⏳ Carregando...</span>}
            {connected && <span className="hero-chip" style={{background:"#166534",marginLeft:8}}>● Dados oficiais</span>}
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

      <section className="data-map-grid" aria-label="Perguntas respondidas pelo painel">
        <article className="data-map-card civic-explain-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Para o cidadão</p>
              <h2>Respostas simples para perguntas legislativas</h2>
            </div>
          </div>
          <div className="citizen-question-list">
            {citizenQuestions.map((item, index) => (
              <article key={item.question}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{item.question}</strong>
                  <p>{item.answer}</p>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="collector-queue-card civic-queue-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">{searchTema ? `Busca: "${searchTema}"` : "Leitura do recorte"}</p>
              <h2>{searchTema
                ? `${searchProposicoes.length} resultados` + (searching ? " (buscando...)" : "")
                : "O que acompanhar primeiro"}</h2>
            </div>
          </div>
          <div className="collector-run-list">
            {(searchTema
              ? searchProposicoes
              : proposicoes
            ).slice(0, RECORTE_LIMIT).map((item, idx) => {
              const sigla = "sigla" in item ? item.sigla : undefined;
              const numero = "numero" in item ? item.numero : undefined;
              const ano = "ano" in item ? item.ano : undefined;
              const ementa = "ementa" in item ? item.ementa : undefined;
              const status = "status" in item ? item.status : undefined;
              const responsavel = "responsavel" in item ? item.responsavel : undefined;
              const impacto = "impacto" in item ? item.impacto : undefined;
              return (
                <article key={`${sigla}-${numero}-${idx}`}>
                  <BarChart3 aria-hidden="true" size={18} />
                  <div>
                    <strong>
                      {sigla} {numero}{ano ? `/${ano}` : ""}
                    </strong>
                    <span>{status ?? ementa?.slice(0, 50)}</span>
                  </div>
                  <p>{responsavel ?? ementa?.slice(0, 80)}</p>
                  <small>{impacto ?? "Resultado da busca"}</small>
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
                      nome: p.nome, cargo: p.cargo, partido: p.partido, uf: p.uf, proposicoes: p.proposicoes, participacao: p.participacao
                    }))); show("CSV exportado!"); }}>
              <Download aria-hidden="true" size={16} />
              CSV
            </button>
          </div>

          <div className="parlamentar-list">
            {loading && !connected ? (
              [...Array(5)].map((_, i) => (
                <div className="skeleton-row" key={i}>
                  <div className="skeleton skeleton-avatar" />
                  <div className="skeleton skeleton-text" style={{width:"60%"}} />
                  <div className="skeleton skeleton-metric" />
                </div>
              ))
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
                <span className="row-compare" onClick={(e) => { e.stopPropagation(); toggleCompare(parlamentar.id); }}
                      title="Selecionar para comparar"
                      style={{cursor:"pointer",padding:"0 4px",fontSize:11,color:(compareA===parlamentar.id||compareB===parlamentar.id)?"#2563eb":"#999"}}>
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
              <strong>{activeParlamentar.proposicoes}</strong>
              <span>proposições</span>
            </div>
            <div>
              <strong>{activeParlamentar.autoriaPrincipal}</strong>
              <span>como autor</span>
            </div>
            <div>
              <strong>{activeParlamentar.despesas}</strong>
              <span>cota usada</span>
            </div>
            <div>
              <strong>{activeParlamentar.presenca}</strong>
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
                  <h3>Leitura rápida</h3>
                  <p>{activeParlamentar.leituraPublica}</p>
                </section>
                <section className="detail-card wide evidence-card">
                  <h3>Mensagem pública</h3>
                  <p>{activeParlamentar.destaque}</p>
                </section>
                <section className="detail-card">
                  <h3>Temas recorrentes</h3>
                  {perfilTemas.length > 0 ? (
                    <div className="tag-list">
                      {perfilTemas.map((tema) => (
                        <span key={tema}>{tema}</span>
                      ))}
                    </div>
                  ) : (
                    <p className="muted-note">
                      {detalheLoading ? "Carregando temas…" : "Sem temas classificados para este parlamentar."}
                    </p>
                  )}
                </section>
                <section className="detail-card">
                  <h3>O que observar</h3>
                  <p>{activeParlamentar.proximaAcao}</p>
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
                    <p>
                      A página pública mostra onde o parlamentar trabalha, quais
                      colegiados acompanha e quais frentes parlamentares dialogam
                      com seus temas prioritários.
                    </p>
                  </article>
                  <article>
                    <strong>Temas de atuação</strong>
                    <span>{perfilTemas.length > 0 ? perfilTemas.join(", ") : "Sem temas classificados"}</span>
                    <p>
                      O recorte por tema ajuda gabinetes e cidadãos a apresentar
                      produção legislativa sem depender de linguagem técnica.
                    </p>
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

      <section className="collector-board civic-board" aria-label="Informações legislativas disponíveis">
        <div className="section-head collector-board-head">
          <div>
            <p className="eyebrow">O que o painel mostra</p>
            <h2>Leitura completa da atuação pública</h2>
            <p>
              A experiência pública valoriza a produção legislativa e traduz
              informações oficiais para quem precisa acompanhar, comparar e
              prestar contas à sociedade.
            </p>
          </div>
        </div>

        <div className="collector-grid">
          {legislativeHighlights.map((item) => {
            const Icon = item.icon;
            return (
              <article className="collector-card" key={item.title}>
                <div className="collector-card-top">
                  <Icon aria-hidden="true" size={21} />
                  <span>{item.metric}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      {compareA && compareB && (
        <section className="dashboard-grid" style={{marginTop: 24}}>
          <article className="profile-card" style={{maxWidth: "100%"}}>
            <div className="profile-hero">
              <div className="profile-title">
                <p className="eyebrow">Comparação</p>
                <h2>{compareData?.a?.nome ?? "..."} vs {compareData?.b?.nome ?? "..."}</h2>
                <button className="secondary-button" onClick={clearCompare} style={{marginTop:8}}>Limpar comparação</button>
              </div>
            </div>
            {comparing && <p style={{padding:16}}>Carregando comparação...</p>}
            {compareData && (
              <table style={{width:"100%",borderCollapse:"collapse",margin:"16px 0"}}>
                <thead><tr style={{background:"#f8fafc"}}>
                  <th style={{padding:8,textAlign:"left"}}>Indicador</th>
                  <th style={{padding:8,textAlign:"center"}}>{compareData.a.nome}</th>
                  <th style={{padding:8,textAlign:"center"}}>{compareData.b.nome}</th>
                </tr></thead>
                <tbody>
                  {([
                    ["Partido", "partido"],
                    ["UF", "uf"],
                    ["Proposições", "proposicoes"],
                    ["Órgãos", "orgaos"],
                    ["Frentes", "frentes"],
                  ] as [string, keyof ComparacaoStats][]).map(([label, key]) => (
                    <tr key={key} style={{borderBottom:"1px solid #e2e8f0"}}>
                      <td style={{padding:8,fontWeight:500}}>{label}</td>
                      <td style={{padding:8,textAlign:"center",fontWeight:"bold",color:"#2563eb"}}>{compareData.a[key]}</td>
                      <td style={{padding:8,textAlign:"center",fontWeight:"bold",color:"#059669"}}>{compareData.b[key]}</td>
                    </tr>
                  ))}
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
