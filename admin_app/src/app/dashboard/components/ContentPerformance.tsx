"use client";

import React, { useEffect, useState } from "react";
import DetailsDrawer from "@/app/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/app/dashboard/components/performance/LineChart";
import ContentsTable from "@/app/dashboard/components/performance/ContentsTable";
import { SERIES_COLORS } from "@/app/dashboard/components/performance/seriesColors";
import { periodLabel } from "@/app/dashboard/components/TabPanel";
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

const N_TOP_CONTENT = 5;

const AI_SUMMARY_DISABLED =
  "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.";

// How the chart subtitle names the table's sort column.
const SORT_LABELS: Record<string, string> = {
  query_count: "daily average sent",
  positive_votes: "upvotes",
  negative_votes: "downvotes",
  query_count_timeseries: "trend",
  title: "title",
};

// The next-longer preset, offered in the empty table ("Show last month").
const LONGER_PERIOD: Partial<Record<Period, Period>> = {
  day: "week",
  week: "month",
  month: "year",
};

interface PerformanceProps {
  timePeriod: Period;
  customDateParams?: CustomDateParams;
  onTimePeriodChange?: (period: Period) => void;
}

const ContentPerformance: React.FC<PerformanceProps> = ({
  timePeriod,
  customDateParams,
  onTimePeriodChange,
}) => {
  const { token } = useAuth();
  const [contentTableData, setContentTableData] = useState<RowDataType[]>([]);
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);
  const [lineChartData, setLineChartData] = useState<ContentLineChartTSData[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerData, setDrawerData] = useState<DrawerData | null>(null);
  const [drawerAISummary, setDrawerAISummary] = useState<string | null>(null);
  const [selectedOrderColumn, setSelectedOrderColumn] = useState<string>("query_count");
  const [selectedOrderDirection, setSelectedOrderDirection] = useState<
    "ascending" | "descending"
  >("descending");
  const [page, setPage] = useState<number>(1);

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

  // Chart whatever rows the table is currently showing
  useEffect(() => {
    setLineChartData(
      itemsToDisplay.map((row) => ({ name: row.title, data: row.query_count_timeseries })),
    );
  }, [itemsToDisplay]);

  // When a table row is clicked, fetch drawer data and the AI summary in parallel.
  const tableRowClickHandler = (contentId: number) => {
    if (!token) return;
    setDrawerAISummary(null);
    const isCustom =
      timePeriod === "custom" && customDateParams?.startDate && customDateParams?.endDate;
    const args: [Period, number, string, string?, string?] = isCustom
      ? ["custom", contentId, token, customDateParams!.startDate!, customDateParams!.endDate!]
      : [timePeriod, contentId, token];

    getPerformanceDrawerData(...args).then((response) => {
      parseDrawerData(response);
      setDrawerOpen(true);
    });
    getPerformanceDrawerAISummary(...args).then((response) => {
      setDrawerAISummary(response.ai_summary || AI_SUMMARY_DISABLED);
    });
  };

  // One chart row per time bucket: { timestamp, query_count, positive_count, negative_count }
  const parseDrawerData = (data: Record<string, any>) => {
    const rows = Object.entries(
      data.time_series as Record<
        string,
        { query_count: number; positive_count: number; negative_count: number }
      >,
    )
      .map(([period, ts]) => ({
        timestamp: new Date(period).getTime(),
        query_count: ts.query_count,
        positive_count: ts.positive_count,
        negative_count: ts.negative_count,
      }))
      .sort((a, b) => a.timestamp - b.timestamp);

    setDrawerData({
      title: data.title,
      query_count: data.query_count,
      positive_votes: data.positive_votes,
      negative_votes: data.negative_votes,
      daily_query_count_avg: data.daily_query_count_avg,
      line_chart_data: rows,
      user_feedback: data.user_feedback,
    });
  };

  const handleSortChange = (column: string, direction: "ascending" | "descending") => {
    setSelectedOrderColumn(column);
    setSelectedOrderDirection(direction);
  };

  const longer = LONGER_PERIOD[timePeriod];

  return (
    <div className="flex flex-col gap-6">
      <DetailsDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        data={drawerData}
        aiSummary={drawerAISummary}
      />
      <section
        aria-labelledby="top-content"
        className="flex flex-col gap-4 border bg-card p-5 shadow-xs"
      >
        <div>
          <h2 id="top-content" className="text-base font-semibold tracking-tight">
            Top content, {periodLabel(timePeriod)}
          </h2>
          <p className="text-[13px] text-muted-foreground">
            Ordered by {SORT_LABELS[selectedOrderColumn] ?? selectedOrderColumn},{" "}
            {selectedOrderDirection === "descending" ? "highest" : "lowest"} first
            {/* Total pages live in the table footer (it knows about search filtering) */}
            {(page > 1 || contentTableData.length > N_TOP_CONTENT) && ` · page ${page} of results`}.
          </p>
        </div>
        <LineChart data={lineChartData} chartColors={SERIES_COLORS} />
      </section>
      <ContentsTable
        rows={contentTableData}
        onClick={tableRowClickHandler}
        rowsPerPage={N_TOP_CONTENT}
        chartColors={SERIES_COLORS}
        onItemsToDisplayChange={setItemsToDisplay}
        onSortChange={handleSortChange}
        onPageChange={setPage}
        longerRange={
          longer && onTimePeriodChange
            ? {
                label: `Show ${periodLabel(longer)}`,
                onSelect: () => onTimePeriodChange(longer),
              }
            : undefined
        }
      />
    </div>
  );
};

export default ContentPerformance;
