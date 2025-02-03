import { RowDataType } from "@/app/dashboard/types";
import SwapVertIcon from "@mui/icons-material/SwapVert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Pagination from "@mui/material/Pagination";
import TextField from "@mui/material/TextField";
import { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import theme from "@/theme";
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import React from "react";
import { appColors } from "@/utils";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

interface QueryCountTimeSeriesProps {
  queryCount: number[];
  color: string;
  isIncreasing: boolean;
}

// A small sparkline row chart
const QueryCountTimeSeries: React.FC<QueryCountTimeSeriesProps> = ({
  queryCount,
  color,
  isIncreasing,
}) => {
  const series = [
    {
      name: "Query Count",
      data: queryCount,
    },
  ];
  const options: ApexOptions = {
    chart: {
      stacked: false,
      zoom: { enabled: false },
      sparkline: { enabled: true },
      background: "#fff",
    },
    dataLabels: { enabled: false },
    stroke: {
      width: 2,
      curve: "smooth",
    },
    tooltip: {
      x: { show: true },
    },
    // This is the key: set the color for this row's sparkline
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

const SortButton = ({ onClick }: { onClick: () => void }) => {
  return (
    <Button
      size="small"
      onClick={onClick}
      sx={{
        width: "100%",
        py: 0,
        fontSize: "small",
        fontWeight: 300,
        textTransform: "none",
        color: "text.secondary",
        justifyContent: "left",
        "&:hover": {
          color: "text.primary",
          backgroundColor: "transparent",
          fontWeight: 500,
        },
      }}
    >
      <SwapVertIcon />
      Sort
    </Button>
  );
};

interface ContentsTableProps {
  rows: RowDataType[];
  rowsPerPage: number;
  chartColors: string[];
  onClick: (content_id: number) => void;
  // Pass the current page's rows up to the parent
  onItemsToDisplayChange: (items: RowDataType[]) => void;
}

const ContentsTable: React.FC<ContentsTableProps> = ({
  rows,
  rowsPerPage,
  chartColors,
  onClick,
  onItemsToDisplayChange,
}) => {
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<keyof RowDataType>("query_count");
  const [sortOrder, setSortOrder] = useState<"ascending" | "descending">("ascending");
  const [searchTerm, setSearchTerm] = useState("");

  // Basic “percentage increase” logic for the sparkline
  const percentageIncrease = (queryCount: number[]) => {
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

  // Sort logic
  const sortRows = <K extends keyof RowDataType>(
    byParam: K,
    sortDirection: "ascending" | "descending",
  ): RowDataType[] => {
    return [...rows].sort((a, b) => {
      let comparison: number;
      if (byParam === "query_count_timeseries") {
        const diffA = percentageIncrease(a[byParam] as number[]);
        const diffB = percentageIncrease(b[byParam] as number[]);
        comparison = diffA > diffB ? 1 : diffA < diffB ? -1 : 0;
      } else {
        const valA = a[byParam] as number;
        const valB = b[byParam] as number;
        comparison = valA > valB ? 1 : valA < valB ? -1 : 0;
      }
      return sortDirection === "ascending" ? comparison : -comparison;
    });
  };

  const onSort = (column: keyof RowDataType) => {
    if (column === sortColumn) {
      setSortOrder(sortOrder === "ascending" ? "descending" : "ascending");
    } else {
      setSortColumn(column);
      setSortOrder("ascending");
    }
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  // If the user typed in the search box, filter the base `rows`
  const filteredRows = React.useMemo(() => {
    if (!searchTerm) return rows;
    return rows.filter((r) => r.title.toLowerCase().includes(searchTerm.toLowerCase()));
  }, [rows, searchTerm]);

  // Sort them, then slice for pagination
  const displayedRows = React.useMemo(() => {
    const sorted = sortRows(sortColumn, sortOrder);
    const from = (page - 1) * rowsPerPage;
    const to = page * rowsPerPage;
    return sorted.slice(from, to);
  }, [rows, page, sortColumn, sortOrder, rowsPerPage]);

  // Keep track of displayedRows in state so we can pass them up
  useEffect(() => {
    setItemsToDisplay(displayedRows);
  }, [displayedRows]);

  // Each time itemsToDisplay changes, bubble it up
  useEffect(() => {
    onItemsToDisplayChange(itemsToDisplay);
  }, [itemsToDisplay, onItemsToDisplayChange]);

  // The total page count for pagination
  const pageCount = Math.ceil(filteredRows.length / rowsPerPage);

  return (
    <TableContainer component={Paper} sx={{ marginTop: 3 }}>
      <Table>
        <TableHead sx={{ backgroundColor: theme.palette.lightgray.main }}>
          <TableRow>
            <TableCell>Content Title</TableCell>
            <TableCell>Daily Average Sent</TableCell>
            <TableCell>Upvotes</TableCell>
            <TableCell>Downvotes</TableCell>
            <TableCell>Trend</TableCell>
          </TableRow>
          <TableRow>
            <TableCell style={{ paddingTop: 0 }}>
              <TextField
                id="content-search"
                placeholder="Search"
                size="small"
                sx={{ width: "90%", marginTop: 1.5, bgcolor: "white" }}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </TableCell>
            <TableCell>
              <SortButton onClick={() => onSort("query_count")} />
            </TableCell>
            <TableCell>
              <SortButton onClick={() => onSort("positive_votes")} />
            </TableCell>
            <TableCell>
              <SortButton onClick={() => onSort("negative_votes")} />
            </TableCell>
            <TableCell>
              <SortButton onClick={() => onSort("query_count_timeseries")} />
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {itemsToDisplay.map((row, idx) => {
            // color for this row from the chartColors palette
            const color = chartColors[idx] || "#000";

            return (
              <TableRow
                key={row.id}
                onClick={() => onClick(row.id)}
                sx={{
                  "&:hover": {
                    boxShadow: "0px 0px 8px rgba(211, 211, 211, 0.75)",
                    zIndex: 1000,
                    cursor: "pointer",
                  },
                }}
              >
                <TableCell style={{ width: "35%" }}>{row.title}</TableCell>
                <TableCell style={{ width: "15%" }}>{row.query_count}</TableCell>
                <TableCell style={{ width: "10%" }}>{row.positive_votes}</TableCell>
                <TableCell style={{ width: "10%" }}>{row.negative_votes}</TableCell>
                <TableCell style={{ width: "30%" }}>
                  <QueryCountTimeSeries
                    queryCount={row.query_count_timeseries}
                    color={color}
                    isIncreasing={percentageIncrease(row.query_count_timeseries) > 0}
                  />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      <Box
        justifyContent="center"
        alignItems="center"
        sx={{
          display: "flex",
          flexDirection: "row",
          marginTop: 2,
          marginBottom: 4,
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
