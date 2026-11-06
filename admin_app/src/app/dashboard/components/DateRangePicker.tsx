import React, { useEffect, useState } from "react";
import { differenceInCalendarDays, format } from "date-fns";
import type { DateRange } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { CustomDashboardFrequency } from "@/app/dashboard/types";

interface DateRangePickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelectDateRange: (
    startDate: string,
    endDate: string,
    frequency: CustomDashboardFrequency,
  ) => void;
  initialStartDate?: string | null;
  initialEndDate?: string | null;
  initialFrequency?: CustomDashboardFrequency;
}

// Longest range (in days) each frequency allows, so charts don't get too many bars.
const frequencyLimits: Record<CustomDashboardFrequency, number> = {
  Hour: 14,
  Day: 100,
  Week: 365,
  Month: 1825,
};

const frequencyOptions: CustomDashboardFrequency[] = ["Hour", "Day", "Week", "Month"];

const frequencyLabels: Record<CustomDashboardFrequency, string> = {
  Hour: "Hourly",
  Day: "Daily",
  Week: "Weekly",
  Month: "Monthly",
};

const DateRangePickerDialog: React.FC<DateRangePickerDialogProps> = ({
  open,
  onClose,
  onSelectDateRange,
  initialStartDate = null,
  initialEndDate = null,
  initialFrequency = "Day",
}) => {
  const [range, setRange] = useState<DateRange | undefined>(undefined);
  const [frequency, setFrequency] =
    useState<CustomDashboardFrequency>(initialFrequency);

  const startDate = range?.from ?? null;
  const endDate = range?.to ?? null;

  // Inclusive number of days in the range, or null until both ends are picked.
  const diffDays: number | null =
    startDate && endDate
      ? Math.abs(differenceInCalendarDays(endDate, startDate)) + 1
      : null;

  // Reset to the last applied range each time the dialog opens.
  useEffect(() => {
    if (open) {
      setRange(
        initialStartDate
          ? {
              from: new Date(initialStartDate),
              to: initialEndDate ? new Date(initialEndDate) : undefined,
            }
          : undefined,
      );
      setFrequency(initialFrequency || "Day");
    }
  }, [open, initialStartDate, initialEndDate, initialFrequency]);

  // If the range is too long for the chosen frequency, step up to the first one that fits.
  useEffect(() => {
    if (diffDays !== null && diffDays > frequencyLimits[frequency]) {
      const validOption = frequencyOptions.find(
        (option) => diffDays <= frequencyLimits[option],
      );
      if (validOption && validOption !== frequency) {
        setFrequency(validOption);
      }
    }
  }, [diffDays, frequency]);

  const handleOk = () => {
    if (startDate && endDate) {
      const [finalStartDate, finalEndDate] =
        startDate.getTime() > endDate.getTime()
          ? [endDate, startDate]
          : [startDate, endDate];
      onSelectDateRange(
        format(finalStartDate, "yyyy-MM-dd"),
        format(finalEndDate, "yyyy-MM-dd"),
        frequency,
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="flex flex-col gap-5 p-6 sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">Custom date range</DialogTitle>
          <DialogDescription className="text-sm">
            {startDate && endDate
              ? `${format(startDate, "MMM d, yyyy")} – ${format(endDate, "MMM d, yyyy")} (${diffDays} days)`
              : "Pick a start date, then an end date."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex justify-center overflow-x-auto border">
          <Calendar
            mode="range"
            numberOfMonths={2}
            defaultMonth={startDate ?? undefined}
            selected={range}
            onSelect={setRange}
          />
        </div>

        <Field className="max-w-48">
          <FieldLabel htmlFor="frequency-select">Frequency</FieldLabel>
          <NativeSelect
            id="frequency-select"
            className="w-full"
            value={frequency}
            onChange={(event) =>
              setFrequency(event.target.value as CustomDashboardFrequency)
            }
          >
            {frequencyOptions.map((option) => (
              <NativeSelectOption
                key={option}
                value={option}
                disabled={diffDays !== null && diffDays > frequencyLimits[option]}
              >
                {frequencyLabels[option]}
              </NativeSelectOption>
            ))}
          </NativeSelect>
        </Field>

        <p className="bg-muted p-3 text-xs text-muted-foreground">
          Frequency only changes the bar chart on the Overview page. It doesn’t
          affect Content Performance or Query Topics.
        </p>

        <DialogFooter>
          <Button variant="outline" size="lg" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="lg"
            onClick={handleOk}
            disabled={
              !startDate ||
              !endDate ||
              (diffDays !== null && diffDays > frequencyLimits[frequency])
            }
          >
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DateRangePickerDialog;
