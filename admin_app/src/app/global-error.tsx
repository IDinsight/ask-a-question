"use client"; // Error boundaries must be Client Components.

// global-error replaces the root layout, so it brings its own styles and font.
import "../../globals.css";
import { useEffect } from "react";

import { inter } from "@/fonts";

/**
 * Last-resort fallback when the root layout itself fails (for example a
 * provider throws). It replaces the whole document, so it can't rely on the
 * app shell, auth context or React Query, and uses plain elements styled with
 * the shared theme tokens instead of shadcn components.
 */
export default function GlobalError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  const digest =
    error instanceof Error && "digest" in error
      ? String((error as Error & { digest?: unknown }).digest)
      : undefined;

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body className={inter.className}>
        {/* metadata exports aren't supported here; React's <title> is. */}
        <title>Something went wrong | Ask A Question</title>
        <main className="flex min-h-svh items-center justify-center bg-background p-6">
          <div className="flex max-w-md flex-col items-center gap-4 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">
              Ask A Question couldn&apos;t load
            </h1>
            <p className="text-sm text-muted-foreground">
              Something went wrong while starting the app. Try again, and if it
              keeps happening, reload the page.
            </p>
            {digest && (
              <p className="font-mono text-xs text-muted-foreground">
                Reference: {digest}
              </p>
            )}
            <button
              type="button"
              onClick={() => retry()}
              className="h-9 bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              Try again
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
