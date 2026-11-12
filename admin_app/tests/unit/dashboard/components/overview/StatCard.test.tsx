import { render, screen } from "@testing-library/react";
import { IconMessage } from "@tabler/icons-react";

import { StatCard } from "@/components/features/dashboard/components/overview/StatCard";

// Matches how the component formats the change, so tests don't depend on locale.
const pct = (n: number) =>
  n.toLocaleString(undefined, {
    style: "percent",
    minimumFractionDigits: 1,
    signDisplay: "exceptZero",
  });

describe("StatCard", () => {
  it("shows the title, value and an increase since the last period", () => {
    render(
      <StatCard
        title="Total queries"
        value={1234}
        percentageChange={0.125}
        Icon={IconMessage}
        period="week"
      />,
    );

    expect(screen.getByText("Total queries")).toBeInTheDocument();
    expect(screen.getByText((1234).toLocaleString())).toBeInTheDocument();
    expect(screen.getByText(pct(0.125))).toBeInTheDocument();
    expect(screen.getByText("since last week")).toBeInTheDocument();
  });

  it("shows a decrease, and neutral wording for custom ranges", () => {
    render(
      <StatCard
        title="Urgent queries"
        value={5}
        percentageChange={-0.3}
        Icon={IconMessage}
        iconClassName="text-urgent"
        period="custom"
      />,
    );

    expect(screen.getByText(pct(-0.3))).toBeInTheDocument();
    expect(screen.getByText("vs. previous period")).toBeInTheDocument();
  });

  it("says there is no change data when value and change are both zero", () => {
    render(
      <StatCard
        title="Total queries"
        value={0}
        percentageChange={0}
        Icon={IconMessage}
        period="day"
      />,
    );

    expect(screen.getByText("No change data yet")).toBeInTheDocument();
    expect(screen.queryByText("since last day")).not.toBeInTheDocument();
  });
});
