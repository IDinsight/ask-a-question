// @vitest-environment node
/**
 * The BFF proxy (src/lib/bff/server.ts) with a mocked `fetch` standing in for
 * core_backend. Checks the allowlist, header forwarding, request IDs, response
 * relaying, failure mapping and that logs never carry user data.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { proxyToBackend } from "@/lib/bff/server";

const BACKEND = "http://backend.test:8000";

/** A browser request to the BFF on the admin app's origin. */
const bffRequest = (path: string, init: RequestInit = {}) =>
  new Request(`http://admin.test/bff${path}`, init);

let fetchMock: ReturnType<typeof vi.fn>;
let logLines: string[];

beforeEach(() => {
  vi.stubEnv("BACKEND_INTERNAL_URL", BACKEND);
  fetchMock = vi.fn(async () => Response.json([{ tag_id: 1, tag_name: "a" }]));
  vi.stubGlobal("fetch", fetchMock);
  logLines = [];
  const capture = (line: string) => logLines.push(line);
  vi.spyOn(console, "log").mockImplementation(capture);
  vi.spyOn(console, "error").mockImplementation(capture);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** The single Request the proxy sent upstream. */
const upstreamCall = () => {
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
  return { url, init, headers: new Headers(init.headers) };
};

describe("allowlist", () => {
  it("rejects paths that are not in the generated route list with 404", async () => {
    const response = await proxyToBackend(bffRequest("/data-api/contents"));

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Not Found" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a known path with a method the backend doesn't offer (405)", async () => {
    const response = await proxyToBackend(
      bffRequest("/tag/", { method: "PATCH" }),
    );

    expect(response.status).toBe(405);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects path traversal", async () => {
    const response = await proxyToBackend(
      bffRequest("/content/../data-api/contents"),
    );

    // URL parsing already collapses "..", so this lands on a non-allowlisted path.
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("matches static segments before path params", async () => {
    await proxyToBackend(bffRequest("/user/current-user"));

    expect(upstreamCall().url).toBe(`${BACKEND}/user/current-user`);
  });
});

describe("forwarding", () => {
  it("keeps the trailing slash and query string", async () => {
    await proxyToBackend(bffRequest("/content/?skip=0&limit=0"));

    expect(upstreamCall().url).toBe(`${BACKEND}/content/?skip=0&limit=0`);
  });

  it("forwards auth, content-type and x-forwarded-for, and drops cookies", async () => {
    await proxyToBackend(
      bffRequest("/tag/", {
        method: "POST",
        body: JSON.stringify({ tag_name: "x" }),
        headers: {
          authorization: "Bearer [TOKEN]",
          "content-type": "application/json",
          cookie: "session=secret",
          "x-forwarded-for": "203.0.113.7",
        },
      }),
    );

    const { init, headers } = upstreamCall();
    expect(init.method).toBe("POST");
    expect(headers.get("authorization")).toBe("Bearer [TOKEN]");
    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.get("x-forwarded-for")).toBe("203.0.113.7");
    expect(headers.get("cookie")).toBeNull();
    expect(new TextDecoder().decode(init.body as ArrayBuffer)).toBe(
      '{"tag_name":"x"}',
    );
  });

  it("keeps a multipart upload's boundary", async () => {
    const form = new FormData();
    form.append("file", new Blob(["a,b"]), "cards.csv");
    const request = bffRequest("/content/csv-upload", {
      method: "POST",
      body: form,
    });
    const contentType = request.headers.get("content-type");

    await proxyToBackend(request);

    expect(contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect(upstreamCall().headers.get("content-type")).toBe(contentType);
  });

  it("sends no body for GET", async () => {
    await proxyToBackend(bffRequest("/tag/"));

    expect(upstreamCall().init.body).toBeUndefined();
  });
});

describe("request IDs and timing", () => {
  it("creates a request ID and sends it both ways", async () => {
    const response = await proxyToBackend(bffRequest("/tag/"));

    const requestId = response.headers.get("x-request-id");
    expect(requestId).toMatch(/^[0-9a-f-]{36}$/);
    expect(upstreamCall().headers.get("x-request-id")).toBe(requestId);
  });

  it("reuses an incoming request ID", async () => {
    const response = await proxyToBackend(
      bffRequest("/tag/", { headers: { "x-request-id": "abc-123" } }),
    );

    expect(response.headers.get("x-request-id")).toBe("abc-123");
    expect(upstreamCall().headers.get("x-request-id")).toBe("abc-123");
  });

  it("reports upstream time in Server-Timing", async () => {
    const response = await proxyToBackend(bffRequest("/tag/"));

    expect(response.headers.get("server-timing")).toMatch(/^upstream;dur=\d+$/);
  });
});

describe("relaying the backend's response", () => {
  it("passes status, body and content-type through", async () => {
    fetchMock.mockResolvedValueOnce(
      Response.json({ detail: "Tag already exists" }, { status: 400 }),
    );

    const response = await proxyToBackend(
      bffRequest("/tag/", { method: "POST" }),
    );

    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(await response.json()).toEqual({ detail: "Tag already exists" });
  });

  it("returns no body for HEAD", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 404 }));

    const response = await proxyToBackend(
      bffRequest("/user/someone", { method: "HEAD" }),
    );

    expect(response.status).toBe(404);
    expect(response.body).toBeNull();
  });

  it("does not follow backend redirects", async () => {
    await proxyToBackend(bffRequest("/tag/"));

    expect(upstreamCall().init.redirect).toBe("manual");
  });
});

describe("failures", () => {
  it("maps an unreachable backend to 502", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));

    const response = await proxyToBackend(bffRequest("/tag/"));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "Could not reach the server",
    });
  });

  it("maps a timeout to 504", async () => {
    // Never resolves on its own; rejects when the proxy's timeout signal fires.
    fetchMock.mockImplementationOnce(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) =>
          init.signal!.addEventListener("abort", () =>
            reject(init.signal!.reason),
          ),
        ),
    );

    const response = await proxyToBackend(
      bffRequest("/search", { method: "POST" }),
      {
        timeoutMs: 10,
      },
    );

    expect(response.status).toBe(504);
  });
});

