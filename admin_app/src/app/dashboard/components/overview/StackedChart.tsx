"use client";
import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";
import { ApexSeriesData } from "../../types";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const dayOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface StackedBarChartProps {
  data: ApexSeriesData[];
  showDayOfWeek?: boolean;
}

const StackedBarChart: React.FC<StackedBarChartProps> = ({ data, showDayOfWeek }) => {
  // Formatter for weekly day-of-week labels.
  const weeklyFormatter = (val: string) => {
    const d = new Date(val);
    return `${dayOfWeek[d.getDay()]}, ${d.getDate()}`;
  };

  const options: ApexOptions = {
    chart: {
      type: "bar",
      stacked: true,
      stackType: "normal",
      fontFamily: "Inter",
    },
    dataLabels: { enabled: false },
    xaxis: {
      type: "datetime",
      labels: {
        format: showDayOfWeek ? "ddd d" : undefined,
      },
    },
    yaxis: {
      title: { text: "Number of Queries" },
      min: 0,
      forceNiceScale: true,
    },
    legend: {
      position: "top",
      horizontalAlign: "left",
      markers: { shape: "circle" },
    },
    colors: [
      appColors.dashboardPurple, // Urgent + downvoted -> purple
      appColors.dashboardDownvote, // Downvoted only -> blue
      appColors.dashboardPrimary, // Normal -> green
      appColors.dashboardUpvote, // Urgent only -> faded red
    ],
    noData: {
      text: "No data available",
      align: "center",
      verticalAlign: "middle",
      style: { color: "#444", fontSize: "14px" },
    },
  };

  return (
    <div>
      <ReactApexcharts
        type="bar"
        width="100%"
        height={450}
        options={options}
        series={data}
      />
    </div>
  );
};

export default StackedBarChart;
