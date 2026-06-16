"use client";

import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";

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

  return `Ready dataset ${index + 1}`;
}

export default function DashboardPage() {
  const { workspace } = useWorkspaceSession();
  const readyDatasets = workspace?.ready_datasets ?? [];
  const schemaReviewDatasets = workspace?.datasets ?? [];
  const hasReadyDataset = readyDatasets.length > 0;

  return (
    <div className="px-6 py-8">
      {/* Page header with violet icon */}
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-500/12 text-violet-600">
          <svg {...ip}>
            <rect x="3" y="3" width="7" height="9" rx="1.5" />
            <rect x="14" y="3" width="7" height="5" rx="1.5" />
            <rect x="14" y="12" width="7" height="9" rx="1.5" />
            <rect x="3" y="16" width="7" height="5" rx="1.5" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">
            Dashboard
          </h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            One dashboard per session. Ask the AI Analytics Engineer, then
            build it from validated results.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        {/* ── Left: AI Analytics Engineer panel ───────────────────── */}
        <section
          className="self-start rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
          style={{ borderTop: "4px solid #4f46e5" }}
        >
          {/* Panel header */}
          <div className="flex items-center gap-2 mb-4">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <svg
                width={14}
                height={14}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M12 2a5 5 0 0 1 5 5c0 2.76-2.24 5-5 5S7 9.76 7 7a5 5 0 0 1 5-5z" />
                <path d="M2 21v-1a7 7 0 0 1 7-7h6a7 7 0 0 1 7 7v1" />
              </svg>
            </span>
            <h2 className="text-sm font-semibold text-ink">
              AI Analytics Engineer
            </h2>
          </div>

          <p className="text-xs leading-relaxed text-ink-muted mb-4">
            Analysis requires an explicit dataset — there is no hidden
            &ldquo;selected&rdquo; dataset.
          </p>

          <label className="block text-xs font-semibold text-ink">
            Attach dataset
          </label>
          <select
            disabled={!hasReadyDataset}
            defaultValue=""
            aria-label="Attach dataset"
            className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink-muted disabled:cursor-not-allowed disabled:bg-surface-muted"
          >
            <option value="">No ready dataset</option>
            {readyDatasets.map((dataset, index) => {
              const label = datasetLabel(dataset, index);
              return (
                <option key={label} value={label}>
                  {label}
                </option>
              );
            })}
          </select>

          <label className="mt-4 block text-xs font-semibold text-ink">
            Question
          </label>
          <textarea
            disabled={!hasReadyDataset}
            rows={3}
            className="mt-1.5 w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:bg-surface-muted"
          />

          <div className="mt-4">
            <p className="text-xs font-semibold text-ink">Suggested questions</p>
            <p className="mt-1.5 rounded-md bg-surface-muted px-3 py-2.5 text-xs text-ink-muted">
              {schemaReviewDatasets.length > 0
                ? "Prepared question suggestions can be reviewed in Data Flow after semantic preparation. Analysis stays disabled until Data Marts exist."
                : "Suggestions appear after a dataset is loaded and semantic preparation succeeds."}
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
        </section>

        {/* ── Right: dashboard canvas ──────────────────────────────── */}
        <section className="min-w-0">
          <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-violet-200 bg-violet-50/30 px-6 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 text-violet-500">
              <svg {...ip}>
                <rect x="3" y="3" width="7" height="9" rx="1.5" />
                <rect x="14" y="3" width="7" height="5" rx="1.5" />
                <rect x="14" y="12" width="7" height="9" rx="1.5" />
                <rect x="3" y="16" width="7" height="5" rx="1.5" />
              </svg>
            </span>
            <h3 className="mt-4 text-base font-semibold text-ink">
              {hasReadyDataset ? "No dashboard cards yet" : "Prepare a dataset first"}
            </h3>
            <p className="prose-measure mt-2 text-sm text-ink-muted">
              {hasReadyDataset
                ? "Ask the AI Analytics Engineer after the analysis workflow is wired. Generated chart cards will appear here with evidence."
                : "Once a dataset is uploaded and transformed to Data Marts, generated chart cards appear here with a dataset badge, direct insight, and collapsible evidence."}
            </p>
            {!hasReadyDataset ? (
              <a
                href="/demo/upload"
                className="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4.5 py-2.5 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                Upload Dataset
              </a>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
