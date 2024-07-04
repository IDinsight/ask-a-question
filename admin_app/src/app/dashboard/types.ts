type Period = "day" | "week" | "month" | "year";
type TimeFrame = "Last 24 hours" | "Last week" | "Last month" | "Last year";

interface DayHourUsageData {
  [key: string]: {
    [day: string]: number;
  };
}

interface ApexDayHourUsageData {
  name: string;
  data: { x: string; y: number }[];
}

export type { Period, TimeFrame, DayHourUsageData, ApexDayHourUsageData };
