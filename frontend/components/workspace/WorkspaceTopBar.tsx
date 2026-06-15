"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";

const ip = {
  width: 15,
  height: 15,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

type PageMeta = {
  title: string;
  shortDesc: string;
  chipBg: string;
  chipText: string;
  icon: ReactNode;
};

const PAGE_META: Record<string, PageMeta> = {
  "/demo/upload": {
    title: "Upload Dataset",
    shortDesc: "Add a dataset to start the workflow",
    chipBg: "bg-amber-500/12",
    chipText: "text-amber-600",
    icon: (
      <svg {...ip}>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
      </svg>
    ),
  },
  "/demo/data-flow": {
    title: "Data Flow",
    shortDesc: "Prepare and transform your dataset",
    chipBg: "bg-blue-500/12",
    chipText: "text-blue-600",
    icon: (
      <svg {...ip}>
        <circle cx="6" cy="6" r="2" />
        <circle cx="18" cy="12" r="2" />
        <circle cx="6" cy="18" r="2" />
        <path d="M8 6h5a2 2 0 0 1 2 2v1.5M16 12h-5a2 2 0 0 0-2 2v1.5" />
      </svg>
    ),
  },
  "/demo/dashboard": {
    title: "Dashboard",
    shortDesc: "Charts and insights from your analyses",
    chipBg: "bg-violet-500/12",
    chipText: "text-violet-600",
    icon: (
      <svg {...ip}>
        <path d="M12 3l1.9 5.8H20l-5 3.6 1.9 5.8L12 15l-4.9 3.2 1.9-5.8-5-3.6h6.1z" />
      </svg>
    ),
  },
  "/demo/history": {
    title: "History",
    shortDesc: "Past analyses with full evidence",
    chipBg: "bg-purple-500/12",
    chipText: "text-purple-600",
    icon: (
      <svg {...ip}>
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 4v4h4M12 8v4l3 2" />
      </svg>
    ),
  },
};

const FALLBACK: PageMeta = {
  title: "Workspace",
  shortDesc: "MeshFlow demo",
  chipBg: "bg-primary/10",
  chipText: "text-primary",
  icon: null,
};

export function WorkspaceTopBar() {
  const pathname = usePathname();
  const meta = PAGE_META[pathname] ?? FALLBACK;

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-surface/95 px-6 py-2.5 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        {meta.icon ? (
          <span
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
              meta.chipBg,
              meta.chipText,
            )}
          >
            {meta.icon}
          </span>
        ) : null}
        <div>
          <span className="text-sm font-semibold text-ink">{meta.title}</span>
          <span className="ml-2 hidden text-xs text-ink-muted sm:inline">
            {meta.shortDesc}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge status="waiting" label="No session" />
      </div>
    </header>
  );
}
