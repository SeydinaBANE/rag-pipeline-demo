import type {
  FeedbackPayload,
  HealthResponse,
  IngestResponse,
  QueryResponse,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("rag_token") ?? "";
}

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

export async function queryRAG(query: string): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/api/v1/query`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Query failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<QueryResponse>;
}

export async function* streamQuery(query: string): AsyncGenerator<string> {
  const res = await fetch(`${API_URL}/api/v1/query/stream`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Stream failed: ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    for (const line of chunk.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") return;
      try {
        const parsed = JSON.parse(data) as { token: string };
        yield parsed.token;
      } catch {
        // skip malformed SSE lines
      }
    }
  }
}

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/feedback`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Feedback failed: ${res.status}`);
}

export async function ingestFile(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/v1/ingest/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Ingest failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<IngestResponse>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json() as Promise<HealthResponse>;
}
