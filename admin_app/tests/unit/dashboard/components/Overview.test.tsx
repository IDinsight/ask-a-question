import { render, screen, within } from "@testing-library/react";
import { vi } from "vitest";

import Overview from "@/components/features/dashboard/components/Overview";
import type { OverviewData, StatsCardsResponse } from "@/components/features/dashboard/types";

// jsdom can't lay out recharts; the fake renders ticks through our formatters.
vi.mock("recharts", () => import("../rechartsMock"));

const stats = (nQuestions: number): StatsCardsResponse => ({
  query_stats: { n_questions: nQuestions, percentage_increase: 0.1 },
  response_feedback_stats: { n_negative: 2, percentage_negative_increase: -0.2 },
  urgency_stats: { n_urgent: 1, percentage_increase: 0 },
  content_feedback_stats: {
    n_positive: 8,
    n_negative: 3,
    percentage_positive_increase: 0.5,
    percentage_negative_increase: 0.05,
  },
});

const overview = (nQuestions: number): OverviewData => ({
  stats: stats(nQuestions),
  heatmap: { "00:00": { Mon: 2 } },
  // 5 Jan 2026 is a Monday (local time).
  timeseries: [{ timestamp: new Date(2026, 0, 5).getTime(), normal: 1, downvoted: 0, urgent: 0 }],
  topContent: [
    {
      title: "Opening hours",
      query_count: 9,
      positive_votes: 1,
      negative_votes: 0,
      last_updated: "2026-01-01T00:00:00Z",
    },
  ],
});

describe("Overview", () => {
  it("shows skeleton cards and empty sections while loading", () => {
    const { container } = render(
      <Overview timePeriod="day" frequency="Hour" hasContent={false} />,
    );

    expect(container.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(5);
    expect(screen.queryByRole("heading", { name: "Get set up" })).not.toBeInTheDocument();
    expect(screen.getByText("No queries in this period")).toBeInTheDocument();
    expect(screen.getByText(/Nothing has been sent yet/)).toBeInTheDocument();
  });

  it("renders the five stat cards and the chart, heatmap and table from data", () => {
    render(
      <Overview timePeriod="week" frequency="Day" hasContent data={overview(120)} />,
    );

    for (const title of [
      "Total queries",
      "Downvoted responses",
      "Urgent queries",
      "Content upvotes",
      "Content downvotes",
    ]) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
    expect(screen.getByText("120")).toBeInTheDocument();
    // The week view labels bars with the weekday.
    expect(
      within(screen.getByRole("list", { name: "x-axis" })).getByRole("listitem"),
    ).toHaveTextContent("Mon 5");
    expect(screen.getByRole("img", { name: /Busiest time: Mon/ })).toBeInTheDocument();
    expect(screen.getByText("Opening hours")).toBeInTheDocument();
    // Real queries exist, so no setup checklist.
    expect(screen.queryByRole("heading", { name: "Get set up" })).not.toBeInTheDocument();
  });

  it("shows the setup checklist until the first query, without content yet", () => {
    render(
      <Overview timePeriod="month" frequency="Day" hasContent={false} data={overview(0)} />,
    );

    const setup = screen.getByRole("region", { name: "Get set up" });
    expect(within(setup).getByRole("img", { name: "1 of 4 steps complete" })).toBeInTheDocument();
    // Workspace is always done; the rest link to where to do them.
    expect(within(setup).getAllByLabelText("Done")).toHaveLength(1);
    expect(within(setup).getByRole("link", { name: "Add content" })).toHaveAttribute("href", "/content");
    expect(within(setup).getByRole("link", { name: "Open testing" })).toHaveAttribute("href", "/content");
    expect(within(setup).getByRole("link", { name: "View integrations" })).toHaveAttribute(
      "href",
      "/integrations",
    );
  });

  it("ticks off 'Add content' once there is content", () => {
    render(<Overview timePeriod="year" frequency="Month" hasContent data={overview(0)} />);

    const setup = screen.getByRole("region", { name: "Get set up" });
    expect(within(setup).getByRole("img", { name: "2 of 4 steps complete" })).toBeInTheDocument();
    expect(within(setup).getAllByLabelText("Done")).toHaveLength(2);
    expect(within(setup).queryByRole("link", { name: "Add content" })).not.toBeInTheDocument();
  });
});
