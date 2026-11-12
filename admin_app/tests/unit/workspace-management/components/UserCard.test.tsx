import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { UserCard } from "@/components/features/workspace-management/components/UserCard";

const renderCard = (overrides: Partial<React.ComponentProps<typeof UserCard>> = {}) => {
  const props = {
    adminUsername: "admin user",
    userId: 7,
    username: "jane doe",
    userRole: "read_only" as const,
    onRemoveUser: vi.fn(),
    onEditUser: vi.fn(),
    ...overrides,
  };
  // UserCard renders an <li>, so give it a list parent for valid markup.
  render(
    <ul>
      <UserCard {...props} />
    </ul>,
  );
  return props;
};

describe("UserCard", () => {
  it("shows initials, name and a read-only role", () => {
    renderCard();
    expect(screen.getByText("JD")).toBeInTheDocument();
    expect(screen.getByText("jane doe")).toBeInTheDocument();
    expect(screen.getByText("Read only")).toBeInTheDocument();
    expect(screen.queryByText("(You)")).not.toBeInTheDocument();
  });

  it("marks the signed-in admin as (You) with the Admin role", () => {
    renderCard({ username: "admin user", userRole: "admin" });
    expect(screen.getByText("(You)")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("calls onEditUser from the edit button", async () => {
    const user = userEvent.setup();
    const props = renderCard();
    await user.click(screen.getByRole("button", { name: "Edit jane doe" }));
    expect(props.onEditUser).toHaveBeenCalledOnce();
  });

  it("asks for confirmation, then removes the user", async () => {
    const user = userEvent.setup();
    const props = renderCard();
    await user.click(
      screen.getByRole("button", { name: "Remove jane doe from workspace" }),
    );

    expect(
      await screen.findByText("Remove jane doe from this workspace?"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove" }));

    expect(props.onRemoveUser).toHaveBeenCalledWith(7);
    await waitFor(() =>
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
    );
  });

  it("cancelling the confirmation doesn't remove anyone", async () => {
    const user = userEvent.setup();
    const props = renderCard();
    await user.click(
      screen.getByRole("button", { name: "Remove jane doe from workspace" }),
    );
    await user.click(await screen.findByRole("button", { name: "Cancel" }));

    expect(props.onRemoveUser).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
    );
  });
});
