import React from "react";
import Box from "@mui/material/Box";
import DetailsDrawer from "@/app/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import { getPerformancePageData, getPerformanceDrawerData } from "@/app/dashboard/api";
import { ApexData, Period, RowDataType, DrawerData } from "@/app/dashboard/types";
import { useAuth } from "@/utils/auth";
import { useEffect } from "react";
const N_TOP_CONTENT = 10;

interface PerformanceProps {
  timePeriod: Period;
}

const Performance: React.FC<PerformanceProps> = ({ timePeriod }) => {
  const { token } = useAuth();

  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [lineChartData, setLineChartData] = React.useState<ApexData[]>([]);
  const [contentTableData, setContentTableData] = React.useState<RowDataType[]>([]);
  const [drawerData, setDrawerData] = React.useState<DrawerData | null>(null);

  useEffect(() => {
    if (token) {
      getPerformancePageData(timePeriod, token).then((response) => {
        console.log(response.content_time_series);
        parseLineChartData(response.content_time_series.slice(0, N_TOP_CONTENT));
        parseContentTableData(response.content_time_series);
      });
    } else {
      console.log("No token found");
    }
  }, [timePeriod, token]);

  const toggleDrawer = (newOpen: boolean) => () => {
    setDrawerOpen(newOpen);
  };

  const tableRowClickHandler = (contentId: number) => {
    if (token) {
      getPerformanceDrawerData(timePeriod, contentId, token).then((response) => {
        console.log(response);
        parseDrawerData(response);
        setDrawerOpen(true);
      });
    }
  };

  const parseDrawerData = (data: Record<string, any>) => {
    interface Timeseries {
      query_count: number;
      positive_count: number;
      negative_count: number;
    }

    const queryCountSeriesData: ApexData = {
      name: "Query Count",
      data: Object.entries(data.time_series).map(([period, timeseries]) => {
        const date = new Date(period);
        return {
          x: String(date),
          y: (timeseries as Timeseries).query_count as number,
        };
      }),
    };

    const positiveVotesSeriesData: ApexData = {
      name: "Positive Votes",
      data: Object.entries(data.time_series).map(([period, timeseries]) => {
        const date = new Date(period);
        return {
          x: String(date),
          y: (timeseries as Timeseries).positive_count as number,
        };
      }),
    };

    const negativeVotesSeriesData: ApexData = {
      name: "Negative Votes",
      data: Object.entries(data.time_series).map(([period, timeseries]) => {
        const date = new Date(period);
        return {
          x: String(date),
          y: (timeseries as Timeseries).negative_count as number,
        };
      }),
    };

    const drawerData: DrawerData = {
      title: data.title,
      query_count: data.query_count,
      positive_votes: data.positive_votes,
      negative_votes: data.negative_votes,
      daily_query_count_avg: data.daily_query_count_avg,
      line_chart_data: [
        queryCountSeriesData,
        positiveVotesSeriesData,
        negativeVotesSeriesData,
      ],
      user_feedback: data.user_feedback,
    };
    setDrawerData(drawerData);
  };

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
    setLineChartData(apexTimeSeriesData);
  };

  const parseContentTableData = (timeseriesData: Record<string, any>[]) => {
    const rows: RowDataType[] = timeseriesData.map((series) => {
      return {
        id: series.id,
        title: series.title,
        query_count: series.total_query_count,
        positive_votes: series.positive_votes,
        negative_votes: series.negative_votes,
        query_count_timeseries: Object.values(series.query_count_time_series),
      };
    });
    setContentTableData(rows);
  };

  const sampleDrawerData = {
    // This will be deleted when i connect to the backend
    title: "What is the purpose of the Learner Mobilistion phase in Project Pragati?",
    query_count: 100,
    positive_votes: 50,
    negative_votes: 50,
    daily_query_count_avg: 10,
    query_count_timeseries: [
      { x: "2021-09-01T00:00:00.000Z", y: 10 },
      { x: "2021-09-02T00:00:00.000Z", y: 20 },
      { x: "2021-09-03T00:00:00.000Z", y: 30 },
      { x: "2021-09-04T00:00:00.000Z", y: 40 },
      { x: "2021-09-05T00:00:00.000Z", y: 50 },
      { x: "2021-09-06T00:00:00.000Z", y: 60 },
      { x: "2021-09-07T00:00:00.000Z", y: 70 },
      { x: "2021-09-08T00:00:00.000Z", y: 80 },
      { x: "2021-09-09T00:00:00.000Z", y: 90 },
      { x: "2021-09-10T00:00:00.000Z", y: 100 },
    ],
    positive_votes_timeseries: [
      { x: "2021-09-01T00:00:00.000Z", y: 5 },
      { x: "2021-09-02T00:00:00.000Z", y: 10 },
      { x: "2021-09-03T00:00:00.000Z", y: 15 },
      { x: "2021-09-04T00:00:00.000Z", y: 20 },
      { x: "2021-09-05T00:00:00.000Z", y: 25 },
      { x: "2021-09-06T00:00:00.000Z", y: 30 },
      { x: "2021-09-07T00:00:00.000Z", y: 35 },
      { x: "2021-09-08T00:00:00.000Z", y: 40 },
      { x: "2021-09-09T00:00:00.000Z", y: 45 },
      { x: "2021-09-10T00:00:00.000Z", y: 50 },
    ],
    negative_votes_timeseries: [
      { x: "2021-09-01T00:00:00.000Z", y: 5 },
      { x: "2021-09-02T00:00:00.000Z", y: 10 },
      { x: "2021-09-03T00:00:00.000Z", y: 15 },
      { x: "2021-09-04T00:00:00.000Z", y: 20 },
      { x: "2021-09-05T00:00:00.000Z", y: 25 },
      { x: "2021-09-06T00:00:00.000Z", y: 30 },
      { x: "2021-09-07T00:00:00.000Z", y: 35 },
      { x: "2021-09-08T00:00:00.000Z", y: 40 },
      { x: "2021-09-09T00:00:00.000Z", y: 45 },
      { x: "2021-09-10T00:00:00.000Z", y: 50 },
    ],
    user_feedback: [
      {
        timestamp: "2021-09-01T00:00:00.000Z",
        question: "What is Learner Mobilisation?",
        feedback: "Not enough information",
      },
      {
        timestamp: "2021-09-02T00:00:00.000Z",
        question:
          "This is a very long question that should get truncated when displayed",
        feedback:
          "This ia a very long feedback that should get truncated when displayed",
      },
    ],
  };

  return (
    <>
      <DetailsDrawer open={drawerOpen} onClose={toggleDrawer} data={drawerData} />
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
      <ContentsTable
        rows={contentTableData}
        onClick={tableRowClickHandler}
        rowsPerPage={N_TOP_CONTENT}
      />
    </>
  );
};

export default Performance;
