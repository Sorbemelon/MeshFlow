"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";

const ip = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

const WALKTHROUGH = [
  { n: "1", title: "Choose raw data", body: "Use the curated demo or upload your own CSV file." },
  { n: "2", title: "Review schema", body: "Inspect detected columns and confirm the mapping." },
  { n: "3", title: "Transform with warehouse/dbt", body: "Build Staging → Intermediate → Dimensional Model → Data Marts." },
  { n: "4", title: "Ask the AI Analytics Engineer", body: "Attach your dataset and ask a question in plain language." },
  { n: "5", title: "Save charts to dashboard", body: "Validated results land as chart cards with evidence." },
];

export default function UploadPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <div className="px-6 py-8">
      {/* Page header with amber icon */}
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/12 text-amber-600">
          <svg {...ip} width={20} height={20}>
            <path d="M12 16V4M7 9l5-5 5 5" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">
            Upload Dataset
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Add the curated demo dataset or bring your own CSV file.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        {/* ── Left: combined dataset card ─────────────────────────── */}
        <div className="rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]" style={{ borderTop: "4px solid #f59e0b" }}>

          {/* Section 1 — Raw Retail Demo */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-ink">
                Raw Retail Transactions Demo
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                A raw, denormalized retail transactions file. MeshFlow turns it
                into a Dimensional Model and Data Marts — once per session.
              </p>
            </div>
            <StatusBadge status="waiting" label="Not added" className="shrink-0 mt-0.5" />
          </div>

          <Button className="mt-4" size="sm">
            Use Demo Dataset
          </Button>

          {/* Divider */}
          <hr className="my-5 border-border" />

          {/* Section 2 — Upload CSV */}
          <h2 className="text-base font-semibold text-ink">
            Upload your own CSV
          </h2>
          <p className="mt-1 text-sm text-ink-soft">
            MVP: one CSV file per dataset.
          </p>

          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />

          <div className="mt-3 rounded-md border border-dashed border-border bg-surface-muted px-4 py-5 text-center">
            {fileName ? (
              <p className="text-sm text-ink-soft">
                Selected:{" "}
                <span className="font-mono text-ink">{fileName}</span>
              </p>
            ) : (
              <p className="text-sm text-ink-muted">
                Choose a CSV file — nothing is uploaded until you confirm.
              </p>
            )}

            <div className="mt-3 flex items-center justify-center gap-2">
              <Button
                variant={fileName ? "secondary" : "primary"}
                size="sm"
                onClick={() => inputRef.current?.click()}
              >
                Browse
              </Button>
              {fileName ? (
                <Button
                  size="sm"
                  disabled
                  title="Upload runs after CSV validation and S3 + Snowflake readiness checks (Phase 4). Nothing is sent yet."
                >
                  Upload
                </Button>
              ) : null}
            </div>
          </div>

          <p className="mt-3 text-xs text-ink-muted">
            MeshFlow validates the CSV and checks S3 + Snowflake readiness
            before any data is sent. Invalid or unsupported files are rejected
            with a clear reason — no partial or invented success.
          </p>
        </div>

        {/* ── Right: Demo Walkthrough card ────────────────────────── */}
        <div className="rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
          <div className="flex items-center gap-2 text-ink">
            <svg
              width={16}
              height={16}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
              className="text-primary"
            >
              <polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none" />
            </svg>
            <h2 className="text-base font-semibold">Demo walkthrough</h2>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            Five steps from raw file to validated chart.
          </p>

          <ol className="mt-5 space-y-0">
            {WALKTHROUGH.map((step, i) => (
              <li key={step.n} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-tint font-mono text-[0.625rem] font-semibold text-primary">
                    {step.n}
                  </span>
                  {i < WALKTHROUGH.length - 1 ? (
                    <span className="mt-1 w-px flex-1 bg-border" style={{ minHeight: "24px" }} />
                  ) : null}
                </div>
                <div className={i < WALKTHROUGH.length - 1 ? "pb-4" : ""}>
                  <p className="text-sm font-medium text-ink">{step.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
