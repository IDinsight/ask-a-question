import React from "react";
import { IconPencil } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Period, TimeFrame } from "../types";

interface TabPanelProps {
  tabValue: Period;
  handleChange: (newValue: Period) => void;
  onEditCustomPeriod?: () => void;
  customDateParamsSet?: boolean;
}

// Labels follow the backend ranges: "week" is 7 days, "month" is one calendar month.
const tabLabels: Record<TimeFrame, Period> = {
  "Last 24 hours": "day",
  "Last 7 days": "week",
  "Last month": "month",
  "Last year": "year",
};

/** Lower-case phrase for a period, e.g. "last 7 days", for use in headings. */
const periodLabel = (period: Period): string => {
  if (period === "custom") return "custom range";
  const entry = Object.entries(tabLabels).find(([, value]) => value === period);
  return entry ? entry[0].toLowerCase() : period;
};

/** One segment of the time-range control. */
const Segment = ({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) => (
  <button
    type="button"
    aria-pressed={selected}
    onClick={onClick}
    className={cn(
      "h-7 border border-transparent px-3 text-[13px] font-medium text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
      selected && "border-input bg-card text-foreground shadow-xs",
    )}
  >
    {children}
  </button>
);

/**
 * Segmented time-range picker shared by the dashboard pages.
 * "Custom" opens the date range dialog until a range has been chosen;
 * after that a pencil button next to it reopens the dialog.
 */
const TabPanel: React.FC<TabPanelProps> = ({
  tabValue,
  handleChange,
  onEditCustomPeriod,
  customDateParamsSet,
}) => {
  const timePeriods = Object.entries(tabLabels) as [TimeFrame, Period][];

  return (
    <div className="flex items-center gap-1">
      <div
        role="group"
        aria-label="Time range"
        className="inline-flex flex-wrap gap-0.5 bg-muted p-0.75"
      >
        {timePeriods.map(([label, periodValue]) => (
          <Segment
            key={periodValue}
            selected={tabValue === periodValue}
            onClick={() => handleChange(periodValue)}
          >
            {label}
          </Segment>
        ))}
        <Segment selected={tabValue === "custom"} onClick={() => handleChange("custom")}>
          Custom
        </Segment>
      </div>
      {customDateParamsSet && onEditCustomPeriod && (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Edit custom date range"
          onClick={onEditCustomPeriod}
        >
          <IconPencil />
        </Button>
      )}
    </div>
  );
};

export default TabPanel;
export { periodLabel };