describe("logging", () => {
  const parsedLogs = () => logLines.map((line) => JSON.parse(line));

  it("logs one structured line with the route template", async () => {
    await proxyToBackend(bffRequest("/content/42"));

    expect(parsedLogs()).toEqual([
      expect.objectContaining({
        level: "info",
        event: "bff.proxy",
        method: "GET",
        route: "/content/{content_id}",
        status: 200,
        durationMs: expect.any(Number),
        requestId: expect.any(String),
      }),
    ]);
  });

  it("never logs path params, query strings or tokens", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 200 }));

    await proxyToBackend(
      bffRequest("/user/jane.doe?remove_from_workspace_name=Clinic", {
        method: "DELETE",
        headers: { authorization: "Bearer [TOKEN]" },
      }),
    );

    const output = logLines.join("\n");
    expect(output).toContain('"route":"/user/{user_id}"');
    expect(output).not.toContain("jane.doe");
    expect(output).not.toContain("Clinic");
    expect(output).not.toContain("[TOKEN]");
  });

  it("logs 5xx responses at error level", async () => {
    fetchMock.mockResolvedValueOnce(new Response("boom", { status: 500 }));

    await proxyToBackend(bffRequest("/tag/"));

    expect(parsedLogs()[0]).toMatchObject({ level: "error", status: 500 });
  });

  it("logs rejected paths without the path itself", async () => {
    await proxyToBackend(bffRequest("/data-api/queries?user=jane.doe"));

    expect(parsedLogs()[0]).toMatchObject({
      event: "bff.rejected",
      status: 404,
    });
    expect(logLines.join("\n")).not.toContain("jane.doe");
  });
});
