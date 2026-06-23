import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page-shell" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", textAlign: "center" }}>
      <h1 style={{ fontSize: "4rem", color: "var(--accent-strong)", marginBottom: 8 }}>404</h1>
      <p className="eyebrow">Página não encontrada</p>
      <p style={{ marginBottom: 24, color: "var(--ink-soft)" }}>
        A rota que você procura não existe ou foi movida.
      </p>
      <Link className="secondary-button" href="/dashboard">Ir para o dashboard</Link>
    </main>
  );
}
