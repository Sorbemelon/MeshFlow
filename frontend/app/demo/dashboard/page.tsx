"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnalysisDetailDrawer } from "@/components/analysis/AnalysisDetailDrawer";
import { ChartCard } from "@/components/charts/ChartCard";
import { ChartRenderer } from "@/components/charts/ChartRenderer";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { displayDatasetName } from "@/lib/datasetNames";
import {
  createDashboardCardFromAnalysis,
  createAnalysisRun,
  deleteDashboardCard,
  getAnalysisRun,
  getDataset,
  listAnalysisRuns,
  MeshFlowApiError,
  type AnalysisRunChartSummary,
  type AnalysisRunSummary,
  type DashboardCardSummary,
  type DatasetQuestionSuggestionSummary,
  type DatasetSummary,
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

const DASHBOARD_COMPACT_STATE_STORAGE_KEY = "meshflow.dashboardCompactCardKeys";

function datasetLabel(dataset: Record<string, unknown>, index: number): string {
  const name = dataset.name;
  if (typeof name === "string" && name.trim()) {
    return displayDatasetName(name);
  }

  const id = dataset.id;
  if (typeof id === "string" && id.trim()) {
    return id;
  }

  return `Ready dataset ${index + 1}`;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not completed";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function dashboardCardViewKey(card: DashboardCardSummary): string {
  return card.analysis_run_id ?? card.card_snapshot.analysis_run.id ?? card.id;
}

function loadCompactDashboardCardKeys(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }

  try {
    const storedValue = window.sessionStorage.getItem(DASHBOARD_COMPACT_STATE_STORAGE_KEY);
    const storedKeys = storedValue ? JSON.parse(storedValue) : [];
    return new Set(
      Array.isArray(storedKeys)
        ? storedKeys.filter((key): key is string => typeof key === "string")
        : [],
    );
  } catch {
    return new Set();
  }
}

function saveCompactDashboardCardKeys(keys: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    DASHBOARD_COMPACT_STATE_STORAGE_KEY,
    JSON.stringify([...keys]),
  );
}

function InlineSpinner() {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      aria-hidden
      className="animate-spin"
    >
      <path d="M16 5.5A7 7 0 1 0 17 10" />
      <path d="M16 3v3h-3" />
    </svg>
  );
}

