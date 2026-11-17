"use client";

import React, { useState } from "react";
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconChevronDown,
  IconFileOff,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
// nested task rows line up with their parent. File name takes whatever width
// is left; dates get a fixed width wide enough to stay on one line.
// Errors are not a column: they render as a full-width row under the file.
const COLUMNS = [
  { key: "expandToggle", label: "", className: "w-10" },
  { key: "fileName", label: "File name", className: "" },
  { key: "status", label: "Status", className: "w-28" },
  { key: "docsIndexed", label: "Documents", className: "w-24" },
  { key: "createdAt", label: "Created at", className: "w-48" },
  { key: "finishedAt", label: "Finished at", className: "w-48" },
] as const;

const WRAP = "whitespace-normal wrap-break-word";
const DATE = "whitespace-nowrap text-muted-foreground tabular-nums";

const handleEmptyDate = (dateString: string) => {
  if (!dateString) return "—";
  return dateString;
};

type StatusTone = "success" | "pending" | "error" | "neutral";

/** Upload-level ("Done"/"Error") and task-level ("Success"/"Failed") statuses
 *  use different words; map both onto one tone. */
const statusTone = (status: string): StatusTone => {
  switch (status) {
    case "Done":
    case "Success":
      return "success";
    case "Ongoing":
    case "In progress":
      return "pending";
    case "Error":
    case "Failed":
      return "error";
    default:
      return "neutral";
  }
};

const TONE_CLASS: Record<StatusTone, string> = {
  success:
    "bg-green-600/10 text-green-700 dark:bg-green-500/15 dark:text-green-500",
  pending:
    "bg-amber-600/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-500",
  error: "bg-destructive/10 text-destructive dark:bg-destructive/20",
  neutral: "bg-muted text-muted-foreground",
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <Badge className={TONE_CLASS[statusTone(status)]}>{status}</Badge>
);

/**
 * Turns a raw backend error trace into one plain sentence for the admin.
 * Assumption: matching on substrings of LiteLLM / OpenAI error text, which
 * isn't a stable contract. Anything unrecognised falls back to a generic
 * message, and the raw trace is always one click away.
 */
export const summarizeError = (trace: string): string => {
  if (/connection error|connect call failed|cannot connect/i.test(trace)) {
    return "Couldn't reach the AI service. Try again in a few minutes; if it keeps failing, contact your administrator.";
  }
  if (/timed? ?out/i.test(trace)) {
    return "The AI service took too long to respond. Try uploading the file again.";
  }
  if (/rate ?limit|\b429\b/i.test(trace)) {
    return "The AI service is busy right now. Wait a minute, then upload the file again.";
  }
  if (/authentication|api key|\b401\b/i.test(trace)) {
    return "The AI service rejected our credentials. Contact your administrator.";
  }
  return "Something went wrong while processing this file.";
};

/** Full-width row under a failed file: a readable summary, with the raw
 *  trace behind a toggle for whoever needs to debug it. */
const ErrorRow: React.FC<{ trace: string; nested?: boolean }> = ({
  trace,
  nested = false,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <TableRow className="hover:bg-transparent">
      <TableCell />
      <TableCell
        colSpan={COLUMNS.length - 1}
        className={cn("pt-0 pb-3", nested && "pl-6")}
      >
        <div className="flex flex-col gap-2 border-l-2 border-destructive bg-destructive/5 px-3 py-2">
          <div className="flex items-start gap-2 text-destructive">
            <IconAlertTriangle className="mt-0.5 size-4 shrink-0" />
            <p className={cn(WRAP, "text-sm")}>{summarizeError(trace)}</p>
          </div>
          <Button
            variant="link"
            size="xs"
            className="h-auto w-fit p-0 text-muted-foreground"
            aria-expanded={showDetails}
            onClick={(e) => {
              // Don't toggle the parent ZIP row.
              e.stopPropagation();
              setShowDetails(!showDetails);
            }}
          >
            {showDetails ? "Hide technical details" : "Show technical details"}
          </Button>
          {showDetails && (
            <pre className="max-h-40 overflow-auto bg-muted p-2 font-mono text-xs whitespace-pre-wrap break-all text-muted-foreground">
              {trace}
            </pre>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
};

const Row: React.FC<{ entry: DocIndexingStatusRow }> = ({ entry }) => {
  const [open, setOpen] = useState(false);
  const hasMultipleTasks = entry.tasks.length > 1;
  // For a single-task upload the error comes from that task when the
  // upload-level trace is empty.
  const errorTrace =
    entry.errorTrace || (!hasMultipleTasks && entry.tasks[0]?.error_trace) || "";

  return (
    <>
      <TableRow
        className={cn(
          hasMultipleTasks && "cursor-pointer",
          errorTrace && "border-b-0",
        )}
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
        <TableCell>
          <StatusBadge status={entry.status} />
        </TableCell>
        <TableCell className="tabular-nums">{entry.docsIndexed}</TableCell>
        <TableCell className={DATE}>
          {handleEmptyDate(entry.created_at)}
        </TableCell>
        <TableCell className={DATE}>
          {handleEmptyDate(entry.finished_at)}
        </TableCell>
      </TableRow>
      {errorTrace && <ErrorRow trace={errorTrace} />}

      {/* Per-file rows of a ZIP upload, shown when expanded */}
      {hasMultipleTasks &&
        open &&
        entry.tasks.map((task, taskIndex) => (
          <React.Fragment key={taskIndex}>
            <TableRow
              className={cn(
                "bg-muted/40 hover:bg-muted/60",
                task.error_trace && "border-b-0",
              )}
            >
              <TableCell />
              <TableCell className={cn(WRAP, "pl-6")}>{task.doc_name}</TableCell>
              <TableCell>
                <StatusBadge status={task.task_status} />
              </TableCell>
              <TableCell />
              <TableCell className={DATE}>
                {handleEmptyDate(formatDate(task.created_datetime_utc))}
              </TableCell>
              <TableCell className={DATE}>
                {handleEmptyDate(formatDate(task.finished_datetime_utc))}
              </TableCell>
            </TableRow>
            {task.error_trace && <ErrorRow trace={task.error_trace} nested />}
          </React.Fragment>
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
    <div className="max-h-[50vh] min-h-[200px] overflow-auto border [&>[data-slot=table-container]]:overflow-visible">
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
