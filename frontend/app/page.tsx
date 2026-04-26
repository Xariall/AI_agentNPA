"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { ChatInput } from "./components/chat-input";
import { Message } from "./components/message";
import { WelcomeScreen } from "./components/welcome-screen";
import { useChatContext } from "./context/chat-context";
import { streamQuery } from "./lib/api";
import type { ChatMessage } from "./lib/types";

/* Language switcher component — exact from Figma */
function LangSwitcher({ lang, setLang }: { lang: "kz" | "ru"; setLang: (l: "kz" | "ru") => void }) {
  return (
    <div
      className="absolute z-20 flex"
      style={{
        top: 14,
        right: 16,
        outline: "1px solid var(--azure-37)",
        borderRadius: 5,
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setLang("kz")}
        style={{
          padding: "5px 16px",
          fontSize: 14,
          fontFamily: "Roboto, sans-serif",
          fontWeight: 400,
          lineHeight: "16px",
          background: lang === "kz" ? "var(--azure-37)" : "var(--grey-93)",
          color: lang === "kz" ? "var(--white-solid)" : "var(--azure-37)",
          borderRadius: 2,
        }}
      >
        қаз
      </button>
      <button
        onClick={() => setLang("ru")}
        style={{
          padding: "5px 16px",
          fontSize: 14,
          fontFamily: "Roboto, sans-serif",
          fontWeight: 400,
          lineHeight: "16px",
          background: lang === "ru" ? "var(--azure-37)" : "var(--grey-93)",
          color: lang === "ru" ? "var(--white-solid)" : "var(--azure-37)",
          borderRadius: 2,
        }}
      >
        рус
      </button>
    </div>
  );
}

/* Watermark — opacity-30, azure-51 color, positioned like in Figma */
function Watermark() {
  return (
    <div
      className="absolute pointer-events-none select-none"
      style={{
        top: 0,
        left: 0,
        width: "100%",
        height: 144,
        opacity: 0.3,
        overflow: "hidden",
      }}
    >
      <div className="relative" style={{ width: 224, height: 144 }}>
        {/* Exclamation diamond */}
        <div
          className="absolute"
          style={{
            width: 12,
            height: 12,
            left: 78,
            top: 24,
            transform: "rotate(45deg)",
            outline: "1px solid var(--azure-51)",
          }}
        />
        <span
          className="absolute text-center font-bold"
          style={{
            left: 79,
            top: 27,
            fontSize: 8,
            fontFamily: "Inter, sans-serif",
            color: "var(--azure-51)",
          }}
        >!</span>
        <span
          className="absolute text-center"
          style={{
            left: 59,
            top: 54,
            fontSize: 14,
            fontFamily: "Inter, sans-serif",
            color: "var(--azure-51)",
          }}
        >
          Тестовый
        </span>
        <span
          className="absolute text-center"
          style={{
            left: 75,
            top: 60,
            fontSize: 14,
            fontFamily: "Inter, sans-serif",
            color: "var(--azure-51)",
          }}
        >
          режим
        </span>
      </div>
    </div>
  );
}

export default function Home() {
  const { messages, setMessages, docTypeFilter } = useChatContext();
  const [isStreaming, setIsStreaming] = useState(false);
  const [lang, setLang] = useState<"kz" | "ru">("ru");
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
    /* Main area — flex-1, relative, white */
    <div className="flex-1 flex flex-col h-full relative overflow-hidden" style={{ background: "var(--white-solid)" }}>
      <Watermark />
      <LangSwitcher lang={lang} setLang={setLang} />

      {/* Chat area or welcome screen */}
      <div className="flex-1 overflow-y-auto relative z-10">
        {messages.length === 0 ? (
          <div className="flex flex-col justify-center items-center h-full">
            <WelcomeScreen onQuickAction={sendMessage} />

            {/* Input field positioned below welcome content — like in Figma */}
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
          className="flex-shrink-0 relative z-10"
          style={{
            borderTop: "1px solid var(--grey-91)",
            background: "var(--white-solid)",
            padding: "12px 16px",
          }}
        >
          <div className="max-w-3xl mx-auto">
            <ChatInput onSubmit={sendMessage} disabled={isStreaming} />
          </div>
        </div>
      )}
    </div>
  );
}
