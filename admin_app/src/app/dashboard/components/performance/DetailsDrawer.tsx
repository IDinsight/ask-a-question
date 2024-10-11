import { DrawerData } from "@/app/dashboard/types";
import TypingAnimation from "@/components/TypingAnimation";
import theme from "@/theme";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import Typography from "@mui/material/Typography";
import { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";
import React from "react";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

interface DetailsDrawerProps {
  open: boolean;
  onClose: (open: boolean) => (event: React.KeyboardEvent | React.MouseEvent) => void;
  data: DrawerData | null;
  aiSummary: string | null;
}

const ContentLineChart = ({ seriesData }: { seriesData: any }) => {
  const options: ApexOptions = {
    chart: {
      id: "drawer-line-chart",
      stacked: false,
      toolbar: {
        show: false,
      },
      zoom: {
        enabled: false,
      },
      fontFamily: "Inter",
    },
    stroke: {
      width: 3,
      curve: "straight",
    },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
      },
    },
    legend: {
      position: "top",
      horizontalAlign: "center",
      itemMargin: {
        horizontal: 40,
      },
    },
  };

  return (
    <ReactApexcharts
      type="line"
      height="100%"
      width={550}
      options={options}
      series={seriesData}
    />
  );
};

const StatCard: React.FC<{ title: string; value: number }> = ({ title, value }) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "left",
        justifyContent: "center",
        width: "100%",
        height: 100,
      }}
    >
      <Typography
        component="div"
        sx={{
          lineHeight: "24px",
          fontSize: "small",
          fontWeight: 300,
          color: "text.secondary",
        }}
      >
        {title}
      </Typography>
      <Typography
        variant="body2"
        sx={{ lineHeight: "16px", fontWeight: 800, fontSize: "small" }}
      >
        {value}
      </Typography>
    </Box>
  );
};

const DetailsDrawer: React.FC<DetailsDrawerProps> = ({
  open,
  onClose,
  data,
  aiSummary,
}) => {
  if (data === null) return null;
  return (
    <Drawer
      open={open && data !== null}
      onClose={onClose(false)}
      anchor="right"
      sx={{
        [`& .MuiDrawer-paper`]: { boxSizing: "border-box" },
        zIndex: 1000,
      }}
    >
      <Box sx={{ width: 550, pt: 7, margin: 3 }}>
        <Typography
          variant="h6"
          component="div"
          sx={{ lineHeight: "24px", fontWeight: 600 }}
        >
          {data.title}
        </Typography>

        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            alignItems: "stretch",
            gap: 2,
            maxWidth: 1387,
          }}
        >
          <StatCard title="Total Sent" value={data.query_count} />
          <StatCard title="Daily Average Sent" value={data.daily_query_count_avg} />
          <StatCard title="Total Upvotes" value={data.positive_votes} />
          <StatCard title="Total Downvotes" value={data.negative_votes} />
        </Box>

        <Box
          sx={{
            height: 300,
            width: "100%",
            border: 1,
            borderColor: "secondary.main",
            borderRadius: 2,
            alignItems: "center",
            justifyContent: "center",
            display: "flex",
            flexGrow: 1,
          }}
        >
          <ContentLineChart seriesData={data.line_chart_data} />
        </Box>
        <Divider sx={{ my: 3, borderBottomWidth: 2 }} />

        <Typography
          variant="h6"
          component="div"
          sx={{ lineHeight: "24px", mb: 3, fontWeight: 600 }}
        >
          Feedback by Users
        </Typography>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            maxWidth: 1387,
            maxheight: 400,
            border: 1,
            borderColor: "secondary.main",
            borderRadius: 2,
            background: "linear-gradient(to bottom, rgba(176,198,255,0.5), #ffffff)",
            p: 2,
            mb: 3,
          }}
        >
          <Box sx={{ display: "flex", flexDirection: "row", mb: 2 }}>
            <AutoAwesomeIcon sx={{ fontSize: 25, mr: 1, color: "#9eb2e5" }} />

            <Typography
              sx={{
                lineHeight: "24px",
                fontWeight: 600,
                fontColor: "black",
                textAlign: "center",
              }}
            >
              AI Overview
            </Typography>
          </Box>

          <Typography
            sx={{
              lineHeight: "15px",
              fontWeight: 300,
              fontSize: "small",
              fontColor: "black",
              textAlign: "left",
            }}
          >
            {aiSummary === null ? <TypingAnimation /> : aiSummary}
          </Typography>
        </Box>

        <TableContainer component={Paper} sx={{ mt: 2 }}>
          <Table aria-label="user feedback table">
            <TableHead sx={{ backgroundColor: theme.palette.lightgray.main }}>
              <TableRow>
                <TableCell sx={{ fontSize: "small", width: "20%" }}>
                  Timestamp
                </TableCell>
                <TableCell sx={{ fontSize: "small", width: "40%" }}>
                  User Question
                </TableCell>
                <TableCell sx={{ fontSize: "small", width: "40%" }}>
                  User Feedback
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.user_feedback.map((feedback) => (
                <TableRow
                  key={feedback.timestamp}
                  sx={{
                    borderBottom: 1,
                    borderColor: "secondary.main",
                    fontSize: "x-small",
                    overflow: "hidden",
                  }}
                >
                  <TableCell>
                    {Intl.DateTimeFormat("en-ZA", {
                      dateStyle: "short",
                      timeStyle: "short",
                    }).format(new Date(feedback.timestamp))}
                  </TableCell>
                  <TableCell>{feedback.question}</TableCell>
                  <TableCell>{feedback.feedback}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Drawer>
  );
};

export default DetailsDrawer;
