"use client";

import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
} from "@mui/material";
import { Sidebar, PageName } from "@/app/dashboard/components/Sidebar";
import TabPanel from "@/app/dashboard/components/TabPanel";
import { Period, drawerWidth, CustomDateRange } from "./types";
import Overview from "@/app/dashboard/components/Overview";
import ContentPerformance from "@/app/dashboard/components/ContentPerformance";
import Insights from "./components/Insights";
import { appColors } from "@/utils";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

type Page = {
  name: PageName;
  description: string;
};

const pages: Page[] = [
  {
    name: "Overview",
    description: "Overview of user engagement and satisfaction",
  },
  {
    name: "Content Performance",
    description: "Track performance of contents  and identify areas for improvement",
  },
  {
    name: "Query Topics",
    description:
      "Find out what users are asking about to inform creating and updating contents",
  },
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
  const [tempStart, setTempStart] = useState<Date | null>(null);
  const [tempEnd, setTempEnd] = useState<Date | null>(null);

  const handleTabChange = (_: React.ChangeEvent<{}>, newValue: Period) => {
    if (newValue === "custom") {
      if (customDateRange.startDate && customDateRange.endDate) {
        setTimePeriod("custom");
      } else {
        setTempStart(null);
        setTempEnd(null);
        setIsDialogOpen(true);
      }
    } else {
      setTimePeriod(newValue);
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  const handleSaveDialog = () => {
    if (tempStart && tempEnd) {
      setCustomDateRange({ startDate: tempStart, endDate: tempEnd });
      setTimePeriod("custom");
    }
    setIsDialogOpen(false);
  };

  const showPage = () => {
    switch (dashboardPage.name) {
      case "Overview":
        return <Overview timePeriod={timePeriod} />;
      case "Content Performance":
        return <ContentPerformance timePeriod={timePeriod} />;
      case "Query Topics":
        return <Insights timePeriod={timePeriod} />;
      default:
        return <div>Page not found.</div>;
    }
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1075) {
        setSideBarOpen(false);
      } else {
        setSideBarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    setTimeout(() => {
      handleResize();
    }, 750);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
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
          <TabPanel tabValue={timePeriod} handleChange={handleTabChange} />
          <Box sx={{ flexGrow: 1, height: "100%" }}>{showPage()}</Box>
        </Box>
      </Box>
      <Dialog
        open={isDialogOpen}
        onClose={handleCloseDialog}
        PaperProps={{
          sx: {
            width: 420,
            height: 420,
            overflow: "visible",
          },
        }}
      >
        <DialogTitle>Select Date Range</DialogTitle>
        <DialogContent sx={{ overflow: "visible" }}>
          <Box display="flex" flexDirection="column" gap={4} mt={1}>
            <DatePicker
              selected={tempStart}
              onChange={(date) => setTempStart(date)}
              selectsStart
              startDate={tempStart}
              endDate={tempEnd}
              customInput={
                <TextField label="Start Date" variant="outlined" fullWidth />
              }
              dateFormat="MMMM d, yyyy"
              popperClassName="bigDatePickerPopper"
            />
            <DatePicker
              selected={tempEnd}
              onChange={(date) => setTempEnd(date)}
              selectsEnd
              startDate={tempStart}
              endDate={tempEnd}
              customInput={<TextField label="End Date" variant="outlined" fullWidth />}
              dateFormat="MMMM d, yyyy"
              popperClassName="bigDatePickerPopper"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveDialog} disabled={!tempStart || !tempEnd}>
            OK
          </Button>
        </DialogActions>
        <style jsx global>{`
          .bigDatePickerPopper .react-datepicker {
            transform: scale(1.5);
            transform-origin: top left;
          }
        `}</style>
      </Dialog>
    </Box>
  );
};

export default Dashboard;
