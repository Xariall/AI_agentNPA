"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { ChatHistoryItem, ChatMessage, DocTypeFilter } from "../lib/types";

interface ChatContextValue {
  messages: ChatMessage[];
  setMessages: (msgs: ChatMessage[]) => void;
  history: ChatHistoryItem[];
  docTypeFilter: DocTypeFilter;
  setDocTypeFilter: (f: DocTypeFilter) => void;
  currentChatId: string;
  startNewChat: () => void;
  loadChat: (id: string) => void;
  saveCurrentChat: (msgs: ChatMessage[]) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessagesState] = useState<ChatMessage[]>([]);
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);
  const [docTypeFilter, setDocTypeFilter] = useState<DocTypeFilter>(null);
  const [currentChatId, setCurrentChatId] = useState<string>(() => crypto.randomUUID());

  useEffect(() => {
    try {
      const stored = localStorage.getItem("npa_chat_history");
      if (stored) setHistory(JSON.parse(stored));
    } catch {
      // ignore
    }
  }, []);

  const saveCurrentChat = (msgs: ChatMessage[]) => {
    if (msgs.length === 0) return;
    const title = msgs[0].content.slice(0, 50) + (msgs[0].content.length > 50 ? "…" : "");
    const item: ChatHistoryItem = { id: currentChatId, title, createdAt: Date.now(), messages: msgs };
    setHistory((prev) => {
      const filtered = prev.filter((h) => h.id !== currentChatId);
      const updated = [item, ...filtered].slice(0, 20);
      try { localStorage.setItem("npa_chat_history", JSON.stringify(updated)); } catch {}
      return updated;
    });
  };

  const setMessages = (msgs: ChatMessage[]) => {
    setMessagesState(msgs);
    saveCurrentChat(msgs);
  };

  const startNewChat = () => {
    setCurrentChatId(crypto.randomUUID());
    setMessagesState([]);
  };

  const loadChat = (id: string) => {
    const chat = history.find((h) => h.id === id);
    if (chat) {
      setCurrentChatId(id);
      setMessagesState(chat.messages);
    }
  };

  return (
    <ChatContext.Provider value={{
      messages, setMessages, history, docTypeFilter, setDocTypeFilter,
      currentChatId, startNewChat, loadChat, saveCurrentChat,
    }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
