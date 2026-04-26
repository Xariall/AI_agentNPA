"use client";

import { ChatMessage } from "../lib/types";
import { SourceCard } from "./source-card";
import { ConfidenceBadge } from "./confidence-badge";

interface Props {
  message: ChatMessage;
}

/* Small bot avatar — azure-37 circle */
function BotAvatar() {
  return (
    <div
      className="flex-shrink-0 flex items-center justify-center text-white text-xs font-bold"
      style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        background: "var(--azure-37)",
        fontFamily: "Roboto, sans-serif",
        fontWeight: 700,
        fontSize: 11,
      }}
    >
      ИИ
    </div>
  );
}

export function Message({ message }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="text-sm leading-relaxed"
          style={{
            maxWidth: "75%",
            padding: "10px 16px",
            borderRadius: 16,
            background: "var(--azure-37)",
            color: "var(--white-solid)",
            fontFamily: "Roboto, sans-serif",
            fontWeight: 400,
            fontSize: 14,
            lineHeight: "20px",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  /* Assistant message */
  return (
    <div className="flex gap-2.5 mb-5">
      <BotAvatar />
      <div className="flex-1 min-w-0">
        {/* Answer bubble */}
        <div
          style={{
            background: "var(--grey-97)",
            borderRadius: 16,
            padding: "12px 16px",
            fontSize: 14,
            fontFamily: "Roboto, sans-serif",
            fontWeight: 400,
            lineHeight: "22px",
            color: "var(--grey-8)",
          }}
        >
          {message.status === "streaming" && !message.content ? (
            <div className="flex items-center gap-1.5">
              <span className="dot1" />
              <span className="dot2" />
              <span className="dot3" />
              <span style={{ fontSize: 12, color: "var(--azure-51)", marginLeft: 6 }}>
                Обрабатываю запрос...
              </span>
            </div>
          ) : (
            <>
              <span className="whitespace-pre-wrap">{message.content}</span>
              {message.status === "streaming" && <span className="cursor-blink" />}
            </>
          )}

          {message.status === "error" && (
            <span style={{ color: "#dc2626" }}>{message.content}</span>
          )}
        </div>

        {/* Meta: confidence + latency */}
        {message.status === "done" && (
          <div className="flex items-center gap-2 mt-1.5 px-1">
            <ConfidenceBadge level={message.confidence} verificationFailed={message.verification_failed} />
            {message.latency_ms != null && (
              <span style={{ fontSize: 11, color: "var(--azure-51)", fontFamily: "Roboto, sans-serif" }}>
                {(message.latency_ms / 1000).toFixed(1)}с
              </span>
            )}
          </div>
        )}

        {/* Source cards */}
        {message.status === "done" && message.sources && message.sources.length > 0 && (
          <div className="mt-2.5 space-y-1.5">
            <div style={{
              fontSize: 11,
              fontWeight: 700,
              color: "var(--azure-51)",
              fontFamily: "Roboto, sans-serif",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              paddingLeft: 4,
            }}>
              Источники ({message.sources.length})
            </div>
            {message.sources.map((src, i) => (
              <SourceCard key={i} source={src} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
