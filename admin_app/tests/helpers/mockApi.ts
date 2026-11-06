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

export type MockUrgencyRule = {
  urgency_rule_id: number;
  urgency_rule_text: string;
  created_datetime_utc: string;
  updated_datetime_utc: string;
};

export type MockUser = {
  user_id: number;
  username: string;
  user_workspaces: { workspace_name: string; user_role: "admin" | "read_only" }[];
};

/** A user with one role in the mocked "Test workspace". */
export const makeUser = (
  id: number,
  username: string,
  role: "admin" | "read_only" = "read_only",
): MockUser => ({
  user_id: id,
  username,
  user_workspaces: [{ workspace_name: "Test workspace", user_role: role }],
});

export type MockState = {
  tags: MockTag[];
  contents: MockContent[];
  urgencyRules: MockUrgencyRule[];
  /** Response for GET /dashboard/overview/<period>; see `makeOverview`. */
  overview: unknown;
  /** Rows for GET /dashboard/performance/<period>; see `makePerformanceRow`. */
  performance: ReturnType<typeof makePerformanceRow>[];
  /** Response for GET /dashboard/insights/<period>. Refreshing swaps in `insightsAfterRefresh`. */
  insights: unknown;
  insightsAfterRefresh: unknown;
  /** Users for /user/ endpoints; each has a role in "Test workspace". */
  users: MockUser[];
  /** Current workspace (GET /workspace/current-workspace). Rotating the key updates it. */
  workspace: {
    api_key_first_characters: string | null;
    api_key_updated_datetime_utc: string | null;
    api_daily_quota: number | null;
  };
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

/** Build an urgency rule record with fixed timestamps. */
export const makeUrgencyRule = (id: number, text: string): MockUrgencyRule => ({
  urgency_rule_id: id,
  urgency_rule_text: text,
  created_datetime_utc: "2026-01-15T10:00:00Z",
  updated_datetime_utc: "2026-01-15T10:00:00Z",
});

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from(
  { length: 12 },
  (_, i) => `${String(i * 2).padStart(2, "0")}:00`,
);

/**
 * Build a dashboard overview response. With no arguments every count is zero
 * (a brand-new workspace). `queriesPerDay` fills the time series and heatmap.
 */
export const makeOverview = ({
  queriesPerDay = 0,
  topContent = [] as {
    title: string;
    query_count: number;
    positive_votes: number;
    negative_votes: number;
    last_updated: string;
  }[],
} = {}) => {
  const days = Array.from({ length: 7 }, (_, i) => `2026-11-0${i + 1}T00:00:00`);
  const series = (n: number) => Object.fromEntries(days.map((d) => [d, n]));
  return {
    stats_cards: {
      query_stats: {
        n_questions: queriesPerDay * 7,
        percentage_increase: queriesPerDay ? 0.25 : 0,
      },
      response_feedback_stats: {
        n_positive: 0,
        n_negative: queriesPerDay ? 2 : 0,
        percentage_positive_increase: 0,
        percentage_negative_increase: queriesPerDay ? -0.5 : 0,
      },
      urgency_stats: { n_urgent: queriesPerDay ? 3 : 0, percentage_increase: 0 },
      content_feedback_stats: {
        n_positive: queriesPerDay ? 9 : 0,
        n_negative: queriesPerDay ? 1 : 0,
        percentage_positive_increase: queriesPerDay ? 0.1 : 0,
        percentage_negative_increase: 0,
      },
    },
    heatmap: Object.fromEntries(
      HOURS.map((h, i) => [
        h,
        Object.fromEntries(DAYS.map((d, j) => [d, queriesPerDay ? (i + j) % 5 : 0])),
      ]),
    ),
    time_series: {
      normal: series(queriesPerDay),
      downvoted: series(queriesPerDay ? 1 : 0),
      urgent: series(queriesPerDay ? 2 : 0),
    },
    top_content: topContent,
  };
};

/** One content card's row on the content performance page (7 daily points). */
export const makePerformanceRow = (
  id: number,
  title: string,
  perDay: number[] = [1, 2, 3, 2, 4, 5, 6],
  votes: { up?: number; down?: number } = {},
) => ({
  id,
  title,
  total_query_count: perDay.reduce((a, b) => a + b, 0),
  positive_votes: votes.up ?? 0,
  negative_votes: votes.down ?? 0,
  query_count_time_series: Object.fromEntries(
    perDay.map((n, i) => [`2026-11-0${i + 1}T00:00:00`, n]),
  ),
});

/** A topic-discovery response. With no topics the status is "not_started". */
export const makeInsights = (
  topics: { id: number; name: string; queries: string[] }[] = [],
) => ({
  status: topics.length ? "completed" : "not_started",
  refreshTimeStamp: topics.length ? "2026-11-05T09:00:00Z" : "",
  data: topics.map((t) => ({
    topic_id: t.id,
    topic_name: t.name,
    topic_popularity: t.queries.length,
    topic_summary: `People ask about ${t.name.toLowerCase()}.`,
    topic_samples: t.queries.map((q) => ({
      query_text: q,
      query_datetime_utc: "2026-11-04T08:30:00Z",
    })),
  })),
  unclustered_queries: [],
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
  initial: {
    tags?: MockTag[];
    contents?: MockContent[];
    urgencyRules?: MockUrgencyRule[];
    overview?: unknown;
    performance?: ReturnType<typeof makePerformanceRow>[];
    insights?: unknown;
    insightsAfterRefresh?: unknown;
    workspace?: Partial<MockState["workspace"]>;
    users?: MockUser[];
  } = {},
): Promise<MockState> {
  const state: MockState = {
    tags: [...(initial.tags ?? [])],
    contents: [...(initial.contents ?? [])],
    urgencyRules: [...(initial.urgencyRules ?? [])],
    overview: initial.overview ?? makeOverview(),
    performance: initial.performance ?? [],
    insights: initial.insights ?? makeInsights(),
    insightsAfterRefresh: initial.insightsAfterRefresh ?? makeInsights(),
    users: [...(initial.users ?? [makeUser(1, "test-admin", "admin")])],
    workspace: {
      api_key_first_characters: "aD5KZ",
      api_key_updated_datetime_utc: "2026-11-06T09:35:00",
      api_daily_quota: 100,
      ...initial.workspace,
    },
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
      if (method === "GET" && path === "/content/unvalidated-count")
        return json(route, 0);
      if (method === "GET" && path === "/content/next-unvalidated")
        return json(route, null);
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
          return existing
            ? json(route, existing)
            : json(route, { detail: "Not found" }, 404);
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
      if (method === "GET" && path === "/docmuncher/status/data")
        return json(route, []);

      // --- Dashboard overview ---
      if (
        method === "GET" &&
        /^\/dashboard\/overview\/(day|week|month|year|custom)$/.test(path)
      ) {
        return json(route, state.overview);
      }

      // --- Users (workspace management) ---
      if (method === "GET" && path === "/user/") return json(route, state.users);
      if (method === "POST" && path === "/user/") {
        const b = body as { username: string; role: "admin" | "read_only" };
        const user = makeUser(
          Math.max(0, ...state.users.map((u) => u.user_id)) + 1,
          b.username,
          b.role,
        );
        state.users.push(user);
        // Placeholder codes for the test only
        return json(route, {
          username: b.username,
          recovery_codes: ["code-1111", "code-2222"],
        });
      }
      if (method === "POST" && path === "/user/add-existing-user-to-workspace") {
        const b = body as { username: string; role: "admin" | "read_only" };
        state.users.push(
          makeUser(
            Math.max(0, ...state.users.map((u) => u.user_id)) + 1,
            b.username,
            b.role,
          ),
        );
        return json(route, {});
      }
      const userIdMatch = path.match(/^\/user\/(\d+)$/);
      if (userIdMatch) {
        const id = Number(userIdMatch[1]);
        if (method === "PUT") {
          const u = state.users.find((x) => x.user_id === id);
          if (u)
            u.user_workspaces[0].user_role = (
              body as { role: "admin" | "read_only" }
            ).role;
          return json(route, u ?? {});
        }
        if (method === "DELETE") {
          state.users = state.users.filter((x) => x.user_id !== id);
          return json(route, { require_workspace_switch: false });
        }
      }
      // HEAD /user/<username>: 200 if the user exists anywhere. "outsider" exists in another workspace.
      const userNameMatch = path.match(/^\/user\/([^/]+)$/);
      if (method === "HEAD" && userNameMatch) {
        const name = decodeURIComponent(userNameMatch[1]);
        const exists =
          name === "outsider" || state.users.some((u) => u.username === name);
        return route.fulfill({ status: exists ? 200 : 404, headers: CORS_HEADERS });
      }
      const wsMatch = path.match(/^\/workspace\/(\d+)$/);
      if (method === "PUT" && wsMatch) {
        return json(route, {
          workspace_id: 1,
          workspace_name: (body as { workspace_name: string }).workspace_name,
        });
      }

      // --- Workspace / API key ---
      if (method === "GET" && path === "/workspace/current-workspace") {
        return json(route, {
          workspace_id: 1,
          workspace_name: "Test workspace",
          ...state.workspace,
        });
      }
      if (method === "PUT" && path === "/workspace/rotate-key") {
        // Placeholder key: 32 characters, never a real secret
        const newKey = "NEWKEY" + "x".repeat(26);
        state.workspace.api_key_first_characters = newKey.slice(0, 5);
        state.workspace.api_key_updated_datetime_utc = "2026-11-07T10:00:00";
        return json(route, { new_api_key: newKey });
      }

      // --- Dashboard content performance ---
      const perfMatch = path.match(
        /^\/dashboard\/performance\/(day|week|month|year|custom)(?:\/(\d+))?(\/ai-summary)?$/,
      );
      if (method === "GET" && perfMatch) {
        const [, , id, ai] = perfMatch;
        if (!id) return json(route, { content_time_series: state.performance });
        const row = state.performance.find((r) => r.id === Number(id));
        if (ai) return json(route, { ai_summary: `Summary for ${row?.title}.` });
        return json(route, {
          title: row?.title,
          query_count: row?.total_query_count ?? 0,
          positive_votes: row?.positive_votes ?? 0,
          negative_votes: row?.negative_votes ?? 0,
          daily_query_count_avg: Math.round((row?.total_query_count ?? 0) / 7),
          time_series: Object.fromEntries(
            Object.entries(row?.query_count_time_series ?? {}).map(([ts, n]) => [
              ts,
              { query_count: n, positive_count: 1, negative_count: 0 },
            ]),
          ),
          user_feedback: [
            {
              timestamp: "2026-11-03T10:00:00Z",
              question: "When should I go to the clinic?",
              feedback: "Very helpful",
            },
          ],
        });
      }

      // --- Dashboard query topics ---
      const insightsMatch = path.match(
        /^\/dashboard\/insights\/(day|week|month|year|custom)(\/refresh)?$/,
      );
      if (method === "GET" && insightsMatch) {
        if (insightsMatch[2]) {
          state.insights = state.insightsAfterRefresh;
          return json(route, { detail: "Started topic discovery." });
        }
        return json(route, state.insights);
      }

      // --- Urgency rules ---
      if (method === "GET" && path === "/urgency-rules/") {
        return json(route, state.urgencyRules);
      }
      if (method === "POST" && path === "/urgency-rules/") {
        const id = Math.max(0, ...state.urgencyRules.map((r) => r.urgency_rule_id)) + 1;
        const rule = makeUrgencyRule(id, (body as any).urgency_rule_text);
        state.urgencyRules.push(rule);
        return json(route, rule);
      }
      const ruleMatch = path.match(/^\/urgency-rules\/(\d+)$/);
      if (ruleMatch) {
        const id = Number(ruleMatch[1]);
        const existing = state.urgencyRules.find((r) => r.urgency_rule_id === id);
        if (method === "PUT" && existing) {
          existing.urgency_rule_text = (body as any).urgency_rule_text;
          existing.updated_datetime_utc = "2026-02-01T09:30:00Z";
          return json(route, existing);
        }
        if (method === "DELETE") {
          state.urgencyRules = state.urgencyRules.filter(
            (r) => r.urgency_rule_id !== id,
          );
          return json(route, {});
        }
      }
      // Flags a message as urgent if it contains any rule's first word (test-only logic).
      if (method === "POST" && path === "/urgency-detect") {
        const text = String((body as any).message_text).toLowerCase();
        const matched = state.urgencyRules
          .filter((r) => text.includes(r.urgency_rule_text.split(" ")[0].toLowerCase()))
          .map((r) => r.urgency_rule_text);
        return json(route, { is_urgent: matched.length > 0, matched_rules: matched });
      }

      // Anything else: fail loudly so missing mocks are easy to spot.
      console.warn(`[mockBackend] unhandled ${method} ${path}`);
      return json(route, { detail: `Unmocked endpoint ${method} ${path}` }, 404);
    },
  );

  return state;
}
