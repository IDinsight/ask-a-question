import * as React from "react";
import { Tabs, Tab, Box, IconButton } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { Period, TimeFrame } from "../types";

interface TabPanelProps {
  tabValue: Period;
  handleChange: (event: React.SyntheticEvent, newValue: Period) => void;
  onEditCustomPeriod?: () => void;
  customDateRangeSet?: boolean;
}

const tabLabels: Record<TimeFrame, Period> = {
  "Last 24 hours": "day",
  "Last week": "week",
  "Last month": "month",
  "Last year": "year",
  Custom: "custom",
};

const TabPanel: React.FC<TabPanelProps> = ({
  tabValue,
  handleChange,
  onEditCustomPeriod,
  customDateRangeSet,
}) => {
  const timePeriods = Object.entries(tabLabels) as [TimeFrame, Period][];

  return (
    <Box sx={{ my: 1 }}>
      <Tabs value={tabValue} onChange={handleChange}>
        {timePeriods.map(([label, periodValue], index) => (
          <Tab
            key={`tab-${index}`}
            value={periodValue}
            sx={{ textTransform: "none", marginRight: 6 }}
            label={
              periodValue === "custom" ? (
                <Box display="flex" alignItems="center">
                  {label}
                  {customDateRangeSet && onEditCustomPeriod && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditCustomPeriod();
                      }}
                      sx={{ ml: 1 }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              ) : (
                label
              )
            }
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default TabPanel;
