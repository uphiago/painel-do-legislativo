import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://painel-do-legislativo.vercel.app"),
  title: {
    default: "Painel do Legislativo",
    template: "%s · Painel do Legislativo",
  },
  description:
    "Perfis parlamentares, proposições, transparência e leitura de tramitação a partir de dados oficiais da Câmara dos Deputados e do Senado Federal.",
  keywords: [
    "câmara dos deputados",
    "senado federal",
    "parlamentares",
    "proposições",
    "transparência",
    "dados abertos",
    "legislativo",
  ],
  openGraph: {
    type: "website",
    locale: "pt_BR",
    title: "Painel do Legislativo",
    description:
      "Pesquise parlamentares, projetos e temas com dados oficiais da Câmara e do Senado.",
    siteName: "Painel do Legislativo",
  },
  twitter: {
    card: "summary_large_image",
    title: "Painel do Legislativo",
    description:
      "Pesquise parlamentares, projetos e temas com dados oficiais da Câmara e do Senado.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        {children}
        <footer style={{ textAlign: "center", padding: "32px 16px", color: "var(--ink-soft)", fontSize: "0.82rem" }}>
          Painel do Legislativo · Dados oficiais da Câmara dos Deputados e Senado Federal ·{" "}
          <a href="https://github.com/uphiago/painel-do-legislativo" style={{ color: "var(--accent)" }}>GitHub</a>
        </footer>
      </body>
    </html>
  );
}
