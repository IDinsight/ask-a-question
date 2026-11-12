import {
  SESSION_COOKIE,
  clearSessionCookie,
  secondsUntilExpiry,
  setSessionCookie,
} from "@/utils/sessionCookie";

/** Build an unsigned JWT-shaped string; only the payload matters here. */
const fakeJwt = (payload: object) =>
  `header.${btoa(JSON.stringify(payload)).replace(/=+$/, "")}.signature`;

const hasCookie = () =>
  document.cookie.split("; ").some((c) => c.startsWith(`${SESSION_COOKIE}=1`));

describe("secondsUntilExpiry", () => {
  const now = 1_700_000_000_000;

  it("reads the exp claim", () => {
    expect(secondsUntilExpiry(fakeJwt({ exp: now / 1000 + 3600 }), now)).toBe(
      3600,
    );
  });

  it("never goes negative for an expired token", () => {
    expect(secondsUntilExpiry(fakeJwt({ exp: now / 1000 - 10 }), now)).toBe(0);
  });

  it.each([
    ["not a JWT", "plain-token"],
    ["no exp claim", fakeJwt({ sub: "user" })],
    ["garbage payload", "a.%%%.c"],
  ])("returns null for %s", (_, token) => {
    expect(secondsUntilExpiry(token, now)).toBeNull();
  });
});

describe("set/clearSessionCookie", () => {
  afterEach(() => clearSessionCookie());

  it("sets the marker for a JWT and for a non-JWT token (fallback age)", () => {
    setSessionCookie(fakeJwt({ exp: Date.now() / 1000 + 600 }));
    expect(hasCookie()).toBe(true);
    clearSessionCookie();
    setSessionCookie("opaque-token");
    expect(hasCookie()).toBe(true);
  });

  it("clears the marker", () => {
    setSessionCookie("opaque-token");
    clearSessionCookie();
    expect(hasCookie()).toBe(false);
  });
});
