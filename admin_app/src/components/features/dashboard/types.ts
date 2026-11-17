/** Dashboard sub-pages, picked from the app sidebar via ?page=<slug>. */
type PageName = "Overview" | "Content Performance" | "Query Topics";
type Period = "day" | "week" | "month" | "year" | "custom";
type TimeFrame = "Last 24 hours" | "Last 7 days" | "Last month" | "Last year";
type CustomDashboardFrequency = "Hour" | "Day" | "Week" | "Month";

interface CustomDateParams {
  startDate: string | null;
  endDate: string | null;
  frequency: CustomDashboardFrequency;
}
interface DrawerData {
  title: string;
  query_count: number;
  positive_votes: number;
  negative_votes: number;
  daily_query_count_avg: number;
  /** One row per time bucket for the drawer's line chart. */
  line_chart_data: DrawerChartRow[];
  user_feedback: {
    timestamp: string;
    question: string;
    feedback: string;
  }[];
}

interface DrawerChartRow {
  timestamp: number;
  query_count: number;
  positive_count: number;
  negative_count: number;
}

interface DayHourUsageData {
  [key: string]: {
    [day: string]: number;
  };
}

interface ApexData {
  name: string;
  data: { x: string; y: number }[];
  color?: string;
  zIndex?: number;
}

interface InputSeriesData {
  [category: string]: {
    [timestamp: string]: number;
  };
}

interface ApexTSDataPoint {
  x: number;
  y: number;
}

interface ApexSeriesData {
  name: string;
  data: ApexTSDataPoint[];
  group: string;
}

interface ContentData {
  title: string;
  query_count: number;
  positive_votes: number;
  negative_votes: number;
}

const drawerWidth = 240;

interface TopContentData extends ContentData {
  last_updated: string;
}

interface RowDataType extends ContentData {
  id: number;
  query_count_timeseries: ApexTSDataPoint[];
}

interface QueryData {
  query_text: string;
  query_datetime_utc: string;
}

interface TopicModelingData {
  topic_id: number;
  topic_samples: QueryData[];
  topic_summary: string;
  topic_name: string;
  topic_popularity: number;
}

type Status = "not_started" | "in_progress" | "completed" | "error";

interface TopicModelingResponse {
  status: Status;
  refreshTimeStamp: string;
  data: TopicModelingData[];
  unclustered_queries: QueryData[];
  error_message?: string;
  failure_step?: string;
}

interface TopicData {
  topic_id: number;
  topic_name: string;
  topic_popularity: number;
}

interface ContentLineChartTSData {
  name: string;
  data: ApexTSDataPoint[];
  color?: string;
  zIndex?: number;
}
/* ---------- Raw API responses (before parsing in queries.ts) ---------- */

interface StatsCardsResponse {
  query_stats: { n_questions: number; percentage_increase: number };
  response_feedback_stats: {
    n_negative: number;
    percentage_negative_increase: number;
  };
  urgency_stats: { n_urgent: number; percentage_increase: number };
  content_feedback_stats: {
    n_positive: number;
    n_negative: number;
    percentage_positive_increase: number;
    percentage_negative_increase: number;
  };
}

/** GET /dashboard/overview/<period> */
interface OverviewResponse {
  stats_cards: StatsCardsResponse;
  heatmap: DayHourUsageData;
  time_series: InputSeriesData;
  top_content: TopContentData[];
}

/** One row per time bucket in the Overview "Queries over time" chart. */
interface QueriesOverTimeRow {
  timestamp: number;
  normal: number;
  downvoted: number;
  urgent: number;
}

/** Overview data after parsing, ready for the presentational components. */
interface OverviewData {
  stats: StatsCardsResponse;
  heatmap: DayHourUsageData;
  timeseries: QueriesOverTimeRow[];
  topContent: TopContentData[];
}

/** GET /dashboard/performance/<period> */
interface PerformanceResponse {
  content_time_series: {
    id: number;
    title: string;
    total_query_count: number;
    positive_votes: number;
    negative_votes: number;
    query_count_time_series: Record<string, number>;
  }[];
}

/** GET /dashboard/performance/<period>/<content_id> */
interface DrawerResponse {
  title: string;
  query_count: number;
  positive_votes: number;
  negative_votes: number;
  daily_query_count_avg: number;
  time_series: Record<
    string,
    { query_count: number; positive_count: number; negative_count: number }
  >;
  user_feedback: DrawerData["user_feedback"];
}

/** Sort state reported by the content performance table. */
type SortDirection = "ascending" | "descending";

export type {
  PageName,
  StatsCardsResponse,
  OverviewResponse,
  QueriesOverTimeRow,
  OverviewData,
  PerformanceResponse,
  DrawerResponse,
  SortDirection,
  DrawerChartRow,
  Period,
  TimeFrame,
  DrawerData,
  DayHourUsageData,
  ApexData,
  InputSeriesData,
  ApexTSDataPoint,
  ApexSeriesData,
  TopContentData,
  RowDataType,
  QueryData,
  TopicModelingData,
  TopicModelingResponse,
  Status,
  CustomDateParams,
  CustomDashboardFrequency,
  ContentLineChartTSData,
  TopicData,
};

export { drawerWidth };
