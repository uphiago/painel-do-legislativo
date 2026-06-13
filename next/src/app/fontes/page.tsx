import {
  ArrowLeft,
  CheckCircle2,
  PauseCircle,
  ServerCog,
} from "lucide-react";
import Link from "next/link";
import {
  collectorCoverage,
  collectorFindings,
  collectorRuns,
  graphEdges,
  graphNodes,
  sourceHealth,
} from "@/data/mockLegislativo";

export default function FontesPage() {
  return (
    <main className="page-shell">
      <header className="dashboard-header">
        <div>
          <div className="hero-ribbon">
            <span className="hero-chip">Fontes e metodologia</span>
          </div>
          <p className="eyebrow">Bastidor do projeto</p>
          <h1>Como os dados entram no painel</h1>
          <p>
            Esta área organiza a cobertura das fontes oficiais, amostras de
            coleta, rotas candidatas e estrutura que depois alimenta o banco do
            projeto. Ela serve para equipe, validação e planejamento técnico.
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
            <p className="eyebrow">O que já dá para coletar</p>
            <h2>Cobertura descoberta</h2>
            <p>
              Os cards mostram o que os comandos Python já conseguiram buscar
              em APIs e arquivos oficiais. Scraping fica como alternativa quando
              a fonte não tiver rota estruturada suficiente.
            </p>
          </div>
          <span className="collector-badge">
            <ServerCog aria-hidden="true" size={16} />
            backend discovery
          </span>
        </div>

        <div className="collector-grid">
          {collectorCoverage.map((item) => {
            const Icon = item.icon;
            return (
              <article className="collector-card" key={item.title}>
                <div className="collector-card-top">
                  <Icon aria-hidden="true" size={21} />
                  <span>{item.status}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
                <strong>{item.metric}</strong>
              </article>
            );
          })}
        </div>
      </section>

      <section className="data-map-grid" aria-label="Mapa de dados e fila de coleta">
        <article className="data-map-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Grafo de dados</p>
              <h2>Da fonte oficial ao perfil parlamentar</h2>
            </div>
          </div>
          <svg
            className="data-graph"
            viewBox="0 0 700 300"
            role="img"
            aria-label="Grafo das fontes oficiais até o perfil parlamentar"
          >
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <path d="M 0 0 L 8 4 L 0 8 z" />
              </marker>
            </defs>
            {graphEdges.map(([from, to]) => {
              const fromNode = graphNodes.find((node) => node.id === from);
              const toNode = graphNodes.find((node) => node.id === to);
              if (!fromNode || !toNode) return null;
              return (
                <line
                  className="graph-edge"
                  key={`${from}-${to}`}
                  x1={fromNode.x}
                  x2={toNode.x}
                  y1={fromNode.y}
                  y2={toNode.y}
                />
              );
            })}
            {graphNodes.map((node) => (
              <g className={`graph-node ${node.tone}`} key={node.id}>
                <rect x={node.x - 58} y={node.y - 24} width="116" height="48" rx="8" />
                <text x={node.x} y={node.y + 4}>
                  {node.label}
                </text>
              </g>
            ))}
          </svg>
        </article>

        <article className="collector-queue-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Fila do coletor</p>
              <h2>Amostras que já rodaram</h2>
            </div>
          </div>
          <div className="collector-run-list">
            {collectorRuns.map((run) => (
              <article key={`${run.job}-${run.sample}`}>
                <CheckCircle2 aria-hidden="true" size={18} />
                <div>
                  <strong>{run.job}</strong>
                  <span>{run.sample}</span>
                </div>
                <p>{run.result}</p>
                <small>{run.target}</small>
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="findings-grid" aria-label="Achados tecnicos da coleta">
        {collectorFindings.map((item) => {
          const Icon = item.icon;
          return (
            <article className="finding-card" key={item.label}>
              <Icon aria-hidden="true" size={20} />
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <p>{item.detail}</p>
            </article>
          );
        })}
      </section>

      <section className="source-health-card" aria-label="Status das fontes oficiais">
        <div className="section-head compact">
          <div>
            <p className="eyebrow">Fontes oficiais</p>
            <h2>Status de coleta</h2>
          </div>
        </div>
        <div className="source-health-table">
          {sourceHealth.map((source) => (
            <article key={source.source}>
              {source.status === "respondendo" ? (
                <CheckCircle2 aria-hidden="true" size={18} />
              ) : (
                <PauseCircle aria-hidden="true" size={18} />
              )}
              <strong>{source.source}</strong>
              <span>{source.coverage}</span>
              <p>{source.use}</p>
              <small className={source.status === "respondendo" ? "ok" : "pending"}>
                {source.status}
              </small>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
