import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import WorkspaceCreateModal from "@/components/features/workspace-management/components/WorkspaceCreateModal";
import type { Workspace } from "@/components/features/workspace-management/types";

type Props = React.ComponentProps<typeof WorkspaceCreateModal>;

const renderModal = (overrides: Partial<Props> = {}) => {
  const props: Props = {
    open: true,
    onClose: vi.fn(),
    isEdit: false,
    onCreate: vi.fn(),
    loginWorkspace: vi.fn(),
    setSnackMessage: vi.fn(),
    ...overrides,
  };
  render(<WorkspaceCreateModal {...props} />);
  return props;
};

const nameInput = () => screen.getByRole("textbox", { name: "Workspace name" });

// The footer "Cancel" button; the shared Dialog's corner X is named "Close".
const cancelButton = () => screen.getByRole("button", { name: "Cancel" });

describe("WorkspaceCreateModal", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows create copy by default", () => {
    renderModal();
    expect(screen.getByText("Create a workspace")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument();
  });

  it("shows rename copy and prefills the name when editing", () => {
    renderModal({ isEdit: true, existingWorkspace: { workspace_name: "Old name" } });
    expect(screen.getByText("Rename workspace")).toBeInTheDocument();
    expect(nameInput()).toHaveValue("Old name");
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("flags an empty name and clears the flag once the user types", async () => {
    const user = userEvent.setup();
    const props = renderModal();
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(screen.getByText("Please enter a workspace name")).toBeInTheDocument();
    expect(nameInput()).toHaveAttribute("aria-invalid", "true");
    expect(props.onCreate).not.toHaveBeenCalled();

    await user.type(nameInput(), "a");
    expect(screen.queryByText("Please enter a workspace name")).not.toBeInTheDocument();
  });

  it("creates, logs in, notifies, then closes after a delay", async () => {
    // Fake timers for the 3s auto-close; userEvent must advance them.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const created: Workspace = { workspace_name: "Team A", workspace_id: 1 };
    const props = renderModal({ onCreate: vi.fn().mockResolvedValue(created) });

    await user.type(nameInput(), "  Team A  ");
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Name is trimmed before sending.
    expect(props.onCreate).toHaveBeenCalledWith({ workspace_name: "Team A" });
    expect(props.loginWorkspace).toHaveBeenCalledWith(created);
    expect(props.setSnackMessage).toHaveBeenCalledWith({
      message: "Workspace created successfully",
      severity: "success",
    });
    expect(props.onClose).not.toHaveBeenCalled();

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(props.onClose).toHaveBeenCalledOnce();
  });

  it("accepts a non-empty list response and reports an edit", async () => {
    const user = userEvent.setup();
    const ws: Workspace = { workspace_name: "Renamed" };
    const props = renderModal({
      isEdit: true,
      existingWorkspace: { workspace_name: "Old" },
      // The API sometimes returns a list; the component takes the first item.
      onCreate: vi.fn().mockResolvedValue([ws] as unknown as Workspace),
    });

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(props.loginWorkspace).toHaveBeenCalledWith(ws);
    expect(props.setSnackMessage).toHaveBeenCalledWith({
      message: "Workspace edited successfully",
      severity: "success",
    });
  });

  it("works without a setSnackMessage callback", async () => {
    const user = userEvent.setup();
    const props = renderModal({
      setSnackMessage: undefined,
      onCreate: vi.fn().mockResolvedValue({ workspace_name: "X" }),
    });
    await user.type(nameInput(), "X");
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(props.loginWorkspace).toHaveBeenCalled();
  });

  it("says the name is taken when the API returns an empty list", async () => {
    const user = userEvent.setup();
    const props = renderModal({
      onCreate: vi.fn().mockResolvedValue([] as unknown as Workspace),
    });
    await user.type(nameInput(), "Taken");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("Workspace name already exists")).toBeInTheDocument();
    expect(props.loginWorkspace).not.toHaveBeenCalled();
  });

  it("shows a generic error for an unexpected response", async () => {
    const user = userEvent.setup();
    renderModal({ onCreate: vi.fn().mockResolvedValue({} as Workspace) });
    await user.type(nameInput(), "X");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("Error creating workspace")).toBeInTheDocument();
  });

  it("shows the thrown error's message", async () => {
    const user = userEvent.setup();
    renderModal({ onCreate: vi.fn().mockRejectedValue({ message: "Quota reached" }) });
    await user.type(nameInput(), "X");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("Quota reached")).toBeInTheDocument();
  });

  it.each([
    [false, "Error creating workspace"],
    [true, "Error editing workspace"],
  ])("falls back to a default error when nothing useful is thrown (isEdit=%s)", async (isEdit, text) => {
    const user = userEvent.setup();
    renderModal({
      isEdit,
      existingWorkspace: { workspace_name: "W" },
      onCreate: vi.fn().mockRejectedValue(undefined),
    });
    await user.click(screen.getByRole("button", { name: isEdit ? "Save" : "Create" }));

    expect(await screen.findByText(text)).toBeInTheDocument();
  });

  it("Cancel clears the error and calls onClose", async () => {
    const user = userEvent.setup();
    const props = renderModal({ onCreate: vi.fn().mockRejectedValue({ message: "Boom" }) });
    await user.type(nameInput(), "X");
    await user.click(screen.getByRole("button", { name: "Create" }));
    await screen.findByText("Boom");

    await user.click(cancelButton());
    expect(props.onClose).toHaveBeenCalledOnce();
    expect(screen.queryByText("Boom")).not.toBeInTheDocument();
  });

  it("closing via Escape goes through the same close path", async () => {
    const user = userEvent.setup();
    const props = renderModal();
    await user.keyboard("{Escape}");
    expect(props.onClose).toHaveBeenCalledOnce();
  });
});
