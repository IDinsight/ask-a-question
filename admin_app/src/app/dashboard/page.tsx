"use client";

import React, { useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period, drawerWidth, CustomDateRange } from "./types";
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
  const [customDateRange, setCustomDateRange] = useState<CustomDateRange>({
    startDate: null,
    endDate: null,
  });
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleTabChange = (_: React.SyntheticEvent, newValue: Period) => {
    if (newValue === "custom") {
      if (customDateRange.startDate && customDateRange.endDate) {
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

  const handleCustomDateRangeSelected = (start: Date, end: Date) => {
    setCustomDateRange({ startDate: start, endDate: end });
    setTimePeriod("custom");
    setIsDialogOpen(false);
  };

  const showPage = () => {
    switch (dashboardPage.name) {
      case "Overview":
        return (
          <Overview
            timePeriod={timePeriod}
            customDateRange={timePeriod === "custom" ? customDateRange : undefined}
          />
        );
      case "Content Performance":
        return (
          <ContentPerformance
            timePeriod={timePeriod}
            customDateRange={timePeriod === "custom" ? customDateRange : undefined}
          />
        );
      case "Query Topics":
        return (
          <Insights
            timePeriod={timePeriod}
            customDateRange={timePeriod === "custom" ? customDateRange : undefined}
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
        <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
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
            customDateRangeSet={
              !!(customDateRange.startDate && customDateRange.endDate)
            }
          />
          <Box sx={{ flexGrow: 1, height: "100%" }}>{showPage()}</Box>
        </Box>
      </Box>

      <DateRangePickerDialog
        open={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSelectDateRange={handleCustomDateRangeSelected}
        initialStartDate={customDateRange.startDate}
        initialEndDate={customDateRange.endDate}
      />
    </Box>
  );
};

export default Dashboard;
