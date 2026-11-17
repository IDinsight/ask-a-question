import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import UserCreateModal from "@/components/features/workspace-management/components/UserWorkspaceModal";
import type { UserBody } from "@/components/features/workspace-management/types";

type Props = React.ComponentProps<typeof UserCreateModal>;

const existingMember: UserBody = {
  username: "member@example.com",
  role: "read_only",
};

const renderModal = (overrides: Partial<Props> = {}) => {
  const props: Props = {
    open: true,
    onClose: vi.fn(),
    adminUsername: "admin@example.com",
    checkUserExists: vi.fn().mockResolvedValue(true),
    addUserToWorkspace: vi.fn().mockResolvedValue(undefined),
    createUser: vi.fn().mockResolvedValue({}),
    editUser: vi.fn().mockResolvedValue(undefined),
    formType: "create",
    users: [existingMember],
    setSnackMessage: vi.fn(),
    onContinue: vi.fn(),
    ...overrides,
  };
  const utils = render(<UserCreateModal {...props} />);
  return { props, ...utils };
};

// Inputs are labelled via <label htmlFor>, so query by label text.
const usernameInput = () => screen.getByLabelText("Username");
const passwordInput = () => screen.getByLabelText("Password");
const confirmInput = () => screen.getByLabelText("Confirm password");
const roleSelect = () => screen.getByLabelText("Role");

