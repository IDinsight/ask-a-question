import React, { useEffect, useState } from "react";
import { format, differenceInCalendarDays } from "date-fns";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
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

const DateRangePickerDialog: React.FC<DateRangePickerDialogProps> = ({
  open,
  onClose,
  onSelectDateRange,
  initialStartDate = null,
  initialEndDate = null,
  initialFrequency = "Day",
}) => {
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [frequency, setFrequency] =
    useState<CustomDashboardFrequency>(initialFrequency);

  const frequencyLimits: Record<CustomDashboardFrequency, number> = {
    Hour: 14,
    Day: 100,
    Week: 365,
    Month: 1825,
  };

  const frequencyOptions: CustomDashboardFrequency[] = ["Hour", "Day", "Week", "Month"];

  // Compute number of days in the selected range
  const diffDays: number | null =
    startDate && endDate
      ? Math.abs(differenceInCalendarDays(endDate, startDate)) + 1
      : null;

  // When the dialog popup opens -> set variables
  useEffect(() => {
    if (open) {
      setStartDate(initialStartDate ? new Date(initialStartDate) : null);
      setEndDate(initialEndDate ? new Date(initialEndDate) : null);
      setFrequency(initialFrequency || "Day");
    }
  }, [open, initialStartDate, initialEndDate, initialFrequency]);

  // Auto-update the selected frequency if the current one is invalid given the selected date range
  useEffect(() => {
    if (diffDays !== null) {
      if (diffDays > frequencyLimits[frequency]) {
        const validOption = frequencyOptions.find(
          (option) => diffDays <= frequencyLimits[option],
        );
        if (validOption && validOption !== frequency) {
          setFrequency(validOption);
        }
      }
    }
  }, [diffDays, frequency, frequencyOptions, frequencyLimits]);

  const handleOk = () => {
    if (startDate && endDate) {
      // Ensure startDate is before endDate
      const [finalStartDate, finalEndDate] =
        startDate.getTime() > endDate.getTime()
          ? [endDate, startDate]
          : [startDate, endDate];

      // Format to 'YYYY-MM-DD' in local time
      const formattedStartDate = format(finalStartDate, "yyyy-MM-dd");
      const formattedEndDate = format(finalEndDate, "yyyy-MM-dd");

      onSelectDateRange(formattedStartDate, formattedEndDate, frequency);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 600,
          height: 400,
          overflow: "visible",
        },
      }}
    >
      <DialogTitle>Select Date Range and Frequency</DialogTitle>
      <DialogContent sx={{ overflow: "visible" }}>
        <Box display="flex" flexDirection="row" gap={2} mt={1}>
          <DatePicker
            selected={startDate}
            onChange={(date: Date | null) => setStartDate(date)}
            selectsStart
            startDate={startDate}
            endDate={endDate}
            customInput={<TextField label="Start Date" variant="outlined" fullWidth />}
            dateFormat="MMMM d, yyyy"
          />
          <DatePicker
            selected={endDate}
            onChange={(date: Date | null) => setEndDate(date)}
            selectsEnd
            startDate={startDate}
            endDate={endDate}
            customInput={<TextField label="End Date" variant="outlined" fullWidth />}
            dateFormat="MMMM d, yyyy"
          />
          <FormControl variant="outlined">
            <InputLabel id="frequency-label">Frequency</InputLabel>
            <Select
              labelId="frequency-label"
              value={frequency}
              onChange={(event: SelectChangeEvent<CustomDashboardFrequency>) =>
                setFrequency(event.target.value as CustomDashboardFrequency)
              }
              label="Frequency"
            >
              {frequencyOptions.map((option) => (
                <MenuItem
                  key={option}
                  value={option}
                  // Disable the option if diffDays is defined and exceeds its limit.
                  disabled={diffDays !== null && diffDays > frequencyLimits[option]}
                >
                  {option === "Hour" && "Hourly"}
                  {option === "Day" && "Daily"}
                  {option === "Week" && "Weekly"}
                  {option === "Month" && "Monthly"}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleOk}
          disabled={
            !startDate ||
            !endDate ||
            (diffDays !== null && diffDays > frequencyLimits[frequency])
          }
        >
          OK
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DateRangePickerDialog;
