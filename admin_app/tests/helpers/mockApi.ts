import type { Page, Route } from "@playwright/test";

/**
 * Test helpers that let the admin app run without a backend or a real login.
 *
 * - `mockAuth` seeds the localStorage keys AuthProvider reads on load, so
 *   ProtectedComponent treats the browser as logged in.
 * - `mockBackend` intercepts every request to the backend URL and answers
 *   from an in-memory store, so tests can create/delete tags and contents.
 *
 * Assumption: the app talks to the default backend URL (http://localhost:8000).
 * Set BACKEND_URL when running the tests if NEXT_PUBLIC_BACKEND_URL differs.
 */

export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export type MockTag = { tag_id: number; tag_name: string };

export type MockContent = {
  content_id: number;
  display_number: number;
  content_title: string;
  content_text: string;
  content_tags: number[];
  related_contents_id: number[];
  content_metadata: Record<string, unknown>;
  positive_votes: number;
  negative_votes: number;
  created_datetime_utc: string;
  updated_datetime_utc: string;
};

export type MockState = {
  tags: MockTag[];
  contents: MockContent[];
  /** Every request the mock answered, for asserting on API calls. */
  requests: { method: string; path: string; body: unknown }[];
};

/** Build a content record with sensible defaults. */
export const makeContent = (
  id: number,
  overrides: Partial<MockContent> = {},
): MockContent => ({
  content_id: id,
  display_number: id,
  content_title: `Content title ${id}`,
  content_text: `Body text for content ${id}.`,
  content_tags: [],
  related_contents_id: [],
  content_metadata: {},
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2026-01-15T10:00:00Z",
  updated_datetime_utc: "2026-01-15T10:00:00Z",
  ...overrides,
});

/** Log in as a workspace admin by seeding localStorage before any page script runs. */
export async function mockAuth(
  page: Page,
  { role = "admin" }: { role?: "admin" | "read_only" } = {},
) {
  await page.addInitScript((userRole) => {
    // Placeholder token: the mocked backend never validates it.
    window.localStorage.setItem("token", "test-token");
    window.localStorage.setItem("username", "test-admin");
    window.localStorage.setItem("userRole", userRole);
    window.localStorage.setItem(
      "accessLevel",
      userRole === "admin" ? "fullaccess" : "readonly",
    );
    window.localStorage.setItem("workspaceName", "Test workspace");
  }, role);
}

// The page (localhost:3000) calls the backend (localhost:8000) cross-origin,
// so every mocked response needs CORS headers or the browser drops it.
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "*",
  "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
};

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

/**
 * Answer backend calls from an in-memory store. Returns the store so tests
 * can inspect what was created, deleted or requested.
 */
export async function mockBackend(
  page: Page,
  initial: { tags?: MockTag[]; contents?: MockContent[] } = {},
): Promise<MockState> {
  const state: MockState = {
    tags: [...(initial.tags ?? [])],
    contents: [...(initial.contents ?? [])],
    requests: [],
  };
  let nextTagId = Math.max(0, ...state.tags.map((t) => t.tag_id)) + 1;

  // The root layout loads Google sign-in; it isn't needed and slows tests down.
  await page.route("https://accounts.google.com/**", (route) => route.abort());

  await page.route(
    (url) => url.href.startsWith(BACKEND_URL),
    async (route) => {
      const request = route.request();
      const method = request.method();
      const path = new URL(request.url()).pathname;

      // CORS preflight for requests carrying an Authorization header.
      if (method === "OPTIONS") {
        return route.fulfill({ status: 204, headers: CORS_HEADERS });
      }

      let body: unknown = null;
      try {
        body = request.postDataJSON();
      } catch {
        body = request.postData(); // multipart uploads aren't JSON
      }
      state.requests.push({ method, path, body });

      // --- Current user (workspace switcher in the app sidebar) ---
      if (method === "GET" && path === "/user/current-user") {
        return json(route, {
          user_id: 1,
          username: "test-admin",
          user_workspaces: [
            { workspace_id: 1, workspace_name: "Test workspace", user_role: "admin" },
          ],
          is_default_workspace: [true],
        });
      }

      // --- Tags ---
      if (method === "GET" && path === "/tag/") return json(route, state.tags);
      if (method === "POST" && path === "/tag/") {
        const tag = { tag_id: nextTagId++, tag_name: (body as any).tag_name };
        state.tags.push(tag);
        return json(route, tag);
      }
      const tagMatch = path.match(/^\/tag\/(\d+)$/);
      if (method === "DELETE" && tagMatch) {
        const id = Number(tagMatch[1]);
        state.tags = state.tags.filter((t) => t.tag_id !== id);
        state.contents.forEach((c) => {
          c.content_tags = c.content_tags.filter((t) => t !== id);
        });
        return json(route, []);
      }

      // --- Content ---
      if (method === "GET" && path === "/content/") return json(route, state.contents);
      if (method === "GET" && path === "/content/unvalidated-count") return json(route, 0);
      if (method === "GET" && path === "/content/next-unvalidated") return json(route, null);
      if (method === "POST" && path === "/content/") {
        const id = Math.max(0, ...state.contents.map((c) => c.content_id)) + 1;
        const created = makeContent(id, body as Partial<MockContent>);
        state.contents.push(created);
        return json(route, created);
      }
      const contentMatch = path.match(/^\/content\/(\d+)$/);
      if (contentMatch) {
        const id = Number(contentMatch[1]);
        const existing = state.contents.find((c) => c.content_id === id);
        if (method === "GET") {
          return existing ? json(route, existing) : json(route, { detail: "Not found" }, 404);
        }
        if (method === "PUT" && existing) {
          Object.assign(existing, body);
          return json(route, existing);
        }
        // The app "deletes" content by archiving it with a PATCH.
        if (method === "PATCH" || method === "DELETE") {
          state.contents = state.contents.filter((c) => c.content_id !== id);
          return json(route, {});
        }
      }

      // --- PDF processing (docmuncher) ---
      if (method === "GET" && path === "/docmuncher/status/is_job_running") {
        return json(route, false);
      }
      if (method === "GET" && path === "/docmuncher/status/data") return json(route, []);

      // Anything else: fail loudly so missing mocks are easy to spot.
      console.warn(`[mockBackend] unhandled ${method} ${path}`);
      return json(route, { detail: `Unmocked endpoint ${method} ${path}` }, 404);
    },
  );

  return state;
}
