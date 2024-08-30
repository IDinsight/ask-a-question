"use client";
import dynamic from "next/dynamic";

import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const AreaChart = ({ data }: { data: any }) => {
  const timeseriesOptions: ApexOptions = {
    chart: {
      id: "usage-timeseries",
      stacked: true,
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
    legend: {
      position: "top",
      horizontalAlign: "left",
    },
    colors: [
      appColors.dashboardUrgent,
      appColors.dashboardSecondary,
      appColors.dashboardPrimary,
    ],
  };
  return (
    <div>
      <ReactApexcharts
        type="area"
        width="100%"
        height={450}
        options={timeseriesOptions}
        series={data}
      />
    </div>
  );
};

export default AreaChart;
