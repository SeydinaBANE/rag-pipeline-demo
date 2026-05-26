export interface SourceDocument {
  content: string;
  source: string;
  score?: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceDocument[];
  cached: boolean;
  prompt_version: string;
  latency_ms: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDocument[];
  cached?: boolean;
  latency_ms?: number;
  timestamp: Date;
  error?: string;
}

export interface IngestResponse {
  job_id: string;
  tenant_id: string;
  status: string;
  document_count: number;
}

export interface FeedbackPayload {
  query: string;
  answer: string;
  rating: 1 | -1;
  comment?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}
