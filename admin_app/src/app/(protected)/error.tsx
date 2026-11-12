"use client"; // Error boundaries must be Client Components.

import { useEffect } from "react";
import Link from "next/link";
import { IconAlertTriangle, IconRefresh } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

/**
 * Fallback for any render error inside a signed-in page. It sits below
 * (protected)/layout.tsx, so the sidebar and top bar stay usable and the user
 * can retry or move to another page.
 *
 * API errors from TanStack queries are handled inside each feature; this only
 * catches errors that escape them (bugs, unexpected data shapes).
 */
export default function ProtectedError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  // Errors thrown in Client Components may not be Error instances.
  const digest =
    error instanceof Error && "digest" in error
      ? String((error as Error & { digest?: unknown }).digest)
      : undefined;

  useEffect(() => {
    // No client error tracker yet (DSEM Level 4); the console keeps it
    // visible in dev and in browser logs.
    console.error(error);
  }, [error]);

  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <Empty className="mx-auto h-[60vh] max-w-6xl border bg-card">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconAlertTriangle />
          </EmptyMedia>
          <EmptyTitle>This page hit a problem</EmptyTitle>
          <EmptyDescription>
            Something went wrong while showing this page. Try again, or go back
            to your content.
          </EmptyDescription>
          {digest && (
            // Matches the digest in the server logs (src/instrumentation.ts).
            <p className="font-mono text-xs text-muted-foreground">
              Reference: {digest}
            </p>
          )}
        </EmptyHeader>
        <EmptyContent className="flex-row justify-center gap-2">
          <Button onClick={() => retry()}>
            <IconRefresh data-icon="inline-start" />
            Try again
          </Button>
          <Button
            variant="outline"
            nativeButton={false}
            render={<Link href="/content" />}
          >
            Go to content
          </Button>
        </EmptyContent>
      </Empty>
    </div>
  );
}
