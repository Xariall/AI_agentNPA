"use client";

import { useState, useRef } from "react";

interface Props {
  onSubmit: (q: string) => void;
  disabled?: boolean;
}

/* Mic icon — azure-37 */
function MicIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style={{ color: "var(--azure-37)" }}>
      <rect x="9" y="2" width="6" height="12" rx="3" fill="currentColor"/>
      <path d="M5 10a7 7 0 0014 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="12" y1="17" x2="12" y2="22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="9" y1="22" x2="15" y2="22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

/* Send arrow — filled, azure-37 */
function SendIcon() {
  return (
    <svg width="14" height="20" viewBox="0 0 14 20" fill="none">
      <path d="M7 0L0 7H5V20H9V7H14L7 0Z" fill="var(--azure-37)"/>
    </svg>
  );
}

export function ChatInput({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
    setValue("");
    inputRef.current?.focus();
  };

  return (
    /* Outer container — w-[1100px] equivalent, flex row */
    <div className="w-full relative" style={{ height: 48 }}>
      {/* Input field: rounded-3xl, outline azure-83 */}
      <div
        className="absolute inset-0 flex items-center"
        style={{
          right: 80, /* leave room for send button */
        }}
      >
        <div
          className="flex-1 flex items-center"
          style={{
            background: "var(--white-solid)",
            borderRadius: 999,
            outline: "1px solid var(--azure-83)",
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
            placeholder="Отправить сообщение..."
            disabled={disabled}
            style={{
              flex: 1,
              padding: "12px 24px",
              background: "transparent",
              border: "none",
              outline: "none",
              fontSize: 16,
              fontWeight: 400,
              fontFamily: "Roboto, sans-serif",
              color: "rgba(0,0,0,0.5)",
            }}
          />
        </div>
      </div>

      {/* Send button — positioned right of input */}
      <div
        className="absolute flex items-end gap-0"
        style={{ right: 0, bottom: 8, padding: "4px 4px 3px 4px", borderRadius: 5 }}
      >
        {/* Voice tooltip (hidden by default like in Figma) */}
        <button
          disabled
          title="Голосовой ввод"
          className="flex items-center justify-center"
          style={{ width: 24, height: 24 }}
        >
          <MicIcon />
        </button>
      </div>

      {/* Arrow send — slightly left of mic */}
      <button
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        className="absolute flex items-center justify-center"
        style={{
          right: 40,
          top: 8,
          width: 28,
          height: 24,
          borderRadius: 5,
          opacity: !value.trim() || disabled ? 0.4 : 1,
          cursor: !value.trim() || disabled ? "not-allowed" : "pointer",
        }}
      >
        <SendIcon />
      </button>
    </div>
  );
}
