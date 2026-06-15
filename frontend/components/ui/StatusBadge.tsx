import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Status vocabulary maps 1:1 to DESIGN.md / FRONTEND_UX_SCOPE status colors.
 * The Status-Never-Alone Rule: color always ships with an icon AND a label.
 */
export type Status =
  | "ready" // completed / ready — emerald
  | "running" // running / checking — blue
  | "review" // needs review / setup required — amber
  | "failed" // failed — red
  | "ai" // AI / provider / current / selected — indigo
  | "waiting"; // waiting / deleted / neutral — slate

const ICON_PROPS = {
  width: 13,
  height: 13,
  viewBox: "0 0 20 20",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.25,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const ICONS: Record<Status, ReactNode> = {
  ready: (
    <svg {...ICON_PROPS}>
      <path d="M4 10.5l3.5 3.5L16 6" />
    </svg>
  ),
  running: (
    <svg {...ICON_PROPS}>
      <path d="M16 5.5A7 7 0 1 0 17 10" />
      <path d="M16 3v3h-3" />
    </svg>
  ),
  review: (
    <svg {...ICON_PROPS}>
      <path d="M10 3.5 17 16H3z" />
      <path d="M10 8.5v3" />
      <path d="M10 13.7h.01" />
    </svg>
  ),
  failed: (
    <svg {...ICON_PROPS}>
      <circle cx="10" cy="10" r="7" />
      <path d="M12.5 7.5l-5 5M7.5 7.5l5 5" />
    </svg>
  ),
  ai: (
    <svg {...ICON_PROPS}>
      <path d="M10 3v14M3 10h14M6 6l8 8M14 6l-8 8" />
    </svg>
  ),
  waiting: (
    <svg {...ICON_PROPS}>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6.5V10l2.5 1.5" />
    </svg>
  ),
};

const LABELS: Record<Status, string> = {
  ready: "Ready",
  running: "Running",
  review: "Needs review",
  failed: "Failed",
  ai: "AI",
  waiting: "Waiting",
};

const STYLES: Record<Status, string> = {
  ready: "text-status-success bg-status-success/12",
  running: "text-status-running bg-status-running/12",
  review: "text-status-warning bg-status-warning/12",
  failed: "text-status-danger bg-status-danger/12",
  ai: "text-primary bg-primary-tint",
  waiting: "text-status-neutral bg-status-neutral/12",
};

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: Status;
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        STYLES[status],
        className,
      )}
    >
      {ICONS[status]}
      {label ?? LABELS[status]}
    </span>
  );
}
