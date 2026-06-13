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
import { useEffect, useMemo, useState, useCallback } from "react";
import { useLiveDashboard } from "@/data/liveData";
import { createClient } from "@/utils/supabase/client";
import { downloadCSV } from "@/data/comparacao";

const tabs = ["Resumo", "Projetos", "Participacao", "Transparencia", "Tramitacao"];
const UFS = ["Todas","AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];

export default function Home() {
  const { parlamentares, resumoCards, proposicoes, despesas, citizenQuestions,
          legislativeHighlights, connected, loading } = useLiveDashboard();

  const [activeId, setActiveId] = useState(parlamentares[0]?.id ?? "");
  const [activeTab, setActiveTab] = useState(tabs[0]);

  // Search state
  const [searchNome, setSearchNome] = useState("");
  const [searchTema, setSearchTema] = useState("");
  const [searchCasa, setSearchCasa] = useState("Ambas");
  const [searchUf, setSearchUf] = useState("Todas");
  const [searchProposicoes, setSearchProposicoes] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  // Comparison
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  const [compareData, setCompareData] = useState<any>(null);
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

  const loadStatsFn = async (supabase: ReturnType<typeof createClient>, extId: string) => {
    const [parl, propC, orgC, frtC] = await Promise.all([
      supabase.from("parlamentarians").select("nome,partido,uf").eq("external_id", extId).single(),
      supabase.from("proposition_authors").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
      supabase.from("organ_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
      supabase.from("front_memberships").select("*", { count: "exact", head: true }).eq("parliamentarian_external_id", extId),
    ]);
    const p = parl.data;
    return { nome: p?.nome ?? extId, partido: p?.partido ?? "?", uf: p?.uf ?? "?", proposicoes: propC.count ?? 0, orgaos: orgC.count ?? 0, frentes: frtC.count ?? 0 };
  };

  const buscarTema = useCallback(async (tema: string) => {
    if (!tema) return;
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

  // Filter parliamentarians based on search
  const filteredParlamentares = useMemo(() => {
    return parlamentares.filter((p) => {
      if (searchNome && !p.nome.toLowerCase().includes(searchNome.toLowerCase())) return false;
      if (searchCasa !== "Ambas" && p.casa !== searchCasa) return false;
      if (searchUf !== "Todas" && p.uf !== searchUf) return false;
      return true;
    });
  }, [parlamentares, searchNome, searchCasa, searchUf]);

  useEffect(() => {
    if (filteredParlamentares.length > 0 && !filteredParlamentares.find((p) => p.id === activeId)) {
      setActiveId(filteredParlamentares[0].id);
    }
  }, [filteredParlamentares, activeId]);

  const activeParlamentar = useMemo(
    () => filteredParlamentares.find((item) => item.id === activeId) ?? filteredParlamentares[0],
    [activeId, filteredParlamentares],
  );

  return (
    <main className="page-shell">
      <header className="dashboard-header">
        <div>
          <div className="hero-ribbon">
            <span className="hero-chip">Painel do Legislativo</span>
            {connected && <span className="hero-chip live-chip" style={{background:"#166534",marginLeft:8}}>● Dados oficiais</span>}
          </div>
          <p className="eyebrow">Acompanhamento publico</p>
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
                     value={searchTema} onChange={(e) => setSearchTema(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && buscarTema(searchTema)} />
            </div>
          </label>

          <label className="field">
            <span>Casa</span>
            <select value={searchCasa} onChange={(e) => setSearchCasa(e.target.value)}>
              <option>Ambas</option>
              <option>Camara</option>
              <option>Senado</option>
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
            <select defaultValue="Atividade">
              <option>Atividade</option>
              <option>Proposicoes</option>
              <option>Presenca</option>
              <option>Transparencia</option>
            </select>
          </label>

          <button className="primary-button" type="button" onClick={() => buscarTema(searchTema)}>
            <SlidersHorizontal aria-hidden="true" size={18} />
            Filtrar
          </button>
        </div>

        <div className="quick-pills">
          {["Segurança pública", "Saúde", "Educação", "Meio ambiente", "Frentes", "Tramitação"].map(
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
            {(searchTema ? searchProposicoes : proposicoes).map((item: any) => (
              <article key={`${item.sigla}-${item.numero}`}>
                <BarChart3 aria-hidden="true" size={18} />
                <div>
                  <strong>
                    {item.sigla} {item.numero}{item.ano ? `/${item.ano}` : ""}
                  </strong>
                  <span>{item.status ?? item.ementa?.slice(0, 50)}</span>
                </div>
                <p>{item.responsavel ?? item.ementa?.slice(0, 80)}</p>
                <small>{item.impacto ?? "Resultado da busca"}</small>
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <aside className="directory-card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Para acompanhar parlamentares</p>
              <h2>Diretorio publico</h2>
            </div>
            <button className="mini-button" type="button">
              <Download aria-hidden="true" size={16} />
              CSV
            </button>
          </div>

          <div className="parlamentar-list">
            {filteredParlamentares.map((parlamentar) => (
              <button
                className={`parlamentar-row ${
                  parlamentar.id === activeParlamentar.id ? "is-active" : ""
                }`}
                key={parlamentar.id}
                onClick={() => setActiveId(parlamentar.id)}
                type="button"
              >
                <span className="avatar" aria-hidden="true">
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
            ))}
          </div>
        </aside>

        <article className="profile-card">
          <div className="profile-hero">
            <div className="profile-photo" aria-hidden="true">
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
                <span>{activeParlamentar.casa}</span>
                <span>{activeParlamentar.uf}</span>
                <span>{activeParlamentar.temas[0]}</span>
                <span>{activeParlamentar.participacao}</span>
              </div>
            </div>
          </div>

          <div className="profile-kpis">
            <div>
              <strong>{activeParlamentar.proposicoes}</strong>
              <span>proposicoes</span>
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
              <span>participacao</span>
            </div>
          </div>

          <div className="tabs" role="tablist" aria-label="Secoes do perfil">
            {tabs.map((tab) => (
              <button
                className={tab === activeTab ? "is-active" : ""}
                key={tab}
                onClick={() => setActiveTab(tab)}
                type="button"
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="profile-content">
            {activeTab === "Resumo" && (
              <>
                <section className="detail-card wide">
                  <h3>Leitura rapida</h3>
                  <p>{activeParlamentar.leituraPublica}</p>
                </section>
                <section className="detail-card wide evidence-card">
                  <h3>Mensagem publica</h3>
                  <p>{activeParlamentar.destaque}</p>
                </section>
                <section className="detail-card">
                  <h3>Temas recorrentes</h3>
                  <div className="tag-list">
                    {activeParlamentar.temas.map((tema) => (
                      <span key={tema}>{tema}</span>
                    ))}
                  </div>
                </section>
                <section className="detail-card">
                  <h3>O que observar</h3>
                  <p>{activeParlamentar.proximaAcao}</p>
                </section>
              </>
            )}

            {activeTab === "Projetos" && (
              <section className="detail-card wide">
                <h3>Projetos em destaque</h3>
                <div className="proposal-list">
                  {proposicoes.map((proposicao) => (
                    <article key={`${proposicao.sigla}-${proposicao.numero}`}>
                      <strong>
                        {proposicao.sigla} {proposicao.numero}
                      </strong>
                      <span>{proposicao.tema}</span>
                      <p>{proposicao.andamento}</p>
                      <small>{proposicao.responsavel}</small>
                    </article>
                  ))}
                </div>
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
                      A página pública pode mostrar onde o parlamentar trabalha,
                      quais colegiados acompanha e quais frentes parlamentares
                      dialogam com seus temas prioritários.
                    </p>
                  </article>
                  <article>
                    <strong>Temas de atuação</strong>
                    <span>{activeParlamentar.temas.join(", ")}</span>
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
                <h3>Transparência da atividade parlamentar</h3>
                <div className="expense-list">
                  {despesas.map((item) => (
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
              </section>
            )}

            {activeTab === "Tramitacao" && (
              <section className="detail-card wide">
                <h3>O que falta acontecer</h3>
                <div className="timeline-list">
                  {proposicoes.map((proposicao) => (
                    <article key={proposicao.numero}>
                      <BarChart3 aria-hidden="true" size={18} />
                      <div>
                        <strong>
                          {proposicao.sigla} {proposicao.numero} -{" "}
                          {proposicao.status}
                        </strong>
                        <p>{proposicao.andamento}</p>
                        <small>{proposicao.responsavel}</small>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </div>

          <div className="profile-actions">
            <button className="secondary-button" type="button">
              Abrir pagina publica
              <ArrowUpRight aria-hidden="true" size={16} />
            </button>
            <button className="secondary-button" type="button">
              Gerar relatorio PDF
              <Download aria-hidden="true" size={16} />
            </button>
          </div>
        </article>
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
                  {[
                    ["Partido", "partido"],
                    ["UF", "uf"],
                    ["Proposições", "proposicoes"],
                    ["Órgãos", "orgaos"],
                    ["Frentes", "frentes"],
                  ].map(([label, key]) => (
                    <tr key={key} style={{borderBottom:"1px solid #e2e8f0"}}>
                      <td style={{padding:8,fontWeight:500}}>{label}</td>
                      <td style={{padding:8,textAlign:"center",fontWeight:"bold",color:"#2563eb"}}>{(compareData.a as any)[key]}</td>
                      <td style={{padding:8,textAlign:"center",fontWeight:"bold",color:"#059669"}}>{(compareData.b as any)[key]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        </section>
      )}

    </main>
  );
}
