import Link from "next/link";
import Image from "next/image";
import { ArrowRight, BarChart3, FileText, Gavel, Search, Users } from "lucide-react";

async function fetchLiveStats() {
  try {
    const { createClient } = await import("@/utils/supabase/server");
    const supabase = await createClient();
    const [parl, prop, exp] = await Promise.all([
      supabase.from("parlamentarians").select("*", { count: "exact", head: true }),
      supabase.from("propositions").select("*", { count: "exact", head: true }),
      supabase.from("expenses").select("*", { count: "exact", head: true }),
    ]);
    return {
      parlamentares: parl.count ?? 594,
      proposicoes: `${Math.round((prop.count ?? 107000) / 1000)} mil+`,
      despesas: `${Math.round((exp.count ?? 193000) / 1000)} mil+`,
    };
  } catch {
    return { parlamentares: 594, proposicoes: "107 mil+", despesas: "193 mil+" };
  }
}

export default async function Home() {
  const stats = await fetchLiveStats();

  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <div className="landing-copy">
          <div className="hero-ribbon">
            <span className="hero-chip">Painel do Legislativo</span>
            <span className="hero-chip" style={{ background: "#166534", marginLeft: 8 }}>● Dados oficiais</span>
          </div>

          <p className="eyebrow">Pesquisa legislativa para qualquer pessoa</p>
          <h1>Projetos, parlamentares e andamento em linguagem clara.</h1>
          <p className="landing-text">
            Perfis com fotos oficiais, proposições, tramitação explicada e transparência
            pública — tudo reunido para o cidadão entender o que foi proposto, onde está
            e quem pode fazer avançar.
          </p>

          <div className="landing-actions">
            <Link className="landing-primary" href="/dashboard">
              Abrir dashboard
              <ArrowRight aria-hidden="true" size={18} />
            </Link>
            <Link className="landing-secondary-link" href="/fontes">
              Fontes e metodologia
            </Link>
          </div>

          <div className="landing-stats" aria-label="Resumo">
            <article>
              <Users aria-hidden="true" size={18} />
              <strong>{stats.parlamentares}</strong>
              <span>perfis parlamentares</span>
            </article>
            <article>
              <FileText aria-hidden="true" size={18} />
              <strong>{stats.proposicoes}</strong>
              <span>proposições</span>
            </article>
            <article>
              <Gavel aria-hidden="true" size={18} />
              <strong>{stats.despesas}</strong>
              <span>despesas CEAP</span>
            </article>
          </div>
        </div>

        <aside className="landing-preview" aria-label="Previa do dashboard">
          <div className="preview-window">
            <div className="preview-topbar">
              <span>Dashboard</span>
              <strong>Painel do Legislativo</strong>
            </div>

            <div className="preview-search">
              <Search aria-hidden="true" size={17} />
              <span>Busque por nome, tema ou palavra-chave</span>
            </div>

            <div className="preview-photos">
              <PhotoStrip />
            </div>

            <div className="preview-grid">
              <article className="preview-feature">
                <Users aria-hidden="true" size={20} />
                <div>
                  <strong>Perfis completos</strong>
                  <p>Foto oficial, partido, UF, mandato, órgãos e frentes.</p>
                </div>
              </article>
              <article className="preview-feature">
                <Gavel aria-hidden="true" size={20} />
                <div>
                  <strong>Tramitação explicada</strong>
                  <p>Situação atual, próxima etapa e órgão responsável.</p>
                </div>
              </article>
              <article className="preview-feature">
                <BarChart3 aria-hidden="true" size={20} />
                <div>
                  <strong>Comparação lado a lado</strong>
                  <p>Selecione 2 parlamentares e compare atuação.</p>
                </div>
              </article>
              <article className="preview-feature">
                <FileText aria-hidden="true" size={20} />
                <div>
                  <strong>Exportação</strong>
                  <p>CSV dos parlamentares. PDF com perfil e proposições.</p>
                </div>
              </article>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}

function PhotoStrip() {
  const fotos = [
    "https://www.camara.leg.br/internet/deputado/bandep/204379.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/220593.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/204436.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/204554.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/220714.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/204379.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/220593.jpg",
    "https://www.camara.leg.br/internet/deputado/bandep/204436.jpg",
  ];

  return (
    <div className="photo-strip">
      {fotos.map((url, i) => (
        <div key={i} className="photo-circle" style={{ animationDelay: `${i * 0.15}s` }}>
          <Image src={url} alt="" width={48} height={64} unoptimized />
        </div>
      ))}
    </div>
  );
}
