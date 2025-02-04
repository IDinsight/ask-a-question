"use client";

import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import DetailsDrawer from "@/app/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import {
  getPerformancePageData,
  getPerformanceDrawerData,
  getPerformanceDrawerAISummary,
} from "@/app/dashboard/api";
import {
  ContentLineChartTSData,
  Period,
  RowDataType,
  CustomDateParams,
  DrawerData,
} from "@/app/dashboard/types";
import { useAuth } from "@/utils/auth";

const CHART_COLORS = ["#ff0000", "#008000", "#0000ff", "#ff00ff", "#ff8c00"];
const N_TOP_CONTENT = 5;

interface PerformanceProps {
  timePeriod: Period;
  customDateParams?: CustomDateParams;
}

const ContentPerformance: React.FC<PerformanceProps> = ({
  timePeriod,
  customDateParams,
}) => {
  const { token } = useAuth();
  const [contentTableData, setContentTableData] = useState<RowDataType[]>([]);
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);
  const [lineChartData, setLineChartData] = useState<ContentLineChartTSData[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerData, setDrawerData] = useState<DrawerData | null>(null);
  const [drawerAISummary, setDrawerAISummary] = useState<string | null>(null);

  // Fetch page data and build table rows
  useEffect(() => {
    if (!token) return;
    getPerformancePageData(
      timePeriod,
      token,
      customDateParams?.startDate ?? undefined,
      customDateParams?.endDate ?? undefined,
    ).then((response) => {
      const tableData: RowDataType[] = response.content_time_series.map(
        (series: any) => ({
          id: series.id,
          title: series.title,
          query_count: series.total_query_count,
          positive_votes: series.positive_votes,
          negative_votes: series.negative_votes,
          query_count_timeseries: Object.entries(series.query_count_time_series).map(
            ([timestamp, value]) => ({
              x: new Date(timestamp).getTime(),
              y: value as number,
            }),
          ),
        }),
      );
      setContentTableData(tableData);
    });
  }, [timePeriod, token, customDateParams]);

  // Build line chart data based on the items currently displayed
  useEffect(() => {
    const chartData: ContentLineChartTSData[] = itemsToDisplay.map((row) => ({
      name: row.title,
      data: row.query_count_timeseries,
    }));
    setLineChartData(chartData);
  }, [itemsToDisplay]);

  // When a table row is clicked, fetch and parse drawer data and AI summary.
  const tableRowClickHandler = (contentId: number) => {
    if (!token) return;
    setDrawerAISummary(null);
    if (
      timePeriod === "custom" &&
      customDateParams?.startDate &&
      customDateParams?.endDate
    ) {
      getPerformanceDrawerData(
        "custom",
        contentId,
        token,
        customDateParams.startDate,
        customDateParams.endDate,
      ).then((response) => {
        parseDrawerData(response);
        setDrawerOpen(true);
      });
      getPerformanceDrawerAISummary(
        "custom",
        contentId,
        token,
        customDateParams.startDate,
        customDateParams.endDate,
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

  // Parse drawer data to create the series for the drawer's line chart.
  const parseDrawerData = (data: Record<string, any>) => {
    function createSeriesData(
      name: string,
      key: "query_count" | "positive_count" | "negative_count",
      data: Record<string, any>,
    ): DrawerData["line_chart_data"][0] {
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
        onClose={() => (e) => setDrawerOpen(false)}
        data={drawerData}
        aiSummary={drawerAISummary}
      />
      <Box bgcolor="white" sx={{ height: 430, border: 0, padding: 2 }}>
        <LineChart
          data={lineChartData}
          nTopContent={N_TOP_CONTENT}
          timePeriod={timePeriod}
          chartColors={CHART_COLORS}
        />
      </Box>
      <ContentsTable
        rows={contentTableData}
        onClick={tableRowClickHandler}
        rowsPerPage={N_TOP_CONTENT}
        chartColors={CHART_COLORS}
        onItemsToDisplayChange={(items) => setItemsToDisplay(items)}
      />
    </>
  );
};

export default ContentPerformance;
