import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Papa from "papaparse";
import { vi } from "vitest";

import { DownloadModal } from "@/components/features/content/components/DownloadModal";
import type { Content, Tag } from "@/components/features/content/types";

const content: Content = {
  content_id: 7,
  display_number: 1,
  content_title: "Handwashing",
  content_text: "Wash for 20 seconds.",
  content_tags: [1, 2],
  related_contents_id: [],
  content_metadata: { source: "test" },
  positive_votes: 4,
  negative_votes: 1,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-02T00:00:00Z",
};
const tags: Tag[] = [
  { tag_id: 1, tag_name: "hygiene" },
  { tag_id: 2, tag_name: "health" },
];

const renderModal = (fetchContents: () => Promise<{ contents: Content[]; tags: Tag[] }>) => {
  const props = {
    onClose: vi.fn(),
    onFailedDownload: vi.fn(),
    onNoDataFound: vi.fn(),
  };
  render(<DownloadModal open fetchContents={fetchContents} {...props} />);
  return props;
};

describe("DownloadModal", () => {
  beforeEach(() => {
    // jsdom doesn't navigate on anchor clicks; stub so the download is a no-op
    // we can assert on.
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it("downloads contents as a CSV with tag names and stringified metadata", async () => {
    const user = userEvent.setup();
    const unparse = vi.spyOn(Papa, "unparse");
    const createObjectURL = vi.spyOn(URL, "createObjectURL");
    const props = renderModal(async () => ({ contents: [content], tags }));

    await user.click(screen.getByRole("button", { name: "Download" }));

    await waitFor(() => expect(props.onClose).toHaveBeenCalled());
    expect(unparse).toHaveBeenCalledWith([
      {
        content_id: 7,
        title: "Handwashing",
        text: "Wash for 20 seconds.",
        tags: ["hygiene", "health"],
        content_metadata: JSON.stringify({ source: "test" }),
        positive_votes: 4,
        negative_votes: 1,
        created_datetime_utc: "2024-01-01T00:00:00Z",
        updated_datetime_utc: "2024-01-02T00:00:00Z",
      },
    ]);
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce();
    expect(props.onNoDataFound).not.toHaveBeenCalled();
  });

  it("reports when there is nothing to download", async () => {
    const user = userEvent.setup();
    const props = renderModal(async () => ({ contents: [], tags: [] }));

    await user.click(screen.getByRole("button", { name: "Download" }));

    await waitFor(() => expect(props.onNoDataFound).toHaveBeenCalled());
    expect(props.onClose).toHaveBeenCalled();
    expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
  });

  it("reports a generic message for network/server failures", async () => {
    const user = userEvent.setup();
    const props = renderModal(() => Promise.reject(new Error("boom")));

    await user.click(screen.getByRole("button", { name: "Download" }));

    await waitFor(() =>
      expect(props.onFailedDownload).toHaveBeenCalledWith("Failed to download content"),
    );
    expect(props.onClose).toHaveBeenCalled();
  });

  it("reports the backend's detail for a 4xx error", async () => {
    const user = userEvent.setup();
    // A CustomError, as the API client's interceptor produces for 4xx.
    const customError = { status: 403, message: "Not allowed" };
    const props = renderModal(() => Promise.reject(customError));

    await user.click(screen.getByRole("button", { name: "Download" }));

    await waitFor(() => expect(props.onFailedDownload).toHaveBeenCalledWith("Not allowed"));
  });

  it("disables both buttons while the download is in progress", async () => {
    const user = userEvent.setup();
    let resolve!: (v: { contents: Content[]; tags: Tag[] }) => void;
    renderModal(() => new Promise((r) => (resolve = r)));

    await user.click(screen.getByRole("button", { name: "Download" }));

    expect(screen.getByRole("button", { name: /Download/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();

    resolve({ contents: [], tags: [] });
    await waitFor(() => expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled());
  });

  it("calls onClose on Cancel", async () => {
    const user = userEvent.setup();
    const props = renderModal(async () => ({ contents: [], tags: [] }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onClose).toHaveBeenCalled();
  });
});
