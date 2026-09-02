export type NavigationTab = 'dashboard' | 'comparison' | 'benchmarks' | 'reliability';

export interface EvidenceUnit {
  id: string;
  source: string;
  page: number | null;
  text: string;
  program: string;
  score: number;
  kind: string;
  citation: string;
}

export interface VerificationResult {
  status: string;
  confidence: number;
  rationale: string;
  supported_claims: string[];
  unsupported_claims: string[];
}

export interface AnswerResult {
  status: string;
  answer: string;
  programs: string[];
  latency_ms: number;
  cache_hit: boolean;
  verification: VerificationResult | null;
  evidence: EvidenceUnit[];
}

export interface ProgramInfo {
  code: string;
  display: string;
  file: string;
}

export interface HealthResult {
  ok: boolean;
  detail: string;
  model: string;
  evidence_units: number;
  programs: ProgramInfo[];
}

export interface BenchmarkRow {
  id: number;
  question: string;
  type: string;
  passed: boolean;
  status: string;
  note: string;
  latency_ms: number;
}

export interface BenchmarkResult {
  passed: number;
  total: number;
  score: number;
  rows: BenchmarkRow[];
}
