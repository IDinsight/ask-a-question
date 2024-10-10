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

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const QueryCountTimeSeries = ({
  queryCount,
  isIncreasing,
}: {
  queryCount: number[];
  isIncreasing: boolean;
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
      zoom: {
        enabled: false,
      },
      sparkline: {
        enabled: true,
      },
      background: "#fff",
    },
    dataLabels: {
      enabled: false,
    },
    stroke: {
      width: 2,
      curve: "smooth",
    },
    tooltip: {
      x: {
        show: false,
      },
    },
    colors: isIncreasing ? ["#4CAF50"] : ["#FF1654"],
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
const ContentsTable = ({
  rows,
  onClick,
  rowsPerPage,
}: {
  rows: RowDataType[];
  onClick: (content_id: number) => void;
  rowsPerPage: number;
}) => {
  const [itemsToDisplay, setItemsToDisplay] = useState<RowDataType[]>([]);
  const [page, setPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<keyof RowDataType>("query_count");
  const [sortOrder, setSortOrder] = useState<"ascending" | "descending">("ascending");

  const percentageIncrease = (queryCount: number[]) => {
    // if the last quarter is greater than the third quarter
    // then the trend is increasing
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

    return (lastQuarterValue - thirdQuarterValue) / thirdQuarterValue;
  };

  const sortRows = <K extends keyof RowDataType>(
    byParam: K,
    sortOrder: "ascending" | "descending",
  ): RowDataType[] => {
    return rows.sort((a: RowDataType, b: RowDataType) => {
      const comparison =
        byParam === "query_count_timeseries"
          ? percentageIncrease(a[byParam] as number[]) >
            percentageIncrease(b[byParam] as number[])
            ? 1
            : percentageIncrease(a[byParam] as number[]) <
              percentageIncrease(b[byParam] as number[])
            ? -1
            : 0
          : a[byParam] > b[byParam]
          ? 1
          : a[byParam] < b[byParam]
          ? -1
          : 0;

      return sortOrder === "ascending" ? comparison : -comparison;
    });
  };

  const onSort = (column: keyof RowDataType) => {
    if (column === sortColumn) {
      setSortOrder(sortOrder === "ascending" ? "descending" : "ascending");
    } else {
      setSortOrder("ascending");
    }
    setSortColumn(column);
    setItemsToDisplay(paginateRows(sortRows(column, sortOrder), page, rowsPerPage));
  };

  const paginateRows = (rows: RowDataType[], page: number, rowsPerPage: number) => {
    return rows.slice((page - 1) * rowsPerPage, page * rowsPerPage);
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    setItemsToDisplay(paginateRows(rows, value, rowsPerPage));
  };

  useEffect(() => {
    setItemsToDisplay(rows.slice(0, rowsPerPage));
  }, [rows]);

  const filterRowsByTitle = (title: string) => {
    return paginateRows(
      rows.filter((row) => row.title.toLowerCase().includes(title.toLowerCase())),
      1,
      rowsPerPage,
    );
  };

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
                sx={{
                  width: "90%",
                  marginTop: 1.5,
                  bgcolor: "white",
                }}
                onChange={(e) => setItemsToDisplay(filterRowsByTitle(e.target.value))}
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
          {itemsToDisplay.map((row) => (
            <TableRow
              key={row.id}
              onClick={() => onClick(row.id)}
              sx={{
                "&:hover": {
                  boxShadow: "0px 0px 8px rgba(211, 211, 211, 0.75)",
                  zIndex: "1000",
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
                  isIncreasing={percentageIncrease(row.query_count_timeseries) > 0}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Box
        justifyContent="center"
        justifySelf={"center"}
        alignItems="center"
        sx={{
          display: "flex",
          flexDirection: "row",
          flexGrow: 1,
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
          count={Math.ceil(rows.length / rowsPerPage)}
        />
      </Box>
    </TableContainer>
  );
};

export default ContentsTable;
