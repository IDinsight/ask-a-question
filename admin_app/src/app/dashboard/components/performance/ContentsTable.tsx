import { RowDataType } from "@/app/dashboard/types";
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import SwapVertIcon from "@mui/icons-material/SwapVert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Pagination from "@mui/material/Pagination";
import TextField from "@mui/material/TextField";
import Grid from "@mui/material/Unstable_Grid2";
import { ApexOptions } from "apexcharts";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

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
    <Grid container columns={14} sx={{ mt: 3 }} columnSpacing={{ xs: 0 }}>
      <Grid
        container
        spacing={2}
        md={14}
        columns={14}
        sx={{
          border: 1,
          borderColor: "secondary.main",
          mt: 3,
          fontSize: "small",
          fontWeight: 700,
        }}
      >
        <Grid md={6}>Content Title</Grid>
        <Grid md={2}>Daily Average Sent</Grid>
        <Grid md={2}>Upvotes</Grid>
        <Grid md={2}>Downvotes</Grid>
        <Grid md={2}>Trend</Grid>
      </Grid>
      <Grid
        container
        spacing={2}
        md={14}
        columns={14}
        sx={{
          border: 1,
          borderTop: 0,
          borderColor: "secondary.main",
          mt: 1,
        }}
      >
        <Grid xs={6} sx={{ height: 20 }}>
          <TextField
            id="content-search"
            placeholder="Search"
            size="small"
            sx={{
              width: "90%",
              mt: -0.4,
              maxHeight: 20,
              marginRight: 1,
              bgcolor: "white",
              "& .MuiOutlinedInput-root": {},
            }}
            onChange={(e) => setItemsToDisplay(filterRowsByTitle(e.target.value))}
            margin="none"
            inputProps={{
              style: {
                height: 30,
                backgroundColor: "white",
                padding: "0 14px",
              },
            }}
          />
          <FilterAltOutlinedIcon fontSize="small" sx={{ fontWeight: 300 }} />
        </Grid>
        <Grid xs={2} display="flex" alignItems="center">
          <SortButton onClick={() => onSort("query_count")} />
        </Grid>
        <Grid xs={2} display="flex" alignItems="center">
          <SortButton onClick={() => onSort("positive_votes")} />
        </Grid>
        <Grid xs={2} display="flex" alignItems="center">
          <SortButton onClick={() => onSort("negative_votes")} />
        </Grid>
        <Grid xs={2} display="flex" alignItems="center">
          <SortButton onClick={() => onSort("query_count_timeseries")} />
        </Grid>
      </Grid>

      {itemsToDisplay.map((row) => (
        <Grid
          container
          key={row.id}
          spacing={2}
          md={14}
          columns={14}
          onClick={() => onClick(row.id)}
          sx={{
            border: 1,
            borderTop: 0,
            borderColor: "secondary.main",
            borderBottomColor: "grey.300",
            bgcolor: "white",
            mt: 1,
            fontSize: "small",
            fontWeight: 300,
            "&:hover": {
              boxShadow: "0px 0px 8px rgba(211, 211, 211, 0.75)",
              zIndex: "1000",
              cursor: "pointer",
            },
          }}
        >
          <Grid md={6}>{row.title}</Grid>
          <Grid md={2}>{row.query_count}</Grid>
          <Grid md={2}>{row.positive_votes}</Grid>
          <Grid md={2}>{row.negative_votes}</Grid>
          <Grid md={2}>
            <QueryCountTimeSeries
              queryCount={row.query_count_timeseries}
              isIncreasing={percentageIncrease(row.query_count_timeseries) > 0}
            />
          </Grid>
        </Grid>
      ))}
      <Box
        justifyContent="center"
        justifySelf={"center"}
        alignItems="center"
        sx={{
          display: "flex",
          flexDirection: "row",
          flexGrow: 1,
          mt: 3,
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
    </Grid>
  );
};

export default ContentsTable;
