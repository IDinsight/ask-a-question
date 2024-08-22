"use client";
import dynamic from "next/dynamic";

import { ApexOptions } from "apexcharts";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const HeatMap = ({ data }: { data: any }) => {
  const heatmapOptions: ApexOptions = {
    chart: {
      id: "usage-heatmap",
      width: "100%",
      height: "100%",
    },
    dataLabels: {
      enabled: false,
    },
    title: {
      text: "Usage Frequency",
      margin: 2,
      offsetX: 6,
      offsetY: 8,
      floating: false,
      style: {
        fontSize: "16px",
        fontWeight: "bold",
        fontFamily: undefined,
        color: "#263238",
      },
    },
    colors: ["#008FFB"],
    plotOptions: {
      heatmap: {
        radius: 1,
      },
    },
  };

  return (
    <div>
      <ReactApexcharts
        type="heatmap"
        height={450}
        width="100%"
        options={heatmapOptions}
        series={data}
      />
    </div>
  );
};

export default HeatMap;
