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
import { appColors } from "@/utils";
import { useAuth } from "@/utils/auth";
import { getDocIndexingStatusData } from "../api";
import { DocIndexingStatusRow } from "../schemas";
import { IndexingStatusRow } from "./IndexingStatusRow";

interface IndexingStatusModalProps {
  open: boolean;
  onClose: () => void;
}

const getColumnStyles = () => {
  return {
    expandToggle: "48px",
    fileName: "25%",
    status: "15%",
    docsIndexed: "15%",
    createdAt: "15%",
    finishedAt: "15%",
    errorTrace: "15%",
  };
};

export const IndexingStatusModal: React.FC<IndexingStatusModalProps> = ({
  open,
  onClose,
}) => {
  const { token } = useAuth();
  const [indexEntries, setIndexEntries] = useState<DocIndexingStatusRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isClosing, setIsClosing] = useState<boolean>(false);

  const columnWidths = getColumnStyles();

  const mainCellPadding = {
    paddingLeft: 2,
    paddingRight: 2,
    paddingTop: 1.5,
    paddingBottom: 1.5,
  };

  const toggleCellPadding = {
    paddingLeft: 1,
    paddingRight: 1,
    paddingTop: 1,
    paddingBottom: 1,
  };

  useEffect(() => {
    if (open && token) {
      setIsClosing(false);
      setLoading(true);
      setError(null);

      getDocIndexingStatusData(token)
        .then((data) => {
          setIndexEntries(data);
        })
        .catch((err) => {
          console.error("Error fetching indexing status:", err);
          setError("Failed to load indexing status.");
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [open, token]);

  const handleClose = () => {
    setIsClosing(true);
    onClose();
  };

  const handleExited = () => {
    if (isClosing) {
      setError(null);
    }
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
        <Table stickyHeader padding="none">
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
                  width: columnWidths.expandToggle,
                  ...toggleCellPadding,
                }}
              />
              <TableCell
                sx={{
                  fontWeight: "bold",
                  color: appColors.primary,
                  backgroundColor: appColors.white,
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                  width: columnWidths.fileName,
                  ...mainCellPadding,
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
                  width: columnWidths.status,
                  ...mainCellPadding,
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
                  width: columnWidths.docsIndexed,
                  ...mainCellPadding,
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
                  top: 0,
                  zIndex: 1,
                  width: columnWidths.createdAt,
                  ...mainCellPadding,
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
                  top: 0,
                  zIndex: 1,
                  width: columnWidths.finishedAt,
                  ...mainCellPadding,
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
                  top: 0,
                  zIndex: 1,
                  width: columnWidths.errorTrace,
                  ...mainCellPadding,
                }}
              >
                Error Trace
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {indexEntries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No indexing data available
                </TableCell>
              </TableRow>
            ) : (
              indexEntries.map((entry, index) => (
                <IndexingStatusRow
                  key={index}
                  entry={entry}
                  index={index}
                  columnWidths={columnWidths}
                />
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
