import * as React from "react";
import { cn } from "cn";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Shared building blocks for the route-level loading.tsx skeletons. Each
 * feature's skeleton (features/<route>/components/<Feature>Skeleton.tsx)
 * mirrors its page's real layout; these two pieces are the parts every page
 * has in common.
 */

/**
 * Wraps a skeleton so screen readers hear "Loading <label>" once instead of a
 * run of empty boxes. The visible shapes are hidden from assistive tech.
 */
export function LoadingRegion({
  label,
  className,
  children,
}: {
  /** What is loading, e.g. "content". Read as "Loading content". */
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div role="status" aria-busy="true" className={className}>
      <span className="sr-only">Loading {label}</span>
      <div aria-hidden="true" className="contents">
        {children}
      </div>
    </div>
  );
}

/**
 * Page title + description, matching the `<header>` every feature page opens
 * with (text-2xl title, text-sm description capped at max-w-2xl). Pass
 * `actions` for pages with buttons on the right of the header.
 */
export function PageHeaderSkeleton({
  actions,
  className,
}: {
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-end justify-between gap-4",
        className,
      )}
    >
      <div className="flex w-full max-w-2xl flex-col gap-2">
        {/* Title: text-2xl line height is 32px */}
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  );
}
