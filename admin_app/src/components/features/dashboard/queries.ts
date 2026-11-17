/**
 * TanStack Query hooks for the dashboard. Every API call the dashboard makes
 * goes through a hook here; DashboardWrapper is the only caller.
 *
 * Conventions: see workspace-management/queries.ts (generated client via
 * /bff, hooks disabled until there is a token, generated query keys).
 * - Responses are parsed into UI-ready shapes with `select`, so components get
 *   plain data and never touch the raw API format.
 * - The dashboard keeps its hand-written response types (./types.ts), which
 *   describe the nested shapes in more detail than the spec's loose
 *   dict[str, ...] models; generated responses are read through them.
 */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { refreshInsightsFrequency } from "@/client";
import {
  createPlotOptions,
  retrieveContentAiSummaryOptions,
  retrieveContentDetailsOptions,
  retrieveContentOptions,
  retrieveInsightsFrequencyOptions,
  retrieveOverviewFrequencyOptions,
  retrievePerformanceFrequencyOptions,
} from "@/client/@tanstack/react-query.gen";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/utils/auth";
import type {
  CustomDashboardFrequency,
  CustomDateParams,
  DrawerData,
  DrawerResponse,
  OverviewData,
  OverviewResponse,
  PerformanceResponse,
  Period,
  RowDataType,
  TopicModelingResponse,
} from "./types";

/* ------------------------------------------------------------------ */
/* Period → request params                                             */
/* ------------------------------------------------------------------ */

/** The date window a dashboard request is scoped to. */
export interface PeriodParams {
  period: Period;
  startDate?: string;
  endDate?: string;
  frequency?: CustomDashboardFrequency;
}

/**
 * Turn the selected period into request params. Custom ranges carry their
 * dates and frequency; presets don't (the backend picks the frequency).
 */
export const toPeriodParams = (
  period: Period,
  custom: CustomDateParams,
): PeriodParams =>
  period === "custom"
    ? {
        period,
        startDate: custom.startDate ?? undefined,
        endDate: custom.endDate ?? undefined,
        frequency: custom.frequency,
      }
    : { period };

/** A custom period is only usable once both dates are picked. */
const isComplete = (p: PeriodParams) =>
  p.period !== "custom" || (!!p.startDate && !!p.endDate);

/** Path params shared by every dashboard endpoint. */
const timeframe = (p: PeriodParams) => ({ timeframe: p.period });

/** Date range query params: only custom periods send them. */
const dateRange = (p: PeriodParams) =>
  p.period === "custom" ? { start_date: p.startDate, end_date: p.endDate } : {};

/**
 * Overview query params. Custom periods also send a frequency (default
 * "Day"); presets only when one was chosen (the backend picks otherwise).
 */
const overviewQuery = (p: PeriodParams) =>
  p.period === "custom"
    ? { ...dateRange(p), frequency: p.frequency || "Day" }
    : p.frequency
    ? { frequency: p.frequency }
    : {};

/* ------------------------------------------------------------------ */
/* Overview                                                            */
/* ------------------------------------------------------------------ */

/** One row per timestamp with all three counts, the shape Recharts expects. */
const parseOverview = (data: OverviewResponse): OverviewData => {
  const series = data.time_series ?? {};
  // Timestamps match across categories; read them from "normal".
  const stamps = Object.keys(series["normal"] || {});
  return {
    stats: data.stats_cards,
    heatmap: data.heatmap,
    topContent: data.top_content,
    timeseries: stamps.map((stamp) => ({
      timestamp: new Date(stamp).getTime(),
      normal: Number(series["normal"]?.[stamp]) || 0,
      downvoted: Number(series["downvoted"]?.[stamp]) || 0,
      urgent: Number(series["urgent"]?.[stamp]) || 0,
    })),
  };
};

export const useOverviewQuery = (params: PeriodParams, enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveOverviewFrequencyOptions({
      path: timeframe(params),
      query: overviewQuery(params),
    }),
    select: (data) => parseOverview(data as unknown as OverviewResponse),
    enabled: enabled && !!token && isComplete(params),
  });
};

