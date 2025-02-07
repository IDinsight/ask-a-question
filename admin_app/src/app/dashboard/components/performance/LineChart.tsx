"use client";

import dynamic from "next/dynamic";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), { ssr: false });

interface LineChartProps {
  data: any;
  nTopContent: number;
  timePeriod: string;
  chartColors: string[];
  orderBy: string;
  orderDirection: "ascending" | "descending";
  pageNumber: number;
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  timePeriod,
  chartColors,
  orderBy,
  orderDirection,
  pageNumber,
}) => {
  const legibleMapping: Record<string, string> = {
    query_count: "Daily Average Sent",
    positive_votes: "Upvotes",
    negative_votes: "Downvotes",
    query_count_timeseries: "Trend",
    title: "Title",
  };

  const displayOrderBy = legibleMapping[orderBy] || orderBy;

  const timeseriesOptions: ApexOptions = {
    title: {
      text: `Top content in the last ${timePeriod}`,
      align: "left",
      style: { fontSize: "18px", fontWeight: 500, color: appColors.black },
    },
    subtitle: {
      text: `Ordered by ${displayOrderBy} ${orderDirection} (Viewing page ${pageNumber} of results)`,
      align: "left",
      style: { fontSize: "14px", fontWeight: 400, color: appColors.darkGrey },
    },
    chart: {
      id: "content-performance-timeseries",
      stacked: false,
      fontFamily: "Inter",
    },
    dataLabels: { enabled: false },
    xaxis: {
      type: "datetime",
      labels: { datetimeUTC: false, format: "MMM dd" },
    },
    yaxis: {
      tickAmount: 3,
      labels: { formatter: (value) => String(Math.round(value)) },
    },
    tooltip: { x: { format: "MMM dd" } },
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      offsetY: -20, // legend was creeping into the chart
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
