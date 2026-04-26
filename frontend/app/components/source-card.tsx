"use client";

import { useState } from "react";
import { Source } from "../lib/types";

interface Props {
  source: Source;
  index: number;
}

/* Document icon — azure-51 */
function DocIcon() {
  return (
    <svg width="14" height="16" viewBox="0 0 14 16" fill="none" style={{ flexShrink: 0, marginTop: 2 }}>
      <rect x="0" y="0" width="10" height="13" rx="2" fill="var(--azure-83)" />
      <rect x="2" y="3" width="6" height="1.2" rx="0.6" fill="var(--azure-37)" />
      <rect x="2" y="5.5" width="6" height="1.2" rx="0.6" fill="var(--azure-37)" />
      <rect x="2" y="8" width="4" height="1.2" rx="0.6" fill="var(--azure-37)" />
    </svg>
  );
}

export function SourceCard({ source, index }: Props) {
  const [expanded, setExpanded] = useState(false);

  const label = [
    source.doc_filename.replace(/\.[^.]+$/, ""),
    source.article ? `Статья ${source.article}` : null,
    source.paragraph ? `п. ${source.paragraph}` : null,
  ].filter(Boolean).join(" · ");

  const scoreColor =
    source.score > 5 ? "#16a34a" :
    source.score > 2 ? "#d97706" :
    "#dc2626";

  return (
    <div
      style={{
        border: "1px solid var(--grey-91)",
        borderRadius: 8,
        background: "var(--white-solid)",
        overflow: "hidden",
        transition: "border-color 0.15s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--azure-83)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--grey-91)")}
    >
      <button
        className="w-full flex items-start gap-2 text-left"
        style={{ padding: "10px 12px" }}
        onClick={() => setExpanded(!expanded)}
      >
        <DocIcon />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span style={{
              fontSize: 12,
              fontWeight: 500,
              color: "var(--grey-8)",
              fontFamily: "Roboto, sans-serif",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {label}
            </span>
            {source.doc_type && (
              <span style={{
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: 4,
                background: "var(--grey-93)",
                color: "var(--azure-37)",
                fontFamily: "Roboto, sans-serif",
                fontWeight: 500,
                flexShrink: 0,
                textTransform: "capitalize",
              }}>
                {source.doc_type}
              </span>
            )}
          </div>
          {source.doc_number && (
            <div style={{ fontSize: 11, color: "var(--azure-51)", marginTop: 2, fontFamily: "Roboto, sans-serif" }}>
              № {source.doc_number}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span style={{ fontSize: 11, fontFamily: "monospace", fontWeight: 600, color: scoreColor }}>
            {source.score.toFixed(2)}
          </span>
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.15s" }}
          >
            <path d="M2 4L6 8L10 4" stroke="var(--azure-51)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>

      {expanded && source.text_preview && (
        <div style={{ borderTop: "1px solid var(--grey-91)", padding: "8px 12px 10px 12px" }}>
          <p style={{
            fontSize: 12,
            color: "var(--grey-8)",
            lineHeight: "18px",
            fontFamily: "Roboto, sans-serif",
            display: "-webkit-box",
            WebkitLineClamp: 6,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}>
            {source.text_preview}
          </p>
        </div>
      )}
    </div>
  );
}
