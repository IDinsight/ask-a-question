import { render, screen, within } from "@testing-library/react";
import { format } from "date-fns";

import TopContentTable from "@/components/features/dashboard/components/overview/TopContentTable";
import type { TopContentData } from "@/components/features/dashboard/types";

const row = (overrides: Partial<TopContentData> = {}): TopContentData => ({
  title: "How do I reset my PIN?",
  query_count: 42,
  positive_votes: 3,
  negative_votes: 1,
  last_updated: "2026-03-04T10:20:00Z",
  ...overrides,
});

describe("TopContentTable", () => {
  it("shows an empty state with a link to add content", () => {
    render(<TopContentTable rows={[]} />);

    expect(
      screen.getByRole("heading", { name: "Most sent content" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Nothing has been sent yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add content" })).toHaveAttribute(
      "href",
      "/content",
    );
  });

  it("renders each row with its date, count and vote split", () => {
    const first = row();
    render(
      <TopContentTable
        rows={[
          first,
          row({
            title: "[DELETED] Old card",
            positive_votes: 0,
            negative_votes: 0,
          }),
        ]}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1); // skip header
    expect(rows).toHaveLength(2);

    const cells = within(rows[0]).getAllByRole("cell");
    expect(cells[0]).toHaveTextContent(first.title);
    // Local-time format, computed the same way so the test is timezone-safe.
    expect(cells[1]).toHaveTextContent(
      format(new Date(first.last_updated), "yyyy-MM-dd HH:mm"),
    );
    expect(cells[2]).toHaveTextContent("42");
    expect(
      within(rows[0]).getByRole("img", {
        name: "75% upvotes, 25% downvotes (4 votes)",
      }),
    ).toBeInTheDocument();
    expect(within(rows[0]).getByText("75% / 25%")).toBeInTheDocument();

    // Deleted content is still listed; with no votes the bar says so.
    expect(within(rows[1]).getByText("[DELETED] Old card")).toHaveClass(
      "text-muted-foreground",
    );
    expect(
      within(rows[1]).getByRole("img", { name: "No votes yet" }),
    ).toBeInTheDocument();
    expect(within(rows[1]).getByText("No votes")).toBeInTheDocument();
  });
});
