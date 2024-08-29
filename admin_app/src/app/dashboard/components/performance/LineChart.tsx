"use client";
import dynamic from "next/dynamic";

import { appColors } from "@/utils/index";
import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const LineChart = ({
  data,
  nTopContent,
  timePeriod,
}: {
  data: any;
  nTopContent: number;
  timePeriod: string;
}) => {
  const timeseriesOptions: ApexOptions = {
    title: {
      text: `Top content in the last ${timePeriod}`,
      align: "left",
      style: {
        fontSize: "18px",
        fontWeight: 500,
        color: appColors.black,
      },
    },
    chart: {
      id: "content-performance-timeseries",
      stacked: false,
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
      tickAmount: 5,
      labels: {
        formatter: function (value) {
          return String(Math.round(value)); // Format labels to show whole numbers
        },
      },
    },
    legend: {
      show: false,
      position: "top",
      horizontalAlign: "left",
    },
    stroke: {
      width: [3, ...Array(nTopContent).fill(3)],
      curve: "smooth",
      dashArray: [0, ...Array(nTopContent).fill(7)],
    },
    colors: appColors.dashboardBlueShades,
  };

  return (
    <div>
      <ReactApexcharts
        type="line"
        height={270}
        width="100%"
        options={timeseriesOptions}
        series={data}
      />
    </div>
  );
};

export default LineChart;
