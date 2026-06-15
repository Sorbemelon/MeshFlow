"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WordmarkOnDark } from "@/components/brand/Logo";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";

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
    chipBg: "bg-purple-500/20",
    chipColor: "text-purple-400",
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

  return (
    <aside className="flex flex-col border-b border-shell-border bg-shell-deep text-slate-300 md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:border-b-0 md:border-r">
      {/* Brand */}
      <div className="px-4 pb-3 pt-4">
        <Link href="/" className="inline-flex" aria-label="MeshFlow home">
          <WordmarkOnDark />
        </Link>
        <p className="mt-3 hidden text-[10px] font-semibold uppercase tracking-widest text-slate-500 md:block">
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
          <StatusBadge status="waiting" label="No session" />
        </div>
        <button
          type="button"
          disabled
          title="Available once a session is active (Phase 3)"
          className="mt-3 w-full rounded-md border border-shell-border px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-shell/70 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset Demo
        </button>
      </div>
    </aside>
  );
}
