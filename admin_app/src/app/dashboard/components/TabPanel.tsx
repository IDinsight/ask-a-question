import React from "react";
import { Tabs, Tab, Box, IconButton } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { Period } from "../types";

interface TabPanelProps {
  tabValue: Period;
  handleChange: (event: React.SyntheticEvent, newValue: Period) => void;
  onEditCustomPeriod?: () => void;
  customDateRangeSet?: boolean;
}

const TabPanel: React.FC<TabPanelProps> = ({
  tabValue,
  handleChange,
  onEditCustomPeriod,
  customDateRangeSet,
}) => {
  return (
    <Box sx={{ my: 1 }}>
      <Tabs value={tabValue} onChange={handleChange}>
        <Tab label="Day" value="day" />
        <Tab label="Week" value="week" />
        <Tab label="Month" value="month" />
        <Tab label="Year" value="year" />
        <Tab
          value="custom"
          label={
            <Box display="flex" alignItems="center">
              Custom
              {customDateRangeSet && onEditCustomPeriod && (
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditCustomPeriod();
                  }}
                  sx={{ ml: 0.5 }}
                >
                  <EditIcon fontSize="small" />
                </IconButton>
              )}
            </Box>
          }
        />
      </Tabs>
    </Box>
  );
};

export default TabPanel;
