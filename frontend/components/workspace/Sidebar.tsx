"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { WordmarkOnDark } from "@/components/brand/Logo";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";

type NavItem = { href: string; label: string; icon: ReactNode };

const iconProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const NAV: NavItem[] = [
  {
    href: "/demo/upload",
    label: "Upload Dataset",
    icon: (
      <svg {...iconProps}>
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
      </svg>
    ),
  },
  {
    href: "/demo/data-flow",
    label: "Data Flow",
    icon: (
      <svg {...iconProps}>
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="12" r="2.5" />
        <circle cx="6" cy="18" r="2.5" />
        <path d="M8.5 6H14a2 2 0 0 1 2 2v1.5M15.5 12H10a2 2 0 0 0-2 2v1.5" />
      </svg>
    ),
  },
  {
    href: "/demo/dashboard",
    label: "Dashboard",
    icon: (
      <svg {...iconProps}>
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
    icon: (
      <svg {...iconProps}>
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 4v4h4M12 8v4l3 2" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col border-b border-shell-border bg-shell-deep text-slate-300 md:sticky md:top-0 md:h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r">
      <div className="px-4 pb-3 pt-4">
        <Link href="/" className="inline-flex" aria-label="MeshFlow home">
          <WordmarkOnDark />
        </Link>
        <p className="mt-3 hidden text-xs font-medium uppercase tracking-wide text-slate-500 md:block">
          Workspace Session
        </p>
      </div>

      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ease-[var(--ease-out-quart)]",
                active
                  ? "bg-shell text-white"
                  : "text-slate-300 hover:bg-shell/70 hover:text-white",
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "h-1.5 w-1.5 shrink-0 rounded-full transition-colors",
                  active
                    ? "bg-primary-soft shadow-[0_0_8px_rgba(99,102,241,0.7)]"
                    : "bg-transparent",
                )}
              />
              <span className="text-slate-400 group-hover:text-slate-200">
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Session status + Reset Demo — placeholders until Phase 3 */}
      <div className="mt-auto hidden border-t border-shell-border px-4 py-4 md:block">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Session</span>
          <StatusBadge status="waiting" label="No session" />
        </div>
        <button
          type="button"
          disabled
          title="Available once a session is active (Phase 3)"
          className="mt-3 w-full rounded-md border border-shell-border px-3 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-shell/70 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset Demo
        </button>
      </div>
    </aside>
  );
}
