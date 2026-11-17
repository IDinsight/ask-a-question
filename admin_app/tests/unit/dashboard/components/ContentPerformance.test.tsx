import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import ContentPerformance from "@/components/features/dashboard/components/ContentPerformance";
import type {
  DrawerData,
  Period,
  RowDataType,
} from "@/components/features/dashboard/types";

// jsdom can't lay out recharts; the fake renders lines/ticks as plain DOM.
vi.mock("recharts", () => import("../rechartsMock"));

const makeRow = (id: number): RowDataType => ({
  id,
  title: `Card ${id}`,
  query_count: id,
  positive_votes: 0,
  negative_votes: 0,
  query_count_timeseries: [{ x: new Date(2026, 0, id).getTime(), y: id }],
});

const drawerData: DrawerData = {
  title: "Drawer card",
  query_count: 1,
  positive_votes: 0,
  negative_votes: 0,
  daily_query_count_avg: 1,
  line_chart_data: [],
  user_feedback: [],
};

const setup = (
  props: Partial<React.ComponentProps<typeof ContentPerformance>> = {},
) => {
  const handlers = {
    onTimePeriodChange: vi.fn(),
    onItemsToDisplayChange: vi.fn(),
    onSortChange: vi.fn(),
    onPageChange: vi.fn(),
    onRowClick: vi.fn(),
  };
  render(
    <ContentPerformance
      timePeriod="week"
      rows={[]}
      itemsToDisplay={[]}
      sortColumn="query_count"
      sortDirection="descending"
      page={1}
      drawer={{
        open: false,
        onOpenChange: vi.fn(),
        data: null,
        aiSummary: null,
      }}
      {...handlers}
      {...props}
    />,
  );
  return { user: userEvent.setup(), ...handlers };
};

const subtitle = () => screen.getByText(/^Ordered by/);

describe("ContentPerformance", () => {
  it("titles the section with the period and describes the sort", () => {
    setup();
    expect(
      screen.getByRole("heading", { name: "Top content, last 7 days" }),
    ).toBeInTheDocument();
    expect(subtitle()).toHaveTextContent(
      "Ordered by daily average sent, highest first.",
    );
  });

  it("names ascending sorts 'lowest first' and falls back to the raw column key", () => {
    setup({ sortColumn: "mystery", sortDirection: "ascending" });
    expect(subtitle()).toHaveTextContent("Ordered by mystery, lowest first.");
  });

  it("mentions the page once there is more than one page of results", () => {
    const rows = [1, 2, 3, 4, 5, 6].map(makeRow);
    setup({ rows, itemsToDisplay: rows.slice(0, 5) });
    expect(subtitle()).toHaveTextContent("· page 1 of results.");
  });

  it("mentions the page when past page 1 even with few rows", () => {
    setup({ page: 2, rows: [makeRow(1)] });
    expect(subtitle()).toHaveTextContent("· page 2 of results.");
  });

  it("charts the rows the table is showing and opens a row on click", async () => {
    const rows = [makeRow(1), makeRow(2)];
    const { user, onRowClick } = setup({ rows, itemsToDisplay: rows });

    expect(screen.getByTestId("line-s0")).toBeInTheDocument();
    expect(screen.getByTestId("line-s1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Card 2" }));
    expect(onRowClick).toHaveBeenCalledWith(2);
  });

  it.each<[Period, string, Period]>([
    ["day", "Show last 7 days", "week"],
    ["week", "Show last month", "month"],
    ["month", "Show last year", "year"],
  ])(
    "offers the next-longer range when %s is empty",
    async (period, label, next) => {
      const { user, onTimePeriodChange } = setup({ timePeriod: period });
      await user.click(screen.getByRole("button", { name: label }));
      expect(onTimePeriodChange).toHaveBeenCalledWith(next);
    },
  );

  it.each<Period>(["year", "custom"])(
    "has no longer range to offer for %s",
    (period) => {
      setup({ timePeriod: period });
      expect(
        screen.getByText("No content performance yet"),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /^Show / }),
      ).not.toBeInTheDocument();
    },
  );

  it("passes drawer state through to the details drawer", () => {
    setup({
      drawer: {
        open: true,
        onOpenChange: vi.fn(),
        data: drawerData,
        aiSummary: "Fine.",
      },
    });
    expect(screen.getByRole("dialog")).toHaveTextContent("Drawer card");
    expect(screen.getByText("Fine.")).toBeInTheDocument();
  });
});
