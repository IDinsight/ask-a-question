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
  IconButton,
  Collapse,
  Box,
} from "@mui/material";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
import {
  DocIndexingStatusRow,
  DocIndexingTask,
  getDocIndexingStatusData,
} from "../api";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";

interface IndexingStatusModalProps {
  open: boolean;
  onClose: () => void;
}

interface RowProps {
  entry: DocIndexingStatusRow;
  index: number;
}

const Row: React.FC<RowProps> = ({ entry, index }) => {
  const [open, setOpen] = useState(false);

  const formatDate = (dateString: string) => {
    if (!dateString) return "—";
    return dateString;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Success":
        return "green";
      case "In progress":
        return "darkorange";
      case "Failed":
        return "red";
      default:
        return "inherit";
    }
  };

  const hasMultipleTasks = entry.tasks.length > 1;

  return (
    <>
      <TableRow sx={{ "& > *": { borderBottom: "unset" } }}>
        <TableCell>
          {hasMultipleTasks && (
            <IconButton
              size="small"
              onClick={() => setOpen(!open)}
              sx={{ marginRight: 1 }}
            >
              {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
            </IconButton>
          )}
        </TableCell>
        <TableCell sx={{ fontWeight: "bold" }}>
          {hasMultipleTasks
            ? entry.fileName
            : entry.tasks[0]?.doc_name || entry.fileName}
        </TableCell>
        <TableCell
          sx={{
            fontWeight: "bold",
            color: getStatusColor(
              hasMultipleTasks
                ? entry.status
                : entry.tasks[0]?.task_status || entry.status,
            ),
          }}
        >
          {hasMultipleTasks
            ? entry.status
            : entry.tasks[0]?.task_status || entry.status}
        </TableCell>
        <TableCell>{entry.docsIndexed}</TableCell>
        <TableCell>
          {hasMultipleTasks
            ? formatDate(entry.created_at)
            : formatDate(entry.tasks[0]?.created_datetime_utc || entry.created_at)}
        </TableCell>
        <TableCell>
          {hasMultipleTasks
            ? formatDate(entry.finished_at)
            : formatDate(entry.tasks[0]?.finished_datetime_utc || entry.finished_at)}
        </TableCell>
        <TableCell
          sx={{
            color:
              (hasMultipleTasks ? entry.status : entry.tasks[0]?.task_status) ===
              "Failed"
                ? "error.main"
                : "inherit",
          }}
        >
          {hasMultipleTasks
            ? entry.errorTrace
            : entry.tasks[0]?.error_trace || entry.errorTrace}
        </TableCell>
      </TableRow>
      {hasMultipleTasks && (
        <TableRow>
          <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box sx={{ margin: 1 }}>
                <Typography variant="h6" gutterBottom component="div">
                  Tasks
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Document Name</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Created At</TableCell>
                      <TableCell>Finished At</TableCell>
                      <TableCell>Error Trace</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {entry.tasks.map((task, taskIndex) => (
                      <TableRow key={taskIndex}>
                        <TableCell>{task.doc_name}</TableCell>
                        <TableCell sx={{ color: getStatusColor(task.task_status) }}>
                          {task.task_status}
                        </TableCell>
                        <TableCell>{formatDate(task.created_datetime_utc)}</TableCell>
                        <TableCell>{formatDate(task.finished_datetime_utc)}</TableCell>
                        <TableCell
                          sx={{
                            color:
                              task.task_status === "Failed" ? "error.main" : "inherit",
                          }}
                        >
                          {task.error_trace}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
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
          console.log("Indexing status data:");
          setError("Failed to load indexing status.");
        })
        .finally(() => {
          console.log("Indexing status data:", indexEntries);
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
              />
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
                <TableCell colSpan={7} align="center">
                  No indexing data available
                </TableCell>
              </TableRow>
            ) : (
              indexEntries.map((entry, index) => (
                <Row key={index} entry={entry} index={index} />
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