function PersistedDashboardCard({
  card,
  editMode,
  isRemoving,
  isCompact,
  isProcessRunning,
  processLabel,
  onToggleCompact,
  onRemove,
  onViewEvidence,
}: {
  card: DashboardCardSummary;
  editMode: boolean;
  isRemoving: boolean;
  isCompact: boolean;
  isProcessRunning: boolean;
  processLabel: string | null;
  onToggleCompact: () => void;
  onRemove: () => void;
  onViewEvidence: () => void;
}) {
  const snapshot = card.card_snapshot;
  const questionInsight =
    snapshot.insights.find(
      (insight) =>
        insight.status === "completed" && insight.insight_level === "question",
    ) ?? null;
  const datasetName =
    displayDatasetName(
      card.dataset_name_snapshot ?? snapshot.dataset.name,
      "Saved dataset snapshot",
    );
  const datasetDeleted = card.source_dataset_deleted || snapshot.dataset.deleted === true;
  const firstChartId = snapshot.charts[0]?.id ?? null;
  const expandButton = (
    <button
      type="button"
      disabled={isProcessRunning}
      onClick={onToggleCompact}
      aria-label={`Expand saved result group ${card.title}`}
      title={
        isProcessRunning
          ? `Wait for the current process to finish: ${processLabel}.`
          : "Expand saved result group"
      }
      className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-violet-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-violet-700 shadow-[0_4px_12px_rgba(15,23,42,0.08)] transition-colors hover:border-violet-300 hover:bg-violet-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-55"
    >
      <svg {...ip} className="h-3.5 w-3.5">
        <path d="M8 3H3v5" />
        <path d="M3 3l6 6" />
        <path d="M16 21h5v-5" />
        <path d="M21 21l-6-6" />
      </svg>
      Expand
    </button>
  );

  return (
    <article
      aria-label={`Saved result group: ${card.title}`}
      className={`rounded-lg border border-violet-200 bg-violet-50/35 p-3 ${
        isCompact ? "space-y-2" : ""
      }`}
    >
      {!isCompact ? (
        <div>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h2 className="text-base font-semibold text-ink">{card.title}</h2>
              <p className="mt-1 text-xs text-ink-muted">Saved {formatDate(card.created_at)}</p>
            </div>
            {editMode ? (
              <button
                type="button"
                disabled={isRemoving || isProcessRunning}
                onClick={onRemove}
                title={
                  isProcessRunning && !isRemoving
                    ? `Wait for the current process to finish: ${processLabel}.`
                    : "Remove this visible card. Public quota usage is not restored."
                }
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-red-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isRemoving ? <InlineSpinner /> : null}
                {isRemoving ? "Removing..." : "Remove"}
              </button>
            ) : null}
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                Dataset: {datasetName}
              </span>
              {datasetDeleted ? (
                <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                  Dataset deleted
                </span>
              ) : null}
              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700">
                Status: {snapshot.analysis_run.status}
              </span>
            </div>
            <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                disabled={isProcessRunning}
                onClick={onViewEvidence}
                title={
                  isProcessRunning
                    ? `Wait for the current process to finish: ${processLabel}.`
                    : "View stored analysis evidence."
                }
                className="cursor-pointer rounded-md border border-violet-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-violet-700 transition-colors hover:border-violet-300 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-55"
              >
                View Evidence
              </button>
              <button
                type="button"
                disabled={isProcessRunning}
                onClick={onToggleCompact}
                aria-pressed={false}
                aria-label={`Compact saved result group ${card.title}`}
                title={
                  isProcessRunning
                    ? `Wait for the current process to finish: ${processLabel}.`
                    : "Compact saved result group"
                }
                className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-violet-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-violet-700 transition-colors hover:border-violet-300 hover:bg-violet-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-55"
              >
                <svg {...ip} className="h-3.5 w-3.5">
                  <path d="M9 3v6H3" />
                  <path d="M3 9l6-6" />
                  <path d="M15 21v-6h6" />
                  <path d="M21 15l-6 6" />
                </svg>
                Compact
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {!isCompact && questionInsight ? (
        <div className="mt-3 rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm text-indigo-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
            Question Insight
          </p>
          {questionInsight.summary ? <p className="mt-1">{questionInsight.summary}</p> : null}
          {questionInsight.key_findings.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-indigo-800">
              {questionInsight.key_findings.map((finding, index) => (
                <li key={`${questionInsight.id}-${index}`}>{finding}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {isCompact && editMode ? (
        <div className="flex justify-end">
          <button
            type="button"
            disabled={isRemoving || isProcessRunning}
            onClick={onRemove}
            title={
              isProcessRunning && !isRemoving
                ? `Wait for the current process to finish: ${processLabel}.`
                : "Remove this visible card. Public quota usage is not restored."
            }
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-red-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRemoving ? <InlineSpinner /> : null}
            {isRemoving ? "Removing..." : "Remove"}
          </button>
        </div>
      ) : null}

      <div className={`${isCompact ? "grid gap-2" : "mt-3 grid gap-3"}`}>
        {snapshot.charts.map((chart) => (
          <ChartCard
            key={chart.id}
            chart={chart}
            insights={snapshot.insights}
            compact={isCompact}
            compactAction={isCompact && chart.id === firstChartId ? expandButton : undefined}
          />
        ))}
      </div>
    </article>
  );
}

function ResultGroupChooserDrawer({
  open,
  resultGroups,
  resultGroupState,
  resultGroupMessage,
  chartPreviews,
  addingResultGroupId,
  isProcessRunning,
  processLabel,
  onAdd,
  onClose,
}: {
  open: boolean;
  resultGroups: AnalysisRunSummary[];
  resultGroupState: "idle" | "loading" | "ready" | "error";
  resultGroupMessage: string | null;
  chartPreviews: Record<string, AnalysisRunChartSummary[]>;
  addingResultGroupId: string | null;
  isProcessRunning: boolean;
  processLabel: string | null;
  onAdd: (analysisRunId: string) => void;
  onClose: () => void;
}) {
  return (
    <div
      className={`fixed inset-0 z-40 transition-opacity duration-200 ${
        open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!open}
    >
      <div className="absolute inset-0 cursor-pointer bg-shell-deep/40" onClick={onClose} />
      <aside
        role="dialog"
        aria-modal
        aria-label="Add saved result group to dashboard"
        className={`absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-border bg-surface shadow-[0_16px_40px_rgba(15,23,42,0.16)] transition-transform duration-200 ease-out-quart ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
              Add to Dashboard
            </p>
            <h2 className="text-base font-semibold text-ink">Saved result groups</h2>
            <p className="mt-1 text-sm text-ink-muted">
              Choose a completed analysis result group with stored charts.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close saved result group chooser"
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
          {resultGroupMessage ? (
            <p
              className={
                resultGroupState === "error"
                  ? "rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
                  : "rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
              }
            >
              {resultGroupMessage}
            </p>
          ) : null}

          {resultGroupState === "loading" ? (
            <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              <InlineSpinner />
              Loading saved result groups...
            </p>
          ) : null}

          {resultGroupState !== "loading" &&
          resultGroupState !== "error" &&
          resultGroups.length === 0 ? (
            <p className="mt-3 rounded-md bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              No saved result groups are available to add. Result groups already on this
              dashboard are hidden here.
            </p>
          ) : null}

          {resultGroups.length > 0 ? (
            <div className="mt-3 grid gap-3">
              {resultGroups.map((resultGroup) => {
                const previewChart = chartPreviews[resultGroup.id]?.[0] ?? null;
                return (
                  <article
                    key={resultGroup.id}
                    className="rounded-md border border-border bg-surface-muted px-3 py-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="break-words text-sm font-semibold text-ink">
                          {resultGroup.question}
                        </p>
                        <p className="mt-1 text-xs text-ink-muted">
                          {displayDatasetName(resultGroup.dataset_name, resultGroup.dataset_id)}
                        {resultGroup.source_model ? ` - ${resultGroup.source_model}` : ""}
                      </p>
                      </div>
                      <button
                        type="button"
                        disabled={addingResultGroupId !== null || isProcessRunning}
                        onClick={() => onAdd(resultGroup.id)}
                        title={
                          isProcessRunning && addingResultGroupId !== resultGroup.id
                            ? `Wait for the current process to finish: ${processLabel}.`
                            : "Add this stored result group to the dashboard."
                        }
                        className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-violet-200 bg-white px-3 py-2 text-xs font-semibold text-violet-700 transition-colors hover:border-violet-300 hover:bg-violet-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-600 disabled:cursor-not-allowed disabled:opacity-55"
                      >
                        {addingResultGroupId === resultGroup.id ? <InlineSpinner /> : null}
                        {addingResultGroupId === resultGroup.id ? "Adding..." : "Add"}
                      </button>
                    </div>
                    {previewChart ? (
                      <div className="mt-3 overflow-hidden rounded-md border border-violet-100 bg-white px-2 py-2">
                        <p className="truncate text-xs font-semibold text-ink">
                          {previewChart.title}
                        </p>
                        <div className="mt-2">
                          <ChartRenderer chart={previewChart} compact />
                        </div>
                      </div>
                    ) : (
                      <p className="mt-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-ink-muted">
                        Chart preview is unavailable for this stored result group.
                      </p>
                    )}
                    <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                      <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 font-semibold text-slate-700">
                        {resultGroup.chart_count} chart
                        {resultGroup.chart_count === 1 ? "" : "s"}
                      </span>
                      <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 font-semibold text-slate-700">
                        {formatDate(resultGroup.completed_at)}
                      </span>
                      {resultGroup.dataset_deleted ? (
                        <span className="rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
                          Dataset deleted
                        </span>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

export default function DashboardPage() {
  const {
    activeProcessLabel,
    datasetDeleteOperation,
    isAnyProcessRunning,
    sessionId,
    startDatasetDelete,
    workspace,
    refresh,
  } = useWorkspaceSession();
  const readyDatasets = useMemo(
    () => workspace?.ready_datasets ?? [],
    [workspace?.ready_datasets],
  );
  const schemaReviewDatasets = useMemo(() => workspace?.datasets ?? [], [workspace?.datasets]);
  const hasReadyDataset = readyDatasets.length > 0;
  const dashboardCards = useMemo(
    () => workspace?.dashboard.cards ?? [],
    [workspace?.dashboard.cards],
  );
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
  const deletingDatasetId =
    datasetDeleteOperation?.status === "deleting" ? datasetDeleteOperation.datasetId : null;
  const datasetDeleteMessage = datasetDeleteOperation?.message ?? null;
  const [detailAnalysisId, setDetailAnalysisId] = useState<string | null>(null);
  const [removingCardId, setRemovingCardId] = useState<string | null>(null);
  const [dashboardEditMode, setDashboardEditMode] = useState(false);
  const [compactDashboardCardKeys, setCompactDashboardCardKeys] = useState<Set<string>>(
    loadCompactDashboardCardKeys,
  );
  const [resultGroups, setResultGroups] = useState<AnalysisRunSummary[]>([]);
  const [resultGroupState, setResultGroupState] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [resultGroupMessage, setResultGroupMessage] = useState<string | null>(null);
  const [resultGroupChartPreviews, setResultGroupChartPreviews] = useState<
    Record<string, AnalysisRunChartSummary[]>
  >({});
  const [addingResultGroupId, setAddingResultGroupId] = useState<string | null>(null);
  const [resultGroupDrawerOpen, setResultGroupDrawerOpen] = useState(false);
  const dashboardProcessRunning =
    isAnyProcessRunning ||
    analysisState === "planning" ||
    removingCardId !== null ||
    addingResultGroupId !== null ||
    resultGroupState === "loading";
  const dashboardProcessLabel =
    analysisState === "planning"
      ? "Generating analysis"
      : removingCardId !== null
        ? "Removing dashboard card"
        : addingResultGroupId !== null
          ? "Adding saved result group"
          : resultGroupState === "loading"
            ? "Loading saved result groups"
            : activeProcessLabel;

  const activeDatasetId = useMemo(() => {
    if (!readyDatasets.length) {
      return "";
    }
    if (selectedDatasetId && readyDatasets.some((dataset) => dataset.id === selectedDatasetId)) {
      return selectedDatasetId;
    }
    return readyDatasets[0].id;
  }, [readyDatasets, selectedDatasetId]);
  const activeDataset = useMemo(
    () => readyDatasets.find((dataset) => dataset.id === activeDatasetId) ?? null,
    [activeDatasetId, readyDatasets],
  );
  const activeDatasetIsDeleting =
    Boolean(deletingDatasetId) && deletingDatasetId === activeDatasetId;

  const hasSchemaReviewDatasets = useMemo(
    () => schemaReviewDatasets.length > 0,
    [schemaReviewDatasets],
  );
  const activeDashboardAnalysisIds = useMemo(
    () =>
      new Set(
        dashboardCards
          .map((card) => card.analysis_run_id)
          .filter((id): id is string => Boolean(id)),
      ),
    [dashboardCards],
  );
  const completedResultGroups = useMemo(
    () =>
      resultGroups.filter(
        (resultGroup) => resultGroup.status === "completed" && resultGroup.chart_count > 0,
      ),
    [resultGroups],
  );
  const availableResultGroups = useMemo(
    () =>
      completedResultGroups.filter(
        (resultGroup) => !activeDashboardAnalysisIds.has(resultGroup.id),
      ),
    [activeDashboardAnalysisIds, completedResultGroups],
  );

  const toggleDashboardCardCompact = useCallback((cardKey: string) => {
    setCompactDashboardCardKeys((current) => {
      const next = new Set(current);
      if (next.has(cardKey)) {
        next.delete(cardKey);
      } else {
        next.add(cardKey);
      }
      saveCompactDashboardCardKeys(next);
      return next;
    });
  }, []);

  const loadResultGroups = useCallback(async () => {
    await Promise.resolve();
    if (!sessionId) {
      setResultGroups([]);
      setResultGroupChartPreviews({});
      setResultGroupState("idle");
      return;
    }

    setResultGroupState("loading");
    setResultGroupMessage(null);
    try {
      const response = await listAnalysisRuns(sessionId);
      setResultGroups(response.analysis_runs);
      const completedGroups = response.analysis_runs.filter(
        (resultGroup) => resultGroup.status === "completed" && resultGroup.chart_count > 0,
      );
      const previewEntries = await Promise.all(
        completedGroups.map(async (resultGroup) => {
          try {
            const detail = await getAnalysisRun(sessionId, resultGroup.id);
            return [resultGroup.id, detail.charts.slice(0, 1)] as const;
          } catch {
            return [resultGroup.id, []] as const;
          }
        }),
      );
      setResultGroupChartPreviews(Object.fromEntries(previewEntries));
      setResultGroupState("ready");
    } catch (caught) {
      setResultGroups([]);
      setResultGroupChartPreviews({});
      setResultGroupState("error");
      setResultGroupMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Saved result groups could not be loaded.",
      );
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || !activeDatasetId || activeDatasetIsDeleting) {
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
        setSuggestedQuestions(detail.question_suggestions.suggestions);
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
  }, [activeDatasetId, activeDatasetIsDeleting, sessionId]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadResultGroups();
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [loadResultGroups]);

  async function handleGenerateAnalysis() {
    if (
      !sessionId ||
      !activeDatasetId ||
      activeDatasetIsDeleting ||
      !questionText.trim() ||
      dashboardProcessRunning
    ) {
      return;
    }

    setAnalysisState("planning");
    setAnalysisMessage("Planning, validating, and running the Snowflake analysis...");

    try {
      const response = await createAnalysisRun(sessionId, {
        attached_dataset_id: activeDatasetId,
        question: questionText.trim(),
        save_to_dashboard: true,
      });
      setAnalysisState(response.reused ? "reused" : "generated");
      setAnalysisMessage(
        response.dashboard_card_message ??
          (response.reused
            ? "Reused a matching completed analysis run."
            : "Generated and saved to the dashboard."),
      );
      await refresh();
      await loadResultGroups();
    } catch (caught) {
      setAnalysisState("failed");
      setAnalysisMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "MeshFlow could not generate the analysis result.",
      );
    }
  }

  async function handleRemoveCard(cardId: string) {
    if (!sessionId || dashboardProcessRunning) {
      return;
    }
    setRemovingCardId(cardId);
    setAnalysisMessage(null);
    try {
      const response = await deleteDashboardCard(sessionId, cardId);
      setAnalysisMessage(
        response.message ??
          "Dashboard card removed from the visible canvas. Public quota was not restored.",
      );
      await refresh();
      await loadResultGroups();
    } catch (caught) {
      setAnalysisMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "MeshFlow could not remove this dashboard card.",
      );
    } finally {
      setRemovingCardId(null);
    }
  }

  async function handleDeleteAttachedDataset(dataset: DatasetSummary, index: number) {
    if (!sessionId || dashboardProcessRunning) {
      return;
    }

    const name = datasetLabel(dataset, index);
    const confirmed = window.confirm(
      `Remove "${name}" from active dataset management? Existing dashboard cards and history remain available, and quota usage is not restored.`,
    );
    if (!confirmed) {
      return;
    }

    setAnalysisMessage(null);
    const response = await startDatasetDelete(dataset);
    if (response) {
      setSelectedDatasetId((current) => (current === dataset.id ? "" : current));
      await refresh();
      await loadResultGroups();
    }
  }

  async function handleAddResultGroupToDashboard(analysisRunId: string) {
    if (!sessionId || dashboardProcessRunning) {
      return;
    }

    setAddingResultGroupId(analysisRunId);
    setResultGroupMessage(null);
    try {
      const response = await createDashboardCardFromAnalysis(sessionId, analysisRunId);
      setResultGroupMessage(
        response.message ??
          (response.created
            ? "Saved result group to the dashboard."
            : "This result group is already on the dashboard."),
      );
      await refresh();
      await loadResultGroups();
    } catch (caught) {
      setResultGroupMessage(
        caught instanceof MeshFlowApiError
          ? caught.details.message
          : "Saved result group could not be added to the dashboard.",
      );
    } finally {
      setAddingResultGroupId(null);
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
          {hasReadyDataset ? (
            <details className="group mt-1.5 rounded-md border border-border bg-surface">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm font-medium text-ink marker:hidden">
                <span className="truncate">
                  {activeDataset
                    ? datasetLabel(
                        activeDataset,
                        readyDatasets.findIndex((dataset) => dataset.id === activeDataset.id),
                      )
                    : "Select ready dataset"}
                </span>
                <svg
                  width={16}
                  height={16}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden
                  className="text-ink-muted transition-transform group-open:rotate-180"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </summary>
              <div className="border-t border-border bg-surface-muted p-1.5">
                {readyDatasets.map((dataset, index) => {
                  const active = dataset.id === activeDatasetId;
                  return (
                    <div
                      key={dataset.id}
                      className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-md ${
                        active ? "bg-violet-50" : "bg-transparent"
                      }`}
                    >
                      <button
                        type="button"
                        disabled={dashboardProcessRunning}
                        onClick={() => setSelectedDatasetId(dataset.id)}
                        className={`min-w-0 cursor-pointer rounded-md px-2.5 py-2 text-left text-xs font-medium transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60 ${
                          active ? "text-violet-800" : "text-ink"
                        }`}
                      >
                        <span className="block truncate">{datasetLabel(dataset, index)}</span>
                      </button>
                      <button
                        type="button"
                        disabled={dashboardProcessRunning}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          void handleDeleteAttachedDataset(dataset, index);
                        }}
                        title={
                            deletingDatasetId === dataset.id
                              ? "Removing dataset..."
                              : dashboardProcessRunning
                                ? `Wait for the current process to finish: ${dashboardProcessLabel}.`
                              : "Remove dataset from active workspace. Quota usage is not restored."
                        }
                        className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={
                          deletingDatasetId === dataset.id
                            ? `Removing ${datasetLabel(dataset, index)} from active workspace`
                            : `Remove ${datasetLabel(dataset, index)} from active workspace`
                        }
                      >
                        {deletingDatasetId === dataset.id ? (
                          <InlineSpinner />
                        ) : (
                          <svg
                            width={17}
                            height={17}
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={1.9}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden
                          >
                            <path d="M3 6h18" />
                            <path d="M8 6V4h8v2" />
                            <path d="M19 6l-1 14H6L5 6" />
                            <path d="M10 11v5M14 11v5" />
                          </svg>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </details>
          ) : (
            <div className="mt-1.5 rounded-md border border-border bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              No ready dataset
            </div>
          )}
          {datasetDeleteMessage ? (
            <p className="mt-2 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
              {deletingDatasetId ? <InlineSpinner /> : null}
              {datasetDeleteMessage}
            </p>
          ) : null}

          <label className="mt-4 block text-xs font-semibold text-ink">Question</label>
          <textarea
            disabled={!hasReadyDataset || activeDatasetIsDeleting || dashboardProcessRunning}
            rows={3}
            value={questionText}
            onChange={(event) => setQuestionText(event.target.value)}
            className="mt-1.5 w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink disabled:cursor-not-allowed disabled:bg-surface-muted"
          />

          <div className="mt-4">
            <p className="text-xs font-semibold text-ink">Suggested questions</p>
          {questionState === "loading" ? (
              <p className="mt-1.5 inline-flex items-center gap-2 rounded-md bg-surface-muted px-3 py-2.5 text-xs text-ink-muted">
                <InlineSpinner />
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
                      disabled={activeDatasetIsDeleting || dashboardProcessRunning}
                      onClick={() => setQuestionText(question.question)}
                      className="rounded-md border border-violet-100 bg-violet-50/40 px-3 py-2 text-left text-xs text-ink-soft transition-colors hover:border-violet-300 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {question.question}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-1.5 rounded-md bg-surface-muted px-3 py-2.5 text-xs text-ink-muted">
                  {hasSchemaReviewDatasets
                    ? "No prepared questions are available for this ready dataset yet. You can still ask a direct question."
                    : "Suggestions appear after a dataset is transformed into Data Marts."}
                </p>
              )
            ) : null}
          </div>

          <button
            type="button"
            disabled={
              !sessionId ||
              !hasReadyDataset ||
              activeDatasetIsDeleting ||
              !questionText.trim() ||
              dashboardProcessRunning
            }
            onClick={handleGenerateAnalysis}
            title={
              activeDatasetIsDeleting
                ? "Wait until dataset removal finishes before generating analysis."
                : dashboardProcessRunning
                  ? `Wait for the current process to finish: ${dashboardProcessLabel}.`
                : hasReadyDataset
                ? "Generate a real analysis result from the attached ready dataset."
                : "Prepare a dataset before asking the AI Analytics Engineer."
            }
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analysisState === "planning" ? <InlineSpinner /> : null}
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

        <section className="min-w-0 space-y-4">
          {dashboardCards.length > 0 ? (
            <div className="grid gap-4">
              <div className="rounded-lg border border-violet-200 bg-violet-50/40 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="min-w-0 flex-1 text-sm text-violet-900">
                    Removing a visible card does not restore public demo quota.
                    {dashboardEditMode
                      ? " Edit mode is limited to visible-card removal in this phase."
                      : ""}
                  </p>
                  <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
                    <span className="rounded-full border border-violet-200 bg-white px-2.5 py-1 text-xs font-semibold text-violet-700">
                      Used {workspace?.dashboard.cards_used ?? 0} / {workspace?.dashboard.cards_limit ?? 8}
                    </span>
                    <button
                      type="button"
                      disabled={dashboardProcessRunning}
                      onClick={() => {
                        setResultGroupDrawerOpen(true);
                        void loadResultGroups();
                      }}
                      title={
                        dashboardProcessRunning
                          ? `Wait for the current process to finish: ${dashboardProcessLabel}.`
                          : "Choose a stored result group to add to the dashboard."
                      }
                      className="cursor-pointer rounded-md border border-violet-200 bg-white px-3 py-1.5 text-xs font-semibold text-violet-700 transition-colors hover:border-violet-300 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      Add to dashboard
                    </button>
                    <button
                      type="button"
                      disabled={dashboardProcessRunning}
                      onClick={() => setDashboardEditMode((current) => !current)}
                      title={
                        dashboardProcessRunning
                          ? `Wait for the current process to finish: ${dashboardProcessLabel}.`
                          : "Toggle visible-card edit mode."
                      }
                      className="cursor-pointer rounded-md border border-violet-200 bg-white px-3 py-1.5 text-xs font-semibold text-violet-700 transition-colors hover:border-violet-300 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      {dashboardEditMode ? "Done" : "Edit"}
                    </button>
                  </div>
                </div>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {dashboardCards.map((card) => {
                  const cardViewKey = dashboardCardViewKey(card);
                  return (
                    <PersistedDashboardCard
                      key={card.id}
                      card={card}
                      editMode={dashboardEditMode}
                      isRemoving={removingCardId === card.id}
                      isCompact={compactDashboardCardKeys.has(cardViewKey)}
                      isProcessRunning={dashboardProcessRunning}
                      processLabel={dashboardProcessLabel}
                      onToggleCompact={() => toggleDashboardCardCompact(cardViewKey)}
                      onRemove={() => void handleRemoveCard(card.id)}
                      onViewEvidence={() => {
                        if (card.analysis_run_id) {
                          setDetailAnalysisId(card.analysis_run_id);
                        }
                      }}
                    />
                  );
                })}
              </div>
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
                  ? "Saved dashboard cards from completed Snowflake analysis runs appear here. Nothing is shown until a real result is persisted."
                  : "Once a dataset is uploaded and transformed to Data Marts, generated chart cards appear here with a dataset badge and evidence."}
              </p>
              {!hasReadyDataset ? (
                <a
                  href="/demo/upload"
                  className="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4.5 py-2.5 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  Upload Dataset
                </a>
              ) : (
                <button
                  type="button"
                  disabled={dashboardProcessRunning}
                  onClick={() => {
                    setResultGroupDrawerOpen(true);
                    void loadResultGroups();
                  }}
                  title={
                    dashboardProcessRunning
                      ? `Wait for the current process to finish: ${dashboardProcessLabel}.`
                      : "Choose a stored result group to add to the dashboard."
                  }
                  className="mt-5 inline-flex cursor-pointer items-center justify-center gap-2 rounded-md bg-primary px-4.5 py-2.5 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-55"
                >
                  Add to dashboard
                </button>
              )}
            </div>
          )}
        </section>
      </div>
      <AnalysisDetailDrawer
        open={detailAnalysisId !== null}
        sessionId={sessionId}
        analysisRunId={detailAnalysisId}
        onClose={() => setDetailAnalysisId(null)}
      />
      <ResultGroupChooserDrawer
        open={resultGroupDrawerOpen}
        resultGroups={availableResultGroups}
        resultGroupState={resultGroupState}
        resultGroupMessage={resultGroupMessage}
        chartPreviews={resultGroupChartPreviews}
        addingResultGroupId={addingResultGroupId}
        isProcessRunning={dashboardProcessRunning}
        processLabel={dashboardProcessLabel}
        onAdd={(analysisRunId) => void handleAddResultGroupToDashboard(analysisRunId)}
        onClose={() => setResultGroupDrawerOpen(false)}
      />
    </div>
  );
}
