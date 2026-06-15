import { Fragment } from "react";
import { Logo, WordmarkOnDark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";

const ARCHITECTURE = [
  "Raw Input",
  "S3",
  "Snowflake",
  "dbt",
  "Dimensional Model",
  "Data Marts",
  "AI Analysis",
  "Dashboard",
];

const CAPABILITIES = [
  {
    title: "Warehouse-backed, not a toy",
    body: "Raw files become real Snowflake tables and dbt models — Staging, Intermediate, Dimensional Model, Data Marts — not an in-memory shortcut.",
  },
  {
    title: "AI you can check",
    body: "An AI Analytics Engineer drafts the analysis plan, but the warehouse decides the answer. Every result carries its SQL and evidence.",
  },
  {
    title: "Honest by design",
    body: "No fake charts, no invented insights. When something isn't ready, MeshFlow says so plainly.",
  },
];

const WORKFLOW = [
  {
    step: "1",
    title: "Upload raw data",
    body: "Bring a CSV or use the Raw Retail Transactions demo.",
  },
  {
    step: "2",
    title: "Transform with the warehouse",
    body: "Review the schema, then build dbt models up to Data Marts.",
  },
  {
    step: "3",
    title: "Ask the AI Analytics Engineer",
    body: "Attach a dataset and ask a question in plain language.",
  },
  {
    step: "4",
    title: "Read the dashboard & evidence",
    body: "Get a chart, a direct insight, and the lineage behind it.",
  },
];

const TECH_STACK = [
  "Next.js",
  "TypeScript",
  "FastAPI",
  "Snowflake",
  "dbt",
  "S3",
  "Recharts",
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-surface-muted">
      {/* Hero — dark console band (identity moment) */}
      <section className="relative overflow-hidden bg-shell-deep text-white">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 right-0 h-72 w-72 rounded-full bg-primary/25 blur-[120px]"
        />
        <div className="relative mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <WordmarkOnDark />
          <Button href="/demo/upload" size="sm">
            Launch Demo
          </Button>
        </div>

        <div className="relative mx-auto max-w-5xl px-6 pb-16 pt-10 sm:pt-16">
          <h1 className="max-w-3xl text-balance text-4xl font-bold leading-[1.05] tracking-[-0.02em] sm:text-5xl">
            Raw data becomes analysis you can trust.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-300">
            MeshFlow is a warehouse-first AI analytics demo. It prepares your
            data through Snowflake and dbt, then lets an AI Analytics Engineer
            turn questions into validated, explainable dashboard cards.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button href="/demo/upload">Launch Demo</Button>
            <Button
              href="/demo/data-flow"
              variant="secondary"
              className="border-shell-border bg-transparent text-slate-200 hover:bg-white/5 hover:border-slate-500"
            >
              See the data flow
            </Button>
          </div>
        </div>

        {/* Compact architecture strip */}
        <div className="relative border-t border-shell-border bg-shell/60">
          <div className="mx-auto max-w-5xl overflow-x-auto px-6 py-4">
            <ol className="flex items-center gap-2 whitespace-nowrap text-xs font-medium text-slate-300">
              {ARCHITECTURE.map((node, i) => (
                <Fragment key={node}>
                  <li className="rounded-md bg-white/5 px-2.5 py-1 font-mono">
                    {node}
                  </li>
                  {i < ARCHITECTURE.length - 1 ? (
                    <li aria-hidden className="text-slate-500">
                      →
                    </li>
                  ) : null}
                </Fragment>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="text-2xl font-semibold tracking-tight text-ink">
          What makes it different
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <div
              key={cap.title}
              className="rounded-lg border border-border bg-surface p-5"
            >
              <h3 className="text-base font-semibold text-ink">{cap.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                {cap.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 4-step workflow (a real sequence — numbers carry meaning) */}
      <section className="border-y border-border bg-surface">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">
            How it works
          </h2>
          <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {WORKFLOW.map((item) => (
              <li key={item.step} className="flex flex-col gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-tint font-mono text-sm font-semibold text-primary">
                  {item.step}
                </span>
                <h3 className="text-base font-semibold text-ink">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-ink-soft">
                  {item.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Tech stack */}
      <section className="mx-auto max-w-5xl px-6 py-14">
        <h2 className="text-sm font-semibold text-ink-muted">Built with</h2>
        <ul className="mt-4 flex flex-wrap gap-2">
          {TECH_STACK.map((tech) => (
            <li
              key={tech}
              className="rounded-full border border-border bg-surface px-3 py-1 font-mono text-xs text-ink-soft"
            >
              {tech}
            </li>
          ))}
        </ul>
      </section>

      {/* Final CTA */}
      <section className="bg-shell-deep">
        <div className="mx-auto flex max-w-5xl flex-col items-start gap-5 px-6 py-14 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">
              Ready to see the pipeline?
            </h2>
            <p className="mt-1.5 text-sm text-slate-300">
              Launch the demo workspace — no account required.
            </p>
          </div>
          <Button href="/demo/upload">Launch Demo</Button>
        </div>
      </section>

      <footer className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-8 text-xs text-ink-muted">
        <Logo variant="icon" size={20} />
        <span>MeshFlow v2 — portfolio demo. Warehouse-first AI analytics.</span>
      </footer>
    </main>
  );
}
