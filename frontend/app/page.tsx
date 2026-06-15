import { Fragment } from "react";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";

// ─── Architecture pipeline ────────────────────────────────────────────────────
// Exact wording required by FRONTEND_UX_SCOPE / user spec.
const ARCH = [
  {
    label: "Dataset",
    color: "#d97706",
    desc: "Raw CSV / curated retail input",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <ellipse cx="12" cy="6" rx="8" ry="3" />
        <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" />
        <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
      </svg>
    ),
  },
  {
    label: "AWS S3",
    color: "#ea580c",
    desc: "Raw file storage",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        <circle cx="12" cy="12" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    label: "Snowflake",
    color: "#2563eb",
    desc: "Warehouse Raw and query execution",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <line x1="12" y1="2" x2="12" y2="22" />
        <path d="M17 5l-5 5-5-5M7 19l5-5 5 5" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M19 7l-5 5 5 5M5 7l5 5-5 5" />
      </svg>
    ),
  },
  {
    label: "dbt",
    color: "#4f46e5",
    desc: "Staging · Intermediate · Dimensional Model · Data Marts",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        <path d="M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
      </svg>
    ),
  },
  {
    label: "AI Analytics Engineer",
    color: "#7c3aed",
    desc: "Plan, validate, explain",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M12 2a5 5 0 0 1 5 5c0 2.76-2.24 5-5 5S7 9.76 7 7a5 5 0 0 1 5-5z" />
        <path d="M2 21v-1a7 7 0 0 1 7-7h6a7 7 0 0 1 7 7v1" />
      </svg>
    ),
  },
  {
    label: "Dashboard",
    color: "#059669",
    desc: "Charts, insights, evidence",
    icon: (
      <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <rect x="3" y="3" width="7" height="9" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="16" width="7" height="5" rx="1.5" />
      </svg>
    ),
  },
];

const CAPABILITIES = [
  {
    title: "Warehouse-backed",
    body: "Real Snowflake tables and dbt models — not an in-memory shortcut.",
  },
  {
    title: "AI you can verify",
    body: "SQL and evidence are attached to every result. Check the work.",
  },
  {
    title: "Honest by design",
    body: "No fake charts, no invented fallbacks. Failures are visible.",
  },
  {
    title: "Portfolio-grade",
    body: "Maintainable full-stack architecture, clear role boundaries.",
  },
];

const STEPS = [
  { n: "1", title: "Upload raw data", body: "Bring a CSV or use the Raw Retail demo." },
  { n: "2", title: "Review schema", body: "Inspect and confirm column mapping before transforming." },
  { n: "3", title: "Transform with warehouse", body: "Staging → Intermediate → Dimensional Model → Data Marts." },
  { n: "4", title: "Ask the AI Analytics Engineer", body: "Attach a dataset and ask a question in plain language." },
  { n: "5", title: "Read charts & evidence", body: "Dashboard card with insight, SQL, and lineage." },
];

