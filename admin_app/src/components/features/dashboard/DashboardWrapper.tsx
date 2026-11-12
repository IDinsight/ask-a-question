"use client";

import React, { useState } from "react";
import { useSearchParams } from "next/navigation";
import { format, subDays, subMonths, subWeeks, subYears } from "date-fns";

import TabPanel from "./components/TabPanel";
import Overview from "./components/Overview";
import ContentPerformance from "./components/ContentPerformance";
import Insights from "./components/Insights";
import DateRangePickerDialog from "./components/DateRangePicker";
import {
  toPeriodParams,
  useEmbeddingQuery,
  useHasContentQuery,
  useOverviewQuery,
  usePerformanceAISummaryQuery,
  usePerformanceDrawerQuery,
  usePerformanceQuery,
  useTopicInsights,
} from "./queries";
import {
  CustomDashboardFrequency,
  CustomDateParams,
  PageName,
  Period,
  RowDataType,
  SortDirection,
} from "./types";

type Page = {
  name: PageName;
  /** Heading shown on the page (sentence case, per the design boards). */
  title: string;
  /** Value of the ?page= search param used by the app sidebar links. */
  slug: string;
  description: string;
};

const pages: Page[] = [
  {
    name: "Overview",
    title: "Overview",
    slug: "overview",
    description:
      "See how people use your chatbot and whether the answers are helping.",
  },
  {
    name: "Content Performance",
    title: "Content performance",
    slug: "content-performance",
    description:
      "Find the cards your users rely on most, and the ones that need work.",
  },
  {
    name: "Query Topics",
    title: "Query topics",
    slug: "query-topics",
    description: "Find out what your users are asking about.",
  },
];

/**
 * Stable fallback while the performance query loads. A fresh `[]` each render
 * would retrigger ContentsTable's "visible rows changed" effect in a loop.
 */
const NO_ROWS: RowDataType[] = [];

/** Bar size the backend uses for each preset period (see core_backend routers). */
const presetFrequency: Record<
  Exclude<Period, "custom">,
  CustomDashboardFrequency
> = {
  day: "Hour",
  week: "Day",
  month: "Day",
  year: "Month",
};

/**
 * Human-readable span for the selected period, e.g. "Oct 31 – Nov 6, 2026".
 * Mirrors the backend's ranges (see core_backend dashboard routers).
 * Returns null for a custom period that hasn't been set yet.
 */
const describeRange = (
  period: Period,
  custom: CustomDateParams,
): string | null => {
  const now = new Date();
  let start: Date;
  let end = now;
  switch (period) {
    case "day":
      start = subDays(now, 1);
      break;
    case "week":
      start = subWeeks(now, 1);
      break;
    case "month":
      start = subMonths(now, 1);
      break;
    case "year":
      start = subYears(now, 1);
      break;
    case "custom":
      if (!custom.startDate || !custom.endDate) return null;
      start = new Date(custom.startDate);
      end = new Date(custom.endDate);
      break;
  }
  // Only repeat the year when the range crosses into a new one.
  const sameYear = start.getFullYear() === end.getFullYear();
  return `${format(start, sameYear ? "MMM d" : "MMM d, yyyy")} – ${format(
    end,
    "MMM d, yyyy",
  )}`;
};

/**
 * The dashboard feature. Owns:
 * - the selected sub-page (?page=), time period and custom date range;
 * - every dashboard query/mutation (see ./queries.ts), each enabled only while
 *   its sub-page is showing;
 * - state shared between sibling components (table sort/page ↔ chart,
 *   selected row ↔ drawer, selected topic, plot card open/closed).
 * Child components are presentational and get everything through props.
 */
