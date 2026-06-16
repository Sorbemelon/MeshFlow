"use client";

import { useEffect, useState } from "react";
import { AnalysisDetailDrawer } from "@/components/analysis/AnalysisDetailDrawer";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import {
  listAnalysisRuns,
  MeshFlowApiError,
  type AnalysisRunSummary,
} from "@/lib/meshflowApi";

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

function formatDate(value: string | null): string {
  if (!value) {
    return "Not completed";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusTone(status: string): string {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "failed") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  return "border-blue-200 bg-blue-50 text-blue-700";
}

export default function HistoryPage() {
  const { sessionId } = useWorkspaceSession();
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [detailAnalysisId, setDetailAnalysisId] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    let cancelled = false;
    const activeSessionId = sessionId;
    async function loadRuns() {
      setState("loading");
      setMessage(null);
      try {
        const response = await listAnalysisRuns(activeSessionId);
        if (cancelled) {
          return;
        }
        setRuns(response.analysis_runs);
        setState("ready");
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setRuns([]);
        setState("error");
        setMessage(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Analysis history could not be loaded.",
        );
      }
    }

    void loadRuns();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const visibleRuns = sessionId ? runs : [];

  return (
    <div className="px-6 py-8">
      <header className="mb-6 flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/12 text-emerald-600">
          <svg {...ip}>
            <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
            <path d="M3 4v4h4M12 8v4l3 2" />
          </svg>
        </span>
        <div>
          <h1 className="text-xl font-semibold text-ink">History</h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            Real analysis runs are preserved with SQL, ChartSpec, result preview,
            provider evidence, and insight status.
          </p>
        </div>
      </header>

      <div
        className="overflow-hidden rounded-lg border border-border bg-surface"
        style={{ borderTop: "4px solid #059669" }}
      >
        <div className="hidden grid-cols-[1.6fr_1fr_0.8fr_0.7fr_1fr_0.8fr] gap-3 border-b border-border bg-surface-muted px-4 py-2.5 text-xs font-semibold text-ink-muted md:grid">
          <span>Question</span>
          <span>Dataset</span>
          <span>Status</span>
          <span>Charts</span>
          <span>Source model</span>
          <span>Detail</span>
        </div>

        {state === "loading" ? (
          <div className="px-6 py-12 text-center text-sm text-ink-muted">
            Loading real analysis history...
          </div>
        ) : null}

        {state === "error" ? (
          <div className="px-6 py-12 text-center">
            <p className="mx-auto max-w-md rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {message}
            </p>
          </div>
        ) : null}

        {state !== "loading" && state !== "error" && visibleRuns.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <svg {...ip}>
                <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                <path d="M3 4v4h4M12 8v4l3 2" />
              </svg>
            </span>
            <h3 className="mt-4 text-base font-semibold text-ink">
              No analysis history yet
            </h3>
            <p className="prose-measure mt-2 text-sm text-ink-muted">
              Generated analyses appear here only after the backend stores a real
              analysis run. No placeholder rows are shown.
            </p>
            <a
              href="/demo/dashboard"
              className="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4.5 py-2.5 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              Go to Dashboard
            </a>
          </div>
        ) : null}

        {visibleRuns.length > 0 ? (
          <div className="divide-y divide-border">
            {visibleRuns.map((run) => (
              <article
                key={run.id}
                className="grid gap-3 px-4 py-4 text-sm md:grid-cols-[1.6fr_1fr_0.8fr_0.7fr_1fr_0.8fr] md:items-center"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-ink">{run.question}</p>
                  <p className="mt-1 text-xs text-ink-muted">
                    Created {formatDate(run.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-xs text-ink-muted">
                  <span className="truncate">{run.dataset_name ?? run.dataset_id}</span>
                  {run.dataset_deleted ? (
                    <span className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
                      Dataset deleted
                    </span>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${statusTone(run.status)}`}
                  >
                    {run.status}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${statusTone(run.insight_status)}`}
                  >
                    insights: {run.insight_status}
                  </span>
                </div>
                <div className="text-xs font-semibold text-ink">{run.chart_count}</div>
                <div className="truncate text-xs text-ink-muted">
                  {run.source_model ?? "No source model"}
                </div>
                <button
                  type="button"
                  onClick={() => setDetailAnalysisId(run.id)}
                  className="cursor-pointer rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 transition-colors hover:border-emerald-300 hover:bg-emerald-100"
                >
                  View Detail
                </button>
              </article>
            ))}
          </div>
        ) : null}
      </div>

      <AnalysisDetailDrawer
        open={detailAnalysisId !== null}
        sessionId={sessionId}
        analysisRunId={detailAnalysisId}
        onClose={() => setDetailAnalysisId(null)}
      />
    </div>
  );
}
