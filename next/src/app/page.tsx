import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  FileText,
  Gavel,
  Search,
  Users,
} from "lucide-react";
import { landingEvidence } from "@/data/mockLegislativo";

export default function Home() {
  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div className="landing-copy">
          <div className="hero-ribbon">
            <span className="hero-chip">Painel do Legislativo</span>
          </div>

          <p className="eyebrow">Pesquisa legislativa para qualquer pessoa</p>
          <h1>Projetos, parlamentares e andamento em linguagem clara.</h1>
          <p className="landing-text">
            Perfis parlamentares, proposicoes, leitura de tramitação e
            transparência pública reunidos em uma interface para o cidadão
            entender o que foi proposto, onde está e o que falta acontecer.
          </p>

          <div className="landing-actions">
            <Link className="landing-primary" href="/dashboard">
              Abrir dashboard
              <ArrowRight aria-hidden="true" size={18} />
            </Link>
            <span className="landing-note">
              Experiência demonstrativa com dados oficiais de amostra.
            </span>
          </div>

          <div className="landing-stats" aria-label="Resumo do MVP">
            {landingEvidence.map((item, index) => {
              const Icon = [Users, FileText, Gavel][index] ?? BarChart3;
              return (
              <article key={item.label}>
                <Icon aria-hidden="true" size={18} />
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </article>
              );
            })}
          </div>
        </div>

        <aside className="landing-preview" aria-label="Previa do dashboard">
          <div className="preview-window">
            <div className="preview-topbar">
              <span>Dashboard</span>
              <strong>Dados oficiais organizados</strong>
            </div>

            <div className="preview-search">
              <Search aria-hidden="true" size={17} />
              <span>Acácio Favacho + saúde</span>
            </div>

            <div className="preview-kpis">
              <article>
                <strong>594</strong>
                <span>perfis oficiais</span>
              </article>
              <article>
                <strong>68 mil+</strong>
                <span>matérias organizadas</span>
              </article>
              <article>
                <strong>512 mil+</strong>
                <span>despesas oficiais</span>
              </article>
            </div>

            <div className="preview-grid">
              <div className="preview-list" aria-label="Lista de parlamentares">
                {[
                  ["Acácio Favacho", "Câmara - AP"],
                  ["Alan Rick", "Senado - AC"],
                  ["Segurança pública", "171 processos"],
                ].map(([name, meta], index) => (
                  <div className={index === 0 ? "is-selected" : ""} key={name}>
                    <span>{name.slice(0, 2).toUpperCase()}</span>
                    <strong>{name}</strong>
                    <small>{meta}</small>
                  </div>
                ))}
              </div>

              <article className="preview-profile">
                <span className="preview-label">Perfil parlamentar</span>
                <h2>Acácio Favacho</h2>
                <p>Deputado Federal - AP - MDB</p>
                <div className="preview-badges">
                  <span>5 órgãos</span>
                  <span>208 frentes</span>
                </div>
              </article>

              <article className="preview-card">
                <Gavel aria-hidden="true" size={18} />
                <strong>Tramitação</strong>
                <p>Situação atual, próximo passo e responsável pela etapa.</p>
              </article>

              <article className="preview-card">
                <BarChart3 aria-hidden="true" size={18} />
                <strong>Temas</strong>
                <div className="preview-bars">
                  <span style={{ width: "76%" }} />
                  <span style={{ width: "54%" }} />
                  <span style={{ width: "38%" }} />
                </div>
              </article>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
