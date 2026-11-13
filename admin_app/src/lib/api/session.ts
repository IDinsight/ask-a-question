import type { AuthenticationDetails } from "@/client/types.gen";
import { clearSessionCookie, setSessionCookie } from "@/utils/sessionCookie";

/**
 * Token storage and refresh for the signed-in user.
 *
 * The backend issues a short-lived access token (ACCESS_TOKEN_EXPIRE_MINUTES,
 * 30 by default) plus a single-use refresh token. Before the access token
 * expires, the API client's `auth` callback (client-config.ts) calls
 * getFreshAccessToken(), which swaps the refresh token for a new pair at
 * POST /refresh. Refreshing on demand rather than on a timer means a laptop
 * that slept for an hour still refreshes on its next request.
 *
 * Refresh tokens rotate: each works once, and presenting one twice revokes the
 * whole login session (the backend treats it as a stolen copy). So two
 * refreshes must never race, in this tab or across tabs, which share
 * localStorage. Refreshes are serialised with the Web Locks API, and inside
 * the lock we re-check whether another tab already refreshed.
 *
 * Uses plain fetch, not the generated SDK: the SDK's client imports
 * client-config.ts, which imports this file (circular), and its error
 * interceptor would treat a failed refresh like any other 401.
 */

const STORAGE = {
  accessToken: "token",
  refreshToken: "refreshToken",
  /** Epoch ms when the access token expires, from `expires_in`. */
  expiresAt: "tokenExpiresAt",
} as const;

/** Refresh this long before expiry, so a slow request doesn't go out stale. */
export const REFRESH_MARGIN_MS = 60_000;

const LOCK_NAME = "aaq-token-refresh";

type Tokens = Pick<
  AuthenticationDetails,
  "access_token" | "refresh_token" | "expires_in"
>;

const hasStorage = () => typeof window !== "undefined";

/**
 * Store a token pair from login, Google login, workspace switch or refresh,
 * and set the proxy's signed-in cookie to last as long as the refresh token
 * (the session can be renewed until then, so pages should stay reachable).
 */
export const saveTokens = ({
  access_token,
  refresh_token,
  expires_in,
}: Tokens) => {
  localStorage.setItem(STORAGE.accessToken, access_token);
  localStorage.setItem(STORAGE.refreshToken, refresh_token);
  // Computed from the browser's own clock, so client/server clock skew
  // doesn't matter.
  localStorage.setItem(
    STORAGE.expiresAt,
    String(Date.now() + expires_in * 1000),
  );
  setSessionCookie(refresh_token);
};

/** Forget both tokens and the proxy cookie. */
export const clearTokens = () => {
  localStorage.removeItem(STORAGE.accessToken);
  localStorage.removeItem(STORAGE.refreshToken);
  localStorage.removeItem(STORAGE.expiresAt);
  clearSessionCookie();
};

export const getRefreshToken = () =>
  hasStorage() ? localStorage.getItem(STORAGE.refreshToken) : null;

/**
 * Make sure the proxy cookie exists for a stored session. Covers sessions
 * that started before the cookie existed. Those have no refresh token, so the
 * cookie follows the access token's own expiry.
 */
export const syncSessionCookie = () => {
  if (!hasStorage()) return;
  const sessionToken =
    localStorage.getItem(STORAGE.refreshToken) ??
    localStorage.getItem(STORAGE.accessToken);
  if (sessionToken) setSessionCookie(sessionToken);
  else clearSessionCookie();
};

/** True when the stored access token is missing or about to expire. */
const needsRefresh = (nowMs = Date.now()) => {
  const expiresAt = Number(localStorage.getItem(STORAGE.expiresAt));
  // No expiry stored: a session from before refresh tokens. Leave it alone;
  // its long-lived token keeps working until the backend rejects it.
  if (!expiresAt) return false;
  return expiresAt - nowMs <= REFRESH_MARGIN_MS;
};

/** Thrown when the backend refuses the refresh token: the session is over. */
export class SessionExpiredError extends Error {
  constructor() {
    super("Your session has expired. Please log in again.");
    this.name = "SessionExpiredError";
  }
}

/** One POST /refresh. Returns false when the session is over, true otherwise. */
const exchangeRefreshToken = async (): Promise<boolean> => {
  // Re-checked inside the lock: another tab may have refreshed while we waited.
  if (!needsRefresh()) return true;
  const refreshToken = localStorage.getItem(STORAGE.refreshToken);
  if (!refreshToken) return false;

  let response: Response;
  try {
    response = await fetch("/bff/refresh", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // Network blip: keep the session and let the request try with the token
    // it has. The next request retries the refresh.
    return true;
  }
  // 401: invalid, expired, reused or revoked. Anything else (429, 5xx) is
  // transient, so keep the session for now.
  if (response.status === 401) return false;
  if (!response.ok) return true;

  const details = (await response.json()) as AuthenticationDetails;
  saveTokens(details);
  // Role or access level can change between logins; keep them current.
  localStorage.setItem("accessLevel", details.access_level);
  localStorage.setItem("userRole", details.user_role);
  localStorage.setItem("workspaceName", details.workspace_name);
  return true;
};

/** Run fn under a cross-tab lock where supported, else under an in-tab one. */
let inTabRefresh: Promise<boolean> | null = null;
const withRefreshLock = (fn: () => Promise<boolean>): Promise<boolean> => {
  if (typeof navigator !== "undefined" && navigator.locks) {
    // request() resolves with the callback's awaited result; this TS lib types
    // it as Promise<Promise<boolean>>, which is the same at runtime.
    return navigator.locks.request(
      LOCK_NAME,
      fn,
    ) as unknown as Promise<boolean>;
  }
  inTabRefresh ??= fn().finally(() => {
    inTabRefresh = null;
  });
  return inTabRefresh;
};

/**
 * The access token to send with the next request, refreshed first if it is
 * about to expire. Returns undefined when signed out. Throws
 * SessionExpiredError when the backend refuses the refresh token; the error
 * interceptor turns that into a redirect to /login.
 */
export const getFreshAccessToken = async (): Promise<string | undefined> => {
  if (!hasStorage()) return undefined;
  if (!localStorage.getItem(STORAGE.accessToken)) return undefined;

  if (needsRefresh()) {
    const stillSignedIn = await withRefreshLock(exchangeRefreshToken);
    if (!stillSignedIn) {
      clearTokens();
      throw new SessionExpiredError();
    }
  }
  return localStorage.getItem(STORAGE.accessToken) ?? undefined;
};

/**
 * Revoke a login session on the backend (POST /logout). Fire-and-forget: the
 * endpoint always answers 204, and signing out locally must not wait on it.
 */
export const revokeRefreshToken = (refreshToken: string | null) => {
  if (!refreshToken) return;
  fetch("/bff/logout", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    // Lets the request finish even if the page navigates away right after.
    keepalive: true,
  }).catch(() => {
    // Nothing to do: the refresh token still expires on its own.
  });
};
