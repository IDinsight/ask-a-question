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
import { appColors } from "@/utils";
import { useAuth } from "@/utils/auth";
import { DocIndexingStatusRow, formatDate, getDocIndexingStatusData } from "../api";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";

interface IndexingStatusModalProps {
  open: boolean;
  onClose: () => void;
}

interface RowProps {
  entry: DocIndexingStatusRow;
  index: number;
  columnWidths: { [key: string]: string };
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

const wrapStyle = {
  whiteSpace: "normal" as const,
  wordBreak: "break-word" as const,
  overflow: "hidden",
  textOverflow: "ellipsis",
};
const handleEmptyDate = (dateString: string) => {
  if (!dateString) return "—";
  return dateString;
};

const Row: React.FC<RowProps> = ({ entry, index, columnWidths }) => {
  const [open, setOpen] = useState(false);

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

  const mainCellPadding = {
    paddingLeft: 2,
    paddingRight: 2,
    paddingTop: 1.5,
    paddingBottom: 1.5,
  };

  const nestedCellPadding = {
    paddingLeft: 3.5,
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

  const nestedRowStyle = {
    backgroundColor: "#fafafa",
  };

  return (
    <>
      <TableRow
        sx={{
          "& > *": { borderBottom: "unset" },
          cursor: hasMultipleTasks ? "pointer" : "default",
          "&:hover": hasMultipleTasks ? { backgroundColor: "#f5f5f5" } : {},
        }}
        onClick={hasMultipleTasks ? () => setOpen(!open) : undefined}
      >
        <TableCell sx={{ width: columnWidths.expandToggle, ...toggleCellPadding }}>
          {hasMultipleTasks && (
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                setOpen(!open);
              }}
            >
              {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
            </IconButton>
          )}
        </TableCell>
        <TableCell
          sx={{
            ...wrapStyle,
            ...mainCellPadding,
            fontWeight: "bold",
            width: columnWidths.fileName,
          }}
        >
          {entry.fileName}
        </TableCell>
        <TableCell
          sx={{
            ...mainCellPadding,
            fontWeight: "bold",
            width: columnWidths.status,
            color:
              entry.status === "Done"
                ? "green"
                : entry.status === "Ongoing"
                ? "darkorange"
                : "red",
          }}
        >
          {entry.status}
        </TableCell>
        <TableCell sx={{ ...mainCellPadding, width: columnWidths.docsIndexed }}>
          {entry.docsIndexed}
        </TableCell>
        <TableCell sx={{ ...mainCellPadding, width: columnWidths.createdAt }}>
          {handleEmptyDate(entry.created_at)}
        </TableCell>
        <TableCell sx={{ ...mainCellPadding, width: columnWidths.finishedAt }}>
          {handleEmptyDate(entry.finished_at)}
        </TableCell>
        <TableCell
          sx={{
            ...wrapStyle,
            ...mainCellPadding,
            width: columnWidths.errorTrace,
            color:
              (hasMultipleTasks ? entry.status : entry.tasks[0]?.task_status) ===
              "Failed"
                ? "error.main"
                : "inherit",
          }}
        >
          {entry.errorTrace}
        </TableCell>
      </TableRow>
      {hasMultipleTasks && (
        <TableRow>
          <TableCell style={{ padding: 0 }} colSpan={7}>
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box sx={{ padding: 0 }}>
                <Table size="small" padding="none">
                  <TableBody>
                    {entry.tasks.map((task, taskIndex) => (
                      <TableRow key={taskIndex} sx={nestedRowStyle}>
                        <TableCell
                          sx={{
                            width: columnWidths.expandToggle,
                            ...toggleCellPadding,
                          }}
                        />
                        <TableCell
                          sx={{
                            ...wrapStyle,
                            ...nestedCellPadding,
                            width: columnWidths.fileName,
                          }}
                        >
                          {task.doc_name}
                        </TableCell>
                        <TableCell
                          sx={{
                            ...nestedCellPadding,
                            width: columnWidths.status,
                            color: getStatusColor(task.task_status),
                          }}
                        >
                          {task.task_status}
                        </TableCell>
                        <TableCell
                          sx={{
                            ...nestedCellPadding,
                            width: columnWidths.docsIndexed,
                          }}
                        />
                        <TableCell
                          sx={{
                            ...nestedCellPadding,
                            width: columnWidths.createdAt,
                          }}
                        >
                          {handleEmptyDate(formatDate(task.created_datetime_utc))}
                        </TableCell>
                        <TableCell
                          sx={{
                            ...nestedCellPadding,
                            width: columnWidths.finishedAt,
                          }}
                        >
                          {handleEmptyDate(formatDate(task.finished_datetime_utc))}
                        </TableCell>
                        <TableCell
                          sx={{
                            ...wrapStyle,
                            ...nestedCellPadding,
                            width: columnWidths.errorTrace,
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
          setIndexEntries(data || []);
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
                <Row
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
