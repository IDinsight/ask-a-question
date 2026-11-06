"use client";
import React from "react";
import { format } from "date-fns";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { CustomDashboardFrequency } from "../../types";

/** One bar position: query counts at a point in time (ms since epoch). */
interface QueriesOverTimeRow {
  timestamp: number;
  normal: number;
  downvoted: number;
  urgent: number;
}

interface StackedBarChartProps {
  data: QueriesOverTimeRow[];
  /** Bucket size of each bar; picks the x-axis label format. */
  frequency: CustomDashboardFrequency;
  /** Label days as "Mon 1" (used for the 7-day view). */
  showDayOfWeek?: boolean;
}

// Colours from the design board: blue normal, amber urgent, red downvoted.
const chartConfig = {
  normal: { label: "Normal", color: "var(--chart-1)" },
  urgent: { label: "Urgent", color: "var(--urgent)" },
  downvoted: { label: "Downvoted", color: "var(--destructive)" },
} satisfies ChartConfig;

const tickFormat = (frequency: CustomDashboardFrequency, showDayOfWeek?: boolean) => {
  switch (frequency) {
    case "Hour":
      return "HH:mm";
    case "Day":
      return showDayOfWeek ? "EEE d" : "MMM d";
    case "Week":
      return "MMM d";
    case "Month":
      return "MMM yyyy";
  }
};

/** Colour key shown in the card header (the board places it top-right). */
const QueriesLegend = () => (
  <div className="flex flex-wrap gap-3.5 text-xs text-muted-foreground">
    {(["normal", "urgent", "downvoted"] as const).map((key) => (
      <span key={key} className="flex items-center gap-1.5">
        <i
          className="inline-block size-2"
          style={{ background: chartConfig[key].color }}
          aria-hidden="true"
        />
        {chartConfig[key].label}
      </span>
    ))}
  </div>
);

/**
 * Queries per time bucket. Normal and downvoted queries stack in one bar;
 * urgent queries get their own bar beside it (they overlap the other two).
 */
const StackedBarChart: React.FC<StackedBarChartProps> = ({
  data,
  frequency,
  showDayOfWeek,
}) => {
  const isEmpty = data.every((row) => !row.normal && !row.downvoted && !row.urgent);
  const labelFormat = tickFormat(frequency, showDayOfWeek);

  return (
    <div className="relative">
      <ChartContainer config={chartConfig} className="aspect-auto h-60 w-full">
        <BarChart data={data} margin={{ left: -16, right: 4, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={16}
            tickFormatter={(value: number) => format(value, labelFormat)}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            // Keep a visible scale when every bar is zero
            domain={isEmpty ? [0, 20] : [0, "auto"]}
          />
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                labelFormatter={(_, payload) => {
                  const ts = payload?.[0]?.payload?.timestamp;
                  return ts ? format(ts, frequency === "Hour" ? "EEE d MMM, HH:mm" : "EEE d MMM yyyy") : "";
                }}
              />
            }
          />
          <Bar dataKey="normal" stackId="a" fill="var(--color-normal)" />
          <Bar dataKey="downvoted" stackId="a" fill="var(--color-downvoted)" />
          <Bar dataKey="urgent" stackId="b" fill="var(--color-urgent)" />
        </BarChart>
      </ChartContainer>
      {isEmpty && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="border bg-card px-2.5 py-0.5 text-xs text-muted-foreground">
            No queries in this period
          </span>
        </div>
      )}
    </div>
  );
};

export default StackedBarChart;
export { QueriesLegend };
export type { QueriesOverTimeRow };
