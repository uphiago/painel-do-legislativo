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
import { useEffect, useMemo, useState } from "react";
import { useLiveDashboard } from "@/data/liveData";

const tabs = ["Resumo", "Projetos", "Participacao", "Transparencia", "Tramitacao"];

export default function Home() {
  const { parlamentares, resumoCards, proposicoes, despesas, citizenQuestions,
          legislativeHighlights, connected, loading } = useLiveDashboard();

  const [activeId, setActiveId] = useState(parlamentares[0]?.id ?? "");
  const [activeTab, setActiveTab] = useState(tabs[0]);

  useEffect(() => {
    if (parlamentares.length > 0 && !parlamentares.find((p) => p.id === activeId)) {
      setActiveId(parlamentares[0].id);
    }
  }, [parlamentares, activeId]);

  const activeParlamentar = useMemo(
    () => parlamentares.find((item) => item.id === activeId) ?? parlamentares[0],
    [activeId],
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
              <input placeholder="Ex.: Acácio Favacho, Alan Rick..." />
            </div>
          </label>

          <label className="field field-wide">
            <span>Tema ou palavra-chave</span>
            <div className="input-shell">
              <Filter aria-hidden="true" size={18} />
              <input placeholder="Ex.: segurança pública, saúde, educação..." />
            </div>
          </label>

          <label className="field">
            <span>Casa</span>
            <select defaultValue="Ambas">
              <option>Ambas</option>
              <option>Camara</option>
              <option>Senado</option>
            </select>
          </label>

          <label className="field">
            <span>UF</span>
            <select defaultValue="Todas">
              <option>Todas</option>
              <option>RJ</option>
              <option>SP</option>
              <option>BA</option>
              <option>MG</option>
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

          <button className="primary-button" type="button">
            <SlidersHorizontal aria-hidden="true" size={18} />
            Filtrar
          </button>
        </div>

        <div className="quick-pills">
          {["Segurança pública", "Saúde", "Educação", "Meio ambiente", "Frentes", "Tramitação"].map(
            (item) => (
              <button className="quick-pill" type="button" key={item}>
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
              <p className="eyebrow">Leitura do recorte</p>
              <h2>O que acompanhar primeiro</h2>
            </div>
          </div>
          <div className="collector-run-list">
            {proposicoes.map((item) => (
              <article key={`${item.sigla}-${item.numero}`}>
                <BarChart3 aria-hidden="true" size={18} />
                <div>
                  <strong>
                    {item.sigla} {item.numero}
                  </strong>
                  <span>{item.status}</span>
                </div>
                <p>{item.responsavel}</p>
                <small>{item.impacto}</small>
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
            {parlamentares.map((parlamentar) => (
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

    </main>
  );
}
