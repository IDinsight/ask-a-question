"use client";
import dynamic from "next/dynamic";

import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const HeatMap = ({ data, options }: { data: any; options: ApexOptions }) => {
  return (
    <div>
      <ReactApexcharts
        type="heatmap"
        height={400}
        width={350}
        options={options}
        series={data}
      />
    </div>
  );
};

export default HeatMap;
