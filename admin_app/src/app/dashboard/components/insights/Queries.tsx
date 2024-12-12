import { AutoFixHigh } from "@mui/icons-material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { LoadingButton } from "@mui/lab";
import { Box } from "@mui/material";
import { grey, orange } from "@mui/material/colors";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import React from "react";
import { QueryData } from "../../types";
import theme from "@/theme";

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
        mb: 1,
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
          whiteSpace: "pre-wrap",
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
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header and Refresh Button */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          mb: 1,
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
          <LoadingButton
            variant="contained"
            startIcon={<AutoFixHigh />}
            disabled={refreshing}
            loading={refreshing}
            loadingPosition="start"
            sx={{
              bgcolor: orange[600],
              width: 220,
              "&:hover": {
                bgcolor: orange[800],
              },
            }}
            onClick={onRefreshClick}
          >
            {data.length > 0 ? "Rerun Discovery" : "Run Discovery"}
          </LoadingButton>
        </Box>
      </Box>

      {/* AI Summary */}
      {data.length > 0 && <AISummary aiSummary={aiSummary} />}

      {/* Table Container */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          flexGrow: 1, // Adjust height dynamically to handle the sidebar being toggled
        }}
      >
        {data.length > 0 ? (
          <TableContainer
            sx={{
              flexGrow: 1, // Fills available space as per above
              border: 1,
              borderColor: grey[300],
              borderRadius: 1,
              overflowY: "auto",
            }}
          >
            <Table size="small">
              <TableHead sx={{ backgroundColor: theme.palette.lightgray.main }}>
                <TableRow sx={{ position: "sticky", top: 0, zIndex: 1 }}>
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
          <Typography>
            Click "Run Discovery" to generate insights for this time period.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default Queries;
