"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { ChatInput } from "./components/chat-input";
import { Message } from "./components/message";
import { WelcomeScreen } from "./components/welcome-screen";
import { useChatContext } from "./context/chat-context";
import { streamQuery } from "./lib/api";
import type { ChatMessage } from "./lib/types";

function Watermark() {
  return <div className="watermark" />;
}

export default function Home() {
  const { messages, setMessages, docTypeFilter } = useChatContext();
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async (question: string) => {
    if (isStreaming) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = { id: assistantId, role: "assistant", content: "", status: "streaming" };
    const newMessages = [...messages, userMsg, assistantMsg];

    setMessages(newMessages);
    setIsStreaming(true);

    try {
      const filters = docTypeFilter ? { doc_type: docTypeFilter } : null;
      let accumulated = "";
      let msgMeta: Partial<ChatMessage> = {};

      for await (const event of streamQuery(question, filters)) {
        if (event.event === "sources") {
          msgMeta = {
            sources: event.data.sources,
            confidence: event.data.confidence as ChatMessage["confidence"],
            verification_failed: event.data.verification_failed,
            refused: event.data.refused,
          };
        } else if (event.event === "token") {
          accumulated += event.data.token;
          setMessages(newMessages.map((m) =>
            m.id === assistantId ? { ...m, content: accumulated, status: "streaming" } : m
          ));
        } else if (event.event === "done") {
          setMessages(newMessages.map((m) =>
            m.id === assistantId
              ? { ...m, content: accumulated, status: "done", latency_ms: event.data.latency_ms, ...msgMeta }
              : m
          ));
        }
      }
    } catch {
      setMessages(newMessages.map((m) =>
        m.id === assistantId
          ? { ...m, content: "Ошибка соединения с сервером.", status: "error" }
          : m
      ));
    } finally {
      setIsStreaming(false);
    }
  }, [messages, setMessages, isStreaming, docTypeFilter]);

  return (
    <div className="chat-window">
      <Watermark />

      {/* Chat area or welcome screen */}
      <div className="flex-1 w-full overflow-y-auto relative z-10">
        {messages.length === 0 ? (
          <div className="flex flex-col justify-center items-center h-full">
            <WelcomeScreen onQuickAction={sendMessage} />

            {/* Input field positioned below welcome content */}
            <div className="w-full max-w-[1100px] mt-4 px-4">
              <ChatInput onSubmit={sendMessage} disabled={isStreaming} />
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 pt-16 pb-4">
            {messages.map((msg) => (
              <Message key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Persistent input when chatting */}
      {messages.length > 0 && (
        <div
          className="flex-shrink-0 relative z-10 w-full flex justify-center py-4"
          style={{
            borderTop: "1px solid var(--border-mischka)",
            background: "var(--bg-white)",
          }}
        >
          <div className="w-full max-w-[1100px] px-4">
            <ChatInput onSubmit={sendMessage} disabled={isStreaming} />
          </div>
        </div>
      )}
    </div>
  );
}
