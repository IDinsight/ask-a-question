import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { FirstUserSetup } from "@/components/features/login/components/FirstUserSetup";

const codes = ["code-aaaa", "code-bbbb"];

// Walks the flow from the alert to the recovery-codes dialog.
async function goToCodes(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await user.type(screen.getByLabelText("Username"), "admin");
  await user.type(screen.getByLabelText("Password"), "test-pass");
  await user.type(screen.getByLabelText("Confirm password"), "test-pass");
  await user.click(screen.getByRole("button", { name: "Register" }));
  await screen.findByRole("dialog", { name: "Admin user created" });
}

describe("FirstUserSetup", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows nothing when registration isn't required", () => {
    render(<FirstUserSetup requireRegister={false} registerUser={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the alert once the check says registration is required", () => {
    const { rerender } = render(
      <FirstUserSetup requireRegister={false} registerUser={vi.fn()} />,
    );
    rerender(<FirstUserSetup requireRegister registerUser={vi.fn()} />);
    expect(screen.getByRole("dialog", { name: "Initial setup" })).toBeInTheDocument();
  });

  it("walks alert → register → recovery codes → back to sign in", async () => {
    const user = userEvent.setup();
    const registerUser = vi.fn().mockResolvedValue({ recovery_codes: codes });
    render(<FirstUserSetup requireRegister registerUser={registerUser} />);

    await goToCodes(user);

    expect(registerUser).toHaveBeenCalledWith("admin", "test-pass");
    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual(codes);

    await user.click(screen.getByRole("button", { name: "Back to sign in" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ends the flow when the alert is closed", async () => {
    const user = userEvent.setup();
    render(<FirstUserSetup requireRegister registerUser={vi.fn()} />);

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ends the flow when the register dialog is closed", async () => {
    const user = userEvent.setup();
    render(<FirstUserSetup requireRegister registerUser={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByRole("dialog", { name: "Register first user" });
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ends the flow when the codes dialog is closed with Escape", async () => {
    const user = userEvent.setup();
    render(
      <FirstUserSetup
        requireRegister
        registerUser={vi.fn().mockResolvedValue({ recovery_codes: codes })}
      />,
    );
    await goToCodes(user);

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("copies the codes newline-separated and resets the label after 5s", async () => {
    const user = userEvent.setup();
    render(
      <FirstUserSetup
        requireRegister
        registerUser={vi.fn().mockResolvedValue({ recovery_codes: codes })}
      />,
    );
    await goToCodes(user);
    const writeText = vi.spyOn(navigator.clipboard, "writeText");

    // Switch to fake timers only for the reset timer; the clipboard stub is
    // already installed. shouldAdvanceTime keeps userEvent's own delays moving.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await user.click(screen.getByRole("button", { name: "Copy codes" }));

    expect(writeText).toHaveBeenCalledWith(codes.join("\n"));
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(screen.getByRole("button", { name: "Copy codes" })).toBeInTheDocument();
  });

  it("logs and keeps the label when the clipboard is blocked", async () => {
    const user = userEvent.setup();
    render(
      <FirstUserSetup
        requireRegister
        registerUser={vi.fn().mockResolvedValue({ recovery_codes: codes })}
      />,
    );
    await goToCodes(user);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("blocked"));
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    await user.click(screen.getByRole("button", { name: "Copy codes" }));

    expect(consoleError).toHaveBeenCalledWith(
      "Failed to copy recovery codes:",
      expect.any(Error),
    );
    expect(screen.getByRole("button", { name: "Copy codes" })).toBeInTheDocument();
  });
});
