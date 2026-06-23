import {
  Activity,
  Banknote,
  Database,
  FileText,
  Gavel,
  GitBranch,
  Landmark,
  Layers,
  SearchCheck,
  ServerCog,
  ShieldCheck,
  TableProperties,
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
  temas: string[];
  proposicoes: number;
  autoriaPrincipal: number;
  despesas: string;
  despesasValor?: number;
  presenca: string;
  snapshotLabel: string;
  destaque: string;
  coletaResumo: string;
  fontePrincipal: string;
  leituraPublica: string;
  proximaAcao: string;
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
    temas: ["Saúde", "Direito Civil e Processual Civil", "Orçamento"],
    proposicoes: 5,
    autoriaPrincipal: 1,
    despesas: "CEAP 2024",
    presenca: "5 órgãos",
    snapshotLabel: "snapshot Supabase",
    fontePrincipal: "Dados Abertos Câmara",
    destaque:
      "Perfil oficial organizado para mostrar atuação parlamentar, vínculos institucionais, temas de trabalho e proposições em acompanhamento.",
    coletaResumo:
      "Perfil com 13 campos, 5 órgãos, 208 frentes e despesas CEAP por ano disponíveis via API/arquivos.",
    leituraPublica:
      "A leitura pública mostra onde o mandato atua, quais temas aparecem com mais frequência e quais proposições merecem acompanhamento cidadão.",
    proximaAcao:
      "Acompanhar os projetos com despacho pendente e os itens em análise nas comissões responsáveis.",
    participacao: "5 órgãos e 208 frentes parlamentares identificadas",
  },
  {
    id: "alan-rick",
    nome: "Alan Rick",
    cargo: "Senador",
    casa: "Senado",
    uf: "AC",
    partido: "REPUBLICANOS",
    mandato: "2023-2031",
    temas: ["Processos legislativos", "Comissões", "CEAPS"],
    proposicoes: 373,
    autoriaPrincipal: 0,
    despesas: "CEAPS 2024",
    presenca: "comissões",
    snapshotLabel: "snapshot Supabase",
    fontePrincipal: "Senado Legislativo + Administrativo",
    destaque:
      "Perfil do Senado com processos legislativos, comissões e informações de atividade parlamentar reunidas no mesmo painel.",
    coletaResumo:
      "O endpoint novo /processo retornou 373 processos para o código parlamentar 5672.",
    leituraPublica:
      "O cidadão consegue ver o volume de processos, as comissões relacionadas e a situação das matérias sem navegar por páginas técnicas.",
    proximaAcao:
      "Priorizar matérias em tramitação ativa e destacar as que aguardam relatório, pauta ou deliberação.",
    participacao: "comissões, processos legislativos e registros administrativos",
  },
  {
    id: "tema-seguranca",
    nome: "Tema: segurança pública",
    cargo: "Recorte temático",
    casa: "Senado",
    uf: "BR",
    partido: "multi",
    mandato: "2025",
    temas: ["Segurança pública", "Projetos", "Processos"],
    proposicoes: 171,
    autoriaPrincipal: 0,
    despesas: "n/a",
    presenca: "n/a",
    snapshotLabel: "snapshot Supabase",
    fontePrincipal: "Senado /processo",
    destaque:
      "Recorte temático para enxergar como o Legislativo vem tratando segurança pública ao longo do ano.",
    coletaResumo:
      "Bom recorte para alimentar busca temática, ranking de assuntos e página de resultados por tema.",
    leituraPublica:
      "A busca por tema ajuda a reunir propostas de diferentes autores e casas legislativas em uma única visão de interesse público.",
    proximaAcao:
      "Separar os processos por situação, comissão responsável e tipo de matéria para orientar acompanhamento e cobrança.",
    participacao: "171 processos localizados em recorte temático de 2025",
  },
  {
    id: "sargento-portugal",
    nome: "Sargento Portugal",
    cargo: "Deputado Federal",
    casa: "Camara",
    uf: "RJ",
    partido: "PL",
    mandato: "2023-2027",
    temas: ["Segurança pública", "Justiça criminal", "Administração pública"],
    proposicoes: 38,
    autoriaPrincipal: 11,
    despesas: "a coletar",
    presenca: "a coletar",
    snapshotLabel: "snapshot Supabase",
    fontePrincipal: "Mock alvo",
    destaque:
      "Perfil prioritário para demonstrar a entrega: projetos, temas de atuação, transparência e próximos passos apresentados de forma simples.",
    coletaResumo:
      "Quando conectarmos a busca por nome/id da Câmara, este perfil entra no mesmo pipeline de coleta.",
    leituraPublica:
      "A página pública valoriza a produção legislativa, mostra o histórico do mandato e traduz a tramitação para o cidadão acompanhar.",
    proximaAcao:
      "Conectar o identificador oficial da Câmara, carregar proposições, órgãos, frentes e despesas da cota parlamentar.",
    participacao: "estrutura pronta para órgãos, frentes e comissões oficiais",
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
    icon: ShieldCheck,
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
    andamento:
      "Projeto identificado na Câmara com autor, temas e andamento. A próxima leitura pública explica o despacho e a comissão provável.",
    responsavel: "Mesa Diretora / despacho inicial",
    impacto: "Organiza uma pauta de saúde para acompanhamento do cidadão.",
  },
  {
    sigla: "PDL",
    numero: "29/2025",
    tema: "Segurança pública",
    status: "Aguardando relator",
    andamento:
      "Matéria encontrada no recorte de segurança pública. O painel destaca a fase e quem pode impulsionar o parecer.",
    responsavel: "Comissão responsável / relatoria",
    impacto: "Ajuda a entender onde o debate precisa avançar.",
  },
  {
    sigla: "RQS",
    numero: "41/2023",
    tema: "Processo legislativo",
    status: "Aprovada",
    andamento:
      "Registro do Senado com situação aprovada, autores e documento associado para consulta pública.",
    responsavel: "Plenário / secretaria legislativa",
    impacto: "Mostra conclusão do encaminhamento e preserva o link oficial.",
  },
];

