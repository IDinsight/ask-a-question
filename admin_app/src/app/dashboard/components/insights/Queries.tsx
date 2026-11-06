import React from "react";
import Link from "next/link";
import { IconArrowRight, IconCategory, IconSparkles } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { QueryData } from "../../types";

interface QueriesProps {
  data: QueryData[];
  onRefreshClick: () => void;
  lastRefreshed: string;
  refreshing: boolean;
  aiSummary: string;
}

const formatDateTime = (value: string) =>
  Intl.DateTimeFormat("en-ZA", { dateStyle: "short", timeStyle: "short" }).format(
    new Date(value),
  );

/** AI-written summary of the selected topic. */
const AISummary: React.FC<{ aiSummary: string }> = ({ aiSummary }) => (
  <div className="flex flex-col gap-2 border bg-muted/50 p-4">
    <span className="flex items-center gap-2 text-sm font-semibold">
      <IconSparkles className="size-4 text-chart-1" aria-hidden="true" />
      AI overview
    </span>
    <p className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
      {aiSummary}
    </p>
  </div>
);

/** Example queries for the selected topic, plus the "Run discovery" control. */
const Queries: React.FC<QueriesProps> = ({
  data,
  onRefreshClick,
  lastRefreshed,
  refreshing,
  aiSummary,
}) => {
  const formattedLastRefreshed =
    lastRefreshed.length > 0 ? formatDateTime(lastRefreshed) : "Never";

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold tracking-tight">Example queries</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            Last run: {formattedLastRefreshed}
          </span>
          <Button
            size="lg"
            className="bg-warning text-warning-foreground hover:bg-warning/90"
            disabled={refreshing}
            onClick={onRefreshClick}
          >
            {refreshing ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <IconSparkles data-icon="inline-start" />
            )}
            {refreshing
              ? "Running discovery…"
              : data.length > 0
                ? "Rerun discovery"
                : "Run discovery"}
          </Button>
        </div>
      </div>

      {data.length > 0 ? (
        <>
          <AISummary aiSummary={aiSummary} />
          <div className="min-h-0 flex-1 overflow-y-auto border">
            <Table className="text-sm">
              <TableHeader className="sticky top-0 z-10 bg-muted">
                <TableRow>
                  <TableHead className="w-[20%] px-3">Timestamp</TableHead>
                  <TableHead className="px-3">User question</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="px-3 align-top text-muted-foreground tabular-nums">
                      {formatDateTime(row.query_datetime_utc)}
                    </TableCell>
                    <TableCell className="px-3 whitespace-normal">{row.query_text}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 py-8 text-center">
          <div className="mb-1.5 flex size-11 items-center justify-center border bg-muted">
            <IconCategory className="size-5" aria-hidden="true" />
          </div>
          <b className="text-base font-semibold">Discover what people ask about</b>
          <span className="max-w-100 text-[13px] text-muted-foreground">
            Run discovery to group recent queries into topics and see real examples of
            each. It needs queries from your chatbot in this period to find anything.
          </span>
          <Link
            href="/integrations"
            className="inline-flex items-center gap-1.5 text-[13px] font-medium text-primary underline-offset-4 hover:underline"
          >
            Connect your chatbot
            <IconArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </div>
      )}
    </div>
  );
};

export default Queries;
