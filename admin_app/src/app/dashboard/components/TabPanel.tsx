import React from "react";
import { Tabs, Tab, Box, IconButton } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { Period, TimeFrame } from "../types";

interface TabPanelProps {
  tabValue: Period;
  handleChange: (event: React.SyntheticEvent, newValue: Period) => void;
  onEditCustomPeriod?: () => void;
  customDateParamsSet?: boolean;
}

const tabLabels: Record<TimeFrame, Period> = {
  "Last 24 hours": "day",
  "Last week": "week",
  "Last month": "month",
  "Last year": "year",
};

const TabPanel: React.FC<TabPanelProps> = ({
  tabValue,
  handleChange,
  onEditCustomPeriod,
  customDateParamsSet,
}) => {
  const timePeriods = Object.entries(tabLabels) as [TimeFrame, Period][];

  return (
    <Box sx={{ my: 1 }}>
      <Tabs value={tabValue} onChange={handleChange}>
        {timePeriods.map(([label, periodValue], index) => (
          <Tab
            key={`tab-${index}`}
            label={label}
            value={periodValue}
            sx={{ textTransform: "none", marginRight: 6 }}
          />
        ))}
        <Tab
          value="custom"
          sx={{ textTransform: "none" }}
          label={
            <Box display="flex" alignItems="center">
              Custom
              {customDateParamsSet && onEditCustomPeriod && (
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
