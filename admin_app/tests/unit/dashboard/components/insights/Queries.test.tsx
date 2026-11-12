import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import Queries from "@/components/features/dashboard/components/insights/Queries";
import type { QueryData } from "@/components/features/dashboard/types";

// Same formatting as the component, so the test is timezone-safe.
const fmt = (iso: string) =>
  Intl.DateTimeFormat("en-ZA", { dateStyle: "short", timeStyle: "short" }).format(
    new Date(iso),
  );

const samples: QueryData[] = [
  { query_text: "When does the clinic open?", query_datetime_utc: "2026-02-01T08:00:00Z" },
  { query_text: "Is the clinic open on Sunday?", query_datetime_utc: "2026-02-02T09:30:00Z" },
];

describe("Queries", () => {
  it("shows the empty state and 'Never' before discovery has run", async () => {
    const user = userEvent.setup();
    const onRefreshClick = vi.fn();
    render(
      <Queries
        data={[]}
        onRefreshClick={onRefreshClick}
        lastRefreshed=""
        refreshing={false}
        aiSummary="unused"
      />,
    );

    expect(screen.getByText("Last run: Never")).toBeInTheDocument();
    expect(screen.getByText("Discover what people ask about")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connect your chatbot" })).toHaveAttribute(
      "href",
      "/integrations",
    );
    expect(screen.queryByText("unused")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run discovery" }));
    expect(onRefreshClick).toHaveBeenCalledOnce();
  });

  it("shows the AI summary and example queries for a topic", () => {
    render(
      <Queries
        data={samples}
        onRefreshClick={() => {}}
        lastRefreshed="2026-02-03T10:00:00Z"
        refreshing={false}
        aiSummary="People ask about clinic hours."
      />,
    );

    expect(screen.getByText(`Last run: ${fmt("2026-02-03T10:00:00Z")}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rerun discovery" })).toBeEnabled();
    expect(screen.getByText("People ask about clinic hours.")).toBeInTheDocument();

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      fmt(samples[0].query_datetime_utc),
      samples[0].query_text,
    ]);
  });

  it("disables the button with a spinner while discovery runs", () => {
    render(
      <Queries
        data={samples}
        onRefreshClick={() => {}}
        lastRefreshed=""
        refreshing
        aiSummary=""
      />,
    );

    const button = screen.getByRole("button", { name: /Running discovery/ });
    expect(button).toBeDisabled();
    expect(within(button).getByRole("status")).toBeInTheDocument();
  });
});