/** Only used by the setup checklist: does the workspace have any content yet? */
export const useHasContentQuery = (enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveContentOptions({ query: { limit: 1 } }),
    select: (data) => Array.isArray(data) && data.length > 0,
    enabled: enabled && !!token,
  });
};

/* ------------------------------------------------------------------ */
/* Content performance                                                 */
/* ------------------------------------------------------------------ */

const parsePerformance = (data: PerformanceResponse): RowDataType[] =>
  data.content_time_series.map((series) => ({
    id: series.id,
    title: series.title,
    query_count: series.total_query_count,
    positive_votes: series.positive_votes,
    negative_votes: series.negative_votes,
    query_count_timeseries: Object.entries(series.query_count_time_series).map(
      ([timestamp, value]) => ({ x: new Date(timestamp).getTime(), y: value }),
    ),
  }));

export const usePerformanceQuery = (params: PeriodParams, enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    // The performance endpoints take no frequency.
    ...retrievePerformanceFrequencyOptions({
      path: timeframe(params),
      query: dateRange(params),
    }),
    select: (data) => parsePerformance(data as unknown as PerformanceResponse),
    enabled: enabled && !!token && isComplete(params),
  });
};

/** One chart row per time bucket, oldest first. */
const parseDrawer = (data: DrawerResponse): DrawerData => ({
  title: data.title,
  query_count: data.query_count,
  positive_votes: data.positive_votes,
  negative_votes: data.negative_votes,
  daily_query_count_avg: data.daily_query_count_avg,
  user_feedback: data.user_feedback,
  line_chart_data: Object.entries(data.time_series)
    .map(([bucket, ts]) => ({
      timestamp: new Date(bucket).getTime(),
      query_count: ts.query_count,
      positive_count: ts.positive_count,
      negative_count: ts.negative_count,
    }))
    .sort((a, b) => a.timestamp - b.timestamp),
});

/** Details for the content row that was clicked; idle until a row is picked. */
export const usePerformanceDrawerQuery = (
  params: PeriodParams,
  contentId: number | null,
) => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveContentDetailsOptions({
      // -1 only builds a key while idle (contentId null); it is never fetched.
      path: { ...timeframe(params), content_id: contentId ?? -1 },
      query: dateRange(params),
    }),
    select: (data) => parseDrawer(data as unknown as DrawerResponse),
    enabled: contentId !== null && !!token && isComplete(params),
  });
};

const AI_SUMMARY_DISABLED =
  "LLM functionality disabled on the backend. Please check your environment configuration if you wish to enable this feature.";

/** LLM summary for the drawer. Fetched in parallel with the drawer data. */
export const usePerformanceAISummaryQuery = (
  params: PeriodParams,
  contentId: number | null,
) => {
  const { token } = useAuth();
  return useQuery({
    ...retrieveContentAiSummaryOptions({
      path: { ...timeframe(params), content_id: contentId ?? -1 },
      query: dateRange(params),
    }),
    select: (data) => data?.ai_summary || AI_SUMMARY_DISABLED,
    enabled: contentId !== null && !!token && isComplete(params),
  });
};

/* ------------------------------------------------------------------ */
/* Query topics (insights)                                             */
/* ------------------------------------------------------------------ */

const POLLING_INTERVAL = 3 * 1000;
const POLLING_TIMEOUT = 3 * 60 * 1000;

const EMPTY_TOPICS: TopicModelingResponse = {
  status: "not_started",
  refreshTimeStamp: "",
  data: [],
  unclustered_queries: [],
  error_message: "",
  failure_step: "",
};

/**
 * Topic discovery for one period, including the "Run discovery" flow:
 *
 * 1. `runRefresh()` asks the backend to start a new topic-modelling job.
 * 2. The topics query is invalidated and, while the job reports
 *    `in_progress`, refetches every 3s (TanStack's refetchInterval replaces
 *    the old hand-rolled setInterval).
 * 3. Polling stops when the job completes or fails, or after 3 minutes.
 *
 * Toasts report each outcome. Polling only runs while this period is on
 * screen; coming back to a period picks up where it left off.
 */
