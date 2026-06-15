import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";

// Preparation status rail — ONLY these six stages (FRONTEND_UX_SCOPE §7).
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

export default function DataFlowPage() {
  // No dataset in Phase 2 — everything renders its honest empty/disabled state.
  const hasDataset = false;

  return (
    <div className="px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Data Flow
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Prepare a dataset through the warehouse and dbt, stage by stage.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* Left narrow rail */}
        <aside className="space-y-5">
          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Dataset
            </h2>
            <div className="rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-ink-muted">
              No dataset selected
            </div>
          </div>

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
                    className="h-2.5 w-2.5 shrink-0 rounded-full bg-status-neutral/40"
                  />
                  <span className="text-sm text-ink-soft">{stage}</span>
                  <span className="ml-auto text-xs text-ink-muted">Waiting</span>
                </li>
              ))}
            </ol>
          </div>
        </aside>

        {/* Right main area */}
        <section className="min-w-0">
          {/* Tabs — inactive/disabled until a dataset exists */}
          <div
            role="tablist"
            aria-label="Data Flow views"
            className="mb-4 flex flex-wrap gap-1 border-b border-border"
          >
            {TABS.map((tab, i) => (
              <button
                key={tab}
                type="button"
                role="tab"
                disabled={!hasDataset}
                aria-selected={i === 0}
                className={cn(
                  "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
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
