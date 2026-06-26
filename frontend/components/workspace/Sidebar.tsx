"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WordmarkOnDark } from "@/components/brand/Logo";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useWorkspaceSession } from "@/components/workspace/WorkspaceSessionProvider";
import { cn } from "@/lib/cn";
import { DEMO_LIMITS } from "@/lib/demoLimits";

type NavItem = {
  href: string;
  label: string;
  chipBg: string;
  chipColor: string;
  icon: ReactNode;
};

const ip = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

function formatMegabytes(value: number | null | undefined): string {
  const numeric = Number(value ?? 0);
  if (numeric === 0) {
    return "0 MB";
  }
  return `${numeric < 1 ? numeric.toFixed(2) : numeric.toFixed(1)} MB`;
}

const NAV: NavItem[] = [
  {
    href: "/demo/upload",
    label: "Upload Dataset",
    chipBg: "bg-amber-500/20",
    chipColor: "text-amber-400",
    icon: (
      <svg {...ip}>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
      </svg>
    ),
  },
  {
    href: "/demo/data-flow",
    label: "Data Flow",
    chipBg: "bg-blue-500/20",
    chipColor: "text-blue-400",
    icon: (
      <svg {...ip}>
        <circle cx="6" cy="6" r="2" />
        <circle cx="18" cy="12" r="2" />
        <circle cx="6" cy="18" r="2" />
        <path d="M8 6h5a2 2 0 0 1 2 2v1.5M16 12h-5a2 2 0 0 0-2 2v1.5" />
      </svg>
    ),
  },
  {
    href: "/demo/dashboard",
    label: "Dashboard",
    chipBg: "bg-violet-500/20",
    chipColor: "text-violet-400",
    icon: (
      <svg {...ip}>
        <rect x="3" y="3" width="7" height="9" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="16" width="7" height="5" rx="1.5" />
      </svg>
    ),
  },
  {
    href: "/demo/history",
    label: "History",
    chipBg: "bg-emerald-500/20",
    chipColor: "text-emerald-400",
    icon: (
      <svg {...ip}>
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 4v4h4M12 8v4l3 2" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const {
    backendStatus,
    limits,
    resetMessage,
    resetSession,
    sessionStatus,
    usage,
    workspace,
    isResetting,
  } = useWorkspaceSession();

  const sessionBadge =
    sessionStatus === "active"
      ? {
          status: "ready" as const,
          label: workspace?.session.status === "reset" ? "Reset" : "Active",
        }
      : sessionStatus === "checking"
        ? { status: "running" as const, label: "Checking" }
        : sessionStatus === "expired"
          ? { status: "failed" as const, label: "Expired" }
          : { status: "waiting" as const, label: "No session" };

  const usageItems = [
    {
      label: "Session",
      value: `${limits?.retention_days ?? 3} days`,
    },
    {
      label: "Storage",
      value: `${formatMegabytes(usage?.total_upload_mb_used)} / ${
        limits?.max_total_upload_size_mb ?? DEMO_LIMITS.totalUploadSizeMb
      } MB`,
    },
    {
      label: "Demo data",
      value: `${usage?.demo_dataset_used ?? 0} / ${
        limits?.max_demo_datasets_per_session ?? DEMO_LIMITS.demoDatasetPerSession
      }`,
    },
    {
      label: "Analyses",
      value: `${usage?.successful_analysis_runs_used ?? 0} / ${
        limits?.max_successful_analysis_runs_per_session ??
        DEMO_LIMITS.successfulAnalysisRunsPerSession
      }`,
    },
    {
      label: "Cards",
      value: `${usage?.dashboard_cards_used ?? 0} / ${
        limits?.max_dashboard_cards_per_session ??
        DEMO_LIMITS.dashboardCardsPerSession
      }`,
    },
  ];

  const canReset = sessionStatus === "active" && backendStatus === "available";

  async function handleReset() {
    if (!canReset) {
      return;
    }

    const confirmed = window.confirm(
      "Reset workspace metadata? Public quota usage is not restored unless backend development reset usage is enabled.",
    );
    if (!confirmed) {
      return;
    }

    await resetSession();
  }

  return (
    <aside className="flex flex-col border-b border-shell-border bg-shell-deep text-slate-300 md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:border-b-0 md:border-r">
      {/* Brand */}
      <div className="px-4 pb-3 pt-4">
        <Link href="/" className="inline-flex" aria-label="MeshFlow home">
          <WordmarkOnDark
            size={60}
            textClassName="text-[1.75rem] leading-none"
          />
        </Link>
        <p className="mt-4 hidden text-sm font-semibold text-slate-300 md:block">
          Workspace
        </p>
      </div>

      {/* Nav */}
      <nav
        aria-label="Workspace pages"
        className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible"
      >
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-2.5 whitespace-nowrap rounded-lg px-2.5 py-2 text-sm font-medium transition-colors duration-150 ease-out-quart",
                active
                  ? "bg-shell text-white"
                  : "text-slate-400 hover:bg-shell/70 hover:text-white",
              )}
            >
              {/* Colored icon chip — color only when active; dims when inactive */}
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
                  active
                    ? cn(item.chipBg, item.chipColor)
                    : "text-slate-500 group-hover:text-slate-300",
                )}
              >
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Session footer */}
      <div className="mt-auto hidden border-t border-shell-border px-4 py-4 md:block">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Session</span>
          <StatusBadge status={sessionBadge.status} label={sessionBadge.label} />
        </div>
        <div className="mt-3 rounded-lg border border-shell-border bg-shell/55 p-3">
          <p className="text-xs font-semibold text-slate-300">Demo limits</p>
          <div className="mt-2 grid gap-1.5">
            {usageItems.map((limit) => (
              <span
                key={limit.label}
                className="grid grid-cols-[1fr_auto] items-center gap-2 rounded-md bg-slate-800/80 px-2.5 py-1.5 text-[0.6875rem] font-medium text-slate-300 ring-1 ring-shell-border"
              >
                {limit.label}
                <span className="rounded-full bg-primary/25 px-2 py-0.5 text-center font-mono text-[0.625rem] font-semibold text-indigo-200">
                  {limit.value}
                </span>
              </span>
            ))}
          </div>
          <p className="mt-2 text-[0.6875rem] leading-relaxed text-slate-500">
            Public quota counts successful use and is not restored by
            delete/reset.
          </p>
          {resetMessage ? (
            <p className="mt-2 text-[0.6875rem] leading-relaxed text-indigo-200">
              {resetMessage}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          disabled={!canReset || isResetting}
          onClick={() => void handleReset()}
          title={
            canReset
              ? "Reset workspace metadata. Public quota usage is not restored by default."
              : "Available once a backend-backed session is active."
          }
          className="mt-3 w-full rounded-md border border-shell-border px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-shell/70 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isResetting ? "Resetting..." : "Reset Demo"}
        </button>
      </div>
    </aside>
  );
}
