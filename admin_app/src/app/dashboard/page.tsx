"use client";

import React from "react";
import { Box, IconButton, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period, drawerWidth } from "./types";
import Overview from "@/app/dashboard/components/Overview";
import { useState } from "react";
import { appColors } from "@/utils";

const Dashboard: React.FC = () => {
  const [dashboardPage, setDashboardPage] = useState<PageName>("Overview");
  const [timePeriod, setTimePeriod] = useState<Period>("week" as Period);
  const [sideBarOpen, setSideBarOpen] = useState<boolean>(true);
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
        return <div>Products</div>;
      default:
        return <div>Page not found</div>;
    }
  };

  const handleDrawerOpen = () => {
    setSideBarOpen(true);
  };

  return (
    <>
      <Box sx={{ display: "flex", marginTop: 2, flexDirection: "row" }}>
        <Sidebar
          open={sideBarOpen}
          setOpen={setSideBarOpen}
          setDashboardPage={setDashboardPage}
          selectedDashboardPage={dashboardPage}
        />
        <Box
          sx={{
            px: 3,
            height: "100%",
            flexGrow: 1,
            width: `calc(100% - ${sideBarOpen ? drawerWidth : 0}px)`,
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
                display: "flex",
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
            <Box sx={{ flexGrow: 1 }}>{showPage()}</Box>
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Dashboard;
