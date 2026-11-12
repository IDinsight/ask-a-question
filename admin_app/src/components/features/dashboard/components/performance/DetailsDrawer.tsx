"use client";

import React from "react";
import { format } from "date-fns";
import { IconSparkles } from "@tabler/icons-react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Trace, TraceLine, TraceTitle } from "@/components/ui/trace";
import { DrawerData } from "@/components/features/dashboard/types";
import { SERIES_COLORS } from "./seriesColors";

interface DetailsDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: DrawerData | null;
  aiSummary: string | null;
}

const chartConfig = {
  query_count: { label: "Total sent", color: SERIES_COLORS[0] },
  positive_count: { label: "Upvotes", color: SERIES_COLORS[2] },
  negative_count: { label: "Downvotes", color: SERIES_COLORS[1] },
} satisfies ChartConfig;

/** Sent / upvotes / downvotes over the period for one content card. */
const ContentLineChart = ({ rows }: { rows: DrawerData["line_chart_data"] }) => (
  <ChartContainer config={chartConfig} className="aspect-auto h-60 w-full">
    <LineChart data={rows} margin={{ left: -16, right: 8, top: 8 }}>
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
      <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
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
      {/* itemSorter={null} keeps series order (Recharts sorts by key otherwise) */}
      <ChartLegend
        verticalAlign="top"
        itemSorter={null}
        content={<ChartLegendContent className="pb-3" />}
      />
      {(Object.keys(chartConfig) as (keyof typeof chartConfig)[]).map((key) => (
        <Line
          key={key}
          dataKey={key}
          type="monotone"
          stroke={`var(--color-${key})`}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      ))}
    </LineChart>
  </ChartContainer>
);

const Stat = ({ title, value }: { title: string; value: number }) => (
  <div className="flex flex-col gap-0.5 border bg-background p-3">
    <span className="text-xs text-muted-foreground">{title}</span>
    <span className="text-lg font-semibold tabular-nums">{value.toLocaleString()}</span>
  </div>
);

/** Side panel with one content card's numbers, chart, AI summary and user feedback. */
const DetailsDrawer: React.FC<DetailsDrawerProps> = ({
  open,
  onOpenChange,
  data,
  aiSummary,
}) => {
  if (data === null) return null;
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full gap-6 overflow-y-auto p-6 text-sm data-[side=right]:sm:max-w-2xl"
      >
        <SheetHeader className="p-0 pr-8">
          <SheetTitle className="text-lg font-semibold">{data.title}</SheetTitle>
          <SheetDescription>Performance for the selected time range.</SheetDescription>
        </SheetHeader>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat title="Total sent" value={data.query_count} />
          <Stat title="Daily average sent" value={data.daily_query_count_avg} />
          <Stat title="Total upvotes" value={data.positive_votes} />
          <Stat title="Total downvotes" value={data.negative_votes} />
        </div>

        <div className="border p-4">
          <ContentLineChart rows={data.line_chart_data} />
        </div>

        <section aria-labelledby="feedback-heading" className="flex flex-col gap-4">
          <h3 id="feedback-heading" className="text-base font-semibold tracking-tight">
            Feedback by users
          </h3>
          <div className="flex flex-col gap-2 border bg-muted/50 p-4">
            <span className="flex items-center gap-2 font-semibold">
              <IconSparkles className="size-4 text-chart-1" aria-hidden="true" />
              AI overview
            </span>
            {aiSummary === null ? (
              // Shimmer line while the summary is generated, same as the test panels
              <Trace role="status">
                <TraceLine status="running">
                  <TraceTitle>Summarising feedback...</TraceTitle>
                </TraceLine>
              </Trace>
            ) : (
              <p className="leading-relaxed whitespace-pre-wrap text-muted-foreground">
                {aiSummary}
              </p>
            )}
          </div>
          <div className="border">
            <Table aria-label="User feedback">
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="w-[20%] px-3">Timestamp</TableHead>
                  <TableHead className="w-[40%] px-3">User question</TableHead>
                  <TableHead className="w-[40%] px-3">User feedback</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.user_feedback.length === 0 ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell
                      colSpan={3}
                      className="px-3 py-6 text-center text-muted-foreground"
                    >
                      No feedback in this period.
                    </TableCell>
                  </TableRow>
                ) : (
                  data.user_feedback.map((feedback) => (
                    <TableRow key={feedback.timestamp}>
                      <TableCell className="px-3 align-top text-muted-foreground tabular-nums">
                        {Intl.DateTimeFormat("en-ZA", {
                          dateStyle: "short",
                          timeStyle: "short",
                        }).format(new Date(feedback.timestamp))}
                      </TableCell>
                      <TableCell className="px-3 align-top whitespace-normal">
                        {feedback.question}
                      </TableCell>
                      <TableCell className="px-3 align-top whitespace-normal">
                        {feedback.feedback}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </section>
      </SheetContent>
    </Sheet>
  );
};

export default DetailsDrawer;
