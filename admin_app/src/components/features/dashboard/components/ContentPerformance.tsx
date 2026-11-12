"use client";

import React from "react";
import DetailsDrawer from "@/components/features/dashboard/components/performance/DetailsDrawer";
import LineChart from "@/components/features/dashboard/components/performance/LineChart";
import ContentsTable from "@/components/features/dashboard/components/performance/ContentsTable";
import { SERIES_COLORS } from "@/components/features/dashboard/components/performance/seriesColors";
import { periodLabel } from "@/components/features/dashboard/components/TabPanel";
import {
  DrawerData,
  Period,
  RowDataType,
  SortDirection,
} from "@/components/features/dashboard/types";

const N_TOP_CONTENT = 5;

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

/**
 * Presentational: DashboardWrapper owns the data and the state shared between
 * the table, the chart and the drawer, and passes it in here.
 */
interface PerformanceProps {
  timePeriod: Period;
  onTimePeriodChange: (period: Period) => void;
  /** Every content row for the period (the table pages/sorts/filters them). */
  rows: RowDataType[];
  /** The rows currently visible in the table; the chart plots these. */
  itemsToDisplay: RowDataType[];
  onItemsToDisplayChange: (items: RowDataType[]) => void;
  sortColumn: string;
  sortDirection: SortDirection;
  onSortChange: (column: string, direction: SortDirection) => void;
  page: number;
  onPageChange: (page: number) => void;
  onRowClick: (contentId: number) => void;
  drawer: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    data: DrawerData | null;
    aiSummary: string | null;
  };
}

const ContentPerformance: React.FC<PerformanceProps> = ({
  timePeriod,
  onTimePeriodChange,
  rows,
  itemsToDisplay,
  onItemsToDisplayChange,
  sortColumn,
  sortDirection,
  onSortChange,
  page,
  onPageChange,
  onRowClick,
  drawer,
}) => {
  // Chart whatever rows the table is currently showing.
  const lineChartData = itemsToDisplay.map((row) => ({
    name: row.title,
    data: row.query_count_timeseries,
  }));

  const longer = LONGER_PERIOD[timePeriod];

  return (
    <div className="flex flex-col gap-6">
      <DetailsDrawer
        open={drawer.open}
        onOpenChange={drawer.onOpenChange}
        data={drawer.data}
        aiSummary={drawer.aiSummary}
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
            Ordered by {SORT_LABELS[sortColumn] ?? sortColumn},{" "}
            {sortDirection === "descending" ? "highest" : "lowest"} first
            {/* Total pages live in the table footer (it knows about search filtering) */}
            {(page > 1 || rows.length > N_TOP_CONTENT) && ` · page ${page} of results`}.
          </p>
        </div>
        <LineChart data={lineChartData} chartColors={SERIES_COLORS} />
      </section>
      <ContentsTable
        rows={rows}
        onClick={onRowClick}
        rowsPerPage={N_TOP_CONTENT}
        chartColors={SERIES_COLORS}
        onItemsToDisplayChange={onItemsToDisplayChange}
        onSortChange={onSortChange}
        onPageChange={onPageChange}
        longerRange={
          longer
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
