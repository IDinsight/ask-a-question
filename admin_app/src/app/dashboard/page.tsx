"use client";

import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period, drawerWidth } from "./types";
import Overview from "@/app/dashboard/components/Overview";
import { useState } from "react";
import { appColors } from "@/utils";
import { ClickAwayListener } from "@mui/base/ClickAwayListener";

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

  // Close sidebar on small screens
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1075) {
        setSideBarOpen(false);
      } else {
        setSideBarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    // wait 0.75s before first resize (so user can acknowledge the sidebar)
    setTimeout(() => {
      handleResize();
    }, 750);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <>
      <Box sx={{ display: "flex", marginTop: 4, flexDirection: "row" }}>
        <ClickAwayListener onClickAway={() => setSideBarOpen(false)}>
          <Sidebar
            open={sideBarOpen}
            setOpen={setSideBarOpen}
            setDashboardPage={setDashboardPage}
            selectedDashboardPage={dashboardPage}
          />
        </ClickAwayListener>
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
