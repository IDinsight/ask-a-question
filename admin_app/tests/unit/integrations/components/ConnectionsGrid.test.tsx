import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ConnectionsGrid from "@/components/features/integrations/components/ConnectionsGrid";

// Image imports resolve to Next-style { src } objects via the nextStaticImages
// plugin in vitest.config.mts, with src = the asset's repo-relative path.

describe("ConnectionsGrid", () => {
  it("shows a card per connection", () => {
    render(<ConnectionsGrid />);

    const cards = screen.getAllByRole("button", { name: /view setup guide/ });
    expect(cards.map((c) => c.getAttribute("aria-label"))).toEqual([
      "Typebot: view setup guide",
      "Turn: view setup guide",
      "Glific: view setup guide",
      "REST API: view setup guide",
    ]);
  });

  it("uses logo images, except REST API which has none", () => {
    const { container } = render(<ConnectionsGrid />);
    // Logos are decorative (alt=""), so query the DOM rather than by role.
    const srcs = Array.from(container.querySelectorAll("img")).map((img) =>
      img.getAttribute("src"),
    );
    expect(srcs).toEqual([
      "/src/components/features/integrations/assets/typebot_logo.svg",
      "/src/components/features/integrations/assets/turn_logo.png",
      "/src/components/features/integrations/assets/glific_logo.png",
    ]);
  });

  it("opens the matching setup guide and closes it again", async () => {
    const user = userEvent.setup();
    render(<ConnectionsGrid />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Glific: view setup guide" }));
    const dialog = screen.getByRole("dialog", { name: "Glific setup guide" });
    expect(
      within(dialog).getByRole("link", { name: "Open Glific Flow" }),
    ).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the REST API guide (no-logo tile in the title)", async () => {
    const user = userEvent.setup();
    render(<ConnectionsGrid />);

    await user.click(screen.getByRole("button", { name: "REST API: view setup guide" }));

    const dialog = screen.getByRole("dialog", { name: "REST API setup guide" });
    expect(dialog.querySelector("img")).toBeNull();
  });
});
