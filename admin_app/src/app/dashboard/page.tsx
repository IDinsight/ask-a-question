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

  const topics = [
    {
      name: "Flu",
      count: 52,
      examples: [
        {
          timestamp: "2024-07-23 06:01PM",
          userQuestion:
            "What are the eligibility criteria for becoming an Empowered Girls Mobiliser?",
        },
        {
          timestamp: "2024-07-24 02:15PM",
          userQuestion: "How can I prevent the flu?",
        },
      ],
    },
    {
      name: "Headache",
      count: 344,
      examples: [
        {
          timestamp: "2024-07-25 08:30AM",
          userQuestion: "What are the common causes of headaches?",
        },
        {
          timestamp: "2024-07-25 09:45AM",
          userQuestion: "What are some natural remedies for headaches?",
        },
      ],
    },
    {
      name: "Coughing",
      count: 29,
      examples: [
        {
          timestamp: "2024-07-26 11:00AM",
          userQuestion: "Why do I have a persistent cough?",
        },
        {
          timestamp: "2024-07-26 01:20PM",
          userQuestion: "When should I see a doctor for a cough?",
        },
      ],
    },
  ];

  const showPage = () => {
    switch (dashboardPage) {
      case "Overview":
        return <Overview timePeriod={timePeriod} />;
      case "Performance":
        return <div>Users</div>;
      case "Insights":
        return <TopicFiles topics={topics} />;
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
