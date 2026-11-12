"use client";

import React, { useState } from "react";
import {
  IconAlertCircle,
  IconChevronDown,
  IconFileOff,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "cn";
import { formatDate } from "../queries";
import type { DocIndexingStatusRow } from "../types";

// Column headers and widths, shared by the header and every row so the
// nested task rows line up with their parent.
const COLUMNS = [
  { key: "expandToggle", label: "", className: "w-10" },
  { key: "fileName", label: "File name", className: "w-[25%]" },
  { key: "status", label: "Status", className: "w-[15%]" },
  { key: "docsIndexed", label: "Documents processed", className: "w-[15%]" },
  { key: "createdAt", label: "Created at", className: "w-[15%]" },
  { key: "finishedAt", label: "Finished at", className: "w-[15%]" },
  { key: "errorTrace", label: "Error trace", className: "w-[15%]" },
] as const;

const WRAP = "whitespace-normal wrap-break-word";

const handleEmptyDate = (dateString: string) => {
  if (!dateString) return "—";
  return dateString;
};

/** Text colour for a status. Upload-level and task-level statuses differ. */
const statusClassName = (status: string) => {
  switch (status) {
    case "Done":
    case "Success":
      return "text-green-700 dark:text-green-500";
    case "Ongoing":
    case "In progress":
      return "text-amber-700 dark:text-amber-500";
    case "Failed":
      return "text-destructive";
    default:
      return "";
  }
};

const Row: React.FC<{ entry: DocIndexingStatusRow }> = ({ entry }) => {
  const [open, setOpen] = useState(false);
  const hasMultipleTasks = entry.tasks.length > 1;
  // For a single-task upload the row's error colour follows that task.
  const effectiveStatus = hasMultipleTasks
    ? entry.status
    : entry.tasks[0]?.task_status;

  return (
    <>
      <TableRow
        className={cn(hasMultipleTasks && "cursor-pointer")}
        onClick={hasMultipleTasks ? () => setOpen(!open) : undefined}
      >
        <TableCell className="px-2">
          {hasMultipleTasks && (
            <Button
              variant="ghost"
              size="icon-xs"
              aria-expanded={open}
              aria-label={open ? "Hide files" : "Show files"}
              onClick={(e) => {
                e.stopPropagation();
                setOpen(!open);
              }}
            >
              <IconChevronDown
                className={cn("transition-transform", open && "rotate-180")}
              />
            </Button>
          )}
        </TableCell>
        <TableCell className={cn(WRAP, "font-medium")}>
          {entry.fileName}
        </TableCell>
        <TableCell className={cn("font-medium", statusClassName(entry.status))}>
          {entry.status}
        </TableCell>
        <TableCell>{entry.docsIndexed}</TableCell>
        <TableCell>{handleEmptyDate(entry.created_at)}</TableCell>
        <TableCell>{handleEmptyDate(entry.finished_at)}</TableCell>
        <TableCell
          className={cn(
            WRAP,
            effectiveStatus === "Failed" && "text-destructive",
          )}
        >
          {entry.errorTrace}
        </TableCell>
      </TableRow>
      {/* Per-file rows of a ZIP upload, shown when expanded */}
      {hasMultipleTasks &&
        open &&
        entry.tasks.map((task, taskIndex) => (
          <TableRow key={taskIndex} className="bg-muted/40 hover:bg-muted/60">
            <TableCell />
            <TableCell className={cn(WRAP, "pl-6")}>{task.doc_name}</TableCell>
            <TableCell className={statusClassName(task.task_status)}>
              {task.task_status}
            </TableCell>
            <TableCell />
            <TableCell>
              {handleEmptyDate(formatDate(task.created_datetime_utc))}
            </TableCell>
            <TableCell>
              {handleEmptyDate(formatDate(task.finished_datetime_utc))}
            </TableCell>
            <TableCell
              className={cn(
                WRAP,
                task.task_status === "Failed" && "text-destructive",
              )}
            >
              {task.error_trace}
            </TableCell>
          </TableRow>
        ))}
    </>
  );
};

interface IndexingStatusModalProps {
  open: boolean;
  onClose: () => void;
  indexEntries: DocIndexingStatusRow[];
  loading: boolean;
  error: string | null;
}

/** PDF upload history. ContentWrapper fetches it while the dialog is open. */
export const IndexingStatusModal: React.FC<IndexingStatusModalProps> = ({
  open,
  onClose,
  indexEntries,
  loading,
  error,
}) => {
  const handleClose = onClose;

  const renderTable = () => (
    // The inner table container is made non-scrolling so the sticky header
    // sticks to this outer, height-limited box.
    <div className="h-[40vh] overflow-auto border [&>[data-slot=table-container]]:overflow-visible">
      <Table className="table-fixed text-sm">
        <TableHeader className="sticky top-0 z-10 bg-popover">
          <TableRow className="hover:bg-transparent">
            {COLUMNS.map((column) => (
              <TableHead
                key={column.key}
                className={cn(column.className, "whitespace-normal")}
              >
                {column.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {indexEntries.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={COLUMNS.length}>
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <IconFileOff />
                    </EmptyMedia>
                    <EmptyTitle>No PDF uploads yet</EmptyTitle>
                    <EmptyDescription>
                      Files you upload with &quot;Generate cards from PDF&quot;
                      will show their processing status here.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              </TableCell>
            </TableRow>
          ) : (
            indexEntries.map((entry, index) => (
              <Row key={index} entry={entry} />
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && handleClose()}>
      <DialogContent className="gap-5 p-6 text-sm sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            PDF processing status
          </DialogTitle>
          <DialogDescription className="text-sm">
            Processing status of ongoing and previous uploads.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Spinner className="size-6" />
          </div>
        ) : (
          <>
            {error && (
              <Alert variant="destructive">
                <IconAlertCircle />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {renderTable()}
          </>
        )}

        <DialogFooter>
          <Button onClick={handleClose}>Back</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
