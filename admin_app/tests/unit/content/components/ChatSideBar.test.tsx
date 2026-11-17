import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ChatSideBar } from "@/components/features/content/components/ChatSideBar";

// JsonDialog lazy-loads the shiki highlighter. Skip it: the dialog falls back
// to plain text lines, which is all these tests need.
vi.mock("@/lib/highlighter", () => ({
  loadHighlighter: () => Promise.reject(new Error("not in tests")),
}));

// A deferred promise lets a test inspect the "waiting for reply" state
// before deciding how the request ends.
const deferred = <T,>() => {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const reply = (overrides: Record<string, unknown> = {}) => ({
  llm_response: "Use a **bed net** every night.",
  session_id: 42,
  // Keys are rank order; deliberately out of order to check sorting.
  search_results: {
    "1": { id: 11, title: "Second card", text: "second text", distance: 0.4 },
    "0": { id: 10, title: "First card", text: "first text", distance: 0.2 },
  },
  ...overrides,
});

const setup = (getResponse = vi.fn()) => {
  const props = {
    closeSidebar: vi.fn(),
    getResponse,
    setSnackMessage: vi.fn(),
  };
  const user = userEvent.setup();
  render(<ChatSideBar {...props} />);
  const input = screen.getByRole("textbox", { name: "Question" });
  return { ...props, user, input };
};

describe("ChatSideBar", () => {
  beforeEach(() => {
    // The error path logs on purpose; keep test output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("starts empty with send and new-chat disabled", () => {
    setup();
    expect(screen.getByText("Start a test conversation")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Send question" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "New chat" })).toBeDisabled();
  });

  it("closes the sidebar", async () => {
    const { user, closeSidebar } = setup();
    await user.click(screen.getByRole("button", { name: "Close test chat" }));
    expect(closeSidebar).toHaveBeenCalledOnce();
  });

  it("does not send whitespace-only questions", async () => {
    const { user, input, getResponse } = setup();
    await user.type(input, "   {Enter}");
    expect(getResponse).not.toHaveBeenCalled();
  });

  it("sends on Enter, shows a pending turn, then the answer and its sources", async () => {
    const request = deferred<ReturnType<typeof reply>>();
    const { user, input, getResponse } = setup(vi.fn(() => request.promise));

    await user.type(input, "  How do I avoid malaria?  {Enter}");

    // Question is trimmed, the box is cleared, and the first call has no session.
    expect(getResponse).toHaveBeenCalledWith("How do I avoid malaria?");
    expect(input).toHaveValue("");
    expect(screen.getByText("How do I avoid malaria?")).toBeInTheDocument();
    // Pending turn (the send button's spinner is also role=status, so match text).
    expect(screen.getByText("Searching your content...")).toBeInTheDocument();

    await act(async () => request.resolve(reply()));

    expect(
      screen.queryByText("Searching your content..."),
    ).not.toBeInTheDocument();
    expect(screen.getByText("bed net").tagName).toBe("STRONG");

    // Sources are collapsed under a summary line; expand to see them in rank order.
    await user.click(screen.getByText("Used 2 content cards"));
    const first = screen.getByText("First card");
    const second = screen.getByText("Second card");
    expect(
      first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("Shift+Enter adds a new line instead of sending", async () => {
    const { user, input, getResponse } = setup();
    await user.type(input, "line one{Shift>}{Enter}{/Shift}line two");
    expect(getResponse).not.toHaveBeenCalled();
    expect(input).toHaveValue("line one\nline two");
  });

  it("reuses the session id for follow-up questions and resets on New chat", async () => {
    const getResponse = vi.fn().mockResolvedValue(reply());
    const { user, input } = setup(getResponse);

    await user.type(input, "First?");
    // Submit via the send button this time.
    await user.click(screen.getByRole("button", { name: "Send question" }));
    await screen.findByText("bed net");

    await user.type(input, "Second?{Enter}");
    await waitFor(() =>
      expect(getResponse).toHaveBeenLastCalledWith("Second?", 42),
    );

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "New chat" })).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "New chat" }));
    expect(screen.getByText("Start a test conversation")).toBeInTheDocument();

    // After reset the next question starts a new session.
    await user.type(input, "Third?{Enter}");
    await waitFor(() => expect(getResponse).toHaveBeenLastCalledWith("Third?"));
  });

  it("handles a reply with no answer text and a single source", async () => {
    const getResponse = vi.fn().mockResolvedValue(
      reply({
        llm_response: null,
        search_results: {
          "0": { id: 1, title: "Only card", text: "t", distance: 0 },
        },
      }),
    );
    const { user, input } = setup(getResponse);

    await user.type(input, "Anything?{Enter}");

    expect(
      await screen.findByText("No answer text was returned."),
    ).toBeInTheDocument();
    expect(screen.getByText("Used 1 content card")).toBeInTheDocument();
    // Nothing to copy when there's no answer.
    expect(
      screen.queryByRole("button", { name: "Copy answer" }),
    ).not.toBeInTheDocument();
  });

  it("handles a reply without search results", async () => {
    const getResponse = vi
      .fn()
      .mockResolvedValue(reply({ search_results: undefined }));
    const { user, input } = setup(getResponse);

    await user.type(input, "Anything?{Enter}");

    await screen.findByText("bed net");
    expect(screen.queryByText(/Used \d+ content/)).not.toBeInTheDocument();
  });

  it("shows the failure in the thread and reports it", async () => {
    const getResponse = vi.fn().mockRejectedValue({ message: "Service down" });
    const { user, input, setSnackMessage } = setup(getResponse);

    await user.type(input, "Hello?{Enter}");

    expect(
      await screen.findByText(/The chat service couldn't answer this/),
    ).toBeInTheDocument();
    expect(setSnackMessage).toHaveBeenCalledWith("Service down");
    // Error replies can't be copied, but the raw response is still available.
    expect(
      screen.queryByRole("button", { name: "Copy answer" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "View raw response" }));
    expect(
      await screen.findByRole("dialog", { name: "Raw response" }),
    ).toHaveTextContent("Service down");
  });

  it("copies the answer and briefly shows Copied", async () => {
    const getResponse = vi.fn().mockResolvedValue(reply());
    const { user, input } = setup(getResponse);
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    await user.type(input, "Copy me{Enter}");
    await screen.findByText("bed net");

    // Fake timers only from here, so the 1.5s "Copied" reset can be skipped.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await user.click(screen.getByRole("button", { name: "Copy answer" }));

    expect(writeText).toHaveBeenCalledWith("Use a **bed net** every night.");
    expect(
      await screen.findByRole("button", { name: "Copied" }),
    ).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(1600);
    });
    expect(
      screen.getByRole("button", { name: "Copy answer" }),
    ).toBeInTheDocument();
  });
});
