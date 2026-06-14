"use client";

import { jsPDF } from "jspdf";
import { createClient } from "@/utils/supabase/client";

export async function generateParlamentarPDF(parlamentar: {
  id: string;
  nome: string;
  cargo: string;
  partido: string;
  uf: string;
  casa: string;
  proposicoes: number;
  mandato: string;
  leituraPublica: string;
  participacao: string;
}) {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const M = 20;
  let y = M;

  // Header
  doc.setFontSize(18);
  doc.setTextColor(30, 41, 59);
  doc.text("Painel do Legislativo", M, y);
  y += 8;

  doc.setFontSize(12);
  doc.setTextColor(100, 116, 139);
  doc.text("Relatório de Perfil Parlamentar", M, y);
  y += 6;
  doc.setFontSize(9);
  doc.text(`Gerado em ${new Date().toLocaleDateString("pt-BR")}`, M, y);
  y += 10;

  // Divider
  doc.setDrawColor(226, 232, 240);
  doc.line(M, y, 190, y);
  y += 8;

  // Parliamentarian info
  doc.setFontSize(14);
  doc.setTextColor(15, 23, 42);
  doc.text(parlamentar.nome, M, y);
  y += 6;

  doc.setFontSize(10);
  doc.setTextColor(71, 85, 105);
  doc.text(`${parlamentar.cargo} | ${parlamentar.partido} | ${parlamentar.uf} | ${parlamentar.casa}`, M, y);
  y += 5;
  doc.text(`Mandato: ${parlamentar.mandato}`, M, y);
  y += 8;

  // KPI cards
  doc.setFontSize(16);
  doc.setTextColor(37, 99, 235);
  doc.text(String(parlamentar.proposicoes ?? 0), M, y + 5);
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  doc.text("proposições", M, y + 11);

  // Fetch real data from Supabase
  const supabase = createClient();

  // Propositions
  const { data: props } = await supabase
    .from("proposition_authors")
    .select("proposition_external_id")
    .eq("parliamentarian_external_id", parlamentar.id)
    .eq("proposition_source", "camara")
    .limit(20);

  let propIds: string[] = [];
  if (props) propIds = props.map((p: any) => p.proposition_external_id);

  y += 18;

  if (propIds.length > 0) {
    const { data: propDetail } = await supabase
      .from("propositions")
      .select("sigla,numero,ano,ementa")
      .in("external_id", propIds)
      .order("ano", { ascending: false })
      .limit(20);

    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text("Proposições recentes", M, y);
    y += 6;

    if (propDetail?.length) {
      doc.setFontSize(8);
      for (const p of propDetail.slice(0, 15)) {
        if (y > 270) { doc.addPage(); y = M; }
        doc.setTextColor(37, 99, 235);
        doc.text(`${p.sigla} ${p.numero}/${p.ano}`, M, y);
        doc.setTextColor(71, 85, 105);
        const em = (p.ementa ?? "").slice(0, 100);
        doc.text(em, M + 2, y + 4);
        y += 10;
      }
    }
  }

  // Expenses
  const { data: expenses } = await supabase
    .from("expenses")
    .select("categoria,valor")
    .eq("parlamentar_external_id", parlamentar.id)
    .order("valor", { ascending: false })
    .limit(10);

  y += 8;
  if (y > 250) { doc.addPage(); y = M; }

  if (expenses?.length) {
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text("Despesas (CEAP)", M, y);
    y += 6;

    doc.setFontSize(8);
    for (const e of expenses) {
      if (y > 275) { doc.addPage(); y = M; }
      doc.setTextColor(71, 85, 105);
      doc.text((e.categoria ?? "Outros").slice(0, 50), M, y);
      doc.setTextColor(37, 99, 235);
      doc.text(`R$ ${(e.valor ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`, 150, y);
      y += 5;
    }
  }

  // Footer
  doc.setFontSize(7);
  doc.setTextColor(148, 163, 184);
  doc.text("Painel do Legislativo — Dados oficiais da Câmara dos Deputados e Senado Federal", M, 290);
  doc.text("github.com/uphiago/painel-do-legislativo", M, 294);

  doc.save(`relatorio-${parlamentar.nome.toLowerCase().replace(/\s+/g, "-")}.pdf`);
}
