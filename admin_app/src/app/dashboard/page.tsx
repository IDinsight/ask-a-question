"use client";

import React from "react";
import { Box, Container, Grid, Typography } from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import { useState } from "react";

const Dashboard: React.FC = () => {
  const [dashboardPage, setDashboardPage] = useState<PageName>("Overview");
  return (
    <>
      <Sidebar
        setDashboardPage={setDashboardPage}
        selectedDashboardPage={dashboardPage}
      />
      <Box sx={{ flexGrow: 1, m: 10 }}>
        <Typography variant="h5">{dashboardPage}</Typography>
      </Box>
    </>
  );
};

export default Dashboard;
