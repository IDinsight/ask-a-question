"use client";
import dynamic from "next/dynamic";
import Card from "@mui/material/Card";
import { useTheme } from "@mui/material/styles";
import CardHeader from "@mui/material/CardHeader";
import CardContent from "@mui/material/CardContent";

import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});
const WeeklyOverview = ({
  labels,
  data,
}: {
  labels: Array<string>;
  data: Array<number>;
}) => {
  const theme = useTheme();

  const options: ApexOptions = {
    chart: {
      parentHeightOffset: 0,
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        borderRadius: 9,
        columnWidth: "30%",
      },
    },
    stroke: {
      width: 2,
      colors: [theme.palette.background.paper],
    },
    legend: { show: false },
    grid: {
      strokeDashArray: 7,
      padding: {
        top: -1,
        right: 0,
        left: -12,
        bottom: 5,
      },
    },
    dataLabels: { enabled: true },
    colors: [
      theme.palette.background.default,
      theme.palette.background.default,
      theme.palette.background.default,
      theme.palette.primary.main,
      theme.palette.background.default,
      theme.palette.background.default,
    ],
    states: {
      hover: {
        filter: { type: "none" },
      },
      active: {
        filter: { type: "none" },
      },
    },
    xaxis: {
      categories: labels,
      tickPlacement: "on",
      labels: { show: true },
      axisTicks: { show: false },
      axisBorder: { show: false },
      title: {
        text: "Date",
      },
    },
    yaxis: {
      show: true,
      title: {
        text: "Number of questions",
      },
      tickAmount: 5,
      labels: {
        formatter: (value) =>
          `${value > 999 ? `${(value / 1000).toFixed(0)}k` : value}`,
      },
    },
  };

  return (
    <Card>
      <CardHeader
        title="Timeline"
        titleTypographyProps={{
          sx: {
            lineHeight: "2rem !important",
            letterSpacing: "0.15px !important",
          },
        }}
      />
      <CardContent
        sx={{ "& .apexcharts-xcrosshairs.apexcharts-active": { opacity: 0 } }}
      >
        <ReactApexcharts
          type="bar"
          height={300}
          width={"100%"}
          options={options}
          series={[{ name: "Monthly number of questions", data: data }]}
        />
      </CardContent>
    </Card>
  );
};

export default WeeklyOverview;
