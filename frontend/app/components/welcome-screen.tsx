"use client";

import Link from "next/link";

const QUICK_ACTIONS = [
  "Каким приказом регулируется регистрация медицинских изделий в РК?",
  "Какие документы нужны для регистрации медицинских изделий?",
];

interface Props {
  onQuickAction: (q: string) => void;
}

/* Custom robot SVG — own asset, not НЦЭЛС IP */
function RobotSvg() {
  return (
    <svg width="60" height="68" viewBox="0 0 60 68" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Antenna */}
      <rect x="28" y="0" width="4" height="10" rx="2" fill="#1A56DB"/>
      <circle cx="30" cy="2" r="4" fill="#1A56DB"/>
      {/* Head */}
      <rect x="8" y="10" width="44" height="28" rx="10" fill="#1A56DB"/>
      {/* Eyes */}
      <rect x="14" y="18" width="12" height="10" rx="5" fill="white"/>
      <rect x="34" y="18" width="12" height="10" rx="5" fill="white"/>
      <circle cx="20" cy="23" r="4" fill="#1A56DB"/>
      <circle cx="40" cy="23" r="4" fill="#1A56DB"/>
      <circle cx="21" cy="22" r="1.5" fill="white"/>
      <circle cx="41" cy="22" r="1.5" fill="white"/>
      {/* Mouth */}
      <path d="M20 32 Q30 38 40 32" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round"/>
      {/* Body */}
      <rect x="10" y="40" width="40" height="22" rx="10" fill="#2563EB"/>
      {/* Arms */}
      <rect x="0" y="42" width="8" height="14" rx="4" fill="#1A56DB"/>
      <rect x="52" y="42" width="8" height="14" rx="4" fill="#1A56DB"/>
      {/* Body panel */}
      <rect x="20" y="48" width="20" height="6" rx="3" fill="#60A5FA"/>
    </svg>
  );
}

export function WelcomeScreen({ onQuickAction }: Props) {
  return (
    <div className="flex flex-col justify-center items-center h-full px-8">
      {/* Bot + greeting row */}
      <div className="flex justify-start items-center gap-2.5 mb-1.5 w-full max-w-[1080px]">
        <div className="flex-shrink-0">
          <RobotSvg />
        </div>
        <div className="p-2.5 flex flex-col gap-1.5 flex-1">
          <p style={{
            textAlign: "center",
            color: "var(--grey-8)",
            fontSize: 20,
            fontWeight: 600,
            fontFamily: "Roboto, sans-serif",
            lineHeight: "32px",
          }}>
            Здравствуйте! Чем могу вам помочь?
          </p>
          <p style={{
            textAlign: "center",
            color: "var(--grey-8)",
            fontSize: 14,
            fontWeight: 400,
            fontFamily: "Roboto, sans-serif",
            lineHeight: "20px",
            opacity: 0.9,
          }}>
            *Мы работаем в режиме тестирования, ваши вопросы помогут нам улучшить работу бота.
            Если у вас будут предложения, вы можете оставить их{" "}
            <Link href="/dashboard" className="underline" style={{ color: "var(--azure-37)" }}>
              Здесь
            </Link>.
          </p>
        </div>
      </div>

      {/* ── Quick chips — exact layout from Figma ── */}

      {/* Chip 1: outline, wide — metrics link */}
      <div className="mt-3 w-full flex justify-center" style={{ height: 48 }}>
        <Link
          href="/dashboard"
          className="flex items-center justify-center"
          style={{
            padding: "10px 24px",
            borderRadius: 999,
            outline: "2px solid var(--azure-40)",
            color: "var(--azure-40)",
            fontSize: 14,
            fontWeight: 400,
            fontFamily: "Roboto, sans-serif",
            lineHeight: "16px",
            textAlign: "center",
          }}
        >
          Просмотр&nbsp; последних данных метрик качество генерируемых&nbsp; ИИ
        </Link>
      </div>

      {/* Chips 2 & 3: solid dark-blue, side by side */}
      <div className="mt-0 flex justify-center items-start gap-3.5 flex-wrap" style={{ paddingLeft: 28, paddingRight: 56, paddingTop: 28, maxWidth: 985 }}>
        {QUICK_ACTIONS.map((q, i) => (
          <div key={i} className="flex justify-center items-center" style={{ height: 64 }}>
            <button
              onClick={() => onQuickAction(q)}
              style={{
                padding: "14px 20px",
                background: "var(--azure-37)",
                borderRadius: 16,
                color: "var(--white-solid)",
                fontSize: 14,
                fontWeight: 400,
                fontFamily: "Roboto, sans-serif",
                minWidth: i === 0 ? 256 : 288,
              }}
            >
              Пример популярных запросов_No{i + 1}
            </button>
          </div>
        ))}
      </div>

      {/* Chip 4: outline, "Создать обращение" */}
      <div className="mt-0">
        <button
          onClick={() => onQuickAction("Как создать обращение по вопросам обращения медицинских изделий?")}
          style={{
            padding: "10px 24px",
            borderRadius: 999,
            outline: "2px solid var(--azure-40)",
            color: "var(--azure-40)",
            fontSize: 14,
            fontWeight: 400,
            fontFamily: "Roboto, sans-serif",
            lineHeight: "16px",
          }}
        >
          Создать обращение
        </button>
      </div>
    </div>
  );
}
