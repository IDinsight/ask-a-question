/**
 * A small "signed in" marker cookie that mirrors the token in localStorage.
 *
 * Why: the access token lives in localStorage, which only the browser can
 * read. src/proxy.ts runs on the server before a page renders, so it needs
 * something it can see on the request. This cookie is that signal.
 *
 * It holds no token or user data, just "1". It is a UX hint (redirect
 * signed-out users before render), not a security control: the backend still
 * checks the bearer token on every API call.
 *
 * Kept free of React and browser-only imports so proxy.ts can import the
 * cookie name without pulling client code into the proxy bundle.
 */

/** Cookie name read by src/proxy.ts. */
export const SESSION_COOKIE = "aaq_signed_in";

/** Used when the token's expiry can't be read: one day. */
const FALLBACK_MAX_AGE_SECONDS = 60 * 60 * 24;

/**
 * Seconds until the JWT expires, from its `exp` claim. Returns null when the
 * token isn't a readable JWT. The signature is not checked here (the backend
 * does that); we only need the expiry to size the cookie.
 */
export const secondsUntilExpiry = (
  token: string,
  nowMs = Date.now(),
): number | null => {
  try {
    const payload = token.trim().split(".")[1];
    if (!payload) return null;
    // JWTs use base64url; atob needs standard base64 with padding.
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    const { exp } = JSON.parse(atob(padded)) as { exp?: unknown };
    if (typeof exp !== "number") return null;
    return Math.max(0, Math.floor(exp - nowMs / 1000));
  } catch {
    return null;
  }
};

const secureFlag = () =>
  typeof window !== "undefined" && window.location.protocol === "https:"
    ? "; Secure"
    : "";

/**
 * Set the marker so it expires with the token. That way the proxy stops
 * letting a user through at the same moment the backend would reject them.
 */
export const setSessionCookie = (token: string) => {
  if (typeof document === "undefined") return;
  const maxAge = secondsUntilExpiry(token) ?? FALLBACK_MAX_AGE_SECONDS;
  document.cookie = `${SESSION_COOKIE}=1; Path=/; Max-Age=${maxAge}; SameSite=Lax${secureFlag()}`;
};

/** Remove the marker (sign-out, workspace switch, expired session). */
export const clearSessionCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax${secureFlag()}`;
};
