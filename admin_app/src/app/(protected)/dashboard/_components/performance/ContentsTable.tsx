"use client";

import React, { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { IconSearch } from "@tabler/icons-react";
import { Line, LineChart } from "recharts";

import { Button } from "@/components/ui/button";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RowDataType, ApexTSDataPoint } from "@/app/(protected)/dashboard/types";
import { SortableTableHeader } from "./SortableTableHeader";

/** Tiny line of query counts over the period, in the row's chart colour. */
const QueryCountTimeSeries: React.FC<{
  queryCount: ApexTSDataPoint[];
  color: string;
}> = ({ queryCount, color }) => (
  <ChartContainer
    config={{ y: { label: "Sent", color } }}
    className="aspect-auto h-6 w-full min-w-24"
    initialDimension={{ width: 160, height: 24 }}
  >
    <LineChart data={queryCount} margin={{ top: 2, bottom: 2, left: 2, right: 2 }}>
      <ChartTooltip
        cursor={false}
        content={
          <ChartTooltipContent
            labelFormatter={(_, payload) => {
              const x = payload?.[0]?.payload?.x;
              return x ? format(x, "MMM d, yyyy") : "";
            }}
          />
        }
      />
      <Line
        dataKey="y"
        type="monotone"
        stroke="var(--color-y)"
        strokeWidth={2}
        dot={false}
        isAnimationActive={false}
      />
    </LineChart>
  </ChartContainer>
);

interface ContentsTableProps {
  rows: RowDataType[];
  rowsPerPage: number;
  chartColors: string[];
  onClick: (content_id: number) => void;
  onItemsToDisplayChange: (items: RowDataType[]) => void;
  onSortChange: (column: string, direction: "ascending" | "descending") => void;
  onPageChange: (newPage: number) => void;
  /** Shown in the empty state, e.g. "Show last month". Omitted when there's no longer range. */
  longerRange?: { label: string; onSelect: () => void };
}

// Relative change between the last two quarters of the series; drives "Trend" sorting.
const percentageIncrease = (queryCount: number[]): number => {
  if (queryCount.length < 4) return 0;
  const queryLength = queryCount.length;
  const lastQuarter = queryCount.slice(Math.floor((queryLength / 4) * 3), queryLength);
  const lastQuarterValue = lastQuarter.reduce((a, b) => a + b, 0) / lastQuarter.length;
  const thirdQuarter = queryCount.slice(
    Math.floor((queryLength / 4) * 2),
    Math.floor((queryLength / 4) * 3),
  );
  const thirdQuarterValue =
    thirdQuarter.reduce((a, b) => a + b, 0) / thirdQuarter.length;
  return (lastQuarterValue - thirdQuarterValue) / (thirdQuarterValue || 1);
};

const sortRows = <K extends keyof RowDataType>(
  data: RowDataType[],
  byParam: K,
  order: "ascending" | "descending",
): RowDataType[] => {
  return [...data].sort((a, b) => {
    let cmp = 0;
    if (byParam === "query_count_timeseries") {
      const diffA = percentageIncrease(
        (a[byParam] as ApexTSDataPoint[]).map((p) => p.y),
      );
      const diffB = percentageIncrease(
        (b[byParam] as ApexTSDataPoint[]).map((p) => p.y),
      );
      cmp = diffA - diffB;
    } else {
      cmp = (a[byParam] as number) - (b[byParam] as number);
    }
    return order === "ascending" ? cmp : -cmp;
  });
};

