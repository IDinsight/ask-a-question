import React, { useEffect } from "react";
import Link from "next/link";
import {
  IconArrowRight,
  IconBolt,
  IconCheck,
  IconMessage,
  IconThumbDown,
  IconThumbUp,
} from "@tabler/icons-react";

import { useAuth } from "@/utils/auth";
import { getOverviewPageData } from "@/app/dashboard/api";
import { getContentList } from "@/app/content/api";
import StackedBarChart, {
  QueriesLegend,
  type QueriesOverTimeRow,
} from "@/app/dashboard/components/overview/StackedChart";
import HeatMap from "@/app/dashboard/components/overview/HeatMap";
import { StatCard, StatCardProps } from "@/app/dashboard/components/overview/StatCard";
import TopContentTable from "@/app/dashboard/components/overview/TopContentTable";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "cn";
import {
  CustomDashboardFrequency,
  DayHourUsageData,
  InputSeriesData,
  Period,
  TopContentData,
  CustomDateParams,
} from "../types";

interface OverviewProps {
  timePeriod: Period;
  customDateParams?: CustomDateParams;
}

/** Bar size the backend uses for each preset period (see core_backend routers). */
const presetFrequency: Record<Exclude<Period, "custom">, CustomDashboardFrequency> = {
  day: "Hour",
  week: "Day",
  month: "Day",
  year: "Month",
};

const Overview: React.FC<OverviewProps> = ({ timePeriod, customDateParams }) => {
  const { token } = useAuth();
  const [statCardData, setStatCardData] = React.useState<StatCardProps[]>([]);
  const [heatmapData, setHeatmapData] = React.useState<DayHourUsageData>({});
  const [timeseriesData, setTimeseriesData] = React.useState<QueriesOverTimeRow[]>([]);
  const [topContentData, setTopContentData] = React.useState<TopContentData[]>([]);
  const [totalQueries, setTotalQueries] = React.useState<number | null>(null);
  const [hasContent, setHasContent] = React.useState(false);

  const parseCardData = (statsCardsData: Record<string, any>, timePeriod: Period) => {
    const {
      content_feedback_stats,
      query_stats,
      response_feedback_stats,
      urgency_stats,
    } = statsCardsData;

    setTotalQueries(query_stats.n_questions);
    setStatCardData([
      {
        title: "Total queries",
        value: query_stats.n_questions,
        percentageChange: query_stats.percentage_increase,
        Icon: IconMessage,
        period: timePeriod,
      },
      {
        title: "Downvoted responses",
        value: response_feedback_stats.n_negative,
        percentageChange: response_feedback_stats.percentage_negative_increase,
        Icon: IconThumbDown,
        period: timePeriod,
      },
      {
        title: "Urgent queries",
        value: urgency_stats.n_urgent,
        percentageChange: urgency_stats.percentage_increase,
        Icon: IconBolt,
        iconClassName: "text-urgent",
        period: timePeriod,
      },
      {
        title: "Content upvotes",
        value: content_feedback_stats.n_positive,
        percentageChange: content_feedback_stats.percentage_positive_increase,
        Icon: IconThumbUp,
        period: timePeriod,
      },
      {
        title: "Content downvotes",
        value: content_feedback_stats.n_negative,
        percentageChange: content_feedback_stats.percentage_negative_increase,
        Icon: IconThumbDown,
        period: timePeriod,
      },
    ]);
  };

  // One row per timestamp with all three counts, the shape Recharts expects.
  const parseTimeseriesData = (timeseriesData: InputSeriesData) => {
    // Timestamps should match across categories; read them from "normal".
    const timeStamps = Object.keys(timeseriesData["normal"] || {});
    setTimeseriesData(
      timeStamps.map((stamp) => ({
        timestamp: new Date(stamp).getTime(),
        normal: Number(timeseriesData["normal"]?.[stamp]) || 0,
        downvoted: Number(timeseriesData["downvoted"]?.[stamp]) || 0,
        urgent: Number(timeseriesData["urgent"]?.[stamp]) || 0,
      })),
    );
  };

  useEffect(() => {
    if (!token) return;

    const handleData = (data: any) => {
      parseCardData(data.stats_cards, timePeriod);
      setHeatmapData(data.heatmap);
      parseTimeseriesData(data.time_series);
      setTopContentData(data.top_content);
    };

    if (
      timePeriod === "custom" &&
      customDateParams?.startDate &&
      customDateParams?.endDate &&
      customDateParams?.frequency
    ) {
      getOverviewPageData(
        "custom",
        token,
        customDateParams.startDate,
        customDateParams.endDate,
        customDateParams.frequency,
      ).then(handleData);
    } else {
      getOverviewPageData(timePeriod, token).then(handleData);
    }
  }, [timePeriod, token, customDateParams]);

  // Only needed for the setup checklist: does the workspace have any content?
  useEffect(() => {
    if (!token) return;
    getContentList({ token, limit: 1 })
      .then((data) => setHasContent(Array.isArray(data) && data.length > 0))
      .catch(() => setHasContent(false));
  }, [token]);

  const frequency =
    timePeriod === "custom"
      ? customDateParams?.frequency ?? "Day"
      : presetFrequency[timePeriod];

  return (
    <div className="flex flex-col gap-6">
      {/* Setup checklist until real questions start coming in */}
      {totalQueries === 0 && <GetSetUp hasContent={hasContent} />}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        {statCardData.length === 0
          ? Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-[104px]" />
            ))
          : statCardData.map((data) => <StatCard {...data} key={data.title} />)}
      </div>

      <div className="flex flex-wrap gap-4">
        <section
          aria-labelledby="queries-over-time"
          className="flex min-w-0 flex-[2_1_520px] flex-col gap-4 border bg-card p-5 shadow-xs"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2
              id="queries-over-time"
              className="text-base font-semibold tracking-tight"
            >
              Queries over time
            </h2>
            <QueriesLegend />
          </div>
          <StackedBarChart
            data={timeseriesData}
            frequency={frequency}
            showDayOfWeek={timePeriod === "week"}
          />
        </section>
        <section
          aria-labelledby="usage-frequency"
          className="flex min-w-0 flex-[1_1_280px] flex-col gap-4 border bg-card p-5 shadow-xs"
        >
          <h2 id="usage-frequency" className="text-base font-semibold tracking-tight">
            Usage frequency
          </h2>
          <HeatMap data={heatmapData} />
        </section>
      </div>

      <TopContentTable rows={topContentData} />
    </div>
  );
};

