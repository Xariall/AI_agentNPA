"use client";

import Link from "next/link";
import { useChatContext } from "../context/chat-context";

/* НЦЭЛС gradient logo mark — two overlapping rectangles emerald→sky */
function NcelsLogo() {
  return (
    <div className="w-11 h-12 relative overflow-hidden flex-shrink-0">
      <img src="/logo_new.svg" alt="НЦЭЛС" className="w-full h-full object-contain" />
    </div>
  );
}

/* Hamburger icon — 3 lines, azure-37 color */
function HamburgerIcon() {
  return (
    <div className="w-6 h-6 flex flex-col justify-center gap-[5px] cursor-pointer flex-shrink-0">
      <div className="w-5 h-[2px]" style={{ background: "var(--azure-37)" }} />
      <div className="w-5 h-[2px]" style={{ background: "var(--azure-37)" }} />
      <div className="w-5 h-[2px]" style={{ background: "var(--azure-37)" }} />
    </div>
  );
}

/* Trash icon */
function TrashIcon() {
  return (
    <svg className="trash-icon w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
    </svg>
  );
}

/* Plus icon */
function PlusIcon() {
  return (
    <div className="w-4 h-4 relative overflow-hidden flex-shrink-0">
      <img src="/plus.png" alt="Add" className="w-full h-full object-contain" />
    </div>
  );
}

export function Sidebar() {
  const { history, startNewChat, loadChat } = useChatContext();

  const todayItems = history.filter((h) => {
    const today = new Date();
    return new Date(h.createdAt).toDateString() === today.toDateString();
  });

  return (
    <aside className="sidebar">
      {/* ── Header: logo + text + close ── */}
      <div className="sidebar__top">
        <div className="logo-container">
          <NcelsLogo />
        </div>

        <div className="logo__text">
          <p>
            Национальный центр<br />
            экспертизы<br />
            лекарственных средств и<br />
            медицинских изделий
          </p>
        </div>

        <div className="sidebar__close">
          <HamburgerIcon />
        </div>
      </div>

      {/* ── "Новый чат" button ── */}
      <div className="sidebar__buttons-container">
        <div className="sidebar__buttons">
          <div className="button-flex-wrapper">
            <button onClick={startNewChat} className="button-flex">
              <div className="button-flex-shadow" />
              <span>Новый чат</span>
              <div className="icon-wrapper">
                <PlusIcon />
              </div>
              <div className="sidebar__divider" />
            </button>
          </div>

          {/* ── Chat history ── */}
          {todayItems.length > 0 && (
            <div className="sidebar__history-group">
              <div className="sidebar__group-heading">Сегодня</div>
              {todayItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => loadChat(item.id)}
                  className="history-item"
                >
                  <span>{item.title}</span>
                  <TrashIcon />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Warning block ── */}
      <div className="warning-block-wrapper">
        <div className="warning-block">
          <div className="warning-block-shadow" />
          <p>
            Внимание: история запросов, старше 7 дней, автоматически очищается
          </p>
        </div>
      </div>

    </aside>
  );
}
