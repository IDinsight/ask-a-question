"use client";

import React, { useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import {
  Period,
  drawerWidth,
  CustomDateParams,
  CustomDashboardFrequency,
} from "./types";
import Overview from "@/app/dashboard/components/Overview";
import ContentPerformance from "@/app/dashboard/components/ContentPerformance";
import Insights from "./components/Insights";
import { appColors } from "@/utils";
import DateRangePickerDialog from "@/app/dashboard/components/DateRangePicker";

type Page = {
  name: PageName;
  description: string;
};

const pages: Page[] = [
  { name: "Overview", description: "Overview of user engagement and satisfaction" },
  { name: "Content Performance", description: "Track performance of contents..." },
  { name: "Query Topics", description: "Find out what users are asking..." },
];

const Dashboard: React.FC = () => {
  const [dashboardPage, setDashboardPage] = useState<Page>(pages[0]);
  const [timePeriod, setTimePeriod] = useState<Period>("week");
  const [sideBarOpen, setSideBarOpen] = useState(true);
  const [customDateParams, setCustomDateParams] = useState<CustomDateParams>({
    startDate: null,
    endDate: null,
    frequency: "Day",
  });
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleTabChange = (_: React.SyntheticEvent, newValue: Period) => {
    if (newValue === "custom") {
      if (customDateParams.startDate && customDateParams.endDate) {
        setTimePeriod("custom");
      } else {
        setIsDialogOpen(true);
      }
    } else {
      setTimePeriod(newValue);
    }
  };

  const handleEditCustomPeriod = () => {
    setIsDialogOpen(true);
  };

  const handleCustomDateParamsSelected = (
    start: string,
    end: string,
    frequency: CustomDashboardFrequency,
  ) => {
    setCustomDateParams({ startDate: start, endDate: end, frequency: frequency });
    setTimePeriod("custom");
    setIsDialogOpen(false);
  };

  const showPage = () => {
    switch (dashboardPage.name) {
      case "Overview":
        return (
          <Overview
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
          />
        );
      case "Content Performance":
        return (
          <ContentPerformance
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
          />
        );
      case "Query Topics":
        return (
          <Insights
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
          />
        );
      default:
        return <div>Page not found.</div>;
    }
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1075) setSideBarOpen(false);
      else setSideBarOpen(true);
    };
    window.addEventListener("resize", handleResize);
    // wait 0.75s before first resize (so user can acknowledge the sidebar)
    setTimeout(handleResize, 750);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <Box
      sx={{
        display: "flex",
        paddingTop: 5,
        flexDirection: "row",
        minWidth: "900px",
        maxWidth: "1900px",
      }}
    >
      <Sidebar
        open={sideBarOpen}
        setOpen={setSideBarOpen}
        setDashboardPage={(pageName: PageName) => {
          const page = pages.find((p) => p.name === pageName);
          if (page) setDashboardPage(page);
        }}
        selectedDashboardPage={dashboardPage.name}
      />
      <Box
        sx={{
          paddingInline: 3,
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
            height: "100%",
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              paddingInline: 2,
              paddingBottom: 1,
              gap: 2,
              borderBottom: "1px solid",
              borderBottomColor: "divider",
            }}
          >
            <Typography variant="h4" color={appColors.primary}>
              {dashboardPage.name}
            </Typography>
            <Typography variant="body1" align="left" color={appColors.darkGrey}>
              {dashboardPage.description}
            </Typography>
          </Box>
          <TabPanel
            tabValue={timePeriod}
            handleChange={handleTabChange}
            onEditCustomPeriod={handleEditCustomPeriod}
            customDateParamsSet={
              !!(
                customDateParams.startDate &&
                customDateParams.endDate &&
                customDateParams.frequency
              )
            }
          />
          <Box sx={{ flexGrow: 1, height: "100%" }}>{showPage()}</Box>
        </Box>
      </Box>

      <DateRangePickerDialog
        open={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSelectDateRange={handleCustomDateParamsSelected}
        initialStartDate={customDateParams.startDate}
        initialEndDate={customDateParams.endDate}
        initialFrequency={customDateParams.frequency}
      />
    </Box>
  );
};

export default Dashboard;
