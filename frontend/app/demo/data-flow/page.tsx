import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
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

export default function DataFlowPage() {
  // No dataset yet — everything shows its honest no-dataset state.
  const hasDataset = false;

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
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            Data Flow
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Prepare a dataset through the warehouse and dbt, stage by stage.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        {/* ── Left narrow rail ──────────────────────────────────────── */}
        <aside className="space-y-5">
          {/* Dataset selector */}
          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Dataset
            </h2>
            <div className="rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-ink-muted">
              No available dataset
            </div>
            <Button
              href="/demo/upload"
              variant="secondary"
              size="sm"
              className="mt-2 w-full"
            >
              Upload Dataset
            </Button>
          </div>

          {/* Preparation status */}
          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Preparation status
            </h2>
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
                  <span className="text-sm text-ink-soft">{stage}</span>
                  <span className="ml-auto text-xs text-ink-muted">
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
            title="No dataset to prepare yet"
            description="Add the demo dataset or upload a CSV. Once a dataset exists, the preparation stages and evidence tabs become active here."
            ctaLabel="Upload Dataset"
            ctaHref="/demo/upload"
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
