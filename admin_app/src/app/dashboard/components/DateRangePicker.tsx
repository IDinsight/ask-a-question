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
  Typography,
} from "@mui/material";
import DatePicker from "react-datepicker";
import { CustomDashboardFrequency } from "@/app/dashboard/types";
import "react-datepicker/dist/react-datepicker.css";

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

  const diffDays: number | null =
    startDate && endDate
      ? Math.abs(differenceInCalendarDays(endDate, startDate)) + 1
      : null;

  useEffect(() => {
    if (open) {
      setStartDate(initialStartDate ? new Date(initialStartDate) : null);
      setEndDate(initialEndDate ? new Date(initialEndDate) : null);
      setFrequency(initialFrequency || "Day");
    }
  }, [open, initialStartDate, initialEndDate, initialFrequency]);

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
      const [finalStartDate, finalEndDate] =
        startDate.getTime() > endDate.getTime()
          ? [endDate, startDate]
          : [startDate, endDate];
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
          height: "35vh",
          width: "750px",
          overflow: "visible",
          display: "flex",
          flexDirection: "column",
        },
      }}
    >
      <DialogTitle>Select Date Range and Frequency</DialogTitle>
      <DialogContent
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "visible",
        }}
      >
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
          <FormControl variant="outlined" sx={{ minWidth: 180 }}>
            <InputLabel id="frequency-label" sx={{ whiteSpace: "nowrap" }}>
              Frequency
            </InputLabel>
            <Select
              labelId="frequency-label"
              value={frequency}
              onChange={(event: SelectChangeEvent<CustomDashboardFrequency>) =>
                setFrequency(event.target.value as CustomDashboardFrequency)
              }
              label="Frequency"
              sx={{ whiteSpace: "nowrap" }}
            >
              {frequencyOptions.map((option) => (
                <MenuItem
                  key={option}
                  value={option}
                  disabled={diffDays !== null && diffDays > frequencyLimits[option]}
                >
                  {option === "Hour"
                    ? "Hourly"
                    : option === "Day"
                    ? "Daily"
                    : option === "Week"
                    ? "Weekly"
                    : "Monthly"}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <Box mt="auto" p={2} bgcolor="#e8f3fe" borderRadius={1} textAlign="center">
          <Typography variant="caption">
            Note: Frequency setting for custom timeframes will only affect bar graphs in
            the Overview page. The selected frequency will not affect Content
            Performance or Query Topics pages.
          </Typography>
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
