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

  useEffect(() => {
    if (!token) return;
    getPerformancePageData(timePeriod, token).then((response) => {
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
  }, [timePeriod, token]);

  useEffect(() => {
    const chartData: ContentLineChartTSData[] = itemsToDisplay.map((row) => ({
      name: row.title,
      data: row.query_count_timeseries,
    }));
    setLineChartData(chartData);
  }, [itemsToDisplay]);

  const tableRowClickHandler = (contentId: number) => {
    if (!token) return;
    setDrawerAISummary(null);
    getPerformanceDrawerData(timePeriod, contentId, token).then((response) => {
      const seriesData = (key: string) =>
        Object.entries(response.time_series as Record<string, any>).map(
          ([period, timeseries]) => ({
            x: new Date(period).toISOString(),
            y: timeseries[key] as number,
          }),
        );
      setDrawerData({
        title: response.title,
        query_count: response.query_count,
        positive_votes: response.positive_votes,
        negative_votes: response.negative_votes,
        daily_query_count_avg: response.daily_query_count_avg,
        line_chart_data: [
          { name: "Total Sent", data: seriesData("query_count") },
          { name: "Total Upvotes", data: seriesData("positive_count") },
          { name: "Total Downvotes", data: seriesData("negative_count") },
        ],
        user_feedback: response.user_feedback,
      });
      setDrawerOpen(true);
    });
    getPerformanceDrawerAISummary(timePeriod, contentId, token).then((response) => {
      setDrawerAISummary(
        response.ai_summary ||
          "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.",
      );
    });
  };

  return (
    <>
      <DetailsDrawer
        open={drawerOpen}
        onClose={() => (_) => setDrawerOpen(false)}
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
