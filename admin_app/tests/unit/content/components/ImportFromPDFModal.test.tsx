import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ImportFromPDFModal } from "@/components/features/content/components/ImportFromPDFModal";

const pdf = () => new File(["%PDF-1.4"], "guide.pdf", { type: "application/pdf" });

// react-dropzone reads drops from dataTransfer; this is the shape it expects.
const dropData = (files: File[]) => ({
  dataTransfer: {
    files,
    items: files.map((f) => ({ kind: "file", type: f.type, getAsFile: () => f })),
    types: ["Files"],
  },
});

const setup = (postDocument = vi.fn().mockResolvedValue(undefined)) => {
  // applyAccept: false so we can hand the dropzone files it should reject.
  const user = userEvent.setup({
    advanceTimers: vi.advanceTimersByTime,
    applyAccept: false,
  });
  const onClose = vi.fn();
  const onCheckStatus = vi.fn();
  const view = render(
    <ImportFromPDFModal
      open
      onClose={onClose}
      postDocument={postDocument}
      onCheckStatus={onCheckStatus}
    />,
  );
  const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
  const dropZone = screen.getByText(/Drag and drop/).parentElement!;
  return { user, onClose, onCheckStatus, postDocument, input, dropZone, view };
};

// The component waits 500ms before posting (to show a spinner).
const flushUpload = () => act(() => vi.advanceTimersByTimeAsync(500));

describe("ImportFromPDFModal", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("disables Import until a file is chosen, then shows its name", async () => {
    const { user, input } = setup();
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();

    await user.upload(input, pdf());

    expect(await screen.findByText("guide.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import" })).toBeEnabled();
  });

  it("rejects non-PDF files", async () => {
    const { user, input } = setup();
    await user.upload(input, new File(["hi"], "notes.txt", { type: "text/plain" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Only PDF files are allowed.",
    );
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
  });

  it("rejects files over 100MB", async () => {
    const { user, input } = setup();
    const big = pdf();
    Object.defineProperty(big, "size", { value: 101 * 1024 * 1024 });
    await user.upload(input, big);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "File is too large. Maximum size is 100MB.",
    );
  });

  it("shows the dropzone's own message for other rejections", async () => {
    const { dropZone } = setup();
    // Dropping two files breaks the single-file rule ("too-many-files").
    const two = [pdf(), new File(["%PDF"], "b.pdf", { type: "application/pdf" })];
    fireEvent.drop(dropZone, dropData(two));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many files");
  });

  it("highlights the zone while a file is dragged over it", async () => {
    const { dropZone } = setup();
    fireEvent.dragEnter(dropZone, dropData([pdf()]));
    expect(await screen.findByText("Drop the file here...")).toBeInTheDocument();
  });

  it("starts card generation and offers to check status", async () => {
    const { user, input, postDocument, onClose, onCheckStatus } = setup();
    const file = pdf();
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Import" }));

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    await flushUpload();

    expect(postDocument).toHaveBeenCalledWith(file);
    expect(
      await screen.findByText("Card generation task successfully started!"),
    ).toBeInTheDocument();
    // After success the footer only offers Close.
    expect(screen.queryByRole("button", { name: "Import" })).not.toBeInTheDocument();
    // (The dialog's corner X is also labelled "Close"; find the footer one.)
    const footerClose = screen
      .getAllByRole("button", { name: "Close" })
      .find((el) => el.getAttribute("data-slot") !== "dialog-close");
    expect(footerClose).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Check status" }));
    expect(onClose).toHaveBeenCalled();
    expect(onCheckStatus).toHaveBeenCalled();
  });

  it("shows the upload error", async () => {
    const { user, input } = setup(vi.fn().mockRejectedValue(new Error("quota exceeded")));
    await user.upload(input, pdf());
    await user.click(screen.getByRole("button", { name: "Import" }));
    await flushUpload();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An error occurred: quota exceeded",
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Import" })).toBeEnabled(),
    );
  });

  it("resets its state when closed and reopened", async () => {
    const { user, input, view, postDocument, onCheckStatus } = setup();
    await user.upload(input, pdf());
    expect(await screen.findByText("guide.pdf")).toBeInTheDocument();

    const props = { onClose: vi.fn(), postDocument, onCheckStatus };
    view.rerender(<ImportFromPDFModal open={false} {...props} />);
    view.rerender(<ImportFromPDFModal open {...props} />);

    expect(screen.queryByText("guide.pdf")).not.toBeInTheDocument();
  });

  it("calls onClose from Cancel", async () => {
    const { user, onClose } = setup();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when dismissed with Escape", async () => {
    const { user, onClose } = setup();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
