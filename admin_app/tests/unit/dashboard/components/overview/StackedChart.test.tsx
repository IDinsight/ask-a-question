import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import StackedBarChart, {
  QueriesLegend,
} from "@/components/features/dashboard/components/overview/StackedChart";
import type { QueriesOverTimeRow } from "@/components/features/dashboard/types";

// jsdom can't lay out recharts; the fake renders ticks/tooltips through our formatters.
vi.mock("recharts", () => import("../../rechartsMock"));

// Local-time timestamps so formatted labels are the same in any timezone.
// 5 Jan 2026 is a Monday.
const ts = new Date(2026, 0, 5, 14, 30).getTime();
const rows: QueriesOverTimeRow[] = [
  { timestamp: ts, normal: 3, downvoted: 1, urgent: 0 },
  {
    timestamp: new Date(2026, 1, 9).getTime(),
    normal: 0,
    downvoted: 0,
    urgent: 2,
  },
];
const zeroRows: QueriesOverTimeRow[] = [
  { timestamp: ts, normal: 0, downvoted: 0, urgent: 0 },
];

const ticks = () =>
  within(screen.getByRole("list", { name: "x-axis" }))
    .getAllByRole("listitem")
    .map((li) => li.textContent);

describe("StackedBarChart", () => {
  it.each([
    ["Hour", false, ["14:30", "00:00"]],
    ["Day", true, ["Mon 5", "Mon 9"]],
    ["Day", false, ["Jan 5", "Feb 9"]],
    ["Week", false, ["Jan 5", "Feb 9"]],
    ["Month", false, ["Jan 2026", "Feb 2026"]],
  ] as const)(
    "formats %s ticks (day of week: %s)",
    (frequency, showDayOfWeek, expected) => {
      render(
        <StackedBarChart
          data={rows}
          frequency={frequency}
          showDayOfWeek={showDayOfWeek}
        />,
      );
      expect(ticks()).toEqual(expected);
    },
  );

  it("uses a time-of-day tooltip label for hourly bars and a date otherwise", () => {
    const { rerender } = render(
      <StackedBarChart data={rows} frequency="Hour" />,
    );
    expect(screen.getByTestId("tooltip")).toHaveTextContent("Mon 5 Jan, 14:30");

    rerender(<StackedBarChart data={rows} frequency="Week" />);
    expect(screen.getByTestId("tooltip")).toHaveTextContent("Mon 5 Jan 2026");
  });

  it("renders one bar series per query kind with an auto y-scale when there's data", () => {
    render(<StackedBarChart data={rows} frequency="Day" />);

    for (const key of ["normal", "downvoted", "urgent"]) {
      expect(screen.getByTestId(`bar-${key}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("y-axis")).toHaveAttribute(
      "data-domain",
      '[0,"auto"]',
    );
    expect(
      screen.queryByText("No queries in this period"),
    ).not.toBeInTheDocument();
  });

  it("keeps a visible 0–20 scale and an empty message when every bar is zero", () => {
    render(<StackedBarChart data={zeroRows} frequency="Day" />);

    expect(screen.getByTestId("y-axis")).toHaveAttribute(
      "data-domain",
      "[0,20]",
    );
    expect(screen.getByText("No queries in this period")).toBeInTheDocument();
  });
});

describe("QueriesLegend", () => {
  it("names the three colours", () => {
    render(<QueriesLegend />);
    for (const label of ["Normal", "Urgent", "Downvoted"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});