export const despesas = [
  { categoria: "Câmara 2024-2026: prestação de contas", valor: "452 mil+ itens", percentual: 88 },
  { categoria: "Senado 2024-2026: CEAPS", valor: "50 mil+ itens", percentual: 62 },
  { categoria: "Comprovantes e documentos oficiais", valor: "por despesa", percentual: 74 },
  { categoria: "Fornecedores identificados", valor: "por CNPJ/CPF", percentual: 58 },
];

export const legislativeHighlights = [
  {
    title: "Atuação legislativa",
    description:
      "Projetos apresentados, matérias apoiadas, temas recorrentes e histórico por mandato.",
    metric: "autoria, coautoria e tema",
    icon: Gavel,
  },
  {
    title: "Tramitação explicada",
    description:
      "Situação atual, próxima etapa, comissão ou relatoria e orientação de acompanhamento.",
    metric: "o que falta acontecer",
    icon: GitBranch,
  },
  {
    title: "Participação institucional",
    description:
      "Comissões, órgãos, frentes parlamentares e espaços onde o parlamentar atua.",
    metric: "órgãos, frentes e comissões",
    icon: Landmark,
  },
  {
    title: "Transparência da atividade",
    description:
      "Cotas, despesas, fornecedores e documentos oficiais reunidos com contexto público.",
    metric: "prestação de contas",
    icon: Banknote,
  },
];

export const citizenQuestions = [
  {
    question: "O que esse parlamentar tem proposto?",
    answer:
      "O painel reúne projetos, temas, autoria e histórico para mostrar a produção legislativa de forma organizada.",
  },
  {
    question: "Onde o projeto está parado?",
    answer:
      "A tramitação é traduzida em etapa atual, próximo passo e instância que pode movimentar a matéria.",
  },
  {
    question: "Como acompanhar a atuação pública?",
    answer:
      "Perfis, comissões, frentes e despesas aparecem no mesmo contexto, sempre com caminho para a fonte oficial.",
  },
];

