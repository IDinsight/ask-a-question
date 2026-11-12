import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import LineChart from "@/components/features/dashboard/components/performance/LineChart";

// jsdom can't lay out recharts; the fake renders ticks/tooltips through our formatters.
vi.mock("recharts", () => import("../../rechartsMock"));

// Local-time timestamps so labels match in any timezone.
const d1 = new Date(2026, 2, 1).getTime();
const d2 = new Date(2026, 2, 2).getTime();
const d3 = new Date(2026, 2, 3).getTime();

const ticks = () =>
  within(screen.getByRole("list", { name: "x-axis" }))
    .getAllByRole("listitem")
    .map((li) => li.textContent);

describe("LineChart", () => {
  it("merges series on timestamp, sorted, with one line per series", () => {
    render(
      <LineChart
        chartColors={["#111111"]}
        data={[
          // Out of order, and the series only partly overlap.
          {
            name: "Card A",
            data: [
              { x: d3, y: 1 },
              { x: d1, y: 2 },
            ],
          },
          {
            name: "Card B",
            data: [
              { x: d2, y: 5 },
              { x: d1, y: 0 },
            ],
          },
        ]}
      />,
    );

    // One tick per distinct timestamp, in time order.
    expect(ticks()).toEqual(["Mar 1", "Mar 2", "Mar 3"]);
    expect(screen.getByTestId("line-s0")).toBeInTheDocument();
    expect(screen.getByTestId("line-s1")).toBeInTheDocument();

    // Tooltip label is the full date of the hovered row (first row here).
    expect(screen.getByTestId("tooltip")).toHaveTextContent("Sun 1 Mar 2026");

    // More than one series gets a legend; data present means an auto y-scale.
    expect(screen.getByTestId("legend")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toHaveAttribute(
      "data-domain",
      '[0,"auto"]',
    );
    expect(
      screen.queryByText("No content sent in this period"),
    ).not.toBeInTheDocument();
  });

  it("falls back to the first colour when there are more series than colours", () => {
    const { container } = render(
      <LineChart
        chartColors={["#123456"]}
        data={[
          { name: "A", data: [{ x: d1, y: 1 }] },
          { name: "B", data: [{ x: d1, y: 1 }] },
        ]}
      />,
    );
    // ChartContainer writes each series colour as a CSS variable.
    const css = container.querySelector("style")?.innerHTML ?? "";
    expect(css).toContain("--color-s0: #123456");
    expect(css).toContain("--color-s1: #123456");
  });

  it("hides the legend for a single series", () => {
    render(
      <LineChart
        chartColors={["#111"]}
        data={[{ name: "A", data: [{ x: d1, y: 3 }] }]}
      />,
    );
    expect(screen.queryByTestId("legend")).not.toBeInTheDocument();
  });

  it("shows an empty message, no tooltip and a fixed scale when every value is zero", () => {
    render(
      <LineChart
        chartColors={["#111"]}
        data={[{ name: "A", data: [{ x: d1, y: 0 }] }]}
      />,
    );

    expect(
      screen.getByText("No content sent in this period"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("tooltip")).not.toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toHaveAttribute(
      "data-domain",
      "[0,20]",
    );
  });
});
