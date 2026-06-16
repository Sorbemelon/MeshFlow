"use client";

import { useEffect, useMemo, useState } from "react";
import { ChartCard } from "@/components/charts/ChartCard";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import {
  createAnalysisRun,
  getDataset,
  MeshFlowApiError,
  type AnalysisRunResponse,
  type DatasetQuestionSuggestionSummary,
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
  const { sessionId, workspace, refresh } = useWorkspaceSession();
  const readyDatasets = useMemo(
    () => workspace?.ready_datasets ?? [],
    [workspace?.ready_datasets],
  );
  const schemaReviewDatasets = useMemo(() => workspace?.datasets ?? [], [workspace?.datasets]);
  const hasReadyDataset = readyDatasets.length > 0;
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [questionState, setQuestionState] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [questionMessage, setQuestionMessage] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<
    DatasetQuestionSuggestionSummary[]
  >([]);
  const [questionText, setQuestionText] = useState("");
  const [analysisState, setAnalysisState] = useState<
    "idle" | "planning" | "generated" | "reused" | "failed"
  >("idle");
  const [analysisMessage, setAnalysisMessage] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisRunResponse | null>(null);

  const activeDatasetId = useMemo(() => {
    if (!readyDatasets.length) {
      return "";
    }
    if (selectedDatasetId && readyDatasets.some((dataset) => dataset.id === selectedDatasetId)) {
      return selectedDatasetId;
    }
    return readyDatasets[0].id;
  }, [readyDatasets, selectedDatasetId]);

  const selectedDataset = useMemo(
    () => readyDatasets.find((dataset) => dataset.id === activeDatasetId) ?? null,
    [activeDatasetId, readyDatasets],
  );

  const hasSchemaReviewDatasets = useMemo(
    () => schemaReviewDatasets.length > 0,
    [schemaReviewDatasets],
  );

  useEffect(() => {
    if (!sessionId || !activeDatasetId) {
      return;
    }

    let cancelled = false;
    const activeSessionId = sessionId;
    const requestedDatasetId = activeDatasetId;
    async function loadQuestions() {
      await Promise.resolve();
      if (cancelled) {
        return;
      }

      setQuestionState("loading");
      setQuestionMessage(null);
      try {
        const detail = await getDataset(requestedDatasetId, activeSessionId);
        if (cancelled) {
          return;
        }
        setSuggestedQuestions(detail.semantic_preparation.suggested_questions);
        setQuestionState("ready");
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setSuggestedQuestions([]);
        setQuestionState("error");
        setQuestionMessage(
          caught instanceof MeshFlowApiError
            ? caught.details.message
            : "Prepared questions could not be loaded.",
        );
      }
    }

    void loadQuestions();

    return () => {
      cancelled = true;
    };
  }, [activeDatasetId, sessionId]);

  async function handleGenerateAnalysis() {
    if (!sessionId || !activeDatasetId || !questionText.trim()) {
      return;
    }

    setAnalysisState("planning");
    setAnalysisMessage("Planning, validating, and running the Snowflake analysis...");
    setAnalysisResult(null);

    try {
      const response = await createAnalysisRun(sessionId, {
        attached_dataset_id: activeDatasetId,
        question: questionText.trim(),
      });
      setAnalysisResult(response);
      setAnalysisState(response.reused ? "reused" : "generated");
      setAnalysisMessage(
        response.reused
          ? "Reused a matching completed analysis run."
          : "Generated from a completed Snowflake analysis run.",
      );
      await refresh();
    } catch (caught) {
      setAnalysisState("failed");
      setAnalysisResult(null);
      setAnalysisMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "MeshFlow could not generate the analysis result.",
      );
    }
  }

  return (
    <div className="px-6 py-8">
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
          <h1 className="text-xl font-semibold text-ink">Dashboard</h1>
          <p className="mt-0.5 text-sm text-ink-muted">
            One dashboard per session. Ask the AI Analytics Engineer, then
            build it from validated results.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <section
          className="self-start rounded-lg border border-border bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
          style={{ borderTop: "4px solid #4f46e5" }}
        >
          <div className="mb-4 flex items-center gap-2">
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
            <h2 className="text-sm font-semibold text-ink">AI Analytics Engineer</h2>
          </div>

          <p className="mb-4 text-xs leading-relaxed text-ink-muted">
            Analysis requires an explicit dataset. There is no hidden selected dataset.
          </p>

          <label className="block text-xs font-semibold text-ink">Attach dataset</label>
          <select
            disabled={!hasReadyDataset}
            value={activeDatasetId}
            onChange={(event) => setSelectedDatasetId(event.target.value)}
            aria-label="Attach dataset"
            className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink-muted disabled:cursor-not-allowed disabled:bg-surface-muted"
          >
            <option value="">No ready dataset</option>
            {readyDatasets.map((dataset, index) => (
              <option key={dataset.id} value={dataset.id}>
                {datasetLabel(dataset, index)}
              </option>
            ))}
          </select>
          {selectedDataset ? (
            <p className="mt-2 rounded-md border border-violet-200 bg-violet-50/40 px-3 py-2 font-mono text-xs text-violet-900">
              {selectedDataset.raw_table_name}
            </p>
          ) : null}

          <label className="mt-4 block text-xs font-semibold text-ink">Question</label>
          <textarea
            disabled={!hasReadyDataset}
            rows={3}
            value={questionText}
            onChange={(event) => setQuestionText(event.target.value)}
            className="mt-1.5 w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:bg-surface-muted"
          />

          <div className="mt-4">
            <p className="text-xs font-semibold text-ink">Suggested questions</p>
            {questionState === "loading" ? (
              <p className="mt-1.5 rounded-md bg-surface-muted px-3 py-2.5 text-xs text-ink-muted">
                Loading prepared questions...
              </p>
            ) : null}
            {questionState === "error" ? (
              <p className="mt-1.5 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700">
                {questionMessage}
              </p>
            ) : null}
            {questionState !== "loading" && questionState !== "error" ? (
              suggestedQuestions.length > 0 ? (
                <div className="mt-1.5 grid gap-2">
                  {suggestedQuestions.map((question) => (
                    <button
                      type="button"
                      key={question.id}
                      onClick={() => setQuestionText(question.question)}
                      className="rounded-md border border-violet-100 bg-violet-50/40 px-3 py-2 text-left text-xs text-ink-soft transition-colors hover:border-violet-300 hover:bg-violet-50"
                    >
                      {question.question}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-1.5 rounded-md bg-surface-muted px-3 py-2.5 text-xs text-ink-muted">
                  {hasSchemaReviewDatasets
                    ? "No prepared questions are available for this ready dataset yet. You can still ask a direct question."
                    : "Suggestions appear after a dataset is loaded and semantic preparation succeeds."}
                </p>
              )
            ) : null}
          </div>

          <button
            type="button"
            disabled={
              !sessionId ||
              !hasReadyDataset ||
              !questionText.trim() ||
              analysisState === "planning"
            }
            onClick={handleGenerateAnalysis}
            title={
              hasReadyDataset
                ? "Generate a real analysis result from the attached ready dataset."
                : "Prepare a dataset before asking the AI Analytics Engineer."
            }
            className="mt-4 w-full rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analysisState === "planning" ? "Generating..." : "Generate Analysis"}
          </button>
          {analysisMessage ? (
            <p
              className={
                analysisState === "failed"
                  ? "mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
                  : "mt-3 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs text-indigo-700"
              }
            >
              {analysisMessage}
            </p>
          ) : null}
        </section>

        <section className="min-w-0">
          {analysisResult ? (
            <div className="grid gap-4">
              <div className="rounded-lg border border-violet-200 bg-violet-50/40 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                      {analysisResult.reused ? "Reused Result Group" : "Generated Result Group"}
                    </p>
                    <h2 className="mt-1 text-base font-semibold text-ink">
                      {analysisResult.analysis_run.question}
                    </h2>
                  </div>
                  <span className="rounded-full border border-violet-200 bg-white px-2.5 py-1 text-xs font-semibold text-violet-700">
                    {analysisResult.analysis_run.status}
                  </span>
                </div>
                {analysisResult.chart_generation_status === "failed" ? (
                  <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    {analysisResult.chart_generation_message ??
                      "The analysis completed, but MeshFlow could not create a valid ChartSpec for this result."}
                  </p>
                ) : null}
              </div>

              {analysisResult.charts.length > 0 && selectedDataset ? (
                analysisResult.charts.map((chart) => (
                  <ChartCard
                    key={chart.id}
                    chart={chart}
                    analysisRun={analysisResult.analysis_run}
                    datasetName={selectedDataset.name}
                  />
                ))
              ) : analysisResult.chart_generation_status !== "failed" ? (
                <div className="rounded-lg border border-dashed border-violet-200 bg-surface px-6 py-12 text-center">
                  <h3 className="text-base font-semibold text-ink">
                    No chart snapshot returned
                  </h3>
                  <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-muted">
                    The backend returned a completed analysis without chart snapshots.
                    No synthetic chart is shown.
                  </p>
                </div>
              ) : null}
            </div>
          ) : (
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
                {hasReadyDataset ? "Ask a question to generate charts" : "Prepare a dataset first"}
              </h3>
              <p className="prose-measure mt-2 text-sm text-ink-muted">
                {hasReadyDataset
                  ? "Generated chart snapshots from completed Snowflake analysis runs appear here. Dashboard card persistence starts later."
                  : "Once a dataset is uploaded and transformed to Data Marts, generated chart cards appear here with a dataset badge and evidence."}
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
          )}
        </section>
      </div>
    </div>
  );
}
