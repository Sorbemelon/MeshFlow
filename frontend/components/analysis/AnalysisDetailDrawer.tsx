"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import {
  getAnalysisRun,
  MeshFlowApiError,
  type AnalysisInsightSummary,
  type AnalysisRunResponse,
} from "@/lib/meshflowApi";

function formatDate(value: string | null): string {
  if (!value) {
    return "Not completed";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-72 overflow-auto rounded-md border border-border bg-slate-950 px-3 py-2 text-xs leading-relaxed text-slate-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function EvidenceSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <details className="rounded-md border border-border bg-surface">
      <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-ink">
        {title}
      </summary>
      <div className="border-t border-border p-3">{children}</div>
    </details>
  );
}

function CompletedInsight({ insight }: { insight: AnalysisInsightSummary }) {
  return (
    <div className="rounded-md border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-900">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold">
          {insight.insight_level === "question" ? "Question insight" : "Chart insight"}
        </span>
        {insight.confidence ? (
          <span className="rounded-full border border-indigo-200 bg-white px-2 py-0.5 text-[0.6875rem] font-semibold text-indigo-700">
            {insight.confidence}
          </span>
        ) : null}
      </div>
      {insight.summary ? <p className="mt-1">{insight.summary}</p> : null}
      {insight.key_findings.length > 0 ? (
        <ul className="mt-2 space-y-1 text-indigo-800">
          {insight.key_findings.map((finding, index) => (
            <li key={`${insight.id}-${index}`}>{finding}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function AnalysisDetailDrawer({
  open,
  sessionId,
  analysisRunId,
  onClose,
}: {
  open: boolean;
  sessionId: string | null;
  analysisRunId: string | null;
  onClose: () => void;
}) {
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [detail, setDetail] = useState<AnalysisRunResponse | null>(null);

  useEffect(() => {
    if (!open || !sessionId || !analysisRunId) {
      return;
    }

    let cancelled = false;
    const activeSessionId = sessionId;
    const activeAnalysisRunId = analysisRunId;
    async function loadDetail() {
      setState("loading");
      setMessage(null);
      try {
        const response = await getAnalysisRun(activeSessionId, activeAnalysisRunId);
        if (cancelled) {
          return;
        }
        setDetail(response);
        setState("ready");
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setDetail(null);
        setState("error");
        setMessage(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Analysis detail could not be loaded.",
        );
      }
    }

    void loadDetail();

    return () => {
      cancelled = true;
    };
  }, [analysisRunId, open, sessionId]);

  const completedInsights = useMemo(
    () => detail?.insights.filter((insight) => insight.status === "completed") ?? [],
    [detail?.insights],
  );
  const failedInsights = useMemo(
    () => detail?.insights.filter((insight) => insight.status === "failed") ?? [],
    [detail?.insights],
  );

  return (
    <div
      className={cn(
        "fixed inset-0 z-40 transition-opacity duration-200",
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
      )}
      aria-hidden={!open}
    >
      <div className="absolute inset-0 cursor-pointer bg-shell-deep/40" onClick={onClose} />
      <aside
        role="dialog"
        aria-modal
        aria-label="Analysis detail"
        className={cn(
          "absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col border-l border-border bg-surface shadow-[0_16px_40px_rgba(15,23,42,0.16)] transition-transform duration-200 ease-out-quart",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Analysis Evidence
            </p>
            <h2 className="text-base font-semibold text-ink">Analysis detail</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            className="cursor-pointer rounded-md p-1 text-ink-muted transition-colors hover:bg-surface-muted"
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

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {state === "loading" ? (
            <p className="rounded-md bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              Loading stored analysis evidence...
            </p>
          ) : null}

          {state === "error" ? (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {message}
            </p>
          ) : null}

          {state === "ready" && detail ? (
            <div className="space-y-4">
              <section className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                      {detail.analysis_run.status}
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-ink">
                      {detail.analysis_run.question}
                    </h3>
                  </div>
                  <span className="rounded-full border border-emerald-200 bg-white px-2.5 py-1 text-xs font-semibold text-emerald-700">
                    {detail.charts.length} chart{detail.charts.length === 1 ? "" : "s"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-700">
                    Dataset: {detail.analysis_run.dataset_name ?? detail.analysis_run.dataset_id}
                  </span>
                  {detail.analysis_run.source_model ? (
                    <span className="rounded-full border border-indigo-200 bg-white px-2.5 py-1 text-indigo-700">
                      {detail.analysis_run.source_model}
                    </span>
                  ) : null}
                  <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-700">
                    Created: {formatDate(detail.analysis_run.created_at)}
                  </span>
                </div>
              </section>

              {completedInsights.length > 0 ? (
                <section className="space-y-2">
                  <h3 className="text-sm font-semibold text-ink">Insights</h3>
                  {completedInsights.map((insight) => (
                    <CompletedInsight key={insight.id} insight={insight} />
                  ))}
                </section>
              ) : null}

              {detail.insight_generation_status === "failed" || failedInsights.length > 0 ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  {detail.insight_generation_message ??
                    failedInsights[0]?.error_message ??
                    "Analysis completed, but insight generation failed."}
                </p>
              ) : null}

              <section className="space-y-2">
                <h3 className="text-sm font-semibold text-ink">Charts</h3>
                {detail.charts.length > 0 ? (
                  <div className="grid gap-2">
                    {detail.charts.map((chart) => (
                      <div
                        key={chart.id}
                        className="rounded-md border border-border bg-surface-muted px-3 py-2 text-xs"
                      >
                        <p className="font-semibold text-ink">{chart.title}</p>
                        <p className="mt-1 text-ink-muted">
                          {chart.chart_type} - {chart.source_model ?? "No source model"}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-md bg-surface-muted px-3 py-2 text-sm text-ink-muted">
                    No chart snapshots are stored for this analysis.
                  </p>
                )}
              </section>

              <EvidenceSection title="Generated SQL">
                {detail.analysis_run.generated_sql ? (
                  <pre className="max-h-72 overflow-auto rounded-md border border-border bg-slate-950 px-3 py-2 text-xs leading-relaxed text-slate-100">
                    {detail.analysis_run.generated_sql}
                  </pre>
                ) : (
                  <p className="text-sm text-ink-muted">No SQL was stored.</p>
                )}
              </EvidenceSection>

              <EvidenceSection title="ChartSpec JSON">
                <JsonBlock value={detail.charts.map((chart) => chart.chart_spec)} />
              </EvidenceSection>

              <EvidenceSection title="Output Schema">
                <JsonBlock value={detail.analysis_run.output_schema} />
              </EvidenceSection>

              <EvidenceSection title="Preview Rows">
                <JsonBlock value={detail.analysis_run.preview_rows} />
              </EvidenceSection>

              <EvidenceSection title="Provider Evidence">
                <JsonBlock value={detail.analysis_run.provider_runs} />
              </EvidenceSection>
            </div>
          ) : null}

          {state === "idle" ? (
            <p className="rounded-md bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              Select a real analysis run to inspect stored evidence.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
