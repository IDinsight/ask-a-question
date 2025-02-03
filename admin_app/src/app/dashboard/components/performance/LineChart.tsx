"use client";

import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), { ssr: false });

interface LineChartProps {
  data: any; // array of ApexData series
  nTopContent: number;
  timePeriod: string;
  chartColors: string[];
}

const LineChart = ({ data, timePeriod, chartColors }: LineChartProps) => {
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
    dataLabels: { enabled: false },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
        format: "MMM dd", // e.g. "Jan 01"
      },
      // You can also control the tick amount if desired:
      tickAmount: 6,
    },
    yaxis: {
      tickAmount: 5,
      labels: {
        formatter: (value) => String(Math.round(value)),
      },
    },
    tooltip: {
      x: {
        format: "MMM dd, yyyy", // tooltip format
      },
    },
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    stroke: {
      width: 3,
      curve: "smooth",
      dashArray: data.map(() => 0),
    },
    colors: chartColors,
  };

  return (
    <div>
      <ReactApexcharts
        type="line"
        height={400}
        width="100%"
        options={timeseriesOptions}
        series={data}
      />
    </div>
  );
};

export default LineChart;
