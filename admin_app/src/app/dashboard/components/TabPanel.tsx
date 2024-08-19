import * as React from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Box from "@mui/material/Box";

import { Period, TimeFrame } from "../types";

interface TabPanelProps {
  tabValue: Period;
  handleChange: (event: React.SyntheticEvent, newValue: Period) => void;
}

const tabLabels: Record<TimeFrame, Period> = {
  "Last 24 hours": "day",
  "Last week": "week",
  "Last month": "month",
  "Last year": "year",
};

const TabPanel: React.FC<TabPanelProps> = ({ tabValue, handleChange }) => {
  const timePeriods: TimeFrame[] = Object.keys(tabLabels) as TimeFrame[];

  return (
    <Box sx={{ my: 1 }}>
      <Tabs value={tabValue} onChange={handleChange}>
        {timePeriods.map((label: TimeFrame, index: number) => (
          <Tab
            label={label}
            key={`tab-label-${index}`}
            value={tabLabels[label]}
            sx={{ textTransform: "none", marginRight: 6 }}
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default TabPanel;
