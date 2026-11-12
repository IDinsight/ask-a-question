import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { UDSidebar } from "@/components/features/urgency-rules/components/UDSidebar";
import type { UrgencyDetectionResponse } from "@/components/features/urgency-rules/types";

// TestSidebar (rendered for real) reads the token from useAuth, which throws
// outside an AuthProvider. Stub just the hook rather than the whole provider.
vi.mock("@/utils/auth", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

const renderSidebar = (
  onDetect: (message: string) => Promise<UrgencyDetectionResponse>,
  canDetect = true,
) => {
  const closeSidebar = vi.fn();
  render(
    <UDSidebar closeSidebar={closeSidebar} onDetect={onDetect} canDetect={canDetect} />,
  );
  return { closeSidebar };
};

const ask = async (user: ReturnType<typeof userEvent.setup>, text: string) => {
  await user.type(screen.getByRole("textbox", { name: "Question" }), text);
  await user.click(screen.getByRole("button", { name: "Send question" }));
};

describe("UDSidebar", () => {
  it("shows the empty state before anything is sent", () => {
    renderSidebar(vi.fn());
    expect(screen.getByText("Test Urgency Detection")).toBeInTheDocument();
    expect(screen.getByText("Test your rules")).toBeInTheDocument();
  });

  it("calls closeSidebar from the close button", async () => {
    const user = userEvent.setup();
    const { closeSidebar } = renderSidebar(vi.fn());
    await user.click(screen.getByRole("button", { name: "Close Test Urgency Detection" }));
    expect(closeSidebar).toHaveBeenCalledOnce();
  });

  it("shows a loading status while the request is in flight", async () => {
    const user = userEvent.setup();
    // Never-resolving promise keeps the panel in its loading state.
    renderSidebar(() => new Promise(() => {}));
    await ask(user, "help");
    // The send button's Spinner is also role="status", so match by text.
    expect(screen.getByText("Checking your rules...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send question" })).toBeDisabled();
  });

  it("renders an urgent result with a single matched rule", async () => {
    const user = userEvent.setup();
    const onDetect = vi.fn().mockResolvedValue({
      is_urgent: true,
      matched_rules: ["Mentions bleeding"],
    });
    renderSidebar(onDetect);
    await ask(user, "I am bleeding");

    expect(onDetect).toHaveBeenCalledWith("I am bleeding");
    expect(await screen.findByText("Urgent")).toBeInTheDocument();
    expect(screen.getByText(/1 rule matched/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Matched rule" })).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Mentions bleeding");
  });

  it("pluralises when several rules match", async () => {
    const user = userEvent.setup();
    renderSidebar(
      vi.fn().mockResolvedValue({ is_urgent: true, matched_rules: ["Rule A", "Rule B"] }),
    );
    await ask(user, "x");

    expect(await screen.findByText(/2 rules matched/)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Matched rules (2)" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders a not-urgent result and tolerates a missing matched_rules list", async () => {
    const user = userEvent.setup();
    renderSidebar(vi.fn().mockResolvedValue({ is_urgent: false }));
    await ask(user, "hello");

    expect(await screen.findByText("Not urgent")).toBeInTheDocument();
    expect(screen.getByText("No rules matched this message.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("shows the error message when the request fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => {});
    renderSidebar(vi.fn().mockRejectedValue(new Error("Server down")));
    await ask(user, "x");

    expect(await screen.findByText("Request failed")).toBeInTheDocument();
    expect(screen.getByText("Server down")).toBeInTheDocument();
  });

  it("falls back to a generic message for an error without text", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => {});
    renderSidebar(vi.fn().mockRejectedValue(new Error("")));
    await ask(user, "x");

    expect(
      await screen.findByText("The urgency detection request failed."),
    ).toBeInTheDocument();
  });

  it("does nothing when detection isn't allowed yet", async () => {
    const user = userEvent.setup();
    const onDetect = vi.fn();
    renderSidebar(onDetect, false);
    await ask(user, "x");

    expect(onDetect).not.toHaveBeenCalled();
    expect(screen.getByText("Test your rules")).toBeInTheDocument();
  });

  it("opens the raw JSON dialog from the result", async () => {
    const user = userEvent.setup();
    renderSidebar(
      vi.fn().mockResolvedValue({ is_urgent: false, matched_rules: [], extra: "raw-field" }),
    );
    await ask(user, "x");

    await user.click(await screen.findByRole("button", { name: "View raw response" }));
    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    expect(screen.getByRole("dialog")).toHaveTextContent("raw-field");
  });
});
