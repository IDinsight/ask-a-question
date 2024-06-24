"use client";

import React from "react";
import { Box, Container, Grid, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import Overview from "@/app/dashboard/components/Overview";
import { useState } from "react";
import { Global, css } from "@emotion/react";

const Dashboard: React.FC = () => {
  const [dashboardPage, setDashboardPage] = useState<PageName>("Overview");
  const [tabValue, setTabValue] = useState(1);

  const handleTabChange = (event: React.ChangeEvent<{}>, newValue: number) => {
    setTabValue(newValue);
  };

  const showPage = () => {
    switch (dashboardPage) {
      case "Overview":
        return <Overview />;
      case "Performance":
        return <div>Users</div>;
      case "Insights":
        return <div>Products</div>;
      default:
        return <div>Page not found</div>;
    }
  };

  return (
    <>
      <Global
        styles={css`
          body {
            background-color: #fafafa;
          }
        `}
      />
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
              <Typography variant="h4">{dashboardPage}</Typography>
            </Box>
            <TabPanel tabValue={tabValue} handleChange={handleTabChange} />
            <Box sx={{ flexGrow: 1 }}>{showPage()}</Box>
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Dashboard;
