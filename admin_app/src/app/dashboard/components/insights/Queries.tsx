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
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";

interface QueryData {
  query: string;
  datetime_utc: string;
}

interface QueriesProps {
  data: QueryData[];
}

const AISummary: React.FC = () => {
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
        Not available
      </Typography>
    </Box>
  );
};

const Queries: React.FC<QueriesProps> = ({ data }) => {
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
            Last run: 2021-10-01 12:00:00
          </Box>
          <Button
            variant="contained"
            sx={{
              bgcolor: orange[500],
              "&:hover": {
                bgcolor: orange[700],
              },
            }}
          >
            Re-run Discovery
          </Button>
        </Box>
      </Box>
      <AISummary />
      {data.length > 0 ? (
        <TableContainer sx={{ border: 1, borderColor: grey[300], borderRadius: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: grey[100] }}>
                <TableCell sx={{ fontWeight: 800 }}>Timestamp</TableCell>
                <TableCell sx={{ fontWeight: 800 }}>User Question</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row, index) => (
                <TableRow key={index}>
                  <TableCell width="20%">{row.datetime_utc}</TableCell>
                  <TableCell>{row.query}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Box sx={{ fontSize: 18 }}>No queries found</Box>
      )}
    </Box>
  );
};

export default Queries;
