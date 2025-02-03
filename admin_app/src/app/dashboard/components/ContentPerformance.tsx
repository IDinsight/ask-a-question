"use client";

import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";

import {
  getPerformancePageData,
  getPerformanceDrawerData,
  getPerformanceDrawerAISummary,
} from "@/app/dashboard/api";

import DetailsDrawer from "@/app/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import { ApexData, Period, RowDataType, DrawerData } from "@/app/dashboard/types";
import { useAuth } from "@/utils/auth";

// Just an example 5-color palette
const CHART_COLORS = ["#ff0000", "#008000", "#0000ff", "#ff00ff", "#ff8c00"];
const N_TOP_CONTENT = 5;

interface PerformanceProps {
  timePeriod: Period;
}

const ContentPerformance: React.FC<PerformanceProps> = ({ timePeriod }) => {
  const { token } = useAuth();

  // Full dataset from server (the entire "content_time_series")
  const [contentTableData, setContentTableData] = useState<RowDataType[]>([]);

  // The subset of items currently being displayed/paginated in the table
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);

  // For the big line chart
  const [lineChartData, setLineChartData] = useState<ApexData[]>([]);

  // Details drawer states
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerData, setDrawerData] = useState<DrawerData | null>(null);
  const [drawerAISummary, setDrawerAISummary] = useState<string | null>(null);

  // Load data once we have a token
  useEffect(() => {
    if (token) {
      getPerformancePageData(timePeriod, token).then((response) => {
        // The raw server timeseries is in `response.content_time_series`
        // We'll parse it into table rows
        parseContentTableData(response.content_time_series);
      });
    } else {
      console.log("No token found");
    }
  }, [timePeriod, token]);

  // Each time the displayed table rows change, rebuild the top chart
  useEffect(() => {
    const newChartData: ApexData[] = itemsToDisplay.map((row, idx) => {
      return {
        name: row.title,
        // If you only have numeric timeseries for the small chart,
        // you may do index-based x-values:
        data: row.query_count_timeseries.map((val, i) => ({
          x: i,
          y: val,
        })),
      };
    });
    setLineChartData(newChartData);
  }, [itemsToDisplay]);

  // Handle table row click -> show drawer
  const tableRowClickHandler = (contentId: number) => {
    setDrawerAISummary(null);
    if (token) {
      getPerformanceDrawerData(timePeriod, contentId, token).then((response) => {
        parseDrawerData(response);
        setDrawerOpen(true);
      });

      getPerformanceDrawerAISummary(timePeriod, contentId, token).then((response) => {
        if (response.ai_summary) {
          setDrawerAISummary(response.ai_summary);
        } else {
          setDrawerAISummary(
            "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.",
          );
        }
      });
    }
  };

  // Parse the server response for the details drawer
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
        data: Object.entries(data.time_series).map(([period, timeseries]) => ({
          x: String(new Date(period)),
          y: timeseries[key] as number,
        })),
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

  // Parse the server response into the table row structure
  const parseContentTableData = (timeseriesData: Record<string, any>[]) => {
    // The table just needs these columns, plus the numeric array for the small sparkline
    const rows: RowDataType[] = timeseriesData.map((series) => ({
      id: series.id,
      title: series.title,
      query_count: series.total_query_count,
      positive_votes: series.positive_votes,
      negative_votes: series.negative_votes,
      // The small sparkline uses numeric arrays. We skip the date dimension for now.
      query_count_timeseries: Object.values(series.query_count_time_series) as number[],
    }));
    setContentTableData(rows);
  };

  return (
    <>
      <DetailsDrawer
        open={drawerOpen}
        onClose={(open: boolean) => () => setDrawerOpen(open)}
        data={drawerData}
        aiSummary={drawerAISummary}
      />

      {/* Big line chart—always controlled by parent state lineChartData */}
      <Box bgcolor="white" sx={{ height: 400, border: 0, padding: 2 }}>
        <LineChart
          data={lineChartData}
          nTopContent={N_TOP_CONTENT}
          timePeriod={timePeriod}
          chartColors={CHART_COLORS}
        />
      </Box>

      {/* Table that shows only part of contentTableData, plus calls onItemsToDisplayChange */}
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
