import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ImportFromCSVModal } from "@/components/features/content/components/ImportFromCSVModal";

const csv = new File(["title,text\nA,B"], "contents.csv", { type: "text/csv" });

// The component waits 500ms before uploading (to show a spinner) and
// auto-closes 1s after success, so drive time with fake timers.
const setup = (uploadCsv = vi.fn().mockResolvedValue({ status: 200 })) => {
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const onClose = vi.fn();
  render(<ImportFromCSVModal open onClose={onClose} uploadCsv={uploadCsv} />);
  // The file input is hidden behind the "Attach file" button.
  const fileInput = document.querySelector<HTMLInputElement>("#choose-file")!;
  const importButton = () => screen.getByRole("button", { name: /import/i });
  return { user, onClose, uploadCsv, fileInput, importButton };
};

const flushUpload = () => act(() => vi.advanceTimersByTimeAsync(500));

describe("ImportFromCSVModal", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("opens the file picker from Attach file", async () => {
    const { user, fileInput } = setup();
    const click = vi.spyOn(fileInput, "click");
    await user.click(screen.getByRole("button", { name: "Attach file" }));
    expect(click).toHaveBeenCalled();
  });

  it("disables import until a file is chosen, then shows its name", async () => {
    const { user, fileInput, importButton } = setup();
    expect(screen.getByText("No file selected")).toBeInTheDocument();
    expect(importButton()).toBeDisabled();

    await user.upload(fileInput, csv);

    expect(screen.getByText("contents.csv")).toBeInTheDocument();
    expect(importButton()).toBeEnabled();
  });

  it("treats a change with no file list as no file", () => {
    const { fileInput, importButton } = setup();
    fireEvent.change(fileInput, { target: { files: null } });
    expect(importButton()).toBeDisabled();
  });

  it("uploads, shows success, then closes itself", async () => {
    const { user, fileInput, importButton, uploadCsv, onClose } = setup();
    await user.upload(fileInput, csv);
    await user.click(importButton());

    // Spinner shows during the artificial delay.
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    await flushUpload();

    expect(uploadCsv).toHaveBeenCalledWith(csv);
    expect(screen.getByText("File uploaded successfully!")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imported" })).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(1000));
    expect(onClose).toHaveBeenCalled();
  });

  it("lists each validation error the backend returns", async () => {
    const { user, fileInput, importButton } = setup(
      vi.fn().mockResolvedValue({
        status: 400,
        detail: {
          errors: [
            { type: "dup", description: "Duplicate title: A" },
            { type: "len", description: "Text too long in row 3" },
          ],
        },
      }),
    );
    await user.upload(fileInput, csv);
    await user.click(importButton());
    await flushUpload();

    const alerts = screen.getAllByRole("alert");
    expect(alerts.map((a) => a.textContent)).toEqual([
      "Duplicate title: A",
      "Text too long in row 3",
    ]);
    // The file is cleared so the user has to re-attach after fixing it.
    expect(screen.getByText("No file selected")).toBeInTheDocument();
  });

  it("falls back to a generic message when the error has no details", async () => {
    const { user, fileInput, importButton } = setup(
      vi.fn().mockResolvedValue({ status: 500, detail: {} }),
    );
    await user.upload(fileInput, csv);
    await user.click(importButton());
    await flushUpload();
    expect(screen.getByRole("alert")).toHaveTextContent("An unknown error occurred");
  });

  it("shows a retry message when the upload itself fails", async () => {
    const { user, fileInput, importButton } = setup(
      vi.fn().mockRejectedValue(new Error("offline")),
    );
    await user.upload(fileInput, csv);
    await user.click(importButton());
    await flushUpload();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "An unexpected error occurred. Please try again later.",
    );
  });

  it("resets and calls onClose on Cancel", async () => {
    const { user, fileInput, onClose } = setup();
    await user.upload(fileInput, csv);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
    expect(screen.getByText("No file selected")).toBeInTheDocument();
  });

  it("calls onClose when dismissed with Escape", async () => {
    const { user, onClose } = setup();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
