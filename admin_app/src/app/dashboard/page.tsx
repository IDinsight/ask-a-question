"use client";

import React, { useState } from "react";
import { Box, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period } from "./types";
import Overview from "./components/Overview";
import TopicFiles from "@/app/dashboard/components/TopicFiles";
import { appColors } from "@/utils";

const Dashboard: React.FC = () => {
  const [dashboardPage, setDashboardPage] = useState<PageName>("Overview");
  const [timePeriod, setTimePeriod] = useState<Period>("week" as Period);

  const handleTabChange = (_: React.ChangeEvent<{}>, newValue: Period) => {
    setTimePeriod(newValue);
  };

  const showPage = () => {
    switch (dashboardPage) {
      case "Overview":
        return <Overview timePeriod={timePeriod} />;
      case "Performance":
        return <div>Users</div>;
      case "Insights":
        return <TopicFiles />;
      default:
        return <div>Page not found</div>;
    }
  };

  // Function to determine if TabPanel should be shown
  const shouldShowTabPanel = () => {
    return dashboardPage !== "Insights";
  };

  return (
    <>
      <Box sx={{ display: "flex", mt: 4, flexDirection: "row" }}>
        <Box sx={{ width: 240, display: "flex" }}>
          <Sidebar
            setDashboardPage={setDashboardPage}
            selectedDashboardPage={dashboardPage}
          />
        </Box>
        <Box
          sx={{
            px: 3,
            height: "100%",
            flexGrow: 1,
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <Box
              sx={{
                py: 2,
                borderBottom: "1px solid",
                borderBottomColor: "divider",
              }}
            >
              <Typography variant="h4" color={appColors.primary}>
                {dashboardPage}
              </Typography>
            </Box>
            {shouldShowTabPanel() && (
              <TabPanel tabValue={timePeriod} handleChange={handleTabChange} />
            )}
            <Box sx={{ flexGrow: 1 }}>{showPage()}</Box>
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Dashboard;
