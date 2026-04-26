import { Source } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type StreamEvent =
  | { event: "status"; data: { stage: string; message: string } }
  | { event: "sources"; data: { sources: Source[]; confidence: string; verification_failed: boolean; refused: boolean } }
  | { event: "token"; data: { token: string } }
  | { event: "done"; data: { latency_ms: number } };

export async function* streamQuery(
  question: string,
  filters?: { doc_type?: string } | null
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_URL}/api/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, filters: filters || null }),
  });

  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      if (!block.trim()) continue;
      const lines = block.split("\n");
      let event = "";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
      }
      if (event && dataStr) {
        try {
          yield { event, data: JSON.parse(dataStr) } as StreamEvent;
        } catch {
          // skip malformed
        }
      }
    }
  }
}

export async function fetchEvalMetrics() {
  const res = await fetch(`${API_URL}/api/eval/latest`);
  if (!res.ok) throw new Error("Failed to fetch eval metrics");
  return res.json();
}

export async function fetchEvalHistory() {
  const res = await fetch(`${API_URL}/api/eval/history`);
  if (!res.ok) throw new Error("Failed to fetch eval history");
  return res.json();
}
