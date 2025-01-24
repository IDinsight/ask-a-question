import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
} from "@mui/material";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

interface DateRangePickerDialogProps {
  open: boolean;
  onClose: () => void;
  onSelectDateRange: (startDate: Date, endDate: Date) => void;
  initialStartDate?: Date | null;
  initialEndDate?: Date | null;
}

const DateRangePickerDialog: React.FC<DateRangePickerDialogProps> = ({
  open,
  onClose,
  onSelectDateRange,
  initialStartDate = null,
  initialEndDate = null,
}) => {
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);

  useEffect(() => {
    if (open) {
      setStartDate(initialStartDate);
      setEndDate(initialEndDate);
    }
  }, [open, initialStartDate, initialEndDate]);

  const handleOk = () => {
    if (startDate && endDate) {
      if (startDate > endDate) {
        onSelectDateRange(endDate, startDate);
      } else {
        onSelectDateRange(startDate, endDate);
      }
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Select Date Range</DialogTitle>
      <DialogContent>
        <Box display="flex" flexDirection="row" gap={2} mt={1}>
          <DatePicker
            selected={startDate}
            onChange={(date: Date) => setStartDate(date)}
            selectsStart
            startDate={startDate}
            endDate={endDate}
            customInput={<TextField label="Start Date" variant="outlined" fullWidth />}
            dateFormat="MMMM d, yyyy"
          />
          <DatePicker
            selected={endDate}
            onChange={(date: Date) => setEndDate(date)}
            selectsEnd
            startDate={startDate}
            endDate={endDate}
            customInput={<TextField label="End Date" variant="outlined" fullWidth />}
            dateFormat="MMMM d, yyyy"
          />
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