export const collectorCoverage = [
  {
    title: "Câmara - parlamentar",
    status: "Coletável agora",
    description: "Perfil, órgãos, frentes, despesas CEAP, proposições, autores, temas e tramitações.",
    metric: "512 deputados enriquecidos",
    icon: Landmark,
  },
  {
    title: "Senado - parlamentar",
    status: "Coletável agora",
    description: "Senadores, processos por autor, comissões, CEAPS, discursos, mandatos e cargos.",
    metric: "81 senadores enriquecidos",
    icon: Database,
  },
  {
    title: "Busca temática",
    status: "Coletável agora",
    description: "Senado /processo permite termo, autor, situação, datas e tramitação.",
    metric: "68 mil+ matérias normalizadas",
    icon: SearchCheck,
  },
  {
    title: "Prestação de contas",
    status: "Coletável agora",
    description: "CEAP Câmara e CEAPS Senado por ano, categoria, fornecedor, documento e valor líquido.",
    metric: "512 mil+ despesas oficiais",
    icon: ServerCog,
  },
];

export const collectorFindings = [
  {
    label: "Câmara CEAP",
    value: "desde 2008",
    detail: "Arquivos anuais CSV/JSON/ZIP e endpoint por deputado.",
    icon: TableProperties,
  },
  {
    label: "Tramitação Câmara",
    value: "por proposição",
    detail: "Autores, temas e tramitações vêm em endpoints separados.",
    icon: GitBranch,
  },
  {
    label: "Senado /processo",
    value: "endpoint novo",
    detail: "Substitui autorias legado e traz documento, autores e situação.",
    icon: Layers,
  },
  {
    label: "Scheduler",
    value: "Python",
    detail: "Worker periódico grava snapshots no Supabase para o Next ler.",
    icon: Activity,
  },
];

export const sourceHealth = [
  {
    source: "Câmara API v2",
    coverage: "78 endpoints",
    status: "respondendo",
    use: "perfis, proposições, autores, temas, tramitações, órgãos e frentes",
  },
  {
    source: "Câmara arquivos",
    coverage: "CEAP desde 2008",
    status: "respondendo",
    use: "carga anual grande de despesas por deputado",
  },
  {
    source: "Senado Legislativo",
    coverage: "157 endpoints",
    status: "respondendo",
    use: "senadores, processos, comissões, matérias, textos e votações",
  },
  {
    source: "Senado Administrativo",
    coverage: "81 endpoints",
    status: "respondendo",
    use: "CEAPS, escritórios, auxílio-moradia e contratações",
  },
  {
    source: "Portal CGU",
    coverage: "API com chave",
    status: "pendente",
    use: "emendas, convênios, transferências e execução federal",
  },
];

export const collectorRuns = [
  {
    job: "camara-deputado-full",
    sample: "Acácio Favacho",
    result: "13 campos, 5 órgãos, 208 frentes",
    target: "parlamentarians, memberships, fronts",
  },
  {
    job: "camara-proposicao-full",
    sample: "PL 2546/2026",
    result: "1 autor, 2 temas, 1 tramitação",
    target: "propositions, authors, themes, movements",
  },
  {
    job: "senado-processos",
    sample: "Alan Rick",
    result: "373 processos",
    target: "propositions, authors, movements",
  },
  {
    job: "senado-ceaps",
    sample: "2024",
    result: "10 despesas: R$ 27.338,27 na amostra",
    target: "expenses, suppliers",
  },
  {
    job: "camara-despesas",
    sample: "204379 / 2024",
    result: "10 despesas: R$ 6.576,04 na amostra",
    target: "expenses, suppliers",
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
