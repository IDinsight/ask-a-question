import React from "react";
import { IconPencil } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
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

// The toggle's default "on" state is bg-muted, which matches the track here,
// so the selected segment is lifted onto the card colour instead.
const SEGMENT_CLASSES =
  "border border-transparent px-3 text-[13px] text-muted-foreground hover:bg-transparent hover:text-foreground aria-pressed:border-input aria-pressed:bg-card aria-pressed:text-foreground aria-pressed:shadow-xs";

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
      {/* Single-select segmented control. Base UI reports an empty array when
          the selected item is clicked again; ignore that so a range stays selected. */}
      <ToggleGroup
        aria-label="Time range"
        size="sm"
        spacing={0.5}
        value={[tabValue]}
        onValueChange={(values) => {
          if (values.length > 0) handleChange(values[0] as Period);
        }}
        className="flex-wrap bg-muted p-0.75"
      >
        {timePeriods.map(([label, periodValue]) => (
          <ToggleGroupItem
            key={periodValue}
            value={periodValue}
            className={SEGMENT_CLASSES}
          >
            {label}
          </ToggleGroupItem>
        ))}
        <ToggleGroupItem value="custom" className={SEGMENT_CLASSES}>
          Custom
        </ToggleGroupItem>
      </ToggleGroup>
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
