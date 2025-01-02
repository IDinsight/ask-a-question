"use client";
import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";
import { ApexSeriesData } from "../../types";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

interface StackedBarChartProps {
  data: ApexSeriesData[];
  showDayOfWeek?: boolean;
}

const StackedBarChart: React.FC<StackedBarChartProps> = ({ data, showDayOfWeek }) => {
  const options: ApexOptions = {
    chart: {
      type: "bar",
      stacked: true,
      fontFamily: "Inter",
    },
    dataLabels: { enabled: false },
    xaxis: {
      type: "datetime",
      labels: {
        format: showDayOfWeek ? "ddd d" : undefined, // Show D.O.W. like "Mon 1" if showDayOfWeek is true
        // Otherwise the default format adapts to the data
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
      appColors.dashboardUpvote, // normal -> green
      appColors.dashboardDownvote, // downvoted -> light red
      appColors.dashboardUrgent, // urgent -> bright red
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
