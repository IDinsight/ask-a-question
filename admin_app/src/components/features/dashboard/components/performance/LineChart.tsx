"use client";

import React, { useMemo } from "react";
import { format } from "date-fns";
import {
  CartesianGrid,
  Line,
  LineChart as RechartsLineChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { ContentLineChartTSData } from "@/components/features/dashboard/types";

interface LineChartProps {
  /** One series per content card currently shown in the table. */
  data: ContentLineChartTSData[];
  /** Colour per series, by position (matches the table's trend sparklines). */
  chartColors: string[];
}

/**
 * Queries over time for the content cards on the current table page.
 * Recharts wants one row per x value, so the per-card series are merged on
 * timestamp into rows like { timestamp, s0: 4, s1: 2, ... }.
 */
const LineChart: React.FC<LineChartProps> = ({ data, chartColors }) => {
  // Series keys are s0..sN; titles can contain anything, so they only go in labels.
  const config = useMemo<ChartConfig>(
    () =>
      Object.fromEntries(
        data.map((series, i) => [
          `s${i}`,
          { label: series.name, color: chartColors[i] ?? chartColors[0] },
        ]),
      ),
    [data, chartColors],
  );

  const rows = useMemo(() => {
    const byTimestamp = new Map<number, Record<string, number>>();
    data.forEach((series, i) =>
      series.data.forEach(({ x, y }) => {
        const row = byTimestamp.get(x) ?? { timestamp: x };
        row[`s${i}`] = y;
        byTimestamp.set(x, row);
      }),
    );
    return Array.from(byTimestamp.values()).sort(
      (a, b) => a.timestamp - b.timestamp,
    );
  }, [data]);

  const isEmpty = data.every((series) => series.data.every((p) => !p.y));

  return (
    <div className="relative">
      <ChartContainer config={config} className="aspect-auto h-64 w-full">
        <RechartsLineChart data={rows} margin={{ left: -16, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={24}
            tickFormatter={(value: number) => format(value, "MMM d")}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            domain={isEmpty ? [0, 20] : [0, "auto"]}
          />
          {!isEmpty && (
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(_, payload) => {
                    const ts = payload?.[0]?.payload?.timestamp;
                    return ts ? format(ts, "EEE d MMM yyyy") : "";
                  }}
                />
              }
            />
          )}
          {data.length > 1 && (
            <ChartLegend
              verticalAlign="top"
              itemSorter={null} // keep table order, not alphabetical by key
              content={
                <ChartLegendContent className="flex-wrap justify-start pb-4 pl-4" />
              }
            />
          )}
          {data.map((_, i) => (
            <Line
              key={`s${i}`}
              dataKey={`s${i}`}
              type="monotone"
              stroke={`var(--color-s${i})`}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </RechartsLineChart>
      </ChartContainer>
      {isEmpty && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="border bg-card px-2.5 py-0.5 text-xs text-muted-foreground">
            No content sent in this period
          </span>
        </div>
      )}
    </div>
  );
};

export default LineChart;
