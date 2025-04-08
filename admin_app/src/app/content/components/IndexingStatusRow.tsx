import React, { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
  IconButton,
  Collapse,
  Box,
} from "@mui/material";

import { formatDate } from "../api";

import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import { DocIndexingStatusRow } from "../schemas";

interface RowProps {
  entry: DocIndexingStatusRow;
  index: number;
  columnWidths: { [key: string]: string };
}
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

export const IndexingStatusRow: React.FC<RowProps> = ({
  entry,
  index,
  columnWidths,
}) => {
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