const DashboardWrapper: React.FC = () => {
  // The sub-page is picked from the app sidebar via ?page=<slug>.
  // Unknown or missing values fall back to Overview.
  const searchParams = useSearchParams();
  const dashboardPage =
    pages.find((p) => p.slug === searchParams.get("page")) ?? pages[0];
  const [timePeriod, setTimePeriod] = useState<Period>("week");
  const [customDateParams, setCustomDateParams] = useState<CustomDateParams>({
    startDate: null,
    endDate: null,
    frequency: "Day",
  });
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Picking "Custom" before a range exists opens the dialog instead.
  const handleTabChange = (newValue: Period) => {
    if (newValue === "custom") {
      if (customDateParams.startDate && customDateParams.endDate) {
        setTimePeriod("custom");
      } else {
        setIsDialogOpen(true);
      }
    } else {
      setTimePeriod(newValue);
    }
  };

  const handleEditCustomPeriod = () => {
    setIsDialogOpen(true);
  };

  const handleCustomDateParamsSelected = (
    start: string,
    end: string,
    frequency: CustomDashboardFrequency,
  ) => {
    setCustomDateParams({
      startDate: start,
      endDate: end,
      frequency: frequency,
    });
    setTimePeriod("custom");
    setIsDialogOpen(false);
  };

  /* ---------- data ---------- */
  const params = toPeriodParams(timePeriod, customDateParams);
  const onPage = (name: PageName) => dashboardPage.name === name;

  // Overview
  const overview = useOverviewQuery(params, onPage("Overview"));
  const hasContent = useHasContentQuery(onPage("Overview"));
  const frequency =
    timePeriod === "custom"
      ? customDateParams.frequency
      : presetFrequency[timePeriod];

  // Content performance: table/chart share sort, page and visible rows.
  const performance = usePerformanceQuery(
    params,
    onPage("Content Performance"),
  );
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);
  const [sortColumn, setSortColumn] = useState("query_count");
  const [sortDirection, setSortDirection] =
    useState<SortDirection>("descending");
  const [tablePage, setTablePage] = useState(1);
  // The clicked row stays selected after the drawer closes, so the close
  // animation still has data to show.
  const [selectedContentId, setSelectedContentId] = useState<number | null>(
    null,
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawer = usePerformanceDrawerQuery(params, selectedContentId);
  const aiSummary = usePerformanceAISummaryQuery(params, selectedContentId);

  // Query topics
  const insights = useTopicInsights(params, onPage("Query Topics"));
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  // Fall back to the first topic when nothing (or a topic from another
  // period) is selected.
  const topicIds = insights.data.data.map((t) => t.topic_id);
  const activeTopicId =
    selectedTopicId !== null && topicIds.includes(selectedTopicId)
      ? selectedTopicId
      : topicIds[0] ?? null;
  const [plotOpen, setPlotOpen] = useState(false);
  const embedding = useEmbeddingQuery(
    params,
    onPage("Query Topics") && plotOpen,
  );

  const showPage = () => {
    switch (dashboardPage.name) {
      case "Overview":
        return (
          <Overview
            timePeriod={timePeriod}
            frequency={frequency}
            data={overview.data}
            hasContent={hasContent.data ?? false}
          />
        );
      case "Content Performance":
        return (
          <ContentPerformance
            timePeriod={timePeriod}
            onTimePeriodChange={setTimePeriod}
            rows={performance.data ?? NO_ROWS}
            itemsToDisplay={itemsToDisplay}
            onItemsToDisplayChange={setItemsToDisplay}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSortChange={(column, direction) => {
              setSortColumn(column);
              setSortDirection(direction);
            }}
            page={tablePage}
            onPageChange={setTablePage}
            onRowClick={(contentId) => {
              setSelectedContentId(contentId);
              setDrawerOpen(true);
            }}
            drawer={{
              // Like before, the drawer appears once its data has loaded.
              open: drawerOpen && !!drawer.data,
              onOpenChange: setDrawerOpen,
              data: drawer.data ?? null,
              aiSummary: aiSummary.data ?? null,
            }}
          />
        );
      case "Query Topics":
        return (
          <Insights
            data={insights.data}
            selectedTopicId={activeTopicId}
            onSelectTopic={setSelectedTopicId}
            refreshing={insights.refreshing}
            onRefresh={insights.runRefresh}
            plot={{
              open: plotOpen,
              onOpenChange: setPlotOpen,
              plotSpec: embedding.data,
              loading: embedding.isFetching,
              error: embedding.isError,
            }}
          />
        );
      default:
        return <div>Page not found.</div>;
    }
  };

  const rangeText = describeRange(timePeriod, customDateParams);

  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {dashboardPage.title}
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            {dashboardPage.description}
          </p>
        </header>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabPanel
            tabValue={timePeriod}
            handleChange={handleTabChange}
            onEditCustomPeriod={handleEditCustomPeriod}
            customDateParamsSet={
              !!(
                customDateParams.startDate &&
                customDateParams.endDate &&
                customDateParams.frequency
              )
            }
          />
          {rangeText && (
            <span className="text-xs text-muted-foreground">{rangeText}</span>
          )}
        </div>
        <div className="min-w-0">{showPage()}</div>
      </div>

      <DateRangePickerDialog
        open={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSelectDateRange={handleCustomDateParamsSelected}
        initialStartDate={customDateParams.startDate}
        initialEndDate={customDateParams.endDate}
        initialFrequency={customDateParams.frequency}
      />
    </div>
  );
};

export default DashboardWrapper;
