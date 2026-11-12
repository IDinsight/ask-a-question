import "server-only";

import { logger } from "./logger";
import { BFF_ROUTES, type BffRoute } from "./routes.gen";

/**
 * Backend-for-frontend (BFF) proxy, used by src/app/bff/[...path]/route.ts.
 *
 * The browser only talks to `/bff/*` on the admin app's own origin (the
 * generated client's baseUrl). This module forwards each call to core_backend
 * with `fetch` and adds:
 *
 * - An allowlist: only operations in routes.gen.ts (generated from the OpenAPI
 *   spec) are forwarded. Anything else gets 404/405 without touching the backend.
 * - Request IDs: reuses an incoming `x-request-id` or creates one, sends it to
 *   the backend and returns it to the browser, so one ID ties a UI action to the
 *   BFF log line and the backend log.
 * - Structured logs: one JSON line per call with the OpenAPI path template
 *   (e.g. "/user/{username}"), method, status and duration. Never tokens,
 *   bodies, query strings or concrete paths, so usernames stay out of the logs.
 * - Timing: a `Server-Timing: upstream;dur=<ms>` header (browser network tab).
 * - Failure mapping: backend unreachable -> 502, timeout -> 504, both with a
 *   FastAPI-style `{detail}` body.
 *
 * Why /bff and not /api: in the Docker deployment Caddy sends `/api/*` straight
 * to core_backend, so Next.js route handlers under /api would never be reached.
 */

/** URL prefix of the BFF on the admin app's origin. */
export const BFF_PREFIX = "/bff";

/**
 * Where the Next.js server reaches core_backend. Read per request (not at build
 * time) so one Docker image works everywhere. Assumption: in Docker this is the
 * internal service URL (http://core_backend:8000); otherwise localhost:8000.
 */
const backendUrl = (): string =>
  (process.env.BACKEND_INTERNAL_URL || "http://localhost:8000").replace(/\/+$/, "");

/**
 * Default upstream timeout. Matches Caddy's 100s backend read timeout, since
 * search/chat/AI-summary calls wait on an LLM.
 */
export const DEFAULT_TIMEOUT_MS = 100_000;

/** Request headers passed to the backend. Everything else (cookies, ...) is dropped. */
const FORWARDED_REQUEST_HEADERS = ["authorization", "content-type", "accept"];

/** Response headers passed back to the browser. */
const FORWARDED_RESPONSE_HEADERS = ["content-type", "content-disposition"];

/**
 * Find the allowlisted route for a backend path. Returns the route, or
 * "method-not-allowed" when the path exists with other methods, or null.
 */
export const matchRoute = (
  method: string,
  backendPath: string,
): BffRoute | "method-not-allowed" | null => {
  const candidates = BFF_ROUTES.filter((route) => route.pattern.test(backendPath));
  if (candidates.length === 0) return null;
  return candidates.find((route) => route.method === method) ?? "method-not-allowed";
};

const jsonError = (status: number, detail: string, headers: Headers) => {
  headers.set("content-type", "application/json");
  return new Response(JSON.stringify({ detail }), { status, headers });
};

/**
 * Forward one /bff request to core_backend and relay the response.
 * `options.timeoutMs` exists for tests; production uses the default.
 */
export const proxyToBackend = async (
  request: Request,
  options: { timeoutMs?: number } = {},
): Promise<Response> => {
  const started = performance.now();
  const method = request.method.toUpperCase();
  const requestId = request.headers.get("x-request-id") || crypto.randomUUID();
  const responseHeaders = new Headers({ "x-request-id": requestId });

  // --- Resolve and check the path ----------------------------------------
  // Use the raw pathname (still percent-encoded, trailing slash intact; see
  // skipTrailingSlashRedirect in next.config.js) rather than route params, so
  // the backend receives exactly the path the generated client built.
  const { pathname, search } = new URL(request.url);
  const backendPath = pathname.slice(BFF_PREFIX.length) || "/";
  const route = backendPath.includes("..") ? null : matchRoute(method, backendPath);

  if (route === null || route === "method-not-allowed") {
    const status = route === null ? 404 : 405;
    // The concrete path is not logged (it may contain a username).
    logger.warn("bff.rejected", { requestId, method, status });
    return jsonError(status, route === null ? "Not Found" : "Method Not Allowed", responseHeaders);
  }
  const logFields = { requestId, method, route: route.template };

  // --- Build the upstream request ------------------------------------------
  const upstreamHeaders = new Headers({ "x-request-id": requestId });
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) upstreamHeaders.set(name, value);
  }
  // Keep the real client IP visible to the backend (Caddy sets this header).
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) upstreamHeaders.set("x-forwarded-for", forwardedFor);

  // Buffer the body. Multipart uploads keep their original content-type (with
  // boundary), so the backend parses them exactly as before.
  const body =
    method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  // --- Call the backend ------------------------------------------------------
  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl()}${backendPath}${search}`, {
      method,
      headers: upstreamHeaders,
      body,
      cache: "no-store", // per-user data: never cache on the server
      redirect: "manual", // surface backend redirects instead of silently following
      signal: AbortSignal.timeout(options.timeoutMs ?? DEFAULT_TIMEOUT_MS),
    });
  } catch (error) {
    const durationMs = Math.round(performance.now() - started);
    const timedOut = error instanceof DOMException && error.name === "TimeoutError";
    logger.error(timedOut ? "bff.upstream_timeout" : "bff.upstream_unreachable", {
      ...logFields,
      durationMs,
      error: error instanceof Error ? error.message : String(error),
    });
    responseHeaders.set("server-timing", `upstream;dur=${durationMs}`);
    return timedOut
      ? jsonError(504, "The server took too long to respond", responseHeaders)
      : jsonError(502, "Could not reach the server", responseHeaders);
  }

  // --- Relay the response ----------------------------------------------------
  const durationMs = Math.round(performance.now() - started);
  const fields = { ...logFields, status: upstream.status, durationMs };
  if (upstream.status >= 500) logger.error("bff.proxy", fields);
  else if (upstream.status >= 400) logger.warn("bff.proxy", fields);
  else logger.info("bff.proxy", fields);

  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  responseHeaders.set("server-timing", `upstream;dur=${durationMs}`);

  // HEAD and "no content" responses must not carry a body (Response throws).
  const noBody = method === "HEAD" || [204, 205, 304].includes(upstream.status);
  // Stream the body through. fetch already decoded any gzip, so the upstream
  // content-encoding/content-length headers are deliberately not copied.
  return new Response(noBody ? null : upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
};
