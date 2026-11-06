"use client";

import React, { useState } from "react";
import { Box, Typography } from "@mui/material";
import { useSearchParams } from "next/navigation";
import { PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import {
  Period,
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
  /** Value of the ?page= search param used by the app sidebar links. */
  slug: string;
  description: string;
};

const pages: Page[] = [
  {
    name: "Overview",
    slug: "overview",
    description: "Overview of user engagement and satisfaction",
  },
  {
    name: "Content Performance",
    slug: "content-performance",
    description: "Track performance of contents...",
  },
  {
    name: "Query Topics",
    slug: "query-topics",
    description: "Find out what users are asking...",
  },
];

const Dashboard: React.FC = () => {
  // The sub-page is picked from the app sidebar via ?page=<slug>.
  // Unknown or missing values fall back to Overview.
  const searchParams = useSearchParams();
  const dashboardPage =
    pages.find((p) => p.slug === searchParams.get("page")) ?? pages[0];
  const [timePeriod, setTimePeriod] = useState<Period>("week");
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
      <Box
        sx={{
          paddingInline: 3,
          height: "100%",
          flexGrow: 1,
          width: "100%",
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
