import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  LANDING_DEMO_LIMIT_ITEMS,
  LANDING_DEMO_LIMIT_NOTE,
} from "@/lib/demoLimits";

const iconProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

const CAPABILITIES = [
  {
    title: "Warehouse-first preparation",
    body: "Raw files move through AWS S3, Snowflake, and dbt instead of local shortcut analysis.",
    tint: "bg-amber-400/12",
    border: "border-amber-300/25",
    iconColor: "text-amber-300",
    icon: (
      <svg {...iconProps}>
        <path d="M4 19h16" />
        <path d="M6 17V7l6-3 6 3v10" />
        <path d="M9 10h6M9 13h6" />
      </svg>
    ),
  },
  {
    title: "Dimensional modeling",
    body: "MeshFlow transforms raw data into a Dimensional Model and Data Marts for trustworthy analysis.",
    tint: "bg-blue-400/12",
    border: "border-blue-300/25",
    iconColor: "text-blue-300",
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="4" width="7" height="7" rx="1.5" />
        <rect x="14" y="4" width="7" height="7" rx="1.5" />
        <rect x="8.5" y="15" width="7" height="5" rx="1.5" />
        <path d="M10 7.5h4M12 11v4" />
      </svg>
    ),
  },
  {
    title: "AI Analytics Engineer",
    body: "AI plans analysis from prepared marts, validates structure, and explains results from real query output.",
    tint: "bg-violet-400/12",
    border: "border-violet-300/30",
    iconColor: "text-violet-300",
    icon: (
      <svg {...iconProps}>
        <path d="M12 3v18M4 12h16" />
        <path d="M7 7l10 10M17 7 7 17" />
        <circle cx="12" cy="12" r="8" />
      </svg>
    ),
  },
  {
    title: "Evidence-backed dashboard",
    body: "Charts, insights, SQL, ChartSpec, lineage, and provider evidence remain traceable.",
    tint: "bg-emerald-400/12",
    border: "border-emerald-300/25",
    iconColor: "text-emerald-300",
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="3" width="7" height="8" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="15" width="7" height="6" rx="1.5" />
      </svg>
    ),
  },
];

const STEPS = [
  { n: "1", title: "Upload raw data", body: "Bring a CSV or start with the curated retail input." },
  { n: "2", title: "Review schema", body: "Inspect columns before warehouse preparation starts." },
  { n: "3", title: "Transform with warehouse", body: "Staging, Intermediate, Dimensional Model, and Data Marts stay visible." },
  { n: "4", title: "Ask from prepared marts", body: "The AI Analytics Engineer works from real query output and evidence." },
];

const ARCH = [
  {
    label: "Dataset",
    desc: "Raw CSV / curated retail input",
    borderClass: "border-amber-300",
    bgClass: "bg-amber-50",
    textClass: "text-amber-700",
    icon: (
      <svg {...iconProps}>
        <ellipse cx="12" cy="6" rx="8" ry="3" />
        <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" />
        <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" />
      </svg>
    ),
  },
  {
    label: "AWS S3",
    desc: "Raw file storage",
    borderClass: "border-orange-300",
    bgClass: "bg-orange-50",
    textClass: "text-orange-700",
    icon: (
      <svg {...iconProps}>
        <path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        <circle cx="12" cy="12" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    label: "Snowflake",
    desc: "Warehouse Raw and query execution",
    borderClass: "border-blue-300",
    bgClass: "bg-blue-50",
    textClass: "text-blue-700",
    icon: (
      <svg {...iconProps}>
        <line x1="12" y1="2" x2="12" y2="22" />
        <path d="M17 5l-5 5-5-5M7 19l5-5 5 5" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M19 7l-5 5 5 5M5 7l5 5-5 5" />
      </svg>
    ),
  },
  {
    label: "dbt",
    desc: "Staging, Intermediate, Dimensional Model, Data Marts",
    borderClass: "border-indigo-300",
    bgClass: "bg-indigo-50",
    textClass: "text-indigo-700",
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        <path d="M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" />
      </svg>
    ),
  },
  {
    label: "AI Analytics Engineer",
    desc: "Plan, validate, explain",
    borderClass: "border-primary/40",
    bgClass: "bg-primary-tint",
    textClass: "text-primary",
    icon: (
      <svg {...iconProps}>
        <path d="M12 3v18M4 12h16" />
        <path d="M7 7l10 10M17 7 7 17" />
        <circle cx="12" cy="12" r="8" />
      </svg>
    ),
  },
  {
    label: "Dashboard",
    desc: "Charts, insights, evidence",
    borderClass: "border-violet-300",
    bgClass: "bg-violet-50",
    textClass: "text-violet-700",
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="3" width="7" height="8" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="15" width="7" height="6" rx="1.5" />
      </svg>
    ),
  },
];

