import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import {
  KeyRenewConfirmationModal,
  NewKeyModal,
} from "@/components/features/integrations/components/APIKeyModals";

describe("KeyRenewConfirmationModal", () => {
  const renderModal = (
    overrides: Partial<{ isLoading: boolean; open: boolean }> = {},
  ) => {
    const onClose = vi.fn();
    const onRenew = vi.fn();
    render(
      <KeyRenewConfirmationModal
        open={overrides.open ?? true}
        currentKey="test-key"
        onClose={onClose}
        onRenew={onRenew}
        isLoading={overrides.isLoading ?? false}
      />,
    );
    return { onClose, onRenew };
  };

  it("shows the start of the current key in the warning", () => {
    renderModal();
    expect(
      screen.getByRole("alertdialog", {
        name: "Regenerate the workspace API key?",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("test-key")).toBeInTheDocument();
  });

  it("calls onRenew when confirming", async () => {
    const user = userEvent.setup();
    const { onRenew } = renderModal();

    await user.click(screen.getByRole("button", { name: "Generate new key" }));

    expect(onRenew).toHaveBeenCalledOnce();
  });

  it("calls onClose when cancelled", async () => {
    const user = userEvent.setup();
    const { onClose, onRenew } = renderModal();

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledOnce();
    expect(onRenew).not.toHaveBeenCalled();
  });

  it("disables both buttons and shows progress while loading", () => {
    renderModal({ isLoading: true });

    expect(screen.getByRole("button", { name: /Generating…/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });

  it("renders nothing when closed", () => {
    renderModal({ open: false });
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});

describe("NewKeyModal", () => {
  const renderModal = () => {
    const onCopy = vi.fn();
    const onClose = vi.fn();
    render(
      <NewKeyModal
        newKey="test-key-123"
        open
        onCopy={onCopy}
        onClose={onClose}
      />,
    );
    return { onCopy, onClose };
  };

  // The shared Dialog also renders a corner "X" with the sr-only label "Close";
  // the footer button is the one without data-slot="dialog-close".
  const footerClose = () =>
    screen
      .getAllByRole("button", { name: "Close" })
      .find((el) => el.getAttribute("data-slot") !== "dialog-close")!;

  it("shows the new key in a read-only field", () => {
    renderModal();
    const input = screen.getByRole("textbox", { name: "New API key" });
    expect(input).toHaveValue("test-key-123");
    expect(input).toHaveAttribute("readonly");
  });

  it("selects the key when the field gets focus", () => {
    renderModal();
    const input = screen.getByRole<HTMLInputElement>("textbox", {
      name: "New API key",
    });

    input.blur();
    input.focus();

    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe("test-key-123".length);
  });

  it("calls onCopy and flips the button to Copied", async () => {
    const user = userEvent.setup();
    const { onCopy } = renderModal();

    await user.click(screen.getByRole("button", { name: "Copy" }));

    expect(onCopy).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("calls onClose from the footer button", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal();

    await user.click(footerClose());

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose from the corner X", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal();

    const cornerX = screen
      .getAllByRole("button", { name: "Close" })
      .find((el) => el.getAttribute("data-slot") === "dialog-close")!;
    await user.click(cornerX);

    expect(onClose).toHaveBeenCalledOnce();
  });
});
