"use client";
import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

interface DataPoint {
  x: number;
  y: number;
}

interface SeriesData {
  name: string;
  data: DataPoint[];
}

const StackedBarChart = ({ data }: { data: SeriesData[] }) => {
  const options: ApexOptions = {
    chart: {
      type: "bar",
      stacked: true,
      stackType: "normal",
      fontFamily: "Inter",
    },
    dataLabels: {
      enabled: false,
    },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
      },
    },
    yaxis: {
      title: {
        text: "Number of Queries",
      },
      min: 0,
      forceNiceScale: true,
    },
    legend: {
      position: "top",
      horizontalAlign: "left",
      markers: {
        shape: "circle",
      },
    },
    colors: [
      appColors.dashboardPurple, // Urgent + downvoted -> purple
      appColors.dashboardDownvote, // Downvoted only -> blue
      appColors.dashboardPrimary, // Normal -> green
      appColors.dashboardUpvote, // Urgent only -> faded red
    ],
    tooltip: {
      x: {
        format: "dd MMM yyyy",
      },
    },
    noData: {
      text: "No data available",
      align: "center",
      verticalAlign: "middle",
      style: {
        color: "#444",
        fontSize: "14px",
      },
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
