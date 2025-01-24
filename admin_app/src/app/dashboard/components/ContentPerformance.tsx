import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import DetailsDrawer from "@/app/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import {
  getPerformancePageData,
  getPerformanceDrawerData,
  getPerformanceDrawerAISummary,
} from "@/app/dashboard/api";
import {
  ApexData,
  Period,
  RowDataType,
  DrawerData,
  CustomDateRange,
} from "@/app/dashboard/types";
import { useAuth } from "@/utils/auth";

const N_TOP_CONTENT = 10;

interface PerformanceProps {
  timePeriod: Period;
  customDateRange?: CustomDateRange;
}

const ContentPerformance: React.FC<PerformanceProps> = ({
  timePeriod,
  customDateRange,
}) => {
  const { token } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [lineChartData, setLineChartData] = useState<ApexData[]>([]);
  const [contentTableData, setContentTableData] = useState<RowDataType[]>([]);
  const [drawerData, setDrawerData] = useState<DrawerData | null>(null);
  const [drawerAISummary, setDrawerAISummary] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    if (
      timePeriod === "custom" &&
      customDateRange?.startDate &&
      customDateRange.endDate
    ) {
      getPerformancePageData(
        "custom",
        token,
        customDateRange.startDate,
        customDateRange.endDate,
      ).then((response) => {
        parseLineChartData(response.content_time_series.slice(0, N_TOP_CONTENT));
        parseContentTableData(response.content_time_series);
      });
    } else {
      getPerformancePageData(timePeriod, token).then((response) => {
        parseLineChartData(response.content_time_series.slice(0, N_TOP_CONTENT));
        parseContentTableData(response.content_time_series);
      });
    }
  }, [timePeriod, token, customDateRange]);

  const parseLineChartData = (timeseriesData: Record<string, any>[]) => {
    const apexTimeSeriesData: ApexData[] = timeseriesData.map((series, idx) => {
      const zIndex = idx === 0 ? 3 : 2;
      return {
        name: series.title,
        zIndex,
        data: Object.entries(series.query_count_time_series).map(
          ([period, queryCount]) => {
            const date = new Date(period);
            return { x: String(date), y: queryCount as number };
          },
        ),
      };
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

  const toggleDrawer = (newOpen: boolean) => () => {
    setDrawerOpen(newOpen);
  };

  const tableRowClickHandler = (contentId: number) => {
    setDrawerAISummary(null);
    if (!token) return;
    if (
      timePeriod === "custom" &&
      customDateRange?.startDate &&
      customDateRange.endDate
    ) {
      getPerformanceDrawerData(
        "custom",
        contentId,
        token,
        customDateRange.startDate,
        customDateRange.endDate,
      ).then((response) => {
        parseDrawerData(response);
        setDrawerOpen(true);
      });
      getPerformanceDrawerAISummary(
        "custom",
        contentId,
        token,
        customDateRange.startDate,
        customDateRange.endDate,
      ).then((response) => {
        setDrawerAISummary(
          response.ai_summary ||
            "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.",
        );
      });
    } else {
      getPerformanceDrawerData(timePeriod, contentId, token).then((response) => {
        parseDrawerData(response);
        setDrawerOpen(true);
      });
      getPerformanceDrawerAISummary(timePeriod, contentId, token).then((response) => {
        setDrawerAISummary(
          response.ai_summary ||
            "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.",
        );
      });
    }
  };

  const parseDrawerData = (data: Record<string, any>) => {
    interface Timeseries {
      query_count: number;
      positive_count: number;
      negative_count: number;
    }
    function createSeriesData(
      name: string,
      key: keyof Timeseries,
      data: Record<string, Timeseries>,
    ): ApexData {
      return {
        name,
        data: Object.entries(data.time_series).map(([period, timeseries]) => {
          const date = new Date(period);
          return { x: String(date), y: timeseries[key] as number };
        }),
      };
    }
    const queryCountSeriesData = createSeriesData("Total Sent", "query_count", data);
    const positiveVotesSeriesData = createSeriesData(
      "Total Upvotes",
      "positive_count",
      data,
    );
    const negativeVotesSeriesData = createSeriesData(
      "Total Downvotes",
      "negative_count",
      data,
    );
    setDrawerData({
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
    });
  };

  return (
    <>
      <DetailsDrawer
        open={drawerOpen}
        onClose={toggleDrawer}
        data={drawerData}
        aiSummary={drawerAISummary}
      />
      <Box
        bgcolor="white"
        sx={{
          height: 300,
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

export default ContentPerformance;
