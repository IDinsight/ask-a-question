import * as React from "react";
import { styled } from "@mui/material/styles";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell, { tableCellClasses } from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import { TopContentData } from "@/app/dashboard/types";
import { format } from "date-fns";
import { Box, Typography } from "@mui/material";
import { appColors } from "@/utils/index";
import dynamic from "next/dynamic";

const ReactApexcharts = dynamic(() => import("react-apexcharts"), {
  ssr: false,
});

const UpvoteDownvoteBarChart = ({
  positiveVotes,
  negativeVotes,
}: {
  positiveVotes: number;
  negativeVotes: number;
}) => {
  const positiveVotesPercentage = Math.round(
    (positiveVotes / (positiveVotes + negativeVotes)) * 100,
  );
  const negativeVotesPercentage = Math.round(
    (negativeVotes / (positiveVotes + negativeVotes)) * 100,
  );

  return (
    <ReactApexcharts
      options={{
        chart: {
          type: "bar",
          stacked: true,
          toolbar: { show: false },
          parentHeightOffset: 0,
          sparkline: {
            enabled: true,
          },
        },
        plotOptions: {
          bar: { horizontal: true, barHeight: "100%", columnWidth: "100%" },
        },
        xaxis: {
          labels: { show: false },
          max: 100,
          axisBorder: { show: false },
          axisTicks: { show: false },
          position: "bottom",
          floating: true,
        },
        yaxis: { show: false, labels: { show: false } },
        colors: [appColors.dashboardUpvote, appColors.dashboardDownvote],
        legend: { show: false },
        dataLabels: {
          enabled: true,
          formatter: (val, _) => {
            return `${val}%`;
          },
        },
        tooltip: { x: { show: false } },
        grid: {
          show: false,
          padding: {
            top: 0,
            right: 0,
            bottom: 0,
            left: 0,
          },
        },
      }}
      series={[
        { name: "Upvotes", data: [positiveVotesPercentage] },
        { name: "Downvotes", data: [negativeVotesPercentage] },
      ]}
      type="bar"
      height={30}
      width="100%"
    />
  );
};

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.lightgray.main,
    color: theme.palette.lightgray.dark,
    fontWeight: "bold",
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14,
  },
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  "&:nth-of-type(odd)": {
    backgroundColor: theme.palette.action.hover,
  },
  // hide last border
  "&:last-child td, &:last-child th": {
    border: 0,
  },
}));

const isDeleted = (title: string) => title.startsWith("[DELETED]");

const TopContentTable = ({ rows }: { rows: TopContentData[] }) => {
  return (
    <Box sx={{ width: "100%" }}>
      <Typography
        variant="h6"
        gutterBottom
        component="div"
        sx={{ p: 3, py: 2, fontWeight: 500 }}
      >
        Most Sent Content
      </Typography>
      <Box sx={{ mx: 3 }}>
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 700 }} size="small" aria-label="top-content-table">
            <TableHead>
              <TableRow>
                <StyledTableCell>Content</StyledTableCell>
                <StyledTableCell align="right">Last Updated</StyledTableCell>
                <StyledTableCell align="right" style={{ whiteSpace: "nowrap" }}>
                  Total Sent
                </StyledTableCell>
                <StyledTableCell align="right">
                  All-time upvotes vs. downvotes
                </StyledTableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row, i) => (
                <StyledTableRow
                  key={i}
                  sx={{ "&:last-child td, &:last-child th": { border: 0 } }}
                >
                  <StyledTableCell component="th" scope="row">
                    {isDeleted(row.title) ? (
                      <span
                        style={{
                          color: appColors.lightGrey,
                          fontWeight: "bold",
                        }}
                      >
                        {row.title}
                      </span>
                    ) : (
                      row.title
                    )}
                  </StyledTableCell>
                  <StyledTableCell align="right">
                    {format(new Date(row.last_updated), "yyyy-MM-dd HH:mm")}
                  </StyledTableCell>
                  <StyledTableCell align="right">{row.query_count}</StyledTableCell>
                  <StyledTableCell align="right" sx={{ width: 500 }}>
                    <UpvoteDownvoteBarChart
                      positiveVotes={row.positive_votes}
                      negativeVotes={row.negative_votes}
                    />
                  </StyledTableCell>
                </StyledTableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Box>
  );
};

export default TopContentTable;
