"use client";

import { ChartRenderer } from "@/components/charts/ChartRenderer";
import type {
  AnalysisInsightSummary,
  AnalysisRunChartSummary,
  AnalysisRunDetail,
} from "@/lib/meshflowApi";

function readableType(type: string): string {
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function ChartCard({
  chart,
  analysisRun,
  datasetName,
  insights = [],
}: {
  chart: AnalysisRunChartSummary;
  analysisRun: Pick<AnalysisRunDetail, "status">;
  datasetName: string;
  insights?: AnalysisInsightSummary[];
}) {
  const chartInsight = insights.find(
    (insight) =>
      insight.status === "completed" &&
      insight.insight_level === "chart" &&
      insight.analysis_run_chart_id === chart.id,
  );

  return (
    <article className="rounded-lg border border-violet-200 bg-surface p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-ink">{chart.title}</h3>
          {chart.description ? (
            <p className="mt-1 text-sm text-ink-muted">{chart.description}</p>
          ) : null}
        </div>
        <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
          {readableType(chart.chart_type)}
        </span>
      </div>

      <ChartRenderer chart={chart} />

      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-700">
          Dataset: {datasetName}
        </span>
        {chart.source_model ? (
          <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 font-medium text-indigo-700">
            {chart.source_model}
          </span>
        ) : null}
        {chart.metric_summary ? (
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
            Metric: {chart.metric_summary}
          </span>
        ) : null}
        {chart.dimension_summary ? (
          <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 font-medium text-blue-700">
            Dimension: {chart.dimension_summary}
          </span>
        ) : null}
        <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-700">
          Status: {analysisRun.status}
        </span>
      </div>

      {chartInsight ? (
        <div className="mt-4 rounded-md border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-900">
          <p className="font-semibold">Chart insight</p>
          {chartInsight.summary ? <p className="mt-1">{chartInsight.summary}</p> : null}
          {chartInsight.key_findings.length > 0 ? (
            <ul className="mt-2 space-y-1 text-indigo-800">
              {chartInsight.key_findings.map((finding, index) => (
                <li key={`${chartInsight.id}-${index}`}>{finding}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
