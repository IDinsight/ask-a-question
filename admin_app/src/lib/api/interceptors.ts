import { client } from "@/client/client.gen";
import { toApiError } from "@/utils/api";

/**
 * Interceptors for the generated API client. Imported once, for its side
 * effects, by QueryProvider (which wraps the whole app), so they are in place
 * before any query or mutation runs.
 *
 * 1. Error shaping: every failure becomes a CustomError (4xx) or Error
 *    (5xx/network). See `toApiError` in utils/api.ts.
 * 2. Expired session: a 401 while logged in clears the token and sends the user
 *    to /login, returning them to the current page afterwards (same behaviour
 *    as the old axios interceptor). A 401 on the login form itself has no
 *    stored token, so it just surfaces as an error.
 */
const registered = Symbol.for("admin_app.api.interceptors");
const globalFlags = globalThis as unknown as Record<symbol, boolean>;

// Guard against double registration (Fast Refresh re-evaluates modules in dev).
if (!globalFlags[registered]) {
  globalFlags[registered] = true;

  client.interceptors.error.use((error, response) => {
    if (response?.status === 401 && typeof window !== "undefined") {
      if (localStorage.getItem("token")) {
        localStorage.removeItem("token");
        const sourcePage = encodeURIComponent(window.location.pathname);
        window.location.href = `/login?sourcePage=${sourcePage}`;
      }
    }
    return toApiError(error, response);
  });
}
