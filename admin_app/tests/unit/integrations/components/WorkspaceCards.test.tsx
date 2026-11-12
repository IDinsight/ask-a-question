import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { ComponentProps } from "react";

import {
  DailyLimit,
  KeyManagement,
} from "@/components/features/integrations/components/WorkspaceCards";

type KeyProps = ComponentProps<typeof KeyManagement>;

const renderKey = (overrides: Partial<KeyProps> = {}) => {
  const props: KeyProps = {
    workspace: { keyStart: "test-k", keyUpdated: "1 Jan 2026" },
    isGenerating: false,
    confirmationOpen: false,
    onOpenConfirmation: vi.fn(),
    onCloseConfirmation: vi.fn(),
    onRenew: vi.fn(),
    newKey: "",
    newKeyOpen: false,
    onCloseNewKey: vi.fn(),
    ...overrides,
  };
  render(<KeyManagement {...props} />);
  return props;
};

describe("KeyManagement", () => {
  it("shows loading placeholders until the workspace is known", () => {
    renderKey({ workspace: undefined });

    expect(
      screen.getByRole("status", { name: "Checking for current API key" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows the masked key, last-updated date and a regenerate button", async () => {
    const user = userEvent.setup();
    const props = renderKey();

    expect(screen.getByRole("region", { name: "Workspace API key" })).toBeInTheDocument();
    expect(screen.getByText("test-k")).toBeInTheDocument();
    expect(screen.getByText("(rest of key hidden)")).toBeInTheDocument();
    expect(screen.getByText("Last updated 1 Jan 2026")).toBeInTheDocument();
    expect(screen.getByText(/immediately invalidates the old one/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Regenerate key" }));
    expect(props.onOpenConfirmation).toHaveBeenCalledOnce();
  });

  it("omits the last-updated line when the date is missing", () => {
    renderKey({ workspace: { keyStart: "test-k", keyUpdated: null as never } });
    expect(screen.queryByText(/Last updated/)).not.toBeInTheDocument();
  });

  it("disables regenerate while a key is being generated", () => {
    renderKey({ isGenerating: true });
    expect(screen.getByRole("button", { name: "Regenerate key" })).toBeDisabled();
  });

  it("offers to generate the first key when none exists", async () => {
    const user = userEvent.setup();
    const props = renderKey({ workspace: { keyStart: "", keyUpdated: "" } });

    expect(screen.getByText(/doesn’t have an API key yet/)).toBeInTheDocument();
    expect(screen.getByText(/You’ll see the full key once/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate key" }));
    expect(props.onRenew).toHaveBeenCalledOnce();
  });

  it("disables the first-key button while generating", () => {
    renderKey({ workspace: { keyStart: "", keyUpdated: "" }, isGenerating: true });
    // The Spinner carries its own accessible label, so match the name loosely.
    expect(screen.getByRole("button", { name: /Generate key/ })).toBeDisabled();
  });

  it("wires the confirmation dialog to onRenew and onCloseConfirmation", async () => {
    const user = userEvent.setup();
    const props = renderKey({ confirmationOpen: true });

    await user.click(screen.getByRole("button", { name: "Generate new key" }));
    expect(props.onRenew).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onCloseConfirmation).toHaveBeenCalledOnce();
  });

  it("copies the new key to the clipboard from the new-key dialog", async () => {
    const user = userEvent.setup();
    // userEvent.setup() installs a clipboard stub; spy on it to check the payload.
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    renderKey({ newKey: "test-key-123", newKeyOpen: true });

    await user.click(screen.getByRole("button", { name: "Copy" }));

    expect(writeText).toHaveBeenCalledWith("test-key-123");
  });
});

describe("DailyLimit", () => {
  it("shows a placeholder while loading", () => {
    render(<DailyLimit quota={undefined} />);
    expect(screen.queryByText(/requests|No daily limit/)).not.toBeInTheDocument();
  });

  it("shows the formatted limit per day", () => {
    render(<DailyLimit quota={12000} />);
    expect(screen.getByText(`${(12000).toLocaleString()} requests`)).toBeInTheDocument();
    expect(screen.getByText("per day")).toBeInTheDocument();
  });

  it("says there is no limit when the quota is null", () => {
    render(<DailyLimit quota={null} />);
    expect(screen.getByText("No daily limit")).toBeInTheDocument();
    expect(screen.queryByText("per day")).not.toBeInTheDocument();
  });

  it("links to the contact page", () => {
    render(<DailyLimit quota={null} />);
    expect(screen.getByRole("link", { name: "Contact us" })).toHaveAttribute(
      "href",
      expect.stringContaining("contact_us"),
    );
  });
});
