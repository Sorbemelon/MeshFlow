import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

/**
 * Honest empty / setup-required state. First-class screen, never a fake-success
 * stand-in. Optional CTA links to a real route.
 */
export function EmptyState({
  icon,
  title,
  description,
  ctaLabel,
  ctaHref,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  ctaLabel?: string;
  ctaHref?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-surface-muted text-ink-muted">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {description ? (
        <p className="prose-measure mt-1.5 text-sm text-ink-muted">{description}</p>
      ) : null}
      {ctaLabel && ctaHref ? (
        <Button href={ctaHref} className="mt-5">
          {ctaLabel}
        </Button>
      ) : null}
    </div>
  );
}
