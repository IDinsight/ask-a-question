import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import ContentsTable from "@/components/features/dashboard/components/performance/ContentsTable";
import type { RowDataType } from "@/components/features/dashboard/types";

// jsdom can't lay out recharts; the fake renders the sparkline tooltip through our formatter.
vi.mock("recharts", () => import("../../rechartsMock"));

const day = (n: number) => new Date(2026, 4, n).getTime(); // local time, tz-safe labels

const makeRow = (
  id: number,
  overrides: Partial<RowDataType> = {},
): RowDataType => ({
  id,
  title: `Card ${id}`,
  query_count: id * 10,
  positive_votes: id,
  negative_votes: 10 - id,
  query_count_timeseries: [{ x: day(id), y: id }],
  ...overrides,
});

const setup = (
  props: Partial<React.ComponentProps<typeof ContentsTable>> = {},
) => {
  const handlers = {
    onClick: vi.fn(),
    onItemsToDisplayChange: vi.fn(),
    onSortChange: vi.fn(),
    onPageChange: vi.fn(),
  };
  const user = userEvent.setup();
  render(
    <ContentsTable
      rows={[1, 2, 3, 4, 5, 6, 7].map((i) => makeRow(i))}
      rowsPerPage={5}
      chartColors={["#111111"]}
      {...handlers}
      {...props}
    />,
  );
  return { user, ...handlers };
};

// Titles of the body rows, top to bottom.
const titles = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getByRole("button").textContent);

describe("ContentsTable", () => {
  it("starts sorted by daily average sent, highest first, and reports the visible rows", () => {
    const { onItemsToDisplayChange } = setup();

    expect(titles()).toEqual([
      "Card 7",
      "Card 6",
      "Card 5",
      "Card 4",
      "Card 3",
    ]);
    expect(
      screen.getByRole("columnheader", { name: "Daily average sent" }),
    ).toHaveAttribute("aria-sort", "descending");
    const lastCall = onItemsToDisplayChange.mock.lastCall![0] as RowDataType[];
    expect(lastCall.map((r) => r.id)).toEqual([7, 6, 5, 4, 3]);
  });

  it("flips direction on the active column and resets to descending on a new one", async () => {
    const { user, onSortChange } = setup();

    await user.click(
      screen.getByRole("button", { name: "Daily average sent" }),
    );
    expect(onSortChange).toHaveBeenLastCalledWith("query_count", "ascending");
    expect(titles()[0]).toBe("Card 1");

    await user.click(
      screen.getByRole("button", { name: "Daily average sent" }),
    );
    expect(onSortChange).toHaveBeenLastCalledWith("query_count", "descending");
    expect(titles()[0]).toBe("Card 7");

    // Downvotes = 10 - id, so the highest is Card 1.
    await user.click(screen.getByRole("button", { name: "Downvotes" }));
    expect(onSortChange).toHaveBeenLastCalledWith(
      "negative_votes",
      "descending",
    );
    expect(titles()[0]).toBe("Card 1");
  });

  it("sorts by trend: change between the last two quarters of the series", async () => {
    const series = (ys: number[]) => ys.map((y, i) => ({ x: day(i + 1), y }));
    const { user } = setup({
      rows: [
        makeRow(1, {
          title: "Flat",
          query_count_timeseries: series([1, 1, 1, 1]),
        }),
        // Third quarter is 0, so the change divides by 1 instead.
        makeRow(2, {
          title: "Rising",
          query_count_timeseries: series([0, 0, 0, 5]),
        }),
        makeRow(3, {
          title: "Falling",
          query_count_timeseries: series([4, 4, 4, 2]),
        }),
        // Fewer than 4 points counts as no trend.
        makeRow(4, { title: "Short", query_count_timeseries: series([9]) }),
      ],
    });

    await user.click(screen.getByRole("button", { name: "Trend" }));
    const order = titles();
    expect(order[0]).toBe("Rising");
    expect(order[3]).toBe("Falling");
  });

  it("filters by title (case-insensitive) and goes back to page 1", async () => {
    const { user, onPageChange } = setup();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenLastCalledWith(2);

    await user.type(
      screen.getByRole("searchbox", { name: "Search content titles" }),
      "card 2",
    );
    expect(titles()).toEqual(["Card 2"]);
    expect(onPageChange).toHaveBeenLastCalledWith(1);
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  });

  it("says when no titles match the search", async () => {
    const { user } = setup();
    await user.type(screen.getByRole("searchbox"), "zzz");

    expect(
      screen.getByText("No content titles match “zzz”."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("No content performance yet"),
    ).not.toBeInTheDocument();
  });

  it("pages forward and back, disabling buttons at the ends", async () => {
    const { user, onPageChange } = setup();
    const prev = screen.getByRole("button", { name: "Previous" });
    const next = screen.getByRole("button", { name: "Next" });

    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    expect(prev).toBeDisabled();

    await user.click(next);
    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
    expect(titles()).toEqual(["Card 2", "Card 1"]);
    expect(next).toBeDisabled();

    await user.click(prev);
    expect(onPageChange).toHaveBeenLastCalledWith(1);
  });

  it("opens a row from either the title button or the row itself, once per click", async () => {
    const { user, onClick } = setup();

    await user.click(screen.getByRole("button", { name: "Card 7" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenLastCalledWith(7);

    // Clicking elsewhere in the row (the count cell) also opens it.
    await user.click(screen.getByRole("cell", { name: "60" }));
    expect(onClick).toHaveBeenCalledTimes(2);
    expect(onClick).toHaveBeenLastCalledWith(6);
  });

  it("labels each sparkline tooltip with the bucket date", () => {
    setup({ rows: [makeRow(3)] });
    expect(screen.getByTestId("tooltip")).toHaveTextContent("May 3, 2026");
  });

  it("shows an empty state with an optional 'longer range' action", async () => {
    const onSelect = vi.fn();
    const { user } = setup({
      rows: [],
      longerRange: { label: "Show last month", onSelect },
    });

    expect(screen.getByText("No content performance yet")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show last month" }));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("omits the longer-range action when there isn't one", () => {
    setup({ rows: [] });
    expect(screen.getByText("No content performance yet")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^Show / }),
    ).not.toBeInTheDocument();
  });
});