describe("UserWorkspaceModal", () => {
  describe("create", () => {
    it("shows the create form with password and role fields", () => {
      renderModal();
      expect(screen.getByText("Create a user")).toBeInTheDocument();
      expect(passwordInput()).toBeInTheDocument();
      expect(roleSelect()).toHaveValue("read_only");
    });

    it("requires a username", async () => {
      const user = userEvent.setup();
      const { props } = renderModal();
      await user.click(screen.getByRole("button", { name: "Create user" }));
      expect(screen.getByText("Username is required.")).toBeInTheDocument();
      expect(props.createUser).not.toHaveBeenCalled();
    });

    it("requires a password", async () => {
      const user = userEvent.setup();
      renderModal();
      await user.type(usernameInput(), "new@example.com");
      await user.click(screen.getByRole("button", { name: "Create user" }));
      expect(screen.getByText("Password is required.")).toBeInTheDocument();
    });

    it("clears both password fields when they don't match", async () => {
      const user = userEvent.setup();
      renderModal();
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "pw-one");
      await user.type(confirmInput(), "pw-two");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
      expect(passwordInput()).toHaveValue("");
      expect(confirmInput()).toHaveValue("");
    });

    it("creates the user, hands back recovery codes, notifies and closes", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        createUser: vi.fn().mockResolvedValue({ recovery_codes: ["c1", "c2"] }),
      });
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.selectOptions(roleSelect(), "admin");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      expect(props.createUser).toHaveBeenCalledWith(
        "new@example.com",
        "placeholder-pw",
        "admin",
      );
      expect(props.onContinue).toHaveBeenCalledWith(["c1", "c2"]);
      expect(props.setSnackMessage).toHaveBeenCalledWith({
        message: "User successfully created",
        severity: "success",
      });
      // onClose fires after a 300ms delay.
      await waitFor(() => expect(props.onClose).toHaveBeenCalledOnce());
    });

    it("skips onContinue when no recovery codes come back", async () => {
      const user = userEvent.setup();
      const { props } = renderModal();
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      await waitFor(() => expect(props.setSnackMessage).toHaveBeenCalled());
      expect(props.onContinue).not.toHaveBeenCalled();
    });

    it("shows a spinner and disables actions while saving", async () => {
      const user = userEvent.setup();
      renderModal({
        createUser: vi.fn(
          () => new Promise<{ recovery_codes?: string[] }>(() => {}),
        ),
      });
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      expect(
        screen.getByRole("button", { name: /Create user/ }),
      ).toBeDisabled();
      expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    });

    it.each([
      [{ message: "Username taken" }, "Username taken"],
      [{}, "Error processing request"],
    ])("shows the request error (%o)", async (rejection, text) => {
      const user = userEvent.setup();
      renderModal({ createUser: vi.fn().mockRejectedValue(rejection) });
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      expect(await screen.findByText(text)).toBeInTheDocument();
    });

    it("shows nothing when the rejection carries no error", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        createUser: vi.fn().mockRejectedValue(undefined),
      });
      await user.type(usernameInput(), "new@example.com");
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(screen.getByRole("button", { name: "Create user" }));

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: "Create user" }),
        ).toBeEnabled(),
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(props.setSnackMessage).not.toHaveBeenCalled();
    });

    it("Cancel resets the form and calls onClose", async () => {
      const user = userEvent.setup();
      const { props } = renderModal();
      await user.type(usernameInput(), "typed@example.com");
      await user.click(screen.getByRole("button", { name: "Cancel" }));

      expect(props.onClose).toHaveBeenCalledOnce();
      expect(usernameInput()).toHaveValue("");
    });

    it("Escape closes via the dialog's onOpenChange", async () => {
      const user = userEvent.setup();
      const { props } = renderModal();
      await user.keyboard("{Escape}");
      expect(props.onClose).toHaveBeenCalledOnce();
    });
  });

  describe("add", () => {
    it("keeps the submit disabled until the username is verified", async () => {
      const user = userEvent.setup();
      renderModal({ formType: "add" });
      expect(screen.getByText("Add an existing user")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Verify" })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "Add to workspace" }),
      ).toBeDisabled();
      expect(screen.queryByLabelText("Role")).not.toBeInTheDocument();

      // Enter in the field submits the form, which the guard ignores when unverified.
      await user.type(usernameInput(), "someone@example.com{Enter}");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("verifies an existing user and adds them with the chosen role", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({ formType: "add" });
      await user.type(usernameInput(), "someone@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));

      expect(props.checkUserExists).toHaveBeenCalledWith("someone@example.com");
      expect(await screen.findByText("Verified")).toBeInTheDocument();
      expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();

      await user.selectOptions(roleSelect(), "admin");
      await user.click(
        screen.getByRole("button", { name: "Add to workspace" }),
      );

      expect(props.addUserToWorkspace).toHaveBeenCalledWith(
        "someone@example.com",
        "admin",
      );
      expect(props.setSnackMessage).toHaveBeenCalledWith({
        message: "User successfully added",
        severity: "success",
      });
    });

    it("offers to create a user that doesn't exist yet", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        formType: "add",
        checkUserExists: vi.fn().mockResolvedValue(false),
        createUser: vi.fn().mockResolvedValue({ recovery_codes: ["r1"] }),
      });
      await user.type(usernameInput(), "fresh@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));

      expect(
        await screen.findByText(
          "User fresh@example.com does not exist. You can create it below.",
        ),
      ).toBeInTheDocument();
      await user.type(passwordInput(), "placeholder-pw");
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(
        screen.getByRole("button", { name: "Add to workspace" }),
      );

      expect(props.createUser).toHaveBeenCalledWith(
        "fresh@example.com",
        "placeholder-pw",
        "read_only",
      );
      expect(props.onContinue).toHaveBeenCalledWith(["r1"]);
    });

    it("skips onContinue when creating via add returns no codes", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        formType: "add",
        checkUserExists: vi.fn().mockResolvedValue(false),
      });
      await user.type(usernameInput(), "fresh@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      await user.type(
        await screen.findByLabelText("Password"),
        "placeholder-pw",
      );
      await user.type(confirmInput(), "placeholder-pw");
      await user.click(
        screen.getByRole("button", { name: "Add to workspace" }),
      );

      await waitFor(() => expect(props.createUser).toHaveBeenCalled());
      expect(props.onContinue).not.toHaveBeenCalled();
    });

    // Regression: possible-bugs.md #1. Creating a new user from "add" mode
    // used to skip the password checks and send a blank or mismatched password.
    it("requires a password when creating a new user from add", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        formType: "add",
        checkUserExists: vi.fn().mockResolvedValue(false),
      });
      await user.type(usernameInput(), "fresh@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      await screen.findByLabelText("Password");
      await user.click(
        screen.getByRole("button", { name: "Add to workspace" }),
      );

      expect(screen.getByText("Password is required.")).toBeInTheDocument();
      expect(props.createUser).not.toHaveBeenCalled();
    });

    it("rejects mismatched passwords when creating a new user from add", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({
        formType: "add",
        checkUserExists: vi.fn().mockResolvedValue(false),
      });
      await user.type(usernameInput(), "fresh@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      await user.type(await screen.findByLabelText("Password"), "pw-one");
      await user.type(confirmInput(), "pw-two");
      await user.click(
        screen.getByRole("button", { name: "Add to workspace" }),
      );

      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
      expect(passwordInput()).toHaveValue("");
      expect(confirmInput()).toHaveValue("");
      expect(props.createUser).not.toHaveBeenCalled();
    });

    it("refuses a user already in the workspace", async () => {
      const user = userEvent.setup();
      renderModal({ formType: "add" });
      await user.type(usernameInput(), existingMember.username);
      await user.click(screen.getByRole("button", { name: "Verify" }));

      expect(
        await screen.findByText(
          `User ${existingMember.username} is already in the workspace.`,
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Add to workspace" }),
      ).toBeDisabled();
    });

    it("shows a spinner on Verify while checking", async () => {
      const user = userEvent.setup();
      renderModal({
        formType: "add",
        checkUserExists: vi.fn(() => new Promise<boolean>(() => {})),
      });
      await user.type(usernameInput(), "x@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      expect(screen.getByRole("button", { name: /Verify/ })).toBeDisabled();
    });

    it("reports a verification failure", async () => {
      const user = userEvent.setup();
      renderModal({
        formType: "add",
        checkUserExists: vi.fn().mockRejectedValue(new Error("network")),
      });
      await user.type(usernameInput(), "x@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      expect(
        await screen.findByText("Error verifying user."),
      ).toBeInTheDocument();
    });

    it("editing the username after verifying asks to verify again", async () => {
      const user = userEvent.setup();
      renderModal({ formType: "add" });
      await user.type(usernameInput(), "someone@example.com");
      await user.click(screen.getByRole("button", { name: "Verify" }));
      await screen.findByText("Verified");

      await user.type(usernameInput(), "x");
      expect(screen.getByRole("button", { name: "Verify" })).toBeEnabled();
      expect(
        screen.getByRole("button", { name: "Add to workspace" }),
      ).toBeDisabled();
    });
  });

  describe("edit", () => {
    const editing: UserBody = { username: "member@example.com", role: "admin" };

    it("prefills the user, locks the username and saves the new role", async () => {
      const user = userEvent.setup();
      const { props } = renderModal({ formType: "edit", user: editing });

      expect(screen.getByText("Edit user")).toBeInTheDocument();
      expect(usernameInput()).toHaveValue("member@example.com");
      expect(usernameInput()).toBeDisabled();
      expect(roleSelect()).toHaveValue("admin");
      expect(roleSelect()).toBeEnabled();

      await user.selectOptions(roleSelect(), "read_only");
      await user.click(screen.getByRole("button", { name: "Save" }));

      expect(props.editUser).toHaveBeenCalledWith(
        "member@example.com",
        "read_only",
      );
      expect(props.setSnackMessage).toHaveBeenCalledWith({
        message: "User successfully edited",
        severity: "success",
      });
    });

    it("locks the role when admins edit themselves", () => {
      renderModal({
        formType: "edit",
        user: { username: "admin@example.com", role: "admin" },
      });
      expect(roleSelect()).toBeDisabled();
      expect(
        screen.getByText("You can’t change your own role."),
      ).toBeInTheDocument();
    });

    it("hides the role field for a user without a role", () => {
      // Shouldn't happen per the type, but the component guards for it.
      renderModal({
        formType: "edit",
        user: { username: "member@example.com" } as UserBody,
      });
      expect(screen.queryByLabelText("Role")).not.toBeInTheDocument();
    });

    it("reports a missing editUser handler", async () => {
      const user = userEvent.setup();
      renderModal({ formType: "edit", user: editing, editUser: undefined });
      await user.click(screen.getByRole("button", { name: "Save" }));
      expect(
        await screen.findByText("Edit user function is not defined."),
      ).toBeInTheDocument();
    });
  });
});
