import React from "react";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import { getPerformancePageData } from "@/app/dashboard/api";
import { ApexData, Period } from "@/app/dashboard/types";
import { useAuth } from "@/utils/auth";
import { useEffect } from "react";
import rows from "./rows";

const N_TOP_CONTENT = 7;

interface PerformanceProps {
  timePeriod: Period;
}

const Performance: React.FC<PerformanceProps> = ({ timePeriod }) => {
  const { token } = useAuth();

  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [lineChartData, setLineChartData] = React.useState<ApexData[]>([]);
  const toggleDrawer = (newOpen: boolean) => () => {
    setDrawerOpen(newOpen);
  };

  useEffect(() => {
    if (token) {
      getPerformancePageData(timePeriod, token, N_TOP_CONTENT).then(
        (response) => {
          console.log(response.content_time_series);
          parseLineChartData(response.content_time_series);
          // parseContentTableData(response.content_time_series);
        },
      );
    } else {
      console.log("No token found");
    }
  }, [timePeriod, token]);

  const parseLineChartData = (timeseriesData: Record<string, any>[]) => {
    const apexTimeSeriesData: ApexData[] = timeseriesData.map((series, idx) => {
      const zIndex = idx === 0 ? 3 : 2;
      const seriesData = {
        name: series.title,
        zIndex: zIndex,
        data: Object.entries(series.query_count_time_series).map(
          ([period, queryCount]) => {
            const date = new Date(period);
            return {
              x: String(date),
              y: queryCount as number,
            };
          },
        ),
      };
      return seriesData;
    });
    console.log(apexTimeSeriesData);
    setLineChartData(apexTimeSeriesData);
  };

  return (
    <>
      <Drawer open={drawerOpen} onClose={toggleDrawer(false)} anchor="right">
        <Box
          sx={{ width: 450 }}
          role="presentation"
          onClick={toggleDrawer(false)}
        >
          Feedback + AI Summary
        </Box>
      </Drawer>
      <Box
        bgcolor="white"
        sx={{
          height: 300,
          maxWidth: 1387,
          border: 0,
          padding: 2,
        }}
      >
        <LineChart
          data={lineChartData}
          nTopContent={N_TOP_CONTENT}
          timePeriod={timePeriod}
        />
      </Box>
      <ContentsTable rows={rows} onClick={toggleDrawer(true)} />
    </>
  );
};

export default Performance;
