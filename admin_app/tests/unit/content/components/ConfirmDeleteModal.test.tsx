import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ConfirmDeleteModal } from "@/components/features/content/components/ConfirmDeleteModal";

const setup = (count = 3) => {
  const onClose = vi.fn();
  const onConfirm = vi.fn();
  render(
    <ConfirmDeleteModal
      open
      onClose={onClose}
      onConfirm={onConfirm}
      selectedContentsCount={count}
    />,
  );
  const input = screen.getByLabelText(/to confirm/i);
  const deleteButton = screen.getByRole("button", { name: "Delete items" });
  return { onClose, onConfirm, input, deleteButton };
};

describe("ConfirmDeleteModal", () => {
  it("pluralises the count", () => {
    setup(3);
    expect(screen.getByText(/permanently delete/)).toHaveTextContent(
      "permanently delete 3 contents.",
    );
  });

  it("uses the singular for one item", () => {
    setup(1);
    expect(screen.getByText(/permanently delete/)).toHaveTextContent(
      "permanently delete 1 content.",
    );
  });

  it("keeps Delete disabled until 'delete' is typed (any case)", async () => {
    const user = userEvent.setup();
    const { input, deleteButton, onConfirm } = setup();

    expect(deleteButton).toBeDisabled();
    await user.type(input, "DeLeTe");
    expect(deleteButton).toBeEnabled();

    await user.click(deleteButton);
    expect(onConfirm).toHaveBeenCalledOnce();
    // The confirmation text resets after confirming.
    expect(input).toHaveValue("");
  });

  it("confirms with Enter only once the text matches", async () => {
    const user = userEvent.setup();
    const { input, onConfirm } = setup();

    await user.type(input, "del{Enter}");
    expect(onConfirm).not.toHaveBeenCalled();

    await user.type(input, "ete{Enter}");
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("clears the text and calls onClose on Cancel", async () => {
    const user = userEvent.setup();
    const { input, onClose, onConfirm } = setup();

    await user.type(input, "delete");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
    expect(input).toHaveValue("");
  });
});
