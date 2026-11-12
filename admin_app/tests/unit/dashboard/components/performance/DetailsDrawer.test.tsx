import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import DetailsDrawer from "@/components/features/dashboard/components/performance/DetailsDrawer";
import type { DrawerData } from "@/components/features/dashboard/types";

// jsdom can't lay out recharts; the fake renders ticks/tooltips through our formatters.
vi.mock("recharts", () => import("../../rechartsMock"));

const data: DrawerData = {
  title: "How do I renew my licence?",
  query_count: 1200,
  positive_votes: 30,
  negative_votes: 4,
  daily_query_count_avg: 40,
  line_chart_data: [
    // Local-time timestamps so labels match in any timezone.
    { timestamp: new Date(2026, 5, 1).getTime(), query_count: 3, positive_count: 1, negative_count: 0 },
    { timestamp: new Date(2026, 5, 2).getTime(), query_count: 5, positive_count: 2, negative_count: 1 },
  ],
  user_feedback: [
    { timestamp: "2026-06-01T09:15:00Z", question: "Where is the form?", feedback: "Link was broken" },
  ],
};

// Same formatting as the component, computed here so the test is timezone-safe.
const feedbackTime = (iso: string) =>
  Intl.DateTimeFormat("en-ZA", { dateStyle: "short", timeStyle: "short" }).format(
    new Date(iso),
  );

describe("DetailsDrawer", () => {
  it("renders nothing until there is data", () => {
    render(<DetailsDrawer open onOpenChange={() => {}} data={null} aiSummary={null} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows the card's numbers, chart and feedback", () => {
    render(<DetailsDrawer open onOpenChange={() => {}} data={data} aiSummary="Users want a working link." />);

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: data.title })).toBeInTheDocument();
    expect(within(dialog).getByText("Total sent").nextSibling).toHaveTextContent(
      (1200).toLocaleString(),
    );
    expect(within(dialog).getByText("Daily average sent").nextSibling).toHaveTextContent("40");
    expect(within(dialog).getByText("Total upvotes").nextSibling).toHaveTextContent("30");
    expect(within(dialog).getByText("Total downvotes").nextSibling).toHaveTextContent("4");

    // Chart: one line per measure, ticks and tooltip label from our formatters.
    for (const key of ["query_count", "positive_count", "negative_count"]) {
      expect(screen.getByTestId(`line-${key}`)).toBeInTheDocument();
    }
    expect(
      within(screen.getByRole("list", { name: "x-axis" })).getAllByRole("listitem").map((li) => li.textContent),
    ).toEqual(["Jun 1", "Jun 2"]);
    expect(screen.getByTestId("tooltip")).toHaveTextContent("Mon 1 Jun 2026");

    expect(screen.getByText("Users want a working link.")).toBeInTheDocument();
    expect(screen.queryByText("Summarising feedback...")).not.toBeInTheDocument();

    const table = screen.getByRole("table", { name: "User feedback" });
    const [, row] = within(table).getAllByRole("row");
    expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      feedbackTime("2026-06-01T09:15:00Z"),
      "Where is the form?",
      "Link was broken",
    ]);
  });

  it("shows a progress line while the AI summary is pending, and an empty feedback note", () => {
    render(
      <DetailsDrawer
        open
        onOpenChange={() => {}}
        data={{ ...data, user_feedback: [] }}
        aiSummary={null}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Summarising feedback...");
    expect(screen.getByText("No feedback in this period.")).toBeInTheDocument();
  });

  it("asks to close when Escape is pressed", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(<DetailsDrawer open onOpenChange={onOpenChange} data={data} aiSummary="x" />);

    await user.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalled();
    expect(onOpenChange.mock.calls[0][0]).toBe(false);
  });
});
