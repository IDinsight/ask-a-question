import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import {
  ArchiveContentModal,
  ContentViewModal,
  EditContentButton,
} from "@/components/features/content/components/ContentModal";
import type { Content } from "@/components/features/content/types";

// Minimal fake content used as a "related content" badge.
const related = (id: number, title: string): Content => ({
  content_id: id,
  display_number: id,
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-01T00:00:00Z",
  content_title: title,
  content_text: "Body",
  content_tags: [],
  related_contents_id: [],
  content_metadata: {},
});

// Defaults for the view modal; each test overrides what it cares about.
const viewProps = (
  overrides: Partial<Parameters<typeof ContentViewModal>[0]> = {},
) => ({
  title: "Handwashing basics",
  text: "Wash for **twenty** seconds.",
  content_id: 7,
  display_number: 3,
  positive_votes: 4,
  negative_votes: 1,
  last_modified: "2024-05-02T10:30:00Z",
  related_contents: [] as Content[],
  open: true,
  onClose: vi.fn(),
  onRelatedContentClick: vi.fn(),
  editAccess: true,
  ...overrides,
});

describe("EditContentButton", () => {
  it("links to the editor when the user has edit access", async () => {
    const onClick = vi.fn((e: React.MouseEvent) => e.preventDefault());
    render(<EditContentButton content_id={12} editAccess onClick={onClick} />);

    const link = screen.getByRole("button", { name: "Edit" });
    expect(link).toHaveAttribute("href", "/content/edit?content_id=12");

    await userEvent.click(link);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders a disabled button without edit access", () => {
    render(<EditContentButton content_id={12} editAccess={false} />);

    const button = screen.getByRole("button", { name: "Edit" });
    expect(button).toBeDisabled();
    expect(button).not.toHaveAttribute("href");
  });
});

describe("ContentViewModal", () => {
  it("shows the title, rendered markdown, votes and the edit link", () => {
    render(<ContentViewModal {...viewProps()} />);

    expect(
      screen.getByRole("heading", { name: "Content #3" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Handwashing basics" }),
    ).toBeInTheDocument();
    // Markdown is rendered, not shown raw.
    expect(screen.getByText("twenty").tagName).toBe("STRONG");
    expect(screen.getByTitle("Upvotes")).toHaveTextContent("4");
    expect(screen.getByTitle("Downvotes")).toHaveTextContent("1");
    expect(screen.getByText(/Last modified/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute(
      "href",
      "/content/edit?content_id=7",
    );
    // No tags/related sections when the lists are empty.
    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
    expect(screen.queryByText("Related contents")).not.toBeInTheDocument();
  });

  it("lists tags and lets the user open a related content", async () => {
    const onRelatedContentClick = vi.fn();
    const sibling = related(9, "Soap alternatives");
    render(
      <ContentViewModal
        {...viewProps({
          tags: [
            { tag_id: 1, tag_name: "hygiene" },
            { tag_id: 2, tag_name: "children" },
          ],
          related_contents: [sibling],
          onRelatedContentClick,
        })}
      />,
    );

    expect(screen.getByText("hygiene")).toBeInTheDocument();
    expect(screen.getByText("children")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "Soap alternatives" }),
    );
    expect(onRelatedContentClick).toHaveBeenCalledWith(sibling);
  });

  it("shows approve/reject in validation mode and passes the content id", async () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(
      <ContentViewModal
        {...viewProps({ validation_mode: true, onApprove, onReject })}
      />,
    );

    expect(
      screen.queryByRole("button", { name: "Edit" }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(onApprove).toHaveBeenCalledWith(7);
    expect(onReject).toHaveBeenCalledWith(7);
  });

  it("disables approve/reject without edit access", () => {
    render(
      <ContentViewModal
        {...viewProps({ validation_mode: true, editAccess: false })}
      />,
    );
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
  });

  it("does not crash when approve/reject handlers are missing", async () => {
    render(<ContentViewModal {...viewProps({ validation_mode: true })} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
  });

  it("calls onClose when dismissed", async () => {
    const onClose = vi.fn();
    render(<ContentViewModal {...viewProps({ onClose })} />);

    // The dialog's corner close button.
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders nothing when closed", () => {
    render(<ContentViewModal {...viewProps({ open: false })} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ArchiveContentModal", () => {
  const setup = (archiveContent: (id: number) => Promise<unknown>) => {
    const props = {
      content_id: 5,
      open: true,
      onClose: vi.fn(),
      onSuccessfulArchive: vi.fn(),
      onFailedArchive: vi.fn(),
      archiveContent: vi.fn(archiveContent),
    };
    render(<ArchiveContentModal {...props} />);
    return props;
  };

  it("archives, closes immediately and reports success", async () => {
    const props = setup(() => Promise.resolve());

    await userEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(props.archiveContent).toHaveBeenCalledWith(5);
    expect(props.onClose).toHaveBeenCalled();
    await waitFor(() =>
      expect(props.onSuccessfulArchive).toHaveBeenCalledWith(5),
    );
    expect(props.onFailedArchive).not.toHaveBeenCalled();
  });

  it("reports the error message when archiving fails", async () => {
    const props = setup(() => Promise.reject({ message: "Not allowed" }));

    await userEvent.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() =>
      expect(props.onFailedArchive).toHaveBeenCalledWith(5, "Not allowed"),
    );
    expect(props.onSuccessfulArchive).not.toHaveBeenCalled();
  });

  it("closes without archiving on cancel", async () => {
    const props = setup(() => Promise.resolve());

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(props.onClose).toHaveBeenCalled();
    expect(props.archiveContent).not.toHaveBeenCalled();
  });
});