/**
 * Four setup steps. Only "workspace" (always true here) and "content" can be
 * checked from data the app has; the other two stay as links.
 */
const GetSetUp = ({ hasContent }: { hasContent: boolean }) => {
  const steps = [
    {
      title: "Create your workspace",
      text: "Your workspace is ready.",
      done: true,
    },
    {
      title: "Add content",
      text: "Add your FAQs as content cards.",
      done: hasContent,
      link: { href: "/content", label: "Add content" },
    },
    {
      title: "Test your answers",
      text: "Check that responses sound right.",
      done: false,
      link: { href: "/content", label: "Open testing" },
    },
    {
      title: "Connect your chatbot",
      text: "Use your API key and our guides.",
      done: false,
      link: { href: "/integrations", label: "View integrations" },
    },
  ];
  const doneCount = steps.filter((s) => s.done).length;

  return (
    <section
      aria-labelledby="get-set-up"
      className="flex flex-col gap-4 border bg-card p-5 shadow-xs"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="get-set-up" className="text-base font-semibold tracking-tight">
            Get set up
          </h2>
          <p className="text-[13px] text-muted-foreground">
            Your insights appear here once real questions start coming in.
          </p>
        </div>
        <div className="w-56">
          <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <b className="font-medium text-foreground tabular-nums">
              {doneCount} of {steps.length}
            </b>
          </div>
          <div
            role="img"
            aria-label={`${doneCount} of ${steps.length} steps complete`}
            className="h-1.5 bg-muted"
          >
            <span
              className="block h-full bg-primary"
              style={{ width: `${(doneCount / steps.length) * 100}%` }}
            />
          </div>
        </div>
      </div>
      <ol className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {steps.map((step, i) => (
          <li key={step.title} className="flex flex-col gap-2 border bg-background p-4">
            <span
              className={cn(
                "flex size-6 items-center justify-center border border-input text-xs font-semibold text-muted-foreground",
                step.done && "border-primary bg-primary text-primary-foreground",
              )}
            >
              {step.done ? <IconCheck className="size-3.5" aria-label="Done" /> : i + 1}
            </span>
            <b className="text-sm font-semibold">{step.title}</b>
            <span className="text-[13px] text-muted-foreground">{step.text}</span>
            {step.done ? (
              <span className="mt-auto text-xs text-muted-foreground">Done</span>
            ) : (
              step.link && (
                <Link
                  href={step.link.href}
                  className="mt-auto inline-flex items-center gap-1.5 text-[13px] font-medium text-primary underline-offset-4 hover:underline"
                >
                  {step.link.label}
                  <IconArrowRight className="size-3.5" aria-hidden="true" />
                </Link>
              )
            )}
          </li>
        ))}
      </ol>
    </section>
  );
};

export default Overview;
