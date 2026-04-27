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
    <div className="w-[60px] h-[68px] flex-shrink-0">
      <img src="/robot.png" alt="Robot Mascot" className="w-full h-full object-contain" />
    </div>
  );
}

export function WelcomeScreen({ onQuickAction }: Props) {
  return (
    <div className="flex flex-col justify-center items-center h-full px-8">
      {/* Bot + greeting row ── */}
      <div className="greeting-wrapper">
        <div className="greeting-content">
          <div className="flex-shrink-0">
            <RobotSvg />
          </div>
          <div className="greeting-text-container">
            <h1 className="greeting-title">Здравствуйте! Чем могу вам помочь?</h1>
            <p className="greeting-description">
              *Мы работаем в режиме тестирования, ваши вопросы помогут нам улучшить работу бота.
              Если у вас будут предложения, вы можете оставить их{" "}
              <Link href="/dashboard" className="underline" style={{ color: "var(--primary-blue)" }}>
                Здесь
              </Link>.
            </p>
          </div>
        </div>
      </div>

      {/* ── Quick actions ── */}
      <div className="metrics-button-container">
        <Link href="/dashboard" className="btn-metrics">
          Просмотр последних данных метрик качество генерируемых ИИ
        </Link>
      </div>

      <div className="message-list">
        {QUICK_ACTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => onQuickAction(q)}
            className="suggested-query"
          >
            <p>Пример популярных запросов_№{i + 1}</p>
          </button>
        ))}
      </div>

      <div className="registration-container">
        <button
          onClick={() => onQuickAction("Как создать обращение по вопросам обращения медицинских изделий?")}
          className="btn-registration"
        >
          Создать обращение
        </button>
      </div>
    </div>
  );
}
