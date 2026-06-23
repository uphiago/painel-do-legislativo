import {
  FileText,
  Gavel,
  Users,
} from "lucide-react";

export type Parlamentar = {
  id: string;
  nome: string;
  foto_url?: string | null;
  cargo: string;
  casa: "Camara" | "Senado";
  uf: string;
  partido: string;
  mandato: string;
  proposicoes: number;
  autoriaPrincipal: number;
  despesas: string;
  despesasValor?: number;
  participacao: string;
};

export const parlamentares: Parlamentar[] = [
  {
    id: "acacio-favacho",
    nome: "Acácio Favacho",
    cargo: "Deputado Federal",
    casa: "Camara",
    uf: "AP",
    partido: "MDB",
    mandato: "2023-2027",
    proposicoes: 5,
    autoriaPrincipal: 1,
    despesas: "CEAP 2024",
    participacao: "5 órgãos e 208 frentes",
  },
  {
    id: "alan-rick",
    nome: "Alan Rick",
    cargo: "Senador",
    casa: "Senado",
    uf: "AC",
    partido: "REPUBLICANOS",
    mandato: "2023-2031",
    proposicoes: 373,
    autoriaPrincipal: 0,
    despesas: "CEAPS 2024",
    participacao: "Comissões e processos legislativos",
  },
];

export const resumoCards = [
  {
    title: "Parlamentares",
    value: "593",
    label: "deputados e senadores em visão unificada",
    icon: Users,
  },
  {
    title: "Projetos e matérias",
    value: "68 mil+",
    label: "registros legislativos normalizados",
    icon: FileText,
  },
  {
    title: "Transparência",
    value: "512 mil+",
    label: "despesas públicas organizadas",
    icon: Gavel,
  },
];

export type ProposicaoDestaque = {
  sigla: string;
  numero: string;
  ano?: number | null;
  tema: string;
  status: string;
  andamento: string;
  responsavel: string;
  impacto: string;
};

export const proposicoes: ProposicaoDestaque[] = [
  {
    sigla: "PL",
    numero: "2546/2026",
    tema: "Saúde",
    status: "Aguardando despacho",
    andamento: "Projeto identificado na Câmara com autor, temas e andamento.",
    responsavel: "Mesa Diretora / despacho inicial",
    impacto: "Organiza uma pauta de saúde para acompanhamento do cidadão.",
  },
  {
    sigla: "PDL",
    numero: "29/2025",
    tema: "Segurança pública",
    status: "Aguardando relator",
    andamento: "Matéria encontrada no recorte de segurança pública.",
    responsavel: "Comissão responsável / relatoria",
    impacto: "Ajuda a entender onde o debate precisa avançar.",
  },
  {
    sigla: "RQS",
    numero: "41/2023",
    tema: "Processo legislativo",
    status: "Aprovada",
    andamento: "Registro do Senado com situação aprovada.",
    responsavel: "Plenário / secretaria legislativa",
    impacto: "Mostra conclusão do encaminhamento e preserva o link oficial.",
  },
];

export const graphNodes = [
  { id: "fontes", label: "Fontes oficiais", x: 72, y: 78, tone: "dark" },
  { id: "python", label: "Coletores Python", x: 250, y: 78, tone: "accent" },
  { id: "supabase", label: "Supabase", x: 430, y: 78, tone: "warm" },
  { id: "perfil", label: "Perfil parlamentar", x: 610, y: 78, tone: "light" },
  { id: "proposicoes", label: "Proposições", x: 250, y: 218, tone: "light" },
  { id: "tramitacao", label: "Tramitação", x: 430, y: 218, tone: "light" },
  { id: "despesas", label: "Despesas", x: 610, y: 218, tone: "light" },
  { id: "temas", label: "Temas", x: 72, y: 218, tone: "light" },
];

export const graphEdges = [
  ["fontes", "python"],
  ["python", "supabase"],
  ["supabase", "perfil"],
  ["python", "proposicoes"],
  ["python", "temas"],
  ["proposicoes", "tramitacao"],
  ["supabase", "despesas"],
  ["temas", "perfil"],
  ["tramitacao", "perfil"],
  ["despesas", "perfil"],
];
