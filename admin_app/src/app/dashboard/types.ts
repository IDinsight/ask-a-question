type Period = "day" | "week" | "month" | "year" | "custom";
type TimeFrame = "Last 24 hours" | "Last week" | "Last month" | "Last year";
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
  line_chart_data: ApexData[];
  user_feedback: {
    timestamp: string;
    question: string;
    feedback: string;
  }[];
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
export type {
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
