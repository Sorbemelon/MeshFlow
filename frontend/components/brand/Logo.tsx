import Image from "next/image";
import { cn } from "@/lib/cn";

const ICON_SRC = "/brand/meshflow_logo_rounded.png";
const NAME_SRC = "/brand/meshflow_logo-name_rounded.png";

/**
 * Brand assets are user-provided and must not be recolored or modified.
 * - "icon": hexagon mark only (square).
 * - "full": logo + "MeshFlow" wordmark (light backgrounds only — the wordmark
 *   ink is dark, so use `WordmarkOnDark` over the slate shell instead).
 */
export function Logo({
  variant = "icon",
  size = 32,
  className,
  priority = false,
}: {
  variant?: "icon" | "full";
  size?: number;
  className?: string;
  priority?: boolean;
}) {
  if (variant === "full") {
    return (
      <Image
        src={NAME_SRC}
        alt="MeshFlow"
        width={Math.round(size * 2.8)}
        height={size}
        className={cn("h-auto w-auto", className)}
        priority={priority}
      />
    );
  }

  return (
    <Image
      src={ICON_SRC}
      alt="MeshFlow"
      width={size}
      height={size}
      className={cn("rounded-md", className)}
      priority={priority}
    />
  );
}

/**
 * Icon + white wordmark, for use on the dark slate shell where the
 * dark-ink PNG wordmark would be invisible.
 */
export function WordmarkOnDark({
  size = 30,
  textClassName,
}: {
  size?: number;
  textClassName?: string;
}) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Logo variant="icon" size={size} priority />
      <span
        className={cn(
          "font-semibold tracking-tight",
          textClassName ?? "text-[1.05rem]",
        )}
      >
        <span className="text-white">Mesh</span>
        <span className="text-white">Flow</span>
      </span>
    </span>
  );
}
