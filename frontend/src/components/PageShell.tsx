import { Link } from "react-router-dom";
import type { ReactNode } from "react";

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--color-paper)]">
      <header className="border-b border-[var(--color-line)] bg-[var(--color-surface)]">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-sm bg-[var(--color-accent)] font-mono text-xs font-semibold text-white">
              AC
            </span>
            <span className="text-sm font-semibold tracking-tight text-[var(--color-ink)]">
              AI Compliance Copilot
            </span>
          </Link>
          <span className="text-xs text-[var(--color-ink-faint)]">BFSI Document Review</span>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
    </div>
  );
}
