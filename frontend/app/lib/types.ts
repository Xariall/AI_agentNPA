export interface Source {
  doc_filename: string;
  doc_type: string;
  doc_number: string;
  article: string;
  paragraph: string;
  score: number;
  text_preview: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "done" | "error";
  sources?: Source[];
  confidence?: "high" | "medium" | "low";
  verification_failed?: boolean;
  refused?: boolean;
  latency_ms?: number;
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  createdAt: number;
  messages: ChatMessage[];
}

export type DocTypeFilter = string | null;
