"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
} from "@mui/material";
import Pagination from "@mui/material/Pagination";
import { ApexOptions } from "apexcharts";
import Box from "@mui/material/Box";
import theme from "@/theme";
import dynamic from "next/dynamic";
import { RowDataType, ApexTSDataPoint } from "@/app/dashboard/types";
import { SortableTableHeader } from "./SortableTableHeader";
const ReactApexcharts = dynamic(() => import("react-apexcharts"), { ssr: false });

interface QueryCountTimeSeriesProps {
  queryCount: ApexTSDataPoint[];
  color: string;
  isIncreasing: boolean;
}

const QueryCountTimeSeries: React.FC<QueryCountTimeSeriesProps> = ({
  queryCount,
  color,
}) => {
  const series = [
    {
      name: "Query Count",
      data: queryCount.map((pt) => ({
        x: new Date(pt.x).toISOString(),
        y: pt.y,
      })),
    },
  ];
  const options: ApexOptions = {
    chart: { sparkline: { enabled: true }, background: "#fff" },
    dataLabels: { enabled: false },
    stroke: { width: 2, curve: "smooth" },
    xaxis: { type: "datetime" },
    tooltip: { x: { format: "MMM dd, yyyy" } },
    colors: [color],
  };
  return (
    <ReactApexcharts
      type="line"
      options={options}
      series={series}
      height={20}
      width="100%"
    />
  );
};

interface ContentsTableProps {
  rows: RowDataType[];
  rowsPerPage: number;
  chartColors: string[];
  onClick: (content_id: number) => void;
  onItemsToDisplayChange: (items: RowDataType[]) => void;
  onSortChange: (column: string, direction: "ascending" | "descending") => void;
  onPageChange: (newPage: number) => void;
}

const ContentsTable: React.FC<ContentsTableProps> = ({
  rows,
  rowsPerPage,
  chartColors,
  onClick,
  onItemsToDisplayChange,
  onSortChange,
  onPageChange,
}) => {
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<keyof RowDataType>("query_count");
  const [sortOrder, setSortOrder] = useState<"ascending" | "descending">("descending");
  const [searchTerm, setSearchTerm] = useState("");

  const percentageIncrease = (queryCount: number[]): number => {
    if (queryCount.length < 4) return 0;
    const queryLength = queryCount.length;
    const lastQuarter = queryCount.slice(
      Math.floor((queryLength / 4) * 3),
      queryLength,
    );
    const lastQuarterValue =
      lastQuarter.reduce((a, b) => a + b, 0) / lastQuarter.length;
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

  useEffect(() => {
    onItemsToDisplayChange(displayedRows);
  }, [displayedRows, onItemsToDisplayChange]);

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

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    onPageChange(value);
  };

  const pageCount = Math.ceil(filteredRows.length / rowsPerPage);

  return (
    <TableContainer component={Paper} sx={{ marginTop: 3 }}>
      <Table>
        <TableHead sx={{ backgroundColor: theme.palette.lightgray.main }}>
          <TableRow>
            <TableCell>Content Title</TableCell>
            <SortableTableHeader
              label="Daily Average Sent"
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
            />
          </TableRow>
          <TableRow>
            <TableCell sx={{ paddingTop: 0 }}>
              <TextField
                id="content-search"
                placeholder="Search"
                size="small"
                sx={{ width: "90%", mt: 1.5, bgcolor: "white" }}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </TableCell>
            <TableCell colSpan={4} />
          </TableRow>
        </TableHead>
        <TableBody>
          {displayedRows.map((row, idx) => {
            const color = chartColors[idx] || "#000";
            return (
              <TableRow
                key={row.id}
                onClick={() => onClick(row.id)}
                sx={{
                  "&:hover": {
                    boxShadow: "0px 0px 8px rgba(211,211,211,0.75)",
                    zIndex: 1000,
                    cursor: "pointer",
                  },
                }}
              >
                <TableCell sx={{ width: "35%" }}>{row.title}</TableCell>
                <TableCell sx={{ width: "15%" }}>{row.query_count}</TableCell>
                <TableCell sx={{ width: "10%" }}>{row.positive_votes}</TableCell>
                <TableCell sx={{ width: "10%" }}>{row.negative_votes}</TableCell>
                <TableCell sx={{ width: "30%" }}>
                  <QueryCountTimeSeries
                    queryCount={row.query_count_timeseries}
                    color={color}
                    isIncreasing={
                      percentageIncrease(row.query_count_timeseries.map((p) => p.y)) > 0
                    }
                  />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          mt: 2,
          mb: 4,
        }}
      >
        <Pagination
          color="primary"
          showFirstButton
          showLastButton
          page={page}
          onChange={handlePageChange}
          count={pageCount}
        />
      </Box>
    </TableContainer>
  );
};

export default ContentsTable;
