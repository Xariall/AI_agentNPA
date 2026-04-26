interface Props {
  level?: string;
  verificationFailed?: boolean;
}

export function ConfidenceBadge({ level, verificationFailed }: Props) {
  const base: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 4,
    fontFamily: "Roboto, sans-serif",
    fontWeight: 400,
    border: "1px solid",
  };

  if (verificationFailed) {
    return (
      <span style={{ ...base, background: "#fef2f2", color: "#b91c1c", borderColor: "#fca5a5" }}>
        ✕ Цитаты не верифицированы
      </span>
    );
  }

  if (level === "high") {
    return (
      <span style={{ ...base, background: "#f0fdf4", color: "#15803d", borderColor: "#86efac" }}>
        ✓ Высокая уверенность
      </span>
    );
  }

  if (level === "medium") {
    return (
      <span style={{ ...base, background: "var(--warning)", color: "var(--orange-27)", borderColor: "var(--yellow-50)" }}>
        ! Средняя уверенность
      </span>
    );
  }

  return null;
}
