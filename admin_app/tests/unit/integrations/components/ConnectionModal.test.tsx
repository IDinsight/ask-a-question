import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import ChatManagerModal from "@/components/features/integrations/components/ConnectionModal";

const Guide = () => <p>Step one: do the thing.</p>;

describe("ChatManagerModal", () => {
  it("titles the dialog with the connection name and renders its guide", () => {
    render(
      <ChatManagerModal
        name="Typebot"
        logo={<span data-testid="logo" />}
        ModalContent={Guide}
        open
        onClose={() => {}}
      />,
    );

    expect(
      screen.getByRole("dialog", { name: "Typebot setup guide" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("logo")).toBeInTheDocument();
    expect(screen.getByText("Step one: do the thing.")).toBeInTheDocument();
  });

  it("renders an empty body when there is no guide", () => {
    render(
      <ChatManagerModal name="" logo={null} ModalContent={null} open onClose={() => {}} />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByText("Step one: do the thing.")).not.toBeInTheDocument();
  });

  it("calls onClose when the dialog is dismissed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ChatManagerModal
        name="Turn"
        logo={null}
        ModalContent={Guide}
        open
        onClose={onClose}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(onClose).toHaveBeenCalledOnce();
  });
});
