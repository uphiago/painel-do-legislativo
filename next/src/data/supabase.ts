export interface Parlamentar {
  id: number;
  source: string;
  external_id: string;
  name: string;
  house: string;
  party: string | null;
  uf: string | null;
  email: string | null;
  photo_url: string | null;
  updated_at: string;
}

export interface ProposicaoResumo {
  id: number;
  source: string;
  external_id: string;
  house: string;
  sigla: string | null;
  numero: string | null;
  ano: number | null;
  ementa: string | null;
  data_apresentacao: string | null;
  autor_principal: boolean | null;
  updated_at: string;
}

export interface Despesa {
  id: number;
  source: string;
  external_id: string;
  parliamentarian_external_id: string | null;
  parliamentarian_name: string | null;
  ano: number | null;
  mes: number | null;
  category: string | null;
  supplier: string | null;
  document_number: string | null;
  document_date: string | null;
  value: number;
  updated_at: string;
}

export interface PropositionAuthor {
  id: number;
  proposition_source: string;
  proposition_external_id: string;
  parliamentarian_external_id: string | null;
  author_name: string | null;
  author_type: string | null;
  signature_order: number | null;
  proponent: boolean;
}

export interface PropositionTheme {
  id: number;
  proposition_source: string;
  proposition_external_id: string;
  theme_code: string | null;
  theme_name: string | null;
  relevance: number;
}

export interface PropositionTracking {
  id: number;
  proposition_source: string;
  proposition_external_id: string;
  sequencia: number | null;
  data_hora: string | null;
  orgao_sigla: string | null;
  orgao_id: string | null;
  descricao_tramitacao: string | null;
  codigo_tipo_tramitacao: string | null;
  descricao_situacao: string | null;
  codigo_situacao: number | null;
  despacho: string | null;
  url: string | null;
}

export interface Organ {
  id: number;
  source: string;
  external_id: string;
  sigla: string | null;
  nome: string | null;
  tipo: string | null;
  casa: string | null;
}

export interface Party {
  id: number;
  source: string;
  external_id: string;
  sigla: string;
  nome: string | null;
  logo_url: string | null;
}

export interface DashboardStats {
  total_parlamentarians: number;
  total_propositions: number;
  total_expenses: number;
  total_organs: number;
}

export interface ParlamentarWithStats extends Parlamentar {
  proposition_count: number;
  expense_total: number;
  organs_count: number;
}