const ContentsTable: React.FC<ContentsTableProps> = ({
  rows,
  rowsPerPage,
  chartColors,
  onClick,
  onItemsToDisplayChange,
  onSortChange,
  onPageChange,
  longerRange,
}) => {
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<keyof RowDataType>("query_count");
  const [sortOrder, setSortOrder] = useState<"ascending" | "descending">("descending");
  const [searchTerm, setSearchTerm] = useState("");

  const filteredRows = useMemo(() => {
    return searchTerm
      ? rows.filter((r) => r.title.toLowerCase().includes(searchTerm.toLowerCase()))
      : rows;
  }, [rows, searchTerm]);

  const displayedRows = useMemo(() => {
    const sorted = sortRows(filteredRows, sortColumn, sortOrder);
    const start = (page - 1) * rowsPerPage;
    return sorted.slice(start, start + rowsPerPage);
  }, [filteredRows, page, sortColumn, sortOrder, rowsPerPage]);

  // The parent charts whatever rows are on screen.
  useEffect(() => {
    onItemsToDisplayChange(displayedRows);
  }, [displayedRows, onItemsToDisplayChange]);

  const changePage = (value: number) => {
    setPage(value);
    onPageChange(value);
  };

  const handleSort = (column: keyof RowDataType) => {
    let newOrder: "ascending" | "descending" = "descending";
    if (column === sortColumn) {
      newOrder = sortOrder === "ascending" ? "descending" : "ascending";
      setSortOrder(newOrder);
    } else {
      setSortColumn(column);
      setSortOrder("descending");
    }
    onSortChange(column.toString(), newOrder);
  };

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / rowsPerPage));

  return (
    <section
      aria-label="Content table"
      className="overflow-hidden border bg-card shadow-xs"
    >
      <div className="flex flex-wrap gap-2 px-4 py-3">
        <InputGroup className="h-9 w-full sm:w-75">
          <InputGroupAddon>
            <IconSearch aria-hidden="true" />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            aria-label="Search content titles"
            placeholder="Search content titles"
            className="text-sm md:text-sm"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              changePage(1); // new results start from the first page
            }}
          />
        </InputGroup>
      </div>
      <Table className="min-w-[720px] text-sm">
        <TableHeader className="bg-muted">
          <TableRow>
            <TableHead className="w-[35%] px-4">Content title</TableHead>
            <SortableTableHeader
              label="Daily average sent"
              columnKey="query_count"
              sortColumn={sortColumn}
              sortOrder={sortOrder}
              onSort={handleSort}
            />
            <SortableTableHeader
              label="Upvotes"
              columnKey="positive_votes"
              sortColumn={sortColumn}
              sortOrder={sortOrder}
              onSort={handleSort}
            />
            <SortableTableHeader
              label="Downvotes"
              columnKey="negative_votes"
              sortColumn={sortColumn}
              sortOrder={sortOrder}
              onSort={handleSort}
            />
            <SortableTableHeader
              label="Trend"
              columnKey="query_count_timeseries"
              sortColumn={sortColumn}
              sortOrder={sortOrder}
              onSort={handleSort}
              className="w-[25%]"
            />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayedRows.map((row, idx) => (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              onClick={() => onClick(row.id)}
            >
              <TableCell className="px-4 whitespace-normal">
                {/* The title is the keyboard target; the whole row is clickable for mice */}
                <button
                  type="button"
                  className="text-left font-medium underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={(e) => {
                    e.stopPropagation();
                    onClick(row.id);
                  }}
                >
                  {row.title}
                </button>
              </TableCell>
              <TableCell className="px-4 tabular-nums">{row.query_count}</TableCell>
              <TableCell className="px-4 tabular-nums">{row.positive_votes}</TableCell>
              <TableCell className="px-4 tabular-nums">{row.negative_votes}</TableCell>
              <TableCell className="px-4">
                <QueryCountTimeSeries
                  queryCount={row.query_count_timeseries}
                  color={chartColors[idx] ?? chartColors[0]}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {rows.length === 0 && (
        <div className="flex flex-col items-center gap-1.5 px-5 py-12 text-center">
          <b className="text-sm font-semibold">No content performance yet</b>
          <span className="max-w-100 text-[13px] text-muted-foreground">
            Once your chatbot starts sending answers, you will see how each card
            performs and how people rate it. Try a longer time range if you expected
            data.
          </span>
          {longerRange && (
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={longerRange.onSelect}
            >
              {longerRange.label}
            </Button>
          )}
        </div>
      )}
      {rows.length > 0 && filteredRows.length === 0 && (
        <p className="px-5 py-10 text-center text-sm text-muted-foreground">
          No content titles match “{searchTerm}”.
        </p>
      )}

      <nav
        aria-label="Table pages"
        className="flex items-center justify-end gap-2 border-t px-4 py-2.5"
      >
        <span className="mr-auto text-xs text-muted-foreground tabular-nums">
          Page {Math.min(page, pageCount)} of {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => changePage(page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pageCount}
          onClick={() => changePage(page + 1)}
        >
          Next
        </Button>
      </nav>
    </section>
  );
};

export default ContentsTable;
