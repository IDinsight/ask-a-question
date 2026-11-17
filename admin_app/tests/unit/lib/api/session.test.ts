/**
 * Token storage and refresh (src/lib/api/session.ts). `fetch` is mocked;
 * nothing leaves the test. Tokens are placeholders.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  REFRESH_MARGIN_MS,
  SessionExpiredError,
  clearTokens,
  getFreshAccessToken,
  getRefreshToken,
  revokeRefreshToken,
  saveTokens,
  syncSessionCookie,
} from "@/lib/api/session";
import { SESSION_COOKIE } from "@/utils/sessionCookie";

const NOW = 1_700_000_000_000;

const refreshResponse = (overrides: Record<string, unknown> = {}) =>
  Response.json({
    access_token: "[NEW_TOKEN]",
    refresh_token: "[NEW_REFRESH_TOKEN]",
    expires_in: 1800,
    access_level: "fullaccess",
    user_role: "read_only",
    workspace_name: "Renamed workspace",
    username: "test-admin",
    token_type: "bearer",
    ...overrides,
  });

/** A signed-in session whose access token expires `msLeft` from NOW. */
const signIn = (msLeft: number) => {
  localStorage.setItem("token", "[OLD_TOKEN]");
  localStorage.setItem("refreshToken", "[REFRESH_TOKEN]");
  localStorage.setItem("tokenExpiresAt", String(NOW + msLeft));
};

const hasCookie = () =>
  document.cookie.split("; ").some((c) => c.startsWith(`${SESSION_COOKIE}=1`));

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

beforeEach(() => {
  localStorage.clear();
  clearTokens();
  vi.useFakeTimers({ now: NOW, toFake: ["Date"] });
  fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("saveTokens / clearTokens", () => {
  it("stores the pair, the expiry time and the proxy cookie", () => {
    saveTokens({ access_token: "[A]", refresh_token: "[R]", expires_in: 1800 });

    expect(localStorage.getItem("token")).toBe("[A]");
    expect(getRefreshToken()).toBe("[R]");
    expect(localStorage.getItem("tokenExpiresAt")).toBe(
      String(NOW + 1_800_000),
    );
    expect(hasCookie()).toBe(true);
  });

  it("clears all of it", () => {
    saveTokens({ access_token: "[A]", refresh_token: "[R]", expires_in: 1800 });
    clearTokens();

    expect(localStorage.getItem("token")).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(localStorage.getItem("tokenExpiresAt")).toBeNull();
    expect(hasCookie()).toBe(false);
  });
});

describe("syncSessionCookie", () => {
  it("sets the cookie for a session from before refresh tokens", () => {
    localStorage.setItem("token", "[LEGACY_TOKEN]");
    syncSessionCookie();
    expect(hasCookie()).toBe(true);
  });

  it("clears it when nothing is stored", () => {
    saveTokens({ access_token: "[A]", refresh_token: "[R]", expires_in: 1800 });
    localStorage.clear();
    syncSessionCookie();
    expect(hasCookie()).toBe(false);
  });
});

describe("getFreshAccessToken", () => {
  it("returns undefined when signed out", async () => {
    expect(await getFreshAccessToken()).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a token with time left as is", async () => {
    signIn(REFRESH_MARGIN_MS + 1);
    expect(await getFreshAccessToken()).toBe("[OLD_TOKEN]");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("leaves a session from before refresh tokens alone", async () => {
    localStorage.setItem("token", "[LEGACY_TOKEN]");
    expect(await getFreshAccessToken()).toBe("[LEGACY_TOKEN]");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("swaps the refresh token for a new pair when the token is about to expire", async () => {
    signIn(REFRESH_MARGIN_MS);
    fetchMock.mockResolvedValueOnce(refreshResponse());

    expect(await getFreshAccessToken()).toBe("[NEW_TOKEN]");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/bff/refresh");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      refresh_token: "[REFRESH_TOKEN]",
    });
    expect(getRefreshToken()).toBe("[NEW_REFRESH_TOKEN]");
    // Role and workspace from the refresh response replace the stored ones.
    expect(localStorage.getItem("userRole")).toBe("read_only");
    expect(localStorage.getItem("workspaceName")).toBe("Renamed workspace");
  });

  it("refreshes once for concurrent callers (refresh tokens are single use)", async () => {
    signIn(0);
    fetchMock.mockResolvedValueOnce(refreshResponse());

    const tokens = await Promise.all([
      getFreshAccessToken(),
      getFreshAccessToken(),
      getFreshAccessToken(),
    ]);

    expect(tokens).toEqual(["[NEW_TOKEN]", "[NEW_TOKEN]", "[NEW_TOKEN]"]);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("uses the cross-tab lock when the browser has one", async () => {
    signIn(0);
    fetchMock.mockResolvedValueOnce(refreshResponse());
    const request = vi.fn((_name: string, fn: () => Promise<boolean>) => fn());
    vi.stubGlobal("navigator", { locks: { request } });

    expect(await getFreshAccessToken()).toBe("[NEW_TOKEN]");
    expect(request).toHaveBeenCalledWith(
      "aaq-token-refresh",
      expect.any(Function),
    );
  });

  it("ends the session when the backend refuses the refresh token", async () => {
    signIn(0);
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 }));

    await expect(getFreshAccessToken()).rejects.toBeInstanceOf(
      SessionExpiredError,
    );
    expect(localStorage.getItem("token")).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("ends the session when there is no refresh token to use", async () => {
    signIn(0);
    localStorage.removeItem("refreshToken");

    await expect(getFreshAccessToken()).rejects.toBeInstanceOf(
      SessionExpiredError,
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    [
      "a server error",
      () =>
        fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 })),
    ],
    [
      "rate limiting",
      () =>
        fetchMock.mockResolvedValueOnce(new Response(null, { status: 429 })),
    ],
    [
      "a network failure",
      () => fetchMock.mockRejectedValueOnce(new TypeError("offline")),
    ],
  ])("keeps the session through %s", async (_, fail) => {
    signIn(0);
    fail();

    expect(await getFreshAccessToken()).toBe("[OLD_TOKEN]");
    expect(getRefreshToken()).toBe("[REFRESH_TOKEN]");
  });
});

describe("revokeRefreshToken", () => {
  it("posts the token to /bff/logout", () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    revokeRefreshToken("[REFRESH_TOKEN]");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/bff/logout");
    expect(JSON.parse(init?.body as string)).toEqual({
      refresh_token: "[REFRESH_TOKEN]",
    });
    expect(init?.keepalive).toBe(true);
  });

  it("does nothing without a token, and swallows network errors", async () => {
    revokeRefreshToken(null);
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockRejectedValueOnce(new TypeError("offline"));
    expect(() => revokeRefreshToken("[REFRESH_TOKEN]")).not.toThrow();
  });
});
