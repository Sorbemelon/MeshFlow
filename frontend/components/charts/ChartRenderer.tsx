"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalysisRunChartSummary, ChartFieldSpec } from "@/lib/meshflowApi";

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value.replace(/,/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatValue(value: unknown, format?: string | null): string {
  const numeric = asNumber(value);
  if (numeric === null) {
    return String(value ?? "—");
  }
  if (format === "currency") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(numeric);
  }
  if (format === "percent") {
    return new Intl.NumberFormat("en-US", {
      style: "percent",
      maximumFractionDigits: 1,
    }).format(numeric);
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(numeric);
}

function normalizeChartData(
  rows: Record<string, unknown>[],
  numericField?: string,
): Record<string, unknown>[] {
  if (!numericField) {
    return rows;
  }
  return rows.map((row) => {
    const numericValue = asNumber(row[numericField]);
    return {
      ...row,
      [numericField]: numericValue ?? row[numericField],
    };
  });
}

function AxisTooltip({
  active,
  payload,
  label,
  yField,
}: {
  active?: boolean;
  payload?: Array<{ value?: unknown }>;
  label?: string;
  yField: ChartFieldSpec;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-[0_10px_24px_rgba(15,23,42,0.12)]">
      <p className="font-semibold text-ink">{label}</p>
      <p className="mt-1 text-ink-muted">
        {yField.label}: {formatValue(payload[0]?.value, yField.format)}
      </p>
    </div>
  );
}

export function ChartRenderer({ chart }: { chart: AnalysisRunChartSummary }) {
  const spec = chart.chart_spec;

  if (spec.type === "kpi" && spec.value) {
    const value = chart.data[0]?.[spec.value.field];
    return (
      <div className="flex min-h-56 flex-col justify-center rounded-md border border-violet-100 bg-violet-50/40 px-5 py-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
          {spec.value.label}
        </p>
        <p className="mt-3 text-4xl font-semibold text-ink">
          {formatValue(value, spec.value.format)}
        </p>
      </div>
    );
  }

  if (
    (spec.type === "line" || spec.type === "bar" || spec.type === "horizontal_bar") &&
    spec.x &&
    spec.y
  ) {
    const data = normalizeChartData(chart.data, spec.y.field);
    const commonAxisProps = {
      tickLine: false,
      axisLine: false,
      tick: { fill: "#64748b", fontSize: 12 },
    };

    if (spec.type === "line") {
      return (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey={spec.x.field} {...commonAxisProps} />
              <YAxis {...commonAxisProps} />
              <Tooltip content={<AxisTooltip yField={spec.y} />} />
              <Line
                type="monotone"
                dataKey={spec.y.field}
                stroke="#4f46e5"
                strokeWidth={2.5}
                dot={{ r: 3, strokeWidth: 2 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    if (spec.type === "horizontal_bar") {
      return (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 8, right: 16, bottom: 8, left: 24 }}
            >
              <CartesianGrid stroke="#e2e8f0" horizontal={false} />
              <XAxis type="number" {...commonAxisProps} />
              <YAxis
                dataKey={spec.x.field}
                type="category"
                width={110}
                {...commonAxisProps}
              />
              <Tooltip content={<AxisTooltip yField={spec.y} />} />
              <Bar dataKey={spec.y.field} fill="#6366f1" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    return (
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 4 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey={spec.x.field} {...commonAxisProps} />
            <YAxis {...commonAxisProps} />
            <Tooltip content={<AxisTooltip yField={spec.y} />} />
            <Bar dataKey={spec.y.field} fill="#6366f1" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (spec.type === "table" && spec.columns?.length) {
    return (
      <div className="overflow-hidden rounded-md border border-border">
        <div className="grid bg-surface-muted text-xs font-semibold text-ink-muted">
          <div
            className="grid"
            style={{ gridTemplateColumns: `repeat(${spec.columns.length}, minmax(0, 1fr))` }}
          >
            {spec.columns.map((column) => (
              <div key={column.field} className="border-r border-border px-3 py-2 last:border-r-0">
                {column.label}
              </div>
            ))}
          </div>
        </div>
        <div className="divide-y divide-border text-sm text-ink-soft">
          {chart.data.slice(0, 10).map((row, rowIndex) => (
            <div
              key={rowIndex}
              className="grid"
              style={{ gridTemplateColumns: `repeat(${spec.columns?.length ?? 1}, minmax(0, 1fr))` }}
            >
              {spec.columns?.map((column) => (
                <div key={column.field} className="truncate border-r border-border px-3 py-2 last:border-r-0">
                  {formatValue(row[column.field], column.format)}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      This ChartSpec shape is not supported by the current renderer.
    </div>
  );
}
