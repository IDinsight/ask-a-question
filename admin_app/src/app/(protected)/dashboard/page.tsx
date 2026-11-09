"use client";

import React, { useState } from "react";
import { useSearchParams } from "next/navigation";
import { format, subDays, subMonths, subWeeks, subYears } from "date-fns";

import TabPanel from "@/app/(protected)/dashboard/_components/TabPanel";
import { PageName, Period, CustomDateParams, CustomDashboardFrequency } from "./types";
import Overview from "@/app/(protected)/dashboard/_components/Overview";
import ContentPerformance from "@/app/(protected)/dashboard/_components/ContentPerformance";
import Insights from "./_components/Insights";
import DateRangePickerDialog from "@/app/(protected)/dashboard/_components/DateRangePicker";

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
    description: "See how people use your chatbot and whether the answers are helping.",
  },
  {
    name: "Content Performance",
    title: "Content performance",
    slug: "content-performance",
    description: "Find the cards your users rely on most, and the ones that need work.",
  },
  {
    name: "Query Topics",
    title: "Query topics",
    slug: "query-topics",
    description: "Find out what your users are asking about.",
  },
];

/**
 * Human-readable span for the selected period, e.g. "Oct 31 – Nov 6, 2026".
 * Mirrors the backend's ranges (see core_backend dashboard routers).
 * Returns null for a custom period that hasn't been set yet.
 */
const describeRange = (period: Period, custom: CustomDateParams): string | null => {
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

const Dashboard: React.FC = () => {
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
    setCustomDateParams({ startDate: start, endDate: end, frequency: frequency });
    setTimePeriod("custom");
    setIsDialogOpen(false);
  };

  const showPage = () => {
    switch (dashboardPage.name) {
      case "Overview":
        return (
          <Overview
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
          />
        );
      case "Content Performance":
        return (
          <ContentPerformance
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
            onTimePeriodChange={setTimePeriod}
          />
        );
      case "Query Topics":
        return (
          <Insights
            timePeriod={timePeriod}
            customDateParams={timePeriod === "custom" ? customDateParams : undefined}
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

export default Dashboard;
