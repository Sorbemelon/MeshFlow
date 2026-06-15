"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";

// Columns each history row will carry (FRONTEND_UX_SCOPE §9).
// Headers visible now; rows arrive in Phase 8. No fake entries.
const COLUMNS = [
  "Question",
  "Dataset",
  "Status",
  "Decision",
  "Charts",
  "Source model",
  "Provider",
  "Created",
  "",
];

const ip = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

export default function HistoryPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="px-6 py-8">
      {/* Page header with purple icon */}
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-purple-500/12 text-purple-600">
          <svg {...ip}>
            <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
            <path d="M3 4v4h4M12 8v4l3 2" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            History
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Every analysis is preserved with its evidence — even after the
            source dataset is deleted.
          </p>
        </div>
      </header>

      {/* History table with violet top accent */}
      <div
        className="overflow-hidden rounded-lg border border-border bg-surface"
        style={{ borderTop: "4px solid #7c3aed" }}
      >
        {/* Column headers */}
        <div className="hidden grid-cols-9 gap-3 border-b border-border bg-surface-muted px-4 py-2.5 text-xs font-semibold text-ink-muted md:grid">
          {COLUMNS.map((col, i) => (
            <span key={i}>{col}</span>
          ))}
        </div>

        {/* Empty state */}
        <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-50 text-purple-500">
            <svg {...ip}>
              <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
              <path d="M3 4v4h4M12 8v4l3 2" />
            </svg>
          </span>
          <h3 className="mt-4 text-base font-semibold text-ink">
            No analysis history yet
          </h3>
          <p className="prose-measure mt-2 text-sm text-ink-muted">
            Generated analyses appear here with question, dataset badge, status,
            provider, and chart count. Open any row to see its full evidence.
          </p>
          <a
            href="/demo/dashboard"
            className="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4.5 py-2.5 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            Go to Dashboard
          </a>
        </div>
      </div>

      {/* Analysis Detail drawer — scaffold only; no data yet.
          Trigger: each history row's "View Detail" button (Phase 8).
          Exposed here for layout review via URL param or direct open. */}
      <div
        className={cn(
          "fixed inset-0 z-40 transition-opacity duration-200",
          drawerOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
        )}
        aria-hidden={!drawerOpen}
      >
        <div
          className="absolute inset-0 bg-shell-deep/40"
          onClick={() => setDrawerOpen(false)}
        />
        <aside
          role="dialog"
          aria-modal
          aria-label="Analysis detail"
          className={cn(
            "absolute right-0 top-0 flex h-full w-full max-w-lg flex-col border-l border-border bg-surface shadow-[0_16px_40px_rgba(15,23,42,0.16)] transition-transform duration-200 ease-out-quart",
            drawerOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-base font-semibold text-ink">
              Analysis detail
            </h2>
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close drawer"
              className="rounded-md p-1 text-ink-muted transition-colors hover:bg-surface-muted"
            >
              <svg
                width={18}
                height={18}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.8}
                strokeLinecap="round"
                aria-hidden
              >
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>
          <div className="flex-1 px-5 py-8 text-sm text-ink-muted">
            <p>
              When a history row is opened, this drawer will show: question,
              dataset badge, chart(s), direct insight, SQL, ChartSpec JSON,
              provider chain, and lineage evidence.
            </p>
            <p className="mt-4">No analysis is selected.</p>
          </div>
        </aside>
      </div>
    </div>
  );
}