export const useTopicInsights = (params: PeriodParams, enabled: boolean) => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  // The insights endpoint takes only the timeframe, so all custom ranges share
  // one cached result, as on the backend.
  const topicsOptions = retrieveInsightsFrequencyOptions({
    path: timeframe(params),
  });
  const key = topicsOptions.queryKey;
  const keyId = JSON.stringify(key);

  // Polling that ran past POLLING_TIMEOUT, per period key.
  const [timedOut, setTimedOut] = useState<Record<string, boolean>>({});

  const query = useQuery({
    queryKey: key,
    queryFn: async (context): Promise<TopicModelingResponse> =>
      (await topicsOptions.queryFn!(
        context,
      )) as unknown as TopicModelingResponse,
    enabled: enabled && !!token && isComplete(params),
    refetchInterval: (q) =>
      q.state.data?.status === "in_progress" && !timedOut[keyId]
        ? POLLING_INTERVAL
        : false,
  });

  const status = query.data?.status;

  // Give up polling after POLLING_TIMEOUT. The timer restarts whenever a
  // period starts showing "in_progress".
  useEffect(() => {
    if (status !== "in_progress" || timedOut[keyId]) return;
    const timer = setTimeout(() => {
      setTimedOut((prev) => ({ ...prev, [keyId]: true }));
      toast.add({
        title:
          "The processing is taking longer than expected. Please try again later.",
        type: "error",
      });
    }, POLLING_TIMEOUT);
    return () => clearTimeout(timer);
  }, [status, keyId, timedOut]);

  // Toast when a job we were waiting on finishes. `waiting` is set when we see
  // the job running (or start it), so a page load of finished data stays quiet.
  const waiting = useRef<Record<string, boolean>>({});
  useEffect(() => {
    if (status === "in_progress") {
      waiting.current[keyId] = true;
      return;
    }
    if (!waiting.current[keyId] || !status) return;
    waiting.current[keyId] = false;
    if (status === "completed") {
      toast.add({
        title: `Topic analysis successful for period: ${params.period}`,
        type: "success",
      });
    } else if (status === "error") {
      toast.add({
        title: `An error occurred: ${query.data?.error_message}`,
        type: "error",
      });
    }
  }, [status, keyId, params.period, query.data?.error_message]);

  const refresh = useMutation({
    mutationFn: async () => {
      const { data } = await refreshInsightsFrequency({
        path: timeframe(params),
        query: dateRange(params),
      });
      return data as { detail?: string } | undefined;
    },
    onMutate: () => {
      waiting.current[keyId] = true;
      setTimedOut((prev) => ({ ...prev, [keyId]: false }));
    },
    onSuccess: (response) => {
      if (response?.detail) toast.add({ title: response.detail, type: "info" });
      // Refetch now; an "in_progress" answer switches polling on.
      return queryClient.invalidateQueries({ queryKey: key });
    },
    onError: (error: { message?: string }) => {
      waiting.current[keyId] = false;
      toast.add({
        title: error.message || "There was a system error.",
        type: "error",
      });
    },
  });

  // A failed poll (network/5xx) also ends the wait.
  useEffect(() => {
    if (query.isError && waiting.current[keyId]) {
      waiting.current[keyId] = false;
      toast.add({ title: "There was a system error.", type: "error" });
    }
  }, [query.isError, keyId]);

  return {
    data: query.data ?? EMPTY_TOPICS,
    refreshing:
      refresh.isPending || (status === "in_progress" && !timedOut[keyId]),
    runRefresh: () => refresh.mutate(),
  };
};

/* ------------------------------------------------------------------ */
/* Topic visualisation (Bokeh)                                         */
/* ------------------------------------------------------------------ */

/**
 * The Bokeh plot spec (a JSON "item" for `embed_item`). Only fetched once the
 * user opens the plot card. Kept in cache for the session: it's expensive.
 */
export const useEmbeddingQuery = (params: PeriodParams, enabled: boolean) => {
  const { token } = useAuth();
  return useQuery({
    ...createPlotOptions({ path: timeframe(params) }),
    enabled: enabled && !!token && isComplete(params),
    staleTime: Infinity,
  });
};
