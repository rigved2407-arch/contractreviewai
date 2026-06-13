export interface Clause {
  id: string;
  contract_id: string;
  clause_type: string;
  clause_text: string;
  section_header: string | null;
  risk_level: string | null;
  risk_reason: string | null;
  suggested_redline: string | null;
  is_accepted: boolean;
  created_at: string;
}

export interface Contract {
  id: string;
  filename: string;
  file_type: string | null;
  status: string;
  summary: string | null;
  risk_score: number | null;
  created_at: string;
  updated_at: string;
  clauses: Clause[];
}

export interface ContractListItem {
  id: string;
  filename: string;
  file_type: string | null;
  status: string;
  risk_score: number | null;
  created_at: string;
}

export interface PlaybookRule {
  id: string;
  playbook_id: string;
  clause_type: string;
  preferred_position: string;
  risk_if_missing: string | null;
  risk_if_deviates: string | null;
  is_required: boolean;
  priority: number;
  created_at: string;
}

export interface Playbook {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  rules: PlaybookRule[];
}

export interface AnalysisResult {
  contract_id: string;
  status: string;
  total_clauses: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  risk_score: number;
  clauses: Clause[];
  redline_url: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  organization_id: string;
  role: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  gstin?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}
