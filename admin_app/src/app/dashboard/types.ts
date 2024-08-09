type Period = "day" | "week" | "month" | "year";
type TimeFrame = "Last 24 hours" | "Last week" | "Last month" | "Last year";

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
}

export type {
  Period,
  TimeFrame,
  DayHourUsageData,
  ApexData,
  TopContentData,
  RowDataType,
};

export { drawerWidth };
