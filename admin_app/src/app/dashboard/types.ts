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
}

interface TopContentData {
  title: string;
  last_updated: string;
  query_count: number;
  positive_votes: number;
  negative_votes: number;
}

const drawerWidth = 240;

export type { Period, TimeFrame, DayHourUsageData, ApexData, TopContentData };
export { drawerWidth };
