import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import BokehPlot, {
  type BokehPlotProps,
} from "@/components/features/dashboard/components/insights/Bokeh";

// bokehjs needs a real canvas/browser; stand in for its embed API.
const { embedItem } = vi.hoisted(() => ({ embedItem: vi.fn() }));
vi.mock("@bokeh/bokehjs", () => ({ embed: { embed_item: embedItem } }));

const LOAD_ERROR = /There was a system failure/;

const setup = (props: Partial<BokehPlotProps> = {}) => {
  const onOpenChange = vi.fn();
  const utils = render(
    <BokehPlot
      open={false}
      onOpenChange={onOpenChange}
      plotSpec={undefined}
      loading={false}
      error={false}
      {...props}
    />,
  );
  // The decorative placeholder is 7 grey squares, only shown before a plot loads.
  const placeholderCount = () =>
    utils.container.querySelectorAll('[aria-hidden="true"] > span.bg-muted')
      .length;
  return { user: userEvent.setup(), onOpenChange, placeholderCount, ...utils };
};

beforeEach(() => {
  embedItem.mockReset();
});

describe("BokehPlot", () => {
  it("starts collapsed with a placeholder and asks to expand on click", async () => {
    const { user, onOpenChange, placeholderCount } = setup();

    expect(
      screen.getByRole("heading", { name: "Topic visualization" }),
    ).toBeInTheDocument();
    expect(placeholderCount()).toBe(7);

    await user.click(
      screen.getByRole("button", { name: "Expand topic visualization" }),
    );
    expect(onOpenChange).toHaveBeenCalled();
    expect(onOpenChange.mock.calls[0][0]).toBe(true);
    expect(embedItem).not.toHaveBeenCalled();
  });

  it("shows a spinner while loading and the help text on request", async () => {
    const { user, placeholderCount } = setup({ open: true, loading: true });

    expect(placeholderCount()).toBe(0);
    expect(
      screen.getByRole("button", { name: "Collapse topic visualization" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "How to use this tool" }),
    );
    expect(
      screen.getByText(/queries and content grouped by their topic/),
    ).toBeInTheDocument();
    for (const alt of [
      "Scroll Zoom",
      "Pan Tool",
      "Tooltip",
      "Lasso Tool",
      "Reset Tool",
    ]) {
      expect(screen.getByAltText(alt)).toBeInTheDocument();
    }
  });

  it("shows an error when fetching the plot failed", () => {
    setup({ open: true, error: true });
    expect(screen.getByRole("alert")).toHaveTextContent(LOAD_ERROR);
  });

  it("embeds a new plot spec into the plot div and drops the placeholder", async () => {
    const spec = { doc: "fake" };
    const { placeholderCount } = setup({ plotSpec: spec });

    await waitFor(() => expect(embedItem).toHaveBeenCalledWith(spec, "myplot"));
    // Once loaded, the placeholder stays hidden even while collapsed.
    await waitFor(() => expect(placeholderCount()).toBe(0));
    expect(document.getElementById("myplot")).toBeInTheDocument();
  });

  it("shows the error when embedding throws", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    embedItem.mockImplementation(() => {
      throw new Error("bad spec");
    });
    setup({ open: true, plotSpec: { doc: "broken" } });

    expect(await screen.findByRole("alert")).toHaveTextContent(LOAD_ERROR);
    expect(consoleError).toHaveBeenCalledWith(
      "Error embedding the plot:",
      expect.any(Error),
    );
    consoleError.mockRestore();
  });

  it("does not embed if it unmounts before bokehjs loads", async () => {
    const { unmount } = setup({ plotSpec: { doc: "late" } });
    unmount(); // effect cleanup marks the pending load as cancelled

    // Let the dynamic import resolve.
    await new Promise((r) => setTimeout(r, 0));
    expect(embedItem).not.toHaveBeenCalled();
  });
});
