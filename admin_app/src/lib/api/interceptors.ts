import { client } from "@/client/client.gen";
import { SessionExpiredError, clearTokens } from "@/lib/api/session";
import { toApiError } from "@/utils/api";

/**
 * Interceptors for the generated API client. Imported once, for its side
 * effects, by QueryProvider (which wraps the whole app), so they are in place
 * before any query or mutation runs.
 *
 * 1. Error shaping: every failure becomes a CustomError (4xx) or Error
 *    (5xx/network). See `toApiError` in utils/api.ts.
 * 2. Expired session: sends the user to /login, returning them to the current
 *    page afterwards. That happens in two cases:
 *    - the refresh token was refused before the request went out
 *      (SessionExpiredError from session.ts, which already cleared the tokens);
 *    - a request got a 401 while signed in (e.g. the session was revoked
 *      server-side after a password reset).
 *    A 401 on the login form itself has no stored token, so it just surfaces
 *    as an error.
 */
const registered = Symbol.for("admin_app.api.interceptors");
const globalFlags = globalThis as unknown as Record<symbol, boolean>;

const goToLogin = () => {
  const sourcePage = encodeURIComponent(window.location.pathname);
  // A full page load on purpose: this runs outside React (no router), and a
  // reload drops every in-memory trace of the dead session (query cache,
  // auth context).
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `/login?sourcePage=${sourcePage}`;
};

// Guard against double registration (Fast Refresh re-evaluates modules in dev).
if (!globalFlags[registered]) {
  globalFlags[registered] = true;

  client.interceptors.error.use((error, response) => {
    if (typeof window !== "undefined") {
      if (error instanceof SessionExpiredError) {
        goToLogin();
      } else if (response?.status === 401 && localStorage.getItem("token")) {
        // Clears both tokens and the proxy's signed-in cookie, or src/proxy.ts
        // would keep letting this dead session through to protected pages.
        clearTokens();
        goToLogin();
      }
    }
    return toApiError(error, response);
  });
}
