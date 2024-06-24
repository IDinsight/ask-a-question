import * as React from "react";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Box from "@mui/material/Box";

interface TabPanelProps {
  tabValue: number;
  handleChange: (event: React.SyntheticEvent, newValue: number) => void;
}

const TabPanel: React.FC<TabPanelProps> = ({ tabValue, handleChange }) => {
  const tabLabels = ["Last 24 hours", "Last week", "Last month", "Last year"];
  return (
    <Box sx={{ my: 1 }}>
      <Tabs value={tabValue} onChange={handleChange}>
        {tabLabels.map((label, index) => (
          <Tab
            label={label}
            key={`tab-label-${index}`}
            sx={{ textTransform: "none", mr: 6 }}
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default TabPanel;