const TECH = ["Next.js", "TypeScript", "FastAPI", "Snowflake", "dbt", "S3", "Recharts"];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-shell-deep">
      {/* ── 1. Gradient top bar ─────────────────────────────────────── */}
      <header className="flex items-center justify-between bg-linear-to-r from-shell-deep via-[#1e1b4b] to-shell-deep px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <Logo variant="icon" size={26} priority />
          <span className="text-sm font-semibold text-white">MeshFlow</span>
        </div>
        <Button href="/demo/upload" size="sm">
          Launch Demo
        </Button>
      </header>

      {/* ── 2. Main split ───────────────────────────────────────────── */}
      <div className="grid min-h-[calc(100dvh-52px)] lg:grid-cols-2">
        {/* Left — dark identity panel */}
        <section className="flex flex-col justify-center bg-shell-deep px-8 py-14 sm:px-12 lg:px-14">
          {/* Wordmark */}
          <Logo variant="icon" size={52} priority />
          <h1 className="mt-5 text-[3.25rem] font-bold leading-[1.02] tracking-tight">
            <span className="text-white">Mesh</span>
            <span className="text-gradient-brand">Flow</span>
          </h1>
          <p className="mt-3 max-w-sm text-base leading-relaxed text-slate-300">
            Warehouse-first AI analytics — from raw CSV to validated,
            explainable charts.
          </p>

          {/* 4 capability cards */}
          <div className="mt-8 grid grid-cols-2 gap-3">
            {CAPABILITIES.map((cap) => (
              <div
                key={cap.title}
                className="rounded-lg border border-white/8 bg-white/5 p-4"
              >
                <p className="text-sm font-semibold text-white">{cap.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">
                  {cap.body}
                </p>
              </div>
            ))}
          </div>

          <Button href="/demo/upload" className="mt-8 self-start">
            Launch Demo
          </Button>
        </section>

        {/* Right — light panel */}
        <section className="flex flex-col justify-center bg-surface px-8 py-14 sm:px-12 lg:px-14">
          <h2 className="text-xl font-semibold tracking-tight text-ink">
            How it works
          </h2>

          {/* Numbered steps with vertical connector */}
          <ol className="mt-6 space-y-0">
            {STEPS.map((step, i) => (
              <li key={step.n} className="flex gap-4">
                {/* Left: number + connector */}
                <div className="flex flex-col items-center">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-tint font-mono text-[0.6875rem] font-semibold text-primary">
                    {step.n}
                  </span>
                  {i < STEPS.length - 1 ? (
                    <span className="mt-1 w-px flex-1 bg-border" style={{ minHeight: "28px" }} />
                  ) : null}
                </div>
                {/* Right: text */}
                <div className={i < STEPS.length - 1 ? "pb-5" : ""}>
                  <p className="text-sm font-semibold text-ink">{step.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>

          {/* Demo limits */}
          <div className="mt-8 rounded-lg border border-border bg-surface-muted p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Demo limits
            </p>
            <ul className="mt-2 space-y-1 text-xs text-ink-soft">
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1 w-1 rounded-full bg-ink-muted" />
                One demo session at a time
              </li>
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1 w-1 rounded-full bg-ink-muted" />
                One CSV file per upload (MVP)
              </li>
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1 w-1 rounded-full bg-ink-muted" />
                Demo dataset can be added once per session
              </li>
            </ul>
          </div>
        </section>
      </div>

      {/* ── 3. Architecture + built-with strip ──────────────────────── */}
      <div className="border-t border-shell-border bg-shell">
        <div className="mx-auto max-w-6xl px-6 py-10">
          {/* Architecture pipeline */}
          <div className="overflow-x-auto">
            <ol className="flex items-start gap-0 whitespace-nowrap">
              {ARCH.map((node, i) => (
                <Fragment key={node.label}>
                  <li className="flex flex-col items-center gap-1.5 px-3 first:pl-0 last:pr-0">
                    <span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                      style={{ backgroundColor: `${node.color}22`, color: node.color }}
                    >
                      {node.icon}
                    </span>
                    <span className="text-xs font-semibold text-white">
                      {node.label}
                    </span>
                    <span
                      className="max-w-27.5 text-center text-[10px] leading-tight text-slate-400"
                      style={{ whiteSpace: "normal" }}
                    >
                      {node.desc}
                    </span>
                  </li>
                  {i < ARCH.length - 1 ? (
                    <li
                      aria-hidden
                      className="mt-3 shrink-0 px-1 text-slate-500"
                    >
                      →
                    </li>
                  ) : null}
                </Fragment>
              ))}
            </ol>
          </div>

          {/* Built with */}
          <div className="mt-8 flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Built with
            </span>
            {TECH.map((t) => (
              <span
                key={t}
                className="rounded-full border border-shell-border px-2.5 py-0.5 font-mono text-[10px] text-slate-400"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
