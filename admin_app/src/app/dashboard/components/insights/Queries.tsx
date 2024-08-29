import React from "react";
import { Box } from "@mui/material";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import { grey, orange } from "@mui/material/colors";
import Typography from "@mui/material/Typography";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import Button from "@mui/material/Button";
import { QueryData } from "../../types";
import CircularProgress from "@mui/material/CircularProgress";

interface QueriesProps {
  data: QueryData[];
  onRefreshClick: () => void;
  lastRefreshed: string;
  refreshing: boolean;
  aiSummary: string;
}

interface AISummaryProps {
  aiSummary: string;
}
const AISummary: React.FC<AISummaryProps> = ({ aiSummary }) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexGrow: 1,
        flexDirection: "column",
        maxheight: 400,
        border: 1,
        borderColor: "secondary.main",
        borderRadius: 2,
        background: "linear-gradient(to bottom, rgba(176,198,255,0.5), #ffffff)",
        p: 2,
        mb: 3,
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "row", mb: 2 }}>
        <AutoAwesomeIcon sx={{ fontSize: 25, mr: 1, color: "#9eb2e5" }} />
        <Typography
          sx={{
            lineHeight: "24px",
            fontWeight: 600,
            fontColor: "black",
            textAlign: "center",
          }}
        >
          AI Overview
        </Typography>
      </Box>
      <Typography
        sx={{
          lineHeight: "15px",
          fontWeight: 300,
          fontSize: "small",
          fontColor: "black",
          textAlign: "left",
        }}
      >
        {aiSummary}
      </Typography>
    </Box>
  );
};

const Queries: React.FC<QueriesProps> = ({
  data,
  onRefreshClick,
  lastRefreshed,
  refreshing,
  aiSummary,
}) => {
  const formattedLastRefreshed =
    lastRefreshed.length > 0
      ? Intl.DateTimeFormat("en-ZA", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(new Date(lastRefreshed))
      : "Never";

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          mb: 2,
        }}
      >
        <Box sx={{ fontSize: 22, fontWeight: 700 }}>Example Queries</Box>
        <Box sx={{ display: "flex", flexDirection: "row" }}>
          <Box
            sx={{
              display: "flex",
              mr: 2,
              fontSize: "small",
              alignItems: "center",
              color: grey[600],
            }}
          >
            Last run: {formattedLastRefreshed}
          </Box>
          <Button
            disabled={refreshing}
            variant="contained"
            sx={{
              bgcolor: orange[500],
              width: 180,
              "&:hover": {
                bgcolor: orange[700],
              },
            }}
            onClick={onRefreshClick}
          >
            {refreshing ? <CircularProgress size={24} /> : "Re-run Discovery"}
          </Button>
        </Box>
      </Box>
      <AISummary aiSummary={aiSummary} />
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          overflowY: "scroll",
          maxHeight: 200,
        }}
      >
        {data.length > 0 ? (
          <TableContainer sx={{ border: 1, borderColor: grey[300], borderRadius: 1 }}>
            <Table size="small">
              <TableHead>
                <TableRow
                  sx={{ bgcolor: grey[100], position: "sticky", top: 0, zIndex: 1 }}
                >
                  <TableCell sx={{ fontWeight: 800 }}>Timestamp</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>User Question</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell width="20%">
                      {Intl.DateTimeFormat("en-ZA", {
                        dateStyle: "short",
                        timeStyle: "short",
                      }).format(new Date(row.query_datetime_utc))}
                    </TableCell>
                    <TableCell>{row.query_text}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box sx={{ fontSize: "small" }}>
            No queries found. Please re-run discovery
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default Queries;
