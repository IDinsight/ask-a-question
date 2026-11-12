import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ConfirmationModal } from "@/components/features/workspace-management/components/ConfirmationModal";

const codes = ["AAAA-1111", "BBBB-2222", "CCCC-3333"];

// The shared Dialog also renders a corner "X" button whose sr-only label is
// "Close", so pick the footer button by excluding that one (data-slot="dialog-close").
const footerButton = (name: string) =>
  screen
    .getAllByRole("button", { name })
    .find((el) => el.getAttribute("data-slot") !== "dialog-close")!;
const cornerCloseButton = () =>
  screen
    .getAllByRole("button", { name: "Close" })
    .find((el) => el.getAttribute("data-slot") === "dialog-close")!;

describe("ConfirmationModal", () => {
  it("lists every recovery code", () => {
    render(<ConfirmationModal open onClose={() => {}} recoveryCodes={codes} />);

    const list = screen.getByRole("list", { name: "Recovery codes" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual(codes);
  });

  it("uses the default title and close text unless overridden", () => {
    const { rerender } = render(
      <ConfirmationModal open onClose={() => {}} recoveryCodes={codes} />,
    );
    expect(screen.getByText("Admin User Created")).toBeInTheDocument();
    expect(footerButton("Close")).toBeInTheDocument();

    rerender(
      <ConfirmationModal
        open
        onClose={() => {}}
        recoveryCodes={codes}
        dialogTitle="Codes reset"
        closeButtonText="Done"
      />,
    );
    expect(screen.getByText("Codes reset")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Done" })).toBeInTheDocument();
  });

  it("copies all codes newline-separated and flips the button label", async () => {
    const user = userEvent.setup();
    // userEvent.setup() installs a clipboard stub; spy on it to check the payload.
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    render(<ConfirmationModal open onClose={() => {}} recoveryCodes={codes} />);
    await user.click(screen.getByRole("button", { name: "Copy codes" }));

    expect(writeText).toHaveBeenCalledWith(codes.join("\n"));
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("logs, but still shows Copied, when the clipboard write fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<ConfirmationModal open onClose={() => {}} recoveryCodes={codes} />);
    await user.click(screen.getByRole("button", { name: "Copy codes" }));

    expect(consoleError).toHaveBeenCalledWith(
      "Failed to copy recovery codes: ",
      expect.any(Error),
    );
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("calls onClose from the footer button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<ConfirmationModal open onClose={onClose} recoveryCodes={codes} />);
    await user.click(footerButton("Close"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose from the corner X (via onOpenChange)", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<ConfirmationModal open onClose={onClose} recoveryCodes={codes} />);
    await user.click(cornerCloseButton());

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders nothing when closed", () => {
    render(<ConfirmationModal open={false} onClose={() => {}} recoveryCodes={codes} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