const TECH = ["Next.js", "TypeScript", "FastAPI", "Snowflake", "dbt", "AWS S3", "Recharts"];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-shell-deep lg:min-h-dvh">
      <header className="flex h-12 items-center justify-between gap-4 border-b border-shell-border bg-linear-to-r from-shell-deep via-[#1e1b4b] to-shell-deep px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Logo variant="icon" size={30} priority />
          <span className="text-sm font-semibold">
            <span className="text-white">Mesh</span>
            <span className="text-white">Flow</span>
          </span>
          <span className="hidden min-w-0 border-l border-shell-border pl-3 text-sm text-slate-300 md:block">
            Warehouse-first AI analytics engineering demo
          </span>
        </div>
        <div className="flex items-center justify-end gap-2">
          <span className="hidden items-center gap-1.5 rounded-full border border-shell-border bg-shell/55 px-2.5 py-1 sm:inline-flex">
            <span className="text-xs font-medium text-slate-300">Demo</span>
            <StatusBadge status="waiting" label="No session" className="bg-slate-700/80 text-slate-200" />
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-shell-border bg-shell/55 px-2.5 py-1">
            <span className="text-xs font-medium text-slate-300">Backend</span>
            <StatusBadge status="review" label="Not connected" className="bg-amber-500/15 text-amber-200" />
          </span>
        </div>
      </header>

      <div className="relative lg:min-h-[calc(100dvh-96px)]">
        <div className="grid lg:min-h-[calc(100dvh-96px)] lg:grid-cols-[60%_40%]">
          <section className="flex items-center bg-shell-deep px-6 py-7 sm:px-10 lg:px-12 lg:py-5 lg:pb-56 xl:pb-52">
            <div className="mx-auto w-full max-w-3xl">
              <div className="flex items-center justify-center gap-4 sm:gap-5">
                <Logo
                  variant="icon"
                  size={148}
                  priority
                  className="h-28 w-28 shrink-0 rounded-lg sm:h-36 sm:w-36"
                />
                <h1 className="text-5xl font-bold leading-none sm:text-6xl xl:text-7xl">
                  <span className="text-white">Mesh</span>
                  <span className="text-gradient-brand">Flow</span>
                </h1>
              </div>
              <p className="mx-auto mt-4 max-w-xl text-center text-sm leading-relaxed text-slate-300">
                A compact demo workspace for turning raw datasets into
                warehouse-backed, explainable AI analysis.
              </p>

              <div className="mt-4">
                <h2 className="text-xl font-semibold text-white">
                  Key Capabilities
                </h2>
                <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                  {CAPABILITIES.map((cap) => (
                    <article
                      key={cap.title}
                      className={`rounded-lg border ${cap.border} bg-white/[0.045] p-2 text-left`}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${cap.tint} ${cap.iconColor}`}
                        >
                          {cap.icon}
                        </span>
                        <h3 className="text-sm font-semibold leading-tight text-white">
                          {cap.title}
                        </h3>
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                        {cap.body}
                      </p>
                    </article>
                  ))}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2">
                <Button href="/demo/upload">
                  <svg {...iconProps} width={17} height={17}>
                    <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3h4.8a2 2 0 0 1 1.4.6L19.4 9a2 2 0 0 1 .6 1.4v6.1a2.5 2.5 0 0 1-2.5 2.5h-10A2.5 2.5 0 0 1 5 16.5v-11z" />
                    <path d="M13 3v5a2 2 0 0 0 2 2h5" />
                    <path d="M9 14h6M12 11v6" />
                  </svg>
                  Launch Demo
                </Button>
                <p className="whitespace-nowrap text-sm text-slate-400">
                  No account needed · anonymous 3-day demo session
                </p>
              </div>
            </div>
          </section>

          <section className="flex items-center border-l border-indigo-200 bg-linear-to-br from-indigo-200 via-primary-tint to-violet-200 px-6 py-7 sm:px-10 lg:px-12 lg:py-5 lg:pb-56 xl:pb-52">
            <div className="mx-auto grid w-full max-w-3xl gap-4">
              <div className="rounded-lg border border-blue-400/70 bg-blue-50/40 p-4">
                <div className="flex items-center gap-2 text-ink">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-100 text-blue-700">
                    <svg {...iconProps}>
                      <path d="M4 5h16M4 12h16M4 19h16" />
                      <path d="M8 5v14" />
                    </svg>
                  </span>
                  <h2 className="text-lg font-semibold">
                    How it works
                  </h2>
                </div>
                <ol className="mt-3 space-y-0">
                  {STEPS.map((step, index) => (
                    <li key={step.n} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white font-mono text-[0.6875rem] font-semibold text-primary ring-1 ring-blue-200">
                          {step.n}
                        </span>
                        {index < STEPS.length - 1 ? (
                          <span className="mt-1 w-px flex-1 bg-blue-200" style={{ minHeight: "24px" }} />
                        ) : null}
                      </div>
                      <div className={index < STEPS.length - 1 ? "pb-3.5" : ""}>
                        <p className="text-sm font-semibold text-ink">{step.title}</p>
                        <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">
                          {step.body}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="rounded-lg border border-indigo-400/70 bg-primary-tint/80 p-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white text-primary ring-1 ring-indigo-200">
                    <svg {...iconProps}>
                      <path d="M12 8v5" />
                      <path d="M12 16h.01" />
                      <path d="M10.3 3.5 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.5a2 2 0 0 0-3.4 0z" />
                    </svg>
                  </span>
                  <h2 className="text-lg font-semibold text-ink">
                    Demo Limits
                  </h2>
                </div>
                <ul className="mt-3 grid gap-2 xl:grid-cols-2">
                  {LANDING_DEMO_LIMIT_ITEMS.map((limit) => (
                    <li
                      key={`${limit.count}-${limit.label}`}
                      className="flex items-center gap-2 whitespace-nowrap rounded-md bg-white/75 px-2.5 py-1.5 text-[0.72rem] leading-none text-indigo-950 ring-1 ring-indigo-200/80"
                    >
                      <span className="w-[3.25rem] rounded-full bg-indigo-100 px-2 py-1 text-center font-mono text-[0.6875rem] font-semibold text-primary">
                        {limit.count}
                      </span>
                      <span>{limit.label}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs leading-relaxed text-indigo-950/75">
                  {LANDING_DEMO_LIMIT_NOTE}
                </p>
              </div>
            </div>
          </section>
        </div>

        <section className="pointer-events-none relative z-10 mx-auto w-full px-6 pb-4 lg:absolute lg:bottom-0 lg:left-1/2 lg:-translate-x-1/2">
          <div className="pointer-events-auto mx-auto w-full max-w-[92rem] rounded-lg border border-slate-400 bg-slate-100 p-4">
            <div className="flex items-center justify-center gap-2.5 text-ink">
              <svg {...iconProps} width={34} height={34} className="text-primary">
                <path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z" />
                <path d="m7 16.5-4.74-2.85" />
                <path d="m7 16.5 5-3" />
                <path d="M7 16.5v5.17" />
                <path d="M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z" />
                <path d="m17 16.5-5-3" />
                <path d="m17 16.5 4.74-2.85" />
                <path d="M17 16.5v5.17" />
                <path d="M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z" />
                <path d="M12 8 7.26 5.15" />
                <path d="m12 8 4.74-2.85" />
                <path d="M12 13.5V8" />
              </svg>
              <h2 className="text-lg font-semibold text-ink">
                Architecture Overview
              </h2>
            </div>
            <ol className="mt-3 grid auto-rows-fr items-stretch gap-2 md:grid-cols-3 xl:grid-cols-6 xl:gap-5">
              {ARCH.map((node, index) => (
                <li
                  key={node.label}
                  className="relative flex h-full min-w-0 flex-col items-center"
                >
                  <article
                    className={`mx-auto flex h-full w-full min-w-0 max-w-[13.5rem] flex-col rounded-md border ${node.borderClass} ${node.bgClass} px-3 py-2.5 text-center`}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <span
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/75 ${node.textClass} ring-1 ring-white/80`}
                      >
                        {node.icon}
                      </span>
                      <p className={`whitespace-nowrap text-sm font-semibold leading-tight ${node.textClass}`}>
                        {node.label}
                      </p>
                    </div>
                    <p className="mt-2 text-[0.72rem] leading-snug text-ink-soft">
                      {node.desc}
                    </p>
                  </article>
                  {index < ARCH.length - 1 ? (
                    <span className="mt-2 flex h-5 items-center justify-center text-primary xl:absolute xl:-right-5 xl:top-1/2 xl:mt-0 xl:-translate-y-1/2" aria-hidden>
                      <svg
                        width={18}
                        height={18}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={1.8}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="rotate-90 xl:rotate-0"
                      >
                        <path d="M5 12h14" />
                        <path d="M13 6l6 6-6 6" />
                      </svg>
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          </div>
        </section>
      </div>

      <footer className="border-t border-shell-border bg-linear-to-r from-shell-deep via-[#1e1b4b] to-shell-deep px-6 py-2.5 lg:h-12">
        <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-sm text-slate-300">
            Built with real warehouse and analytics-engineering tools.
          </span>
          <div className="flex flex-wrap items-center gap-2">
            {TECH.map((tech) => (
              <span
                key={tech}
                className="rounded-full border border-shell-border px-2.5 py-1 font-mono text-[0.6875rem] text-slate-300"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}
