// Tipos alinhados com o schema REAL do Supabase (colunas em português,
// após as migrations align_column_names + fix_expense_columns).
// Gerados/mantidos à mão; substituem o antigo supabase.ts (que usava
// nomes de coluna em inglês e estava quebrado).

export interface ParlamentarRow {
  id: number;
  source: string;
  external_id: string;
  nome: string;
  casa: string; // "camara" | "senado"
  partido: string | null;
  uf: string | null;
  email: string | null;
  foto_url: string | null;
  updated_at: string;
}

export interface PropositionRow {
  id: number;
  source: string;
  external_id: string;
  casa: string;
  sigla: string | null;
  numero: string | null;
  ano: number | null;
  ementa: string | null;
  data_apresentacao: string | null;
  updated_at: string;
}

export interface ExpenseRow {
  id: number;
  source: string;
  external_id: string;
  parlamentar_external_id: string | null;
  parlamentar_nome: string | null;
  ano: number | null;
  mes: number | null;
  categoria: string | null;
  fornecedor: string | null;
  documento: string | null;
  data: string | null;
  valor: number;
  updated_at: string;
}

export interface PropositionAuthorRow {
  id: number;
  proposition_source: string;
  proposition_external_id: string;
  parliamentarian_external_id: string | null;
  author_name: string | null;
  author_type: string | null;
  signature_order: number | null;
  proponent: boolean;
}

export interface PropositionTrackingRow {
  id: number;
  proposition_source: string;
  proposition_external_id: string;
  sequencia: number | null;
  data_hora: string | null;
  orgao_sigla: string | null;
  descricao_situacao: string | null;
  descricao_tramitacao: string | null;
  despacho: string | null;
  url: string | null;
}

// Resultado de busca por tema (subset de PropositionRow).
export interface BuscaProposicao {
  external_id: string;
  sigla: string | null;
  numero: string | null;
  ano: number | null;
  ementa: string | null;
}

// Linha da tabela de comparação lado a lado.
export interface ComparacaoStats {
  nome: string;
  partido: string;
  uf: string;
  proposicoes: number;
  orgaos: number;
  frentes: number;
  despesas: number;
}
