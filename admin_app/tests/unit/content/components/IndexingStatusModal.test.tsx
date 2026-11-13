import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import type {
  DocIndexingStatusRow,
  DocIndexingTask,
} from "@/components/features/content/types";
import {
  IndexingStatusModal,
  summarizeError,
} from "@/components/features/content/components/IndexingStatusModal";

const task = (overrides: Partial<DocIndexingTask> = {}): DocIndexingTask => ({
  error_trace: "",
  finished_datetime_utc: "2024-03-01T10:05:00Z",
  upload_id: "u1",
  user_id: 1,
  workspace_id: 1,
  parent_file_name: "bundle.zip",
  created_datetime_utc: "2024-03-01T10:00:00Z",
  task_id: "t1",
  doc_name: "doc.pdf",
  task_status: "Success",
  ...overrides,
});

const row = (
  overrides: Partial<DocIndexingStatusRow> = {},
): DocIndexingStatusRow => ({
  fileName: "guide.pdf",
  status: "Done",
  docsIndexed: "1 of 1",
  errorTrace: "",
  created_at: "Mar 1, 2024",
  finished_at: "Mar 1, 2024",
  tasks: [task()],
  ...overrides,
});

const renderModal = (
  props: Partial<React.ComponentProps<typeof IndexingStatusModal>> = {},
) => {
  const onClose = vi.fn();
  render(
    <IndexingStatusModal
      open
      onClose={onClose}
      indexEntries={[]}
      loading={false}
      error={null}
      {...props}
    />,
  );
  return { onClose };
};

describe("IndexingStatusModal", () => {
  it("shows a spinner instead of the table while loading", () => {
    renderModal({ loading: true });
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no uploads", () => {
    renderModal();
    expect(screen.getByText("No PDF uploads yet")).toBeInTheDocument();
  });

  it("shows the error above the table", () => {
    renderModal({ error: "Could not load status" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load status",
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("renders a failed single-task upload with a readable error row", async () => {
    const user = userEvent.setup();
    renderModal({
      indexEntries: [
        row({
          fileName: "broken.pdf",
          status: "Error",
          finished_at: "",
          errorTrace: "parse failed",
          tasks: [task({ task_status: "Failed" })],
        }),
      ],
    });

    const cells = screen.getAllByRole("row")[1].querySelectorAll("td");
    expect(cells[1]).toHaveTextContent("broken.pdf");
    expect(cells[2]).toHaveTextContent("Error");
    expect(screen.getByText("Error")).toHaveClass("text-destructive");
    expect(cells[5]).toHaveTextContent("—");

    // The error shows as a friendly summary; the raw trace is hidden.
    expect(
      screen.getByText("Something went wrong while processing this file."),
    ).toBeInTheDocument();
    expect(screen.queryByText("parse failed")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Show technical details" }),
    );
    expect(screen.getByText("parse failed")).toBeInTheDocument();

    // Single-task rows have no expand toggle.
    expect(
      screen.queryByRole("button", { name: "Show files" }),
    ).not.toBeInTheDocument();
  });

  it("falls back to the task's trace when the upload has none", () => {
    renderModal({
      indexEntries: [
        row({
          status: "Error",
          errorTrace: "",
          tasks: [
            task({ task_status: "Failed", error_trace: "Connection error." }),
          ],
        }),
      ],
    });
    expect(screen.getByText(/Couldn't reach the AI service/)).toBeInTheDocument();
  });

  it.each([
    ["OpenAIException - Connection error.", /Couldn't reach the AI service/],
    ["Request timed out", /took too long/],
    ["RateLimitError 429", /busy right now/],
    ["AuthenticationError: bad API key", /rejected our credentials/],
    ["something odd", /Something went wrong/],
  ])("summarizes %j", (trace, expected) => {
    expect(summarizeError(trace)).toMatch(expected);
  });

  it("handles an upload with no tasks", () => {
    renderModal({ indexEntries: [row({ status: "Ongoing", tasks: [] })] });
    expect(screen.getByText("Ongoing")).toHaveClass("text-amber-700");
  });

  it("expands a multi-file upload via the toggle button and the row", async () => {
    const user = userEvent.setup();
    renderModal({
      indexEntries: [
        row({
          fileName: "bundle.zip",
          docsIndexed: "1 of 3",
          tasks: [
            task({ doc_name: "a.pdf", task_status: "Success" }),
            task({
              doc_name: "b.pdf",
              task_status: "In progress",
              finished_datetime_utc: "",
            }),
            task({
              doc_name: "c.pdf",
              task_status: "Failed",
              error_trace: "bad pdf",
            }),
          ],
        }),
      ],
    });

    expect(screen.queryByText("a.pdf")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show files" }));
    expect(screen.getByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("Success")).toHaveClass("text-green-700");
    expect(screen.getByText("In progress")).toHaveClass("text-amber-700");
    // The failed task gets its own error row and a red badge.
    expect(screen.getByText("Failed")).toHaveClass("text-destructive");
    expect(
      screen.getByText("Something went wrong while processing this file."),
    ).toBeInTheDocument();
    // The in-progress task has no finish time.
    expect(
      within(screen.getByText("b.pdf").closest("tr")!).getByText("—"),
    ).toBeInTheDocument();

    // Clicking the row itself toggles too.
    await user.click(screen.getByText("bundle.zip"));
    expect(screen.queryByText("a.pdf")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show files" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("calls onClose from the Back button", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when dismissed with Escape", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
