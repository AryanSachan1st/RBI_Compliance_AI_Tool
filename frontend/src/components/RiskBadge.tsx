interface RiskConfig {
  label: string;
  text: string;
  bg: string;
  border: string;
}

// Tolerant matching: the LLM-authored `risk` string won't always come back
// byte-identical to a fixed enum, so we match on keywords rather than exact string.
function resolveRisk(raw: string): RiskConfig {
  const normalized = raw.toLowerCase();
  if (normalized.includes("non") || normalized.includes("fail") || normalized.includes("violat")) {
    return { label: "Non-Compliant", text: "text-[var(--color-risk-bad)]", bg: "bg-[var(--color-risk-bad-tint)]", border: "border-[var(--color-risk-bad)]" };
  }
  if (normalized.includes("review") || normalized.includes("uncertain") || normalized.includes("caution")) {
    return { label: "Needs Review", text: "text-[var(--color-risk-warn)]", bg: "bg-[var(--color-risk-warn-tint)]", border: "border-[var(--color-risk-warn)]" };
  }
  if (normalized.includes("complian")) {
    return { label: "Compliant", text: "text-[var(--color-risk-good)]", bg: "bg-[var(--color-risk-good-tint)]", border: "border-[var(--color-risk-good)]" };
  }
  // Fallback: show the raw label rather than guessing wrong
  return { label: raw, text: "text-[var(--color-ink-soft)]", bg: "bg-[var(--color-surface-sunken)]", border: "border-[var(--color-line-strong)]" };
}

export function RiskBadge({ risk }: { risk: string }) {
  const cfg = resolveRisk(risk);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-1 font-mono text-[11px] font-medium uppercase tracking-wide ${cfg.text} ${cfg.bg} ${cfg.border}`}
    >
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${cfg.text.replace("text-", "bg-")}`} />
      {cfg.label}
    </span>
  );
}
