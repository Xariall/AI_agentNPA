"use client";

import Link from "next/link";
import { useChatContext } from "../context/chat-context";

/* НЦЭЛС gradient logo mark — two overlapping rectangles emerald→sky */
function NcelsLogo() {
  return (
    <div className="w-11 h-12 relative overflow-hidden flex-shrink-0">
      {/* Bottom bar */}
      <div className="w-11 h-6 absolute left-0 top-[24px]"
        style={{ background: "linear-gradient(to right, #059669, #0ea5e9)" }} />
      {/* Top bar (offset 2.5px) */}
      <div className="w-11 h-6 absolute left-[2.5px] top-[2.5px]"
        style={{ background: "linear-gradient(to right, #059669, #0ea5e9)" }} />
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
    <div className="w-4 h-4 relative overflow-hidden flex-shrink-0">
      <div className="w-3.5 h-4 absolute left-[2px] top-0"
        style={{ background: "var(--azure-34)", clipPath: "polygon(20% 10%, 80% 10%, 100% 30%, 100% 100%, 0% 100%, 0% 30%)" }} />
    </div>
  );
}

/* Plus icon */
function PlusIcon() {
  return (
    <div className="w-4 h-4 relative overflow-hidden flex-shrink-0">
      {/* vertical line */}
      <div className="w-0 h-3 absolute left-[7.5px] top-[2.5px] border border-white" />
      {/* horizontal line */}
      <div className="w-3 h-0 absolute left-[2px] top-[7.5px] border border-white" />
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
    <aside
      className="flex-shrink-0 flex flex-col h-full overflow-hidden"
      style={{
        width: 320,
        minWidth: 320,
        background: "var(--grey-97)",
        boxShadow: "0px 0px 1px 0px rgba(0,0,0,0.25)",
        padding: 28,
      }}
    >
      {/* ── Header: logo + text + hamburger ── */}
      <div className="flex justify-start items-start gap-2">
        <NcelsLogo />

        <div className="flex flex-col justify-start items-start pr-3 h-12">
          <div style={{
            fontSize: 10,
            lineHeight: "12px",
            fontFamily: "Roboto, sans-serif",
            fontWeight: 400,
            textTransform: "uppercase",
            color: "var(--black-solid)",
          }}>
            Национальный центр<br />
            экспертизы<br />
            лекарственных средств и<br />
            медицинских изделий
          </div>
        </div>

        <div className="flex-1 flex justify-end">
          <HamburgerIcon />
        </div>
      </div>

      {/* ── "Новый чат" button ── */}
      <div className="mt-14 w-full">
        <button
          onClick={startNewChat}
          className="w-full relative flex justify-between items-center rounded-xl"
          style={{
            padding: "16px 24px",
            background: "var(--white-solid)",
            borderBottom: "1px solid var(--azure-37)",
            boxShadow: "0px 4px 4px -2px rgba(24,39,75,0.08), 0px 2px 4px -2px rgba(24,39,75,0.12)",
          }}
        >
          <span style={{
            color: "var(--azure-37)",
            fontSize: 18,
            fontWeight: 300,
            fontFamily: "Roboto, sans-serif",
            lineHeight: "16px",
          }}>
            Новый чат
          </span>
          {/* Plus icon: azure-37 filled square with white lines */}
          <div className="w-4 h-4 relative overflow-hidden flex-shrink-0"
            style={{ background: "var(--azure-37)" }}>
            <div className="absolute h-3 border border-white"
              style={{ left: "7px", top: "2.5px", borderWidth: "0.5px" }} />
            <div className="absolute w-3 border border-white"
              style={{ left: "2px", top: "7px", borderWidth: "0.5px" }} />
          </div>
          {/* Bottom divider */}
          <div className="absolute bottom-0 left-0 w-full h-px"
            style={{ background: "rgba(0,0,0,0.08)" }} />
        </button>
      </div>

      {/* ── Chat history ── */}
      <div className="mt-5 flex flex-col gap-2.5 w-full">
        {todayItems.length > 0 && (
          <>
            <div style={{
              fontSize: 12,
              fontWeight: 700,
              fontFamily: "Roboto, sans-serif",
              lineHeight: "16px",
              color: "var(--black-solid)",
            }}>
              Сегодня
            </div>
            {todayItems.map((item) => (
              <button
                key={item.id}
                onClick={() => loadChat(item.id)}
                className="w-full flex justify-between items-center rounded-xl"
                style={{
                  padding: "16px 24px",
                  background: "var(--white-solid)",
                }}
              >
                <span style={{
                  color: "var(--azure-34)",
                  fontSize: 18,
                  fontWeight: 300,
                  fontFamily: "Roboto, sans-serif",
                  lineHeight: "16px",
                }}>
                  {item.title.slice(0, 20)}
                </span>
                <TrashIcon />
              </button>
            ))}
          </>
        )}
      </div>

      {/* ── Warning block ── */}
      <div className="mt-3.5 w-full" style={{
        padding: 10,
        background: "var(--grey-95)",
        borderLeft: "4px solid var(--yellow-50)",
        borderRadius: "0 2px 2px 0",
        boxShadow: "0px 1px 2px -1px rgba(0,0,0,0.10), 0px 1px 3px 0px rgba(0,0,0,0.10)",
      }}>
        <p style={{
          fontSize: 12,
          fontWeight: 400,
          fontFamily: "Roboto, sans-serif",
          lineHeight: "16px",
          color: "var(--orange-27)",
        }}>
          Внимание: история запросов, старше 7<br />
          дней, автоматически очищается
        </p>
      </div>

      {/* ── Dashboard link (our addition) ── */}
      <div className="mt-auto pt-4">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-xs"
          style={{ color: "var(--azure-37)" }}
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Метрики качества
        </Link>
      </div>
    </aside>
  );
}
