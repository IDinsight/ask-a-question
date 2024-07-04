"use client";
import dynamic from "next/dynamic";

import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const AreaChart = ({ data, options }: { data: any; options: ApexOptions }) => {
  return (
    <div>
      <ReactApexcharts
        type="area"
        height={400}
        options={options}
        stacked={true}
        series={data}
      />
    </div>
  );
};

export default AreaChart;
