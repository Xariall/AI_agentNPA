"use client";

import { useState, useRef } from "react";

interface Props {
  onSubmit: (q: string) => void;
  disabled?: boolean;
}

/* Mic icon — azure-37 */
function MicIcon() {
  return (
    <div className="w-6 h-6 flex-shrink-0">
      <img src="/mic.png" alt="Mic" className="w-full h-full object-contain" />
    </div>
  );
}

/* Send arrow — filled, azure-37 */
function SendIcon() {
  return (
    <div className="w-6 h-6 flex-shrink-0">
      <img src="/send.png" alt="Send" className="w-full h-full object-contain" />
    </div>
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
    <div className="bottom-wrapper">
      <div className="input-container">
        <div className="message-input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
            placeholder="Отправить сообщение..."
            disabled={disabled}
            className="input-field"
          />
        </div>

        <button className="voice-input-button" title="Голосовой ввод" disabled>
          <MicIcon />
        </button>

        <button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="send-button"
          style={{
            opacity: !value.trim() || disabled ? 0.4 : 1,
            cursor: !value.trim() || disabled ? "not-allowed" : "pointer",
          }}
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}
