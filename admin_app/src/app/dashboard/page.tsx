"use client";

import React from "react";
import { Box, IconButton, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period } from "./types";
import Overview from "@/app/dashboard/components/Overview";
import { useState } from "react";
import { appColors } from "@/utils";
import MenuIcon from "@mui/icons-material/Menu";

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
        <Box sx={{ width: sideBarOpen ? 240 : 80, display: "flex" }}>
          <Sidebar
            open={sideBarOpen}
            setOpen={setSideBarOpen}
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
                display: "flex",
                py: 2,
                borderBottom: "1px solid",
                borderBottomColor: "divider",
              }}
            >
              <IconButton
                color="inherit"
                size="medium"
                aria-label="open drawer"
                onClick={handleDrawerOpen}
                edge="start"
                sx={{
                  mr: 2,
                  ...(sideBarOpen && { display: "none" }),
                }}
              >
                <MenuIcon />
              </IconButton>
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
