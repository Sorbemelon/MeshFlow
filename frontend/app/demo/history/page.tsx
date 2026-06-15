"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";

// Columns each history row will carry (FRONTEND_UX_SCOPE §9). Shown as headers
// now; rows arrive in Phase 8. No fake entries.
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

export default function HistoryPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="px-6 py-8">
      <header className="mb-6 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            History
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Every analysis is preserved with its evidence — even if the source
            dataset is later deleted.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setDrawerOpen(true)}>
          Preview detail layout
        </Button>
      </header>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        {/* Column header preview */}
        <div className="hidden grid-cols-9 gap-3 border-b border-border bg-surface-muted px-4 py-2.5 text-xs font-semibold text-ink-muted md:grid">
          {COLUMNS.map((col, i) => (
            <span key={i}>{col}</span>
          ))}
        </div>

        <EmptyState
          className="rounded-none border-0"
          title="No analysis history yet"
          description="Generated analyses will appear here with question, dataset badge, status, provider, and chart count. Open one to see its full evidence."
          ctaLabel="Go to Dashboard"
          ctaHref="/demo/dashboard"
          icon={
            <svg
              width={20}
              height={20}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
              <path d="M3 4v4h4M12 8v4l3 2" />
            </svg>
          }
        />
      </div>

      {/* Analysis Detail drawer — placeholder scaffold (no data yet) */}
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
          aria-label="Analysis detail"
          className={cn(
            "absolute right-0 top-0 flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-[0_16px_40px_rgba(15,23,42,0.16)] transition-transform duration-200 ease-[var(--ease-out-quart)]",
            drawerOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-base font-semibold text-ink">Analysis detail</h2>
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close"
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
          <div className="flex-1 px-5 py-6 text-sm text-ink-muted">
            This is the layout an analysis will open into — question, dataset
            badge, chart(s), insight, SQL, ChartSpec, provider chain, and
            lineage. No analysis is selected.
          </div>
        </aside>
      </div>
    </div>
  );
}
