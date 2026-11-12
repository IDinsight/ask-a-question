import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import DateRangePickerDialog from "@/components/features/dashboard/components/DateRangePicker";
import type { CustomDashboardFrequency } from "@/components/features/dashboard/types";

// Dates without a "Z" parse as local midnight, so ranges are the same in any timezone.
const setup = (
  props: Partial<React.ComponentProps<typeof DateRangePickerDialog>> = {},
) => {
  const onClose = vi.fn();
  const onSelectDateRange = vi.fn();
  const utils = render(
    <DateRangePickerDialog
      open
      onClose={onClose}
      onSelectDateRange={onSelectDateRange}
      {...props}
    />,
  );
  return { user: userEvent.setup(), onClose, onSelectDateRange, ...utils };
};

const frequency = () => screen.getByRole("combobox", { name: "Frequency" });
const option = (label: string) => screen.getByRole("option", { name: label });
const apply = () => screen.getByRole("button", { name: "Apply" });

describe("DateRangePickerDialog", () => {
  it("prompts for a range and keeps Apply disabled until one is picked", () => {
    setup();

    expect(screen.getByRole("heading", { name: "Custom date range" })).toBeInTheDocument();
    expect(screen.getByText("Pick a start date, then an end date.")).toBeInTheDocument();
    expect(frequency()).toHaveValue("Day");
    expect(apply()).toBeDisabled();
  });

  it("restores the last applied range and applies it with the chosen frequency", async () => {
    const { user, onSelectDateRange } = setup({
      initialStartDate: "2026-03-01T00:00:00",
      initialEndDate: "2026-03-10T00:00:00",
      initialFrequency: "Week",
    });

    expect(
      screen.getByText("Mar 1, 2026 – Mar 10, 2026 (10 days)"),
    ).toBeInTheDocument();
    expect(frequency()).toHaveValue("Week");

    await user.selectOptions(frequency(), "Hour");
    expect(frequency()).toHaveValue("Hour");

    await user.click(apply());
    expect(onSelectDateRange).toHaveBeenCalledWith("2026-03-01", "2026-03-10", "Hour");
  });

  it("needs both ends of the range", () => {
    setup({ initialStartDate: "2026-03-01T00:00:00" });
    expect(screen.getByText("Pick a start date, then an end date.")).toBeInTheDocument();
    expect(apply()).toBeDisabled();
  });

  it("puts the dates in order if the end is before the start", async () => {
    const { user, onSelectDateRange } = setup({
      initialStartDate: "2026-03-10T00:00:00",
      initialEndDate: "2026-03-01T00:00:00",
    });

    await user.click(apply());
    expect(onSelectDateRange).toHaveBeenCalledWith("2026-03-01", "2026-03-10", "Day");
  });

  it("steps up to the first frequency that fits a long range and disables the rest", () => {
    // 31 days is too long for hourly bars (limit 14).
    setup({
      initialStartDate: "2026-01-01T00:00:00",
      initialEndDate: "2026-01-31T00:00:00",
      initialFrequency: "Hour",
    });

    expect(frequency()).toHaveValue("Day");
    expect(option("Hourly")).toBeDisabled();
    expect(option("Daily")).toBeEnabled();
    expect(apply()).toBeEnabled();
  });

  it("blocks Apply when no frequency fits the range", () => {
    // Over 1825 days: even monthly bars are too many.
    setup({
      initialStartDate: "2020-01-01T00:00:00",
      initialEndDate: "2026-01-01T00:00:00",
    });

    for (const label of ["Hourly", "Daily", "Weekly", "Monthly"]) {
      expect(option(label)).toBeDisabled();
    }
    expect(frequency()).toHaveValue("Day");
    expect(apply()).toBeDisabled();
  });

  it("falls back to daily when given an empty frequency", () => {
    setup({ initialFrequency: "" as CustomDashboardFrequency });
    expect(frequency()).toHaveValue("Day");
  });

  it("lets the user pick a range on the calendar", async () => {
    const { user, onSelectDateRange } = setup({
      // Opens the calendar on March 2026 with a 1-day range already set.
      initialStartDate: "2026-03-02T00:00:00",
      initialEndDate: "2026-03-02T00:00:00",
    });

    // In range mode, clicking a later day extends the range to it.
    const day12 = screen
      .getAllByRole("button")
      .find((b) => /March 12(th)?,? 2026/.test(b.getAttribute("aria-label") ?? ""));
    expect(day12).toBeDefined();
    await user.click(day12!);

    expect(screen.getByText(/Mar 2, 2026 – Mar 12, 2026 \(11 days\)/)).toBeInTheDocument();
    await user.click(apply());
    expect(onSelectDateRange).toHaveBeenCalledWith("2026-03-02", "2026-03-12", "Day");
  });

  it("closes on Cancel or Escape", async () => {
    const { user, onClose } = setup();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("does nothing while closed", () => {
    setup({ open: false, initialStartDate: "2026-03-01T00:00:00" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
