type Period = "day" | "week" | "month" | "year";
type TimeFrame = "Last 24 hours" | "Last week" | "Last month" | "Last year";

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
  query_count_timeseries: number[];
  id: number;
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

interface TopicModelingResponse {
  refreshTimeStamp: string;
  data: TopicModelingData[];
  unclustered_queries: QueryData[];
}

interface TopicData {
  topic_id: number;
  topic_name: string;
  topic_popularity: number;
}

export type {
  DrawerData,
  Period,
  TimeFrame,
  DayHourUsageData,
  ApexData,
  TopContentData,
  RowDataType,
  QueryData,
  TopicData,
  TopicModelingData,
  TopicModelingResponse,
};

export { drawerWidth };
