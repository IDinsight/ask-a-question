/**
 * The generated API client as the app configures it (src/lib/api): base URL,
 * auth token, and the error/401 interceptors that keep the CustomError/Error
 * contract from utils/api.ts. `fetch` is mocked; nothing leaves the test.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { retrieveTag } from "@/client";
import { client } from "@/client/client.gen";
import "@/lib/api/interceptors";
import {
  ApiServerError,
  extractErrorDetail,
  getErrorMessage,
  isCustomError,
  toApiError,
} from "@/utils/api";

// Node's Request needs an absolute URL; the app itself uses the relative "/bff".
const BASE = "http://localhost/bff";

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>(async () => Response.json([]));
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

const call = () => retrieveTag({ baseUrl: BASE, fetch: fetchMock });
const sentRequest = () => fetchMock.mock.calls[0][0] as Request;

describe("client config", () => {
  it("sends every call to the BFF on the same origin", () => {
    expect(client.getConfig().baseUrl).toBe("/bff");
  });

  it("calls the backend path under /bff, trailing slash included", async () => {
    await call();

    expect(sentRequest().url).toBe(`${BASE}/tag/`);
  });

  it("attaches the stored token as a bearer token", async () => {
    localStorage.setItem("token", "[TOKEN]");

    await call();

    expect(sentRequest().headers.get("authorization")).toBe("Bearer [TOKEN]");
  });

  it("sends no Authorization header when signed out", async () => {
    await call();

    expect(sentRequest().headers.get("authorization")).toBeNull();
  });
});

describe("error interceptor", () => {
  it("turns a 4xx into a CustomError with the backend's detail", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Tag already exists" }, { status: 400 }),
    );

    await expect(call()).rejects.toEqual({
      status: 400,
      message: "Tag already exists",
      body: { detail: "Tag already exists" },
    });
  });

  it("turns a 5xx into an ApiServerError", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Could not reach the server" }, { status: 502 }),
    );

    const error = await call().catch((e) => e);

    expect(error).toBeInstanceOf(ApiServerError);
    expect(error).toMatchObject({
      status: 502,
      message: "Could not reach the server",
    });
  });

  it("turns a network failure into a plain Error", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const error = await call().catch((e) => e);

    expect(error).toBeInstanceOf(Error);
    expect(error).not.toBeInstanceOf(ApiServerError);
  });

  it("on a 401 while signed in, clears the token and goes to /login", async () => {
    localStorage.setItem("token", "[TOKEN]");
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "x" }, { status: 401 }),
    );
    // jsdom can't navigate; record where the app tries to go instead.
    const location = { pathname: "/content", href: "" };
    vi.spyOn(window, "location", "get").mockReturnValue(location as Location);

    await call().catch(() => undefined);

    expect(localStorage.getItem("token")).toBeNull();
    expect(location.href).toBe("/login?sourcePage=%2Fcontent");
  });

  it("refreshes an expiring token before the call and sends the new one", async () => {
    localStorage.setItem("token", "[OLD_TOKEN]");
    localStorage.setItem("refreshToken", "[REFRESH_TOKEN]");
    localStorage.setItem("tokenExpiresAt", String(Date.now() + 10_000));
    // session.ts refreshes with the global fetch, not the client's.
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      Response.json({
        access_token: "[NEW_TOKEN]",
        refresh_token: "[NEW_REFRESH_TOKEN]",
        expires_in: 1800,
        access_level: "fullaccess",
        user_role: "admin",
        workspace_name: "Test workspace",
        username: "test-admin",
        token_type: "bearer",
      }),
    );

    await call();

    expect(sentRequest().headers.get("authorization")).toBe(
      "Bearer [NEW_TOKEN]",
    );
  });

  it("goes to /login when the refresh token is refused, without calling the API", async () => {
    localStorage.setItem("token", "[OLD_TOKEN]");
    localStorage.setItem("refreshToken", "[REFRESH_TOKEN]");
    localStorage.setItem("tokenExpiresAt", String(Date.now() + 10_000));
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(null, { status: 401 }),
    );
    const location = { pathname: "/dashboard", href: "" };
    vi.spyOn(window, "location", "get").mockReturnValue(location as Location);

    await expect(call()).rejects.toThrow("Your session has expired");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(localStorage.getItem("token")).toBeNull();
    expect(location.href).toBe("/login?sourcePage=%2Fdashboard");
  });
});

describe("toApiError / extractErrorDetail / getErrorMessage", () => {
  const response = (status: number) => new Response(null, { status });

  it("reads FastAPI validation errors (a list of {msg})", () => {
    expect(
      extractErrorDetail({
        detail: [{ msg: "field required" }, { msg: "too short" }],
      }),
    ).toBe("field required; too short");
  });

  it("falls back to message / error_message keys", () => {
    expect(extractErrorDetail({ message: "a" })).toBe("a");
    expect(extractErrorDetail({ error_message: "b" })).toBe("b");
    expect(extractErrorDetail({})).toBeUndefined();
  });

  it("gives a 4xx without detail a generic message", () => {
    expect(toApiError({}, response(404))).toEqual({
      status: 404,
      message: "Request failed (404)",
      body: {},
    });
  });

  it("shows the backend's reason for a 4xx and the fallback otherwise", () => {
    const customError = toApiError({ detail: "No access" }, response(403));
    const serverError = toApiError({ detail: "Traceback..." }, response(500));

    expect(isCustomError(customError)).toBe(true);
    expect(getErrorMessage(customError, "Failed")).toBe("No access");
    expect(getErrorMessage(serverError, "Failed")).toBe("Failed");
  });
});
