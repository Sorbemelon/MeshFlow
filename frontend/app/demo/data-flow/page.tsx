"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { cn } from "@/lib/cn";

// Preparation rail — ONLY these six stages (FRONTEND_UX_SCOPE §7).
// Analysis Outputs / Dashboard are never preparation steps.
const PREP_STAGES = [
  "Raw Input",
  "Warehouse Raw",
  "Staging",
  "Intermediate",
  "Dimensional Model",
  "Data Marts",
];

const TABS = [
  "Schema Preview",
  "Warehouse Raw",
  "Transformations",
  "Dimensional Model & Data Marts",
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

function datasetLabel(dataset: Record<string, unknown>, index: number): string {
  const name = dataset.name;
  if (typeof name === "string" && name.trim()) {
    return name;
  }

  const id = dataset.id;
  if (typeof id === "string" && id.trim()) {
    return id;
  }

  return `Dataset ${index + 1}`;
}

export default function DataFlowPage() {
  const { workspace } = useWorkspaceSession();
  const datasets = workspace?.datasets ?? [];
  const hasDataset = datasets.length > 0;

  return (
    <div className="px-6 py-8">
      {/* Page header with blue icon */}
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-500/12 text-blue-600">
          <svg {...ip}>
            <circle cx="6" cy="6" r="2" />
            <circle cx="18" cy="12" r="2" />
            <circle cx="6" cy="18" r="2" />
            <path d="M8 6h5a2 2 0 0 1 2 2v1.5M16 12h-5a2 2 0 0 0-2 2v1.5" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">
            Data Flow
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Prepare a dataset through the warehouse and dbt, stage by stage.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        {/* ── Left narrow rail ──────────────────────────────────────── */}
        <aside className="self-start rounded-lg border border-border bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]" style={{ borderTop: "4px solid #2563eb" }}>
          {/* Dataset selector */}
          <div>
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Dataset
            </h3>
            <select
              disabled={!hasDataset}
              defaultValue=""
              aria-label="Select dataset"
              className="w-full rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-ink-muted disabled:cursor-not-allowed disabled:bg-surface-muted"
            >
              <option value="">No available dataset</option>
              {datasets.map((dataset, index) => {
                const label = datasetLabel(dataset, index);
                return (
                  <option key={label} value={label}>
                    {label}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Preparation status */}
          <div className="mt-5">
            <h3 className="mb-2 text-xs font-semibold text-ink-muted">
              Preparation status
            </h3>
            <ol className="space-y-1.5">
              {PREP_STAGES.map((stage) => (
                <li
                  key={stage}
                  className="flex items-center gap-2.5 rounded-md border border-border bg-surface px-3 py-2"
                >
                  <span
                    aria-hidden
                    className="h-2 w-2 shrink-0 rounded-full bg-status-neutral/35"
                  />
                  <span className="whitespace-nowrap text-sm text-ink-soft">{stage}</span>
                  <span className="ml-auto whitespace-nowrap text-xs text-ink-muted">
                    Not Started
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </aside>

        {/* ── Right main area ──────────────────────────────────────── */}
        <section className="min-w-0">
          {/* Tabs — disabled until a dataset exists */}
          <div
            role="tablist"
            aria-label="Data Flow views"
            className="mb-4 flex flex-wrap gap-0 border-b border-border"
          >
            {TABS.map((tab, i) => (
              <button
                key={tab}
                type="button"
                role="tab"
                disabled={!hasDataset}
                aria-selected={i === 0}
                className={cn(
                  "-mb-px border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors duration-150",
                  i === 0
                    ? "border-primary text-ink"
                    : "border-transparent text-ink-muted",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {tab}
              </button>
            ))}
          </div>

          <EmptyState
            title={
              hasDataset
                ? "Preparation details are not started"
                : "No dataset to prepare yet"
            }
            description={
              hasDataset
                ? "Preparation evidence appears after warehouse and dbt processing is available."
                : "Add the demo dataset or upload a CSV. Once a dataset exists, the preparation stages and evidence tabs become active here."
            }
            ctaLabel={hasDataset ? undefined : "Upload Dataset"}
            ctaHref={hasDataset ? undefined : "/demo/upload"}
            className="border-blue-200 bg-blue-50/40"
            icon={
              <svg {...ip}>
                <path d="M12 16V4M7 9l5-5 5 5" />
                <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
              </svg>
            }
          />
        </section>
      </div>
    </div>
  );
}
