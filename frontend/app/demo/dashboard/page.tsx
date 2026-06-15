import { EmptyState } from "@/components/ui/EmptyState";
import { Card } from "@/components/ui/Card";

export default function DashboardPage() {
  // No ready dataset in Phase 2 — the AI panel is disabled and the canvas is empty.
  const hasReadyDataset = false;

  return (
    <div className="px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          One dashboard per session. Ask the AI Analytics Engineer, then build
          it from validated results.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        {/* Left: AI Analytics Engineer panel */}
        <Card as="section" className="self-start">
          <h2 className="text-base font-semibold text-ink">
            AI Analytics Engineer
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Analysis must explicitly attach a dataset — there is no hidden
            “selected” dataset.
          </p>

          <label className="mt-4 block text-xs font-semibold text-ink">
            Attach dataset
          </label>
          <select
            disabled={!hasReadyDataset}
            defaultValue=""
            aria-label="Attach dataset"
            className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink-muted disabled:cursor-not-allowed disabled:bg-surface-muted"
          >
            <option value="">No ready dataset</option>
          </select>

          <label className="mt-4 block text-xs font-semibold text-ink">
            Question
          </label>
          <textarea
            disabled={!hasReadyDataset}
            rows={3}
            placeholder="Prepare a dataset to ask a question…"
            className="mt-1.5 w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted disabled:cursor-not-allowed disabled:bg-surface-muted"
          />

          <div className="mt-4">
            <p className="text-xs font-semibold text-ink">Suggested questions</p>
            <p className="mt-1.5 rounded-md bg-surface-muted px-3 py-2 text-xs text-ink-muted">
              Suggestions appear once a dataset is attached and ready.
            </p>
          </div>

          <button
            type="button"
            disabled
            title="Prepare a dataset before asking the AI Analytics Engineer."
            className="mt-4 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
          >
            Generate analysis
          </button>
        </Card>

        {/* Right: dashboard canvas */}
        <section className="min-w-0">
          <EmptyState
            title="Prepare a dataset before asking the AI Analytics Engineer"
            description="Once a dataset is uploaded and transformed to Data Marts, generated results land here as chart cards — each with its own dataset badge and evidence."
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
                <rect x="3" y="3" width="7" height="9" rx="1.5" />
                <rect x="14" y="3" width="7" height="5" rx="1.5" />
                <rect x="14" y="12" width="7" height="9" rx="1.5" />
                <rect x="3" y="16" width="7" height="5" rx="1.5" />
              </svg>
            }
          />
        </section>
      </div>
    </div>
  );
}
