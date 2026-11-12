import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { SearchSidebar } from "@/components/features/content/components/SearchSidebar";

// TestSidebar reads the auth token from context. Stub it so tests don't need
// an AuthProvider; `authState.token` can be changed per test.
const authState = vi.hoisted(() => ({ token: "fake-token" as string | null }));
vi.mock("@/utils/auth", () => ({ useAuth: () => authState }));

// JsonDialog lazy-loads the shiki highlighter. Skip it: plain text is enough here.
vi.mock("@/lib/highlighter", () => ({
  loadHighlighter: () => Promise.reject(new Error("not in tests")),
}));

const deferred = <T,>() => {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
};

// Shape of a successful search, as useSearchMutation resolves it.
const okResponse = (overrides: Record<string, unknown> = {}) => ({
  status: 200,
  query_id: 99,
  feedback_secret_key: "fake-secret",
  llm_response: "Boil water for **one minute**.",
  // Keys are rank order; deliberately out of order to check sorting.
  search_results: {
    "1": { id: 21, title: "Water storage", text: "Keep containers covered." },
    "0": { id: 20, title: "Safe drinking water", text: "Boil or filter water." },
  },
  ...overrides,
});

const setup = ({
  search = vi.fn().mockResolvedValue(okResponse()),
  sendFeedback = vi.fn().mockResolvedValue({ parsedData: "ok" }),
} = {}) => {
  const closeSidebar = vi.fn();
  const user = userEvent.setup();
  render(
    <SearchSidebar closeSidebar={closeSidebar} search={search} sendFeedback={sendFeedback} />,
  );
  const input = screen.getByRole("textbox", { name: "Question" });
  return { user, input, search, sendFeedback, closeSidebar };
};

describe("SearchSidebar", () => {
  beforeEach(() => {
    authState.token = "fake-token";
    // The component logs on purpose (errors, feedback); keep output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it("starts with an empty state and can be closed", async () => {
    const { user, closeSidebar } = setup();
    expect(screen.getByText("Test your content")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close Test Search" }));
    expect(closeSidebar).toHaveBeenCalledOnce();
  });

  it("does not search while logged out", async () => {
    authState.token = null;
    const { user, input, search } = setup();

    await user.type(input, "Is tap water safe?{Enter}");
    expect(search).not.toHaveBeenCalled();
  });

  it("lists results in rank order without an answer block", async () => {
    const request = deferred<ReturnType<typeof okResponse>>();
    const { user, input, search } = setup({ search: vi.fn(() => request.promise) });

    await user.type(input, "Is tap water safe?{Enter}");
    expect(search).toHaveBeenCalledWith("Is tap water safe?", false);
    expect(screen.getByText("Searching your content...")).toBeInTheDocument();

    await act(async () => request.resolve(okResponse()));

    // Heading says "Results" (not "References") when no answer was requested.
    expect(screen.getByText("Results (2)")).toBeInTheDocument();
    expect(screen.queryByText("one minute")).not.toBeInTheDocument();
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("1Safe drinking water");
    expect(items[1]).toHaveTextContent("2Water storage");
  });

  it("asks for and shows the AI answer when the toggle is on", async () => {
    const { user, input, search } = setup();

    await user.click(screen.getByRole("checkbox"));
    await user.type(input, "Is tap water safe?");
    await user.click(screen.getByRole("button", { name: "Send question" }));

    expect(search).toHaveBeenCalledWith("Is tap water safe?", true);
    expect(await screen.findByText("one minute")).toBeInTheDocument();
    expect(screen.getByText("References (2)")).toBeInTheDocument();
  });

  it("says when the answer was empty and when no content matched", async () => {
    const { user, input } = setup({
      search: vi.fn().mockResolvedValue(okResponse({ llm_response: null, search_results: {} })),
    });

    await user.click(screen.getByRole("checkbox"));
    await user.type(input, "Anything?{Enter}");

    expect(await screen.findByText("No answer text was returned.")).toBeInTheDocument();
    expect(screen.getByText("No matching content was found.")).toBeInTheDocument();
  });

  it("treats missing search_results as no results", async () => {
    const { user, input } = setup({
      search: vi.fn().mockResolvedValue(okResponse({ search_results: null })),
    });
    await user.type(input, "Anything?{Enter}");
    expect(await screen.findByText("Results (0)")).toBeInTheDocument();
  });

  it("opens a reference in a dialog with its full text", async () => {
    const { user, input } = setup();
    await user.type(input, "water{Enter}");

    await user.click(await screen.findByRole("button", { name: /Safe drinking water/ }));

    const dialog = await screen.findByRole("dialog", { name: "Safe drinking water" });
    expect(dialog).toHaveTextContent("Reference 1 · Content #20");
    expect(dialog).toHaveTextContent("Boil or filter water.");
  });

  it("shows an error bubble for a non-200 response", async () => {
    const { user, input } = setup({
      search: vi.fn().mockResolvedValue({ status: 500, detail: "boom" }),
    });
    await user.type(input, "water{Enter}");

    expect(
      await screen.findByText(/The search service returned an error \(500\)/),
    ).toBeInTheDocument();
    // No feedback buttons without a feedback key, but the raw response is there.
    expect(screen.queryByRole("button", { name: "Helpful" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View raw response" })).toBeInTheDocument();
  });

  it("shows an error bubble when the request fails and exposes the raw error", async () => {
    const { user, input } = setup({
      search: vi.fn().mockRejectedValue(new Error("network down")),
    });
    await user.type(input, "water{Enter}");

    expect(await screen.findByText(/The search request failed/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View raw response" }));
    expect(await screen.findByRole("dialog", { name: "Raw response" })).toHaveTextContent(
      "network down",
    );
  });

  it("sends thumbs up/down feedback once each", async () => {
    const { user, input, sendFeedback } = setup();
    await user.type(input, "water{Enter}");

    await user.click(await screen.findByRole("button", { name: "Helpful" }));
    expect(sendFeedback).toHaveBeenCalledWith({
      queryId: 99,
      sentiment: "positive",
      feedbackSecretKey: "fake-secret",
    });
    const marked = screen.getByRole("button", { name: "Marked helpful" });
    expect(marked).toHaveAttribute("aria-pressed", "true");

    // A second click on the same thumb is ignored.
    await user.click(marked);
    expect(sendFeedback).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Not helpful" }));
    expect(sendFeedback).toHaveBeenLastCalledWith({
      queryId: 99,
      sentiment: "negative",
      feedbackSecretKey: "fake-secret",
    });
    expect(screen.getByRole("button", { name: "Marked not helpful" })).toBeInTheDocument();
  });

  it("logs when sending feedback fails", async () => {
    const { user, input } = setup({
      sendFeedback: vi.fn().mockRejectedValue(new Error("feedback failed")),
    });
    await user.type(input, "water{Enter}");
    await user.click(await screen.findByRole("button", { name: "Helpful" }));

    await vi.waitFor(() =>
      expect(console.error).toHaveBeenCalledWith(new Error("feedback failed")),
    );
  });

  it("clears the feedback state for each new search", async () => {
    const { user, input } = setup();
    await user.type(input, "water{Enter}");
    await user.click(await screen.findByRole("button", { name: "Helpful" }));
    expect(screen.getByRole("button", { name: "Marked helpful" })).toBeInTheDocument();

    await user.type(input, "{Enter}");
    expect(await screen.findByRole("button", { name: "Helpful" })).toBeInTheDocument();
  });
});
