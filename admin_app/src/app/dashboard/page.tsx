"use client";

import React from "react";
import { Box, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period } from "./types";
import Overview from "@/app/dashboard/components/Overview";
import Performance from "@/app/dashboard/components/Performance";
import { useState } from "react";
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
        return <Performance />;
      case "Insights":
        return <div>Products</div>;
      default:
        return <div>Page not found</div>;
    }
  };

  return (
    <>
      <Box
        sx={{ display: "flex", mt: 4, flexDirection: "row", height: "100%" }}
      >
        <Box sx={{ width: 240, display: "flex", height: "100%" }}>
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
              height: "100%",
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
            <TabPanel tabValue={timePeriod} handleChange={handleTabChange} />
            <Box sx={{ flexGrow: 1, height: "100%" }}>{showPage()}</Box>
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Dashboard;
