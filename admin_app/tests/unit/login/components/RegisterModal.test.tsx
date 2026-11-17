import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import {
  AdminAlertModal,
  RegisterModal,
} from "@/components/features/login/components/RegisterModal";

describe("AdminAlertModal", () => {
  it("explains the setup step and continues on click", async () => {
    const user = userEvent.setup();
    const onContinue = vi.fn();
    render(<AdminAlertModal open onContinue={onContinue} onClose={vi.fn()} />);

    expect(
      screen.getByRole("dialog", { name: "Initial setup" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(onContinue).toHaveBeenCalledOnce();
  });

  it("calls onClose on Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<AdminAlertModal open onContinue={vi.fn()} onClose={onClose} />);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe("RegisterModal", () => {
  const setup = (
    registerUser = vi.fn().mockResolvedValue({ recovery_codes: [] }),
  ) => {
    const user = userEvent.setup();
    const onContinue = vi.fn();
    const onClose = vi.fn();
    render(
      <RegisterModal
        open
        registerUser={registerUser}
        onContinue={onContinue}
        onClose={onClose}
      />,
    );
    // Labels are unique, so getByLabelText finds the input for each.
    const fields = {
      username: screen.getByLabelText("Username"),
      password: screen.getByLabelText("Password"),
      confirm: screen.getByLabelText("Confirm password"),
    };
    const submit = () =>
      user.click(screen.getByRole("button", { name: "Register" }));
    return { user, registerUser, onContinue, onClose, fields, submit };
  };

  it("shows required-field errors and does not submit an empty form", async () => {
    const { submit, registerUser } = setup();

    await submit();

    expect(
      await screen.findByText("Username is required."),
    ).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(
      screen.getByText("Please confirm the password."),
    ).toBeInTheDocument();
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("flags mismatched passwords", async () => {
    const { user, fields, submit, registerUser } = setup();

    await user.type(fields.username, "admin");
    await user.type(fields.password, "pass-one");
    await user.type(fields.confirm, "pass-two");
    await submit();

    expect(
      await screen.findByText("Passwords do not match."),
    ).toBeInTheDocument();
    expect(fields.confirm).toHaveAttribute("aria-invalid", "true");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("registers with a trimmed username and hands back the recovery codes", async () => {
    const registerUser = vi
      .fn()
      .mockResolvedValue({ recovery_codes: ["code-1", "code-2"] });
    const { user, fields, submit, onContinue } = setup(registerUser);

    await user.type(fields.username, "  admin  ");
    await user.type(fields.password, "test-pass");
    await user.type(fields.confirm, "test-pass");
    await submit();

    expect(registerUser).toHaveBeenCalledWith("admin", "test-pass");
    expect(onContinue).toHaveBeenCalledWith(["code-1", "code-2"]);
  });

  it("passes an empty list when the response has no codes", async () => {
    const registerUser = vi.fn().mockResolvedValue(undefined);
    const { user, fields, submit, onContinue } = setup(registerUser);

    await user.type(fields.username, "admin");
    await user.type(fields.password, "test-pass");
    await user.type(fields.confirm, "test-pass");
    await submit();

    expect(onContinue).toHaveBeenCalledWith([]);
  });

  it("shows the API error message and stays open on failure", async () => {
    const registerUser = vi
      .fn()
      .mockRejectedValue({ status: 400, message: "Username already taken." });
    const { user, fields, submit, onContinue } = setup(registerUser);

    await user.type(fields.username, "admin");
    await user.type(fields.password, "test-pass");
    await user.type(fields.confirm, "test-pass");
    await submit();

    expect(
      await screen.findByText("Username already taken."),
    ).toBeInTheDocument();
    expect(onContinue).not.toHaveBeenCalled();
  });

  it("falls back to a generic message when the error has none", async () => {
    const registerUser = vi.fn().mockRejectedValue(new Error(""));
    const { user, fields, submit } = setup(registerUser);

    await user.type(fields.username, "admin");
    await user.type(fields.password, "test-pass");
    await user.type(fields.confirm, "test-pass");
    await submit();

    expect(
      await screen.findByText("Error processing request."),
    ).toBeInTheDocument();
  });

  it("disables Register while the request is in flight", async () => {
    // Keep the promise pending so the submitting state is visible.
    let resolve!: (v: unknown) => void;
    const registerUser = vi.fn(() => new Promise((r) => (resolve = r)));
    const { user, fields, submit } = setup(registerUser);

    await user.type(fields.username, "admin");
    await user.type(fields.password, "test-pass");
    await user.type(fields.confirm, "test-pass");
    await submit();

    expect(screen.getByRole("button", { name: /Register/ })).toBeDisabled();
    resolve({ recovery_codes: [] });
  });

  it("toggles both password fields between hidden and visible", async () => {
    const { user, fields } = setup();

    expect(fields.password).toHaveAttribute("type", "password");
    expect(fields.confirm).toHaveAttribute("type", "password");

    // Both fields render a toggle; either one flips them together.
    const [toggle] = screen.getAllByRole("button", { name: "Show passwords" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    await user.click(toggle);

    expect(fields.password).toHaveAttribute("type", "text");
    expect(fields.confirm).toHaveAttribute("type", "text");
    expect(
      screen.getAllByRole("button", { name: "Hide passwords" }),
    ).toHaveLength(2);
  });

  it("calls onClose on Escape", async () => {
    const { user, onClose } = setup();

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledOnce();
  });
});
