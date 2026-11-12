import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ContentCard } from "@/components/features/content/components/ContentCard";
import type { Content, Tag } from "@/components/features/content/types";

const tags: Tag[] = [
  { tag_id: 1, tag_name: "a-very-long-tag-name-indeed" },
  { tag_id: 2, tag_name: "short" },
];

const related: Content = {
  content_id: 9,
  display_number: 2,
  content_title: "Related card",
  content_text: "Related body",
  content_tags: [2],
  related_contents_id: [],
  content_metadata: {},
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-03T00:00:00Z",
};

const renderCard = (
  overrides: Partial<React.ComponentProps<typeof ContentCard>> = {},
) => {
  const props: React.ComponentProps<typeof ContentCard> = {
    title: "Handwashing",
    text: "Wash for 20 seconds.",
    content_id: 5,
    display_number: 1,
    last_modified: "2024-02-01T00:00:00Z",
    tags,
    positive_votes: 3,
    negative_votes: 1,
    related_contents: [related],
    onSuccessfulArchive: vi.fn(),
    onFailedArchive: vi.fn(),
    archiveContent: vi.fn().mockResolvedValue(undefined),
    editAccess: true,
    isSelectMode: false,
    selectedContents: [],
    setSelectedContents: vi.fn(),
    getRelatedContent: vi.fn().mockReturnValue([]),
    ...overrides,
  };
  render(<ContentCard {...props} />);
  return props;
};

const card = () =>
  screen.getByRole("button", { name: "Open content #1: Handwashing" });

describe("ContentCard", () => {
  it("shows title, text, the first tag (truncated) and a count of the rest", () => {
    renderCard();
    expect(
      screen.getByRole("heading", { name: "Handwashing" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Wash for 20 seconds.")).toBeInTheDocument();
    expect(screen.getByText("a-very-long-tag...")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("shows a short single tag as-is with no count", () => {
    renderCard({ tags: [tags[1]] });
    expect(screen.getByText("short")).toBeInTheDocument();
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });

  it("renders without tags", () => {
    renderCard({ tags: [] });
    expect(screen.queryByText("short")).not.toBeInTheDocument();
  });

  it("opens the view modal on click", async () => {
    const user = userEvent.setup();
    renderCard();
    await user.click(card());
    expect(screen.getByRole("dialog")).toHaveTextContent("Content #1");
  });

  it("opens with Enter or Space, but ignores other keys and keys from child controls", () => {
    renderCard();
    fireEvent.keyDown(card(), { key: "a" });
    fireEvent.keyDown(screen.getByRole("checkbox"), { key: "Enter" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.keyDown(card(), { key: " " });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("opens with Enter", () => {
    renderCard();
    fireEvent.keyDown(card(), { key: "Enter" });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("jumps to a related content inside the modal", async () => {
    const user = userEvent.setup();
    const props = renderCard();
    await user.click(card());
    await user.click(screen.getByRole("button", { name: "Related card" }));

    expect(props.getRelatedContent).toHaveBeenCalledWith([]);
    expect(screen.getByRole("dialog")).toHaveTextContent("Content #2");
    expect(screen.getByRole("dialog")).toHaveTextContent("Related body");
    // Only the tags the related content carries are shown.
    expect(screen.getByRole("dialog")).toHaveTextContent("short");
    expect(screen.getByRole("dialog")).not.toHaveTextContent(
      "a-very-long-tag-name-indeed",
    );

    // Closing and reopening the card shows the card itself again.
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await user.click(card());
    expect(screen.getByRole("dialog")).toHaveTextContent("Content #1");
  });

  it("selects the card via its checkbox without opening it", async () => {
    const user = userEvent.setup();
    const props = renderCard({ selectedContents: [8] });
    await user.click(
      screen.getByRole("checkbox", { name: "Select content #1" }),
    );
    expect(props.setSelectedContents).toHaveBeenCalledWith([8, 5]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("deselects an already-selected card", async () => {
    const user = userEvent.setup();
    const props = renderCard({ selectedContents: [5, 8], isSelectMode: true });
    const checkbox = screen.getByRole("checkbox", {
      name: "Select content #1",
    });
    expect(checkbox).toBeChecked();
    await user.click(checkbox);
    expect(props.setSelectedContents).toHaveBeenCalledWith([8]);
  });

  it("deletes after confirmation and reports success", async () => {
    const user = userEvent.setup();
    const props = renderCard({ selectedContents: [5] });
    await user.click(screen.getByRole("button", { name: "Delete content #1" }));

    // Opening delete drops the card from the selection and doesn't open the view.
    expect(props.setSelectedContents).toHaveBeenCalledWith([]);
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "Remove this content?",
    );

    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(props.archiveContent).toHaveBeenCalledWith(5);
    await waitFor(() =>
      expect(props.onSuccessfulArchive).toHaveBeenCalledWith(5),
    );
  });

  it("reports a failed delete", async () => {
    const user = userEvent.setup();
    const props = renderCard({
      archiveContent: vi
        .fn()
        .mockRejectedValue({ status: 500, message: "nope" }),
    });
    await user.click(screen.getByRole("button", { name: "Delete content #1" }));
    await user.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() =>
      expect(props.onFailedArchive).toHaveBeenCalledWith(5, "nope"),
    );
  });

  it("disables delete and edit without edit access", () => {
    renderCard({ editAccess: false });
    expect(
      screen.getByRole("button", { name: "Delete content #1" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
  });

  it("links Edit to the editor without opening the card", async () => {
    const user = userEvent.setup();
    renderCard();
    // Base UI's Button rendered as a <Link> keeps role="button".
    const edit = screen.getByRole("button", { name: "Edit" });
    expect(edit).toHaveAttribute("href", "/content/edit?content_id=5");
    await user.click(edit);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
