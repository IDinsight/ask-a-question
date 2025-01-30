import React, { useEffect, useState } from "react";
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

const timeFrequencies: CustomDashboardFrequency[] = ["Hour", "Day", "Week", "Month"];

interface DateRangePickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelectDateRange: (
    startDate: Date,
    endDate: Date,
    frequency: CustomDashboardFrequency,
  ) => void;
  initialStartDate?: Date | null;
  initialEndDate?: Date | null;
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

  useEffect(() => {
    if (open) {
      setStartDate(initialStartDate);
      setEndDate(initialEndDate);
      setFrequency(initialFrequency || "Day");
    }
  }, [open, initialStartDate, initialEndDate, initialFrequency]);

  const handleOk = () => {
    if (startDate && endDate) {
      // Ensure startDate is before endDate
      const [finalStartDate, finalEndDate] =
        startDate > endDate ? [endDate, startDate] : [startDate, endDate];
      onSelectDateRange(finalStartDate, finalEndDate, frequency);
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
              <MenuItem value="Hour">Hourly</MenuItem>
              <MenuItem value="Day">Daily</MenuItem>
              <MenuItem value="Week">Weekly</MenuItem>
              <MenuItem value="Month">Monthly</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleOk} disabled={!startDate || !endDate}>
          OK
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DateRangePickerDialog;
