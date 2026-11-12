import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import TabPanel, { periodLabel } from "@/components/features/dashboard/components/TabPanel";
import type { Period } from "@/components/features/dashboard/types";

describe("TabPanel", () => {
  it("shows every preset plus Custom, with the current one pressed", () => {
    render(<TabPanel tabValue="week" handleChange={() => {}} />);

    const group = screen.getByRole("group", { name: "Time range" });
    expect(group).toBeInTheDocument();
    for (const label of ["Last 24 hours", "Last month", "Last year", "Custom"]) {
      expect(screen.getByRole("button", { name: label })).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    }
    expect(screen.getByRole("button", { name: "Last 7 days" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("reports the newly picked period", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<TabPanel tabValue="week" handleChange={handleChange} />);

    await user.click(screen.getByRole("button", { name: "Last year" }));
    expect(handleChange).toHaveBeenCalledWith("year");

    await user.click(screen.getByRole("button", { name: "Custom" }));
    expect(handleChange).toHaveBeenCalledWith("custom");
  });

  it("ignores a click on the already-selected period (keeps a range selected)", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<TabPanel tabValue="day" handleChange={handleChange} />);

    // Base UI reports [] when deselecting; the panel must not forward that.
    await user.click(screen.getByRole("button", { name: "Last 24 hours" }));
    expect(handleChange).not.toHaveBeenCalled();
  });

  it("shows the edit button only once a custom range is set", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const { rerender } = render(
      <TabPanel tabValue="custom" handleChange={() => {}} onEditCustomPeriod={onEdit} />,
    );
    expect(
      screen.queryByRole("button", { name: "Edit custom date range" }),
    ).not.toBeInTheDocument();

    rerender(
      <TabPanel
        tabValue="custom"
        handleChange={() => {}}
        onEditCustomPeriod={onEdit}
        customDateParamsSet
      />,
    );
    await user.click(screen.getByRole("button", { name: "Edit custom date range" }));
    expect(onEdit).toHaveBeenCalledOnce();
  });
});

describe("periodLabel", () => {
  it.each<[Period, string]>([
    ["day", "last 24 hours"],
    ["week", "last 7 days"],
    ["month", "last month"],
    ["year", "last year"],
    ["custom", "custom range"],
  ])("labels %s as %s", (period, label) => {
    expect(periodLabel(period)).toBe(label);
  });

  it("falls back to the raw value for an unknown period", () => {
    expect(periodLabel("decade" as Period)).toBe("decade");
  });
});
