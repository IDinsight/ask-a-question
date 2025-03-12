import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  DialogActions,
} from "@mui/material";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";

interface IndexRow {
  fileName: string;
  status: "Ongoing" | "Done" | "Error";
  docsIndexed: string;
  errorTrace: string;
  created_at: string;
  finished_at: string;
}

interface IndexingStatusModalProps {
  open: boolean;
  onClose: () => void;
}

// Dummy since no API
const dummyData = (): IndexRow[] => {
  return [
    {
      fileName: "sales_report_2025.pdf",
      status: "Done",
      docsIndexed: "42",
      errorTrace: "",
      created_at: "2025-03-10 09:15:23",
      finished_at: "2025-03-10 09:17:45",
    },
    {
      fileName: "product_catalog.xlsx",
      status: "Ongoing",
      docsIndexed: "18",
      errorTrace: "",
      created_at: "2025-03-12 11:32:08",
      finished_at: "",
    },
    {
      fileName: "customer_feedback.csv",
      status: "Error",
      docsIndexed: "0",
      errorTrace: "Invalid file format",
      created_at: "2025-03-11 14:22:56",
      finished_at: "2025-03-11 14:23:10",
    },
    {
      fileName: "financial_summary_Q1.docx",
      status: "Done",
      docsIndexed: "15",
      errorTrace: "",
      created_at: "2025-03-09 16:45:12",
      finished_at: "2025-03-09 16:48:37",
    },
    {
      fileName: "financial_summary_Q1.docx",
      status: "Done",
      docsIndexed: "15",
      errorTrace: "",
      created_at: "2025-03-09 16:45:12",
      finished_at: "2025-03-09 16:48:37",
    },
    {
      fileName: "financial_summary_Q1.docx",
      status: "Done",
      docsIndexed: "15",
      errorTrace: "",
      created_at: "2025-03-09 16:45:12",
      finished_at: "2025-03-09 16:48:37",
    },
    {
      fileName: "financial_summary_Q1.docx",
      status: "Done",
      docsIndexed: "15",
      errorTrace: "",
      created_at: "2025-03-09 16:45:12",
      finished_at: "2025-03-09 16:48:37",
    },
  ];
};

export const IndexingStatusModal: React.FC<IndexingStatusModalProps> = ({
  open,
  onClose,
}) => {
  const { token } = useAuth();
  const [indexEntries, setIndexEntries] = useState<IndexRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isClosing, setIsClosing] = useState<boolean>(false);

  useEffect(() => {
    if (open) {
      setIsClosing(false);
      fetchIndexingStatus();
    }
  }, [open]);

  const fetchIndexingStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("random/endpoint", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }

      const data = await response.json();
      setIndexEntries(data);
    } catch (err) {
      console.error("Error fetching indexing status:", err);
      setError("Failed to load indexing status. Showing demo data instead.");
      setIndexEntries(dummyData());
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setIsClosing(true);
    onClose();
  };

  const handleExited = () => {
    if (isClosing) {
      setError(null);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "—";
    return dateString;
  };

  const renderTable = () => {
    return (
      <TableContainer
        component={Paper}
        sx={{
          boxShadow: "none",
          border: `1px solid ${appColors.outline}`,
          borderRadius: 1,
          height: "40vh",
          maxHeight: "40vh",
          overflow: "auto",
          position: "relative",
        }}
      >
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                }}
              >
                File Name
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                }}
              >
                Status
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                }}
              >
                Docs Indexed
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                }}
              >
                Created At
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                }}
              >
                Finished At
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                }}
              >
                Error Trace
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {indexEntries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No indexing data available
                </TableCell>
              </TableRow>
            ) : (
              indexEntries.map((entry, index) => (
                <TableRow key={index}>
                  <TableCell>{entry.fileName}</TableCell>
                  <TableCell>{entry.status}</TableCell>
                  <TableCell>{entry.docsIndexed}</TableCell>
                  <TableCell>{formatDate(entry.created_at)}</TableCell>
                  <TableCell>{formatDate(entry.finished_at)}</TableCell>
                  <TableCell
                    sx={{
                      color: entry.status === "Error" ? "error.main" : "inherit",
                    }}
                  >
                    {entry.errorTrace}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="indexing-status-dialog-title"
      aria-describedby="indexing-status-dialog-description"
      TransitionProps={{
        onExited: handleExited,
      }}
    >
      <DialogTitle id="indexing-status-dialog-title">Indexing Status</DialogTitle>
      <DialogContent>
        <Typography
          variant="body1"
          color="text.secondary"
          id="indexing-status-dialog-description"
        >
          Indexing status of ongoing and previous uploads.
        </Typography>

        <Layout.Spacer multiplier={2} />

        {loading ? (
          <Layout.FlexBox
            justifyContent="center"
            alignItems="center"
            style={{ minHeight: "200px" }}
          >
            <CircularProgress size={24} />
          </Layout.FlexBox>
        ) : error ? (
          <>
            <Layout.Spacer multiplier={1} />
            <Alert variant="outlined" severity="error">
              {error}
            </Alert>
            <Layout.Spacer multiplier={2} />
            {/* Display table with dummy data even when there's an error */}
            {renderTable()}
          </>
        ) : (
          renderTable()
        )}
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button variant="contained" onClick={handleClose}>
          Back
        </Button>
      </DialogActions>
    </Dialog>
  );
};
