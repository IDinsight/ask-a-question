"use client";
import dynamic from "next/dynamic";

import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const LineChart = ({ data, options }: { data: any; options: ApexOptions }) => {
  return (
    <div>
      <ReactApexcharts
        type="line"
        height={270}
        width="100%"
        options={options}
        series={data}
      />
    </div>
  );
};

export default LineChart;
