import type { Instrumentation } from "next";

/**
 * Log any unhandled server-side error (route handlers, server rendering) as one
 * structured JSON line, in the same shape as the BFF logs (src/lib/bff/logger.ts).
 *
 * Only the path without its query string is logged, and never headers: they
 * carry the user's bearer token.
 */
export const onRequestError: Instrumentation.onRequestError = async (
  error,
  request,
  context,
) => {
  const digest =
    typeof error === "object" && error !== null && "digest" in error
      ? String((error as { digest: unknown }).digest)
      : undefined;
  console.error(
    JSON.stringify({
      ts: new Date().toISOString(),
      level: "error",
      service: "admin_app",
      event: "next.request_error",
      method: request.method,
      // Route pattern (e.g. "/bff/[...path]") is safe; the concrete path may not be.
      route: context.routePath,
      routeType: context.routeType,
      digest,
      error: error instanceof Error ? error.message : String(error),
    }),
  );
};
