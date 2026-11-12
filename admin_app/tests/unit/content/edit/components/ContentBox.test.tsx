import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import {
  ContentBox,
  handleCustomError,
  setSnackMessage,
} from "@/components/features/content/edit/components/ContentBox";
import type { Content, Tag } from "@/components/features/content/types";
import { toast } from "@/components/ui/toast";

const makeContent = (overrides: Partial<Content> = {}): Content => ({
  content_id: 1,
  display_number: 1,
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-01T00:00:00Z",
  content_title: "Clean water",
  content_text: "Boil water before drinking.",
  content_tags: [],
  related_contents_id: [],
  content_metadata: {},
  ...overrides,
});

const TAGS: Tag[] = [
  { tag_id: 1, tag_name: "hygiene" },
  { tag_id: 2, tag_name: "water" },
];
const CONTENTS: Content[] = [
  makeContent({ content_id: 1, content_title: "Clean water" }),
  makeContent({ content_id: 2, content_title: "Hand washing" }),
  makeContent({ content_id: 3, content_title: "Latrine use" }),
];

type Props = React.ComponentProps<typeof ContentBox>;

/**
 * ContentBox is controlled by its parent (content + isSaved state). This
 * harness owns that state like ContentEditWrapper does, and reports every
 * content change through `onContent` so tests can assert on it.
 */
const Harness = ({
  initialContent,
  onContent,
  ...rest
}: Omit<Props, "content" | "setContent" | "isSaved" | "setIsSaved"> & {
  initialContent: Content | null;
  onContent: (c: Content | null) => void;
}) => {
  const [content, setContentState] = React.useState<Content | null>(initialContent);
  const [isSaved, setIsSaved] = React.useState(false);
  const setContent: Props["setContent"] = (next) => {
    setContentState((prev) => {
      const value = typeof next === "function" ? next(prev) : next;
      onContent(value);
      return value;
    });
  };
  return (
    <ContentBox
      {...rest}
      content={content}
      setContent={setContent}
      isSaved={isSaved}
      setIsSaved={setIsSaved}
    />
  );
};

const setup = (
  overrides: Partial<React.ComponentProps<typeof Harness>> = {},
) => {
  const props = {
    initialContent: makeContent() as Content | null,
    onContent: vi.fn(),
    tags: TAGS as Tag[] | undefined,
    contents: CONTENTS as Content[] | undefined,
    addTag: vi.fn(),
    deleteTag: vi.fn(),
    saveContent: vi.fn(),
    isSaving: false,
    onSaved: vi.fn(),
    ...overrides,
  };
  const user = userEvent.setup();
  const utils = render(<Harness {...props} />);
  return { ...props, user, ...utils };
};

/** The most recent content the harness passed to `onContent`. */
const lastContent = (onContent: (c: Content | null) => void) =>
  vi.mocked(onContent).mock.calls.at(-1)?.[0] as Content;

describe("ContentBox", () => {
  let toastAdd: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    toastAdd = vi.spyOn(toast, "add").mockImplementation(() => "id");
    // Save failures log on purpose; keep output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  describe("validation", () => {
    it("flags both fields when saving a blank new card", async () => {
      const { user, saveContent } = setup({ initialContent: null });

      expect(screen.getByLabelText("Title")).toHaveValue("");
      expect(screen.getByLabelText("Content")).toHaveValue("");
      await user.click(screen.getByRole("button", { name: "Save" }));

      expect(screen.getByText("Title should not be empty")).toBeInTheDocument();
      expect(screen.getByText("Content should not be empty")).toBeInTheDocument();
      expect(saveContent).not.toHaveBeenCalled();
    });

    it("flags an empty title, then clears the error on typing", async () => {
      const { user } = setup({ initialContent: makeContent({ content_title: "" }) });

      await user.click(screen.getByRole("button", { name: "Save" }));
      expect(screen.getByText("Title should not be empty")).toBeInTheDocument();
      expect(screen.getByLabelText("Title")).toHaveAttribute("aria-invalid", "true");

      await user.type(screen.getByLabelText("Title"), "A");
      expect(screen.queryByText("Title should not be empty")).not.toBeInTheDocument();
    });

    it("flags empty content text", async () => {
      const { user } = setup({ initialContent: makeContent({ content_text: "" }) });
      await user.click(screen.getByRole("button", { name: "Save" }));
      expect(screen.getByText("Content should not be empty")).toBeInTheDocument();
      expect(screen.queryByText("Title should not be empty")).not.toBeInTheDocument();
    });
  });

  describe("editing", () => {
    it("starts a new card from scratch when typing into an empty form", async () => {
      // A tag already chosen before typing is carried into the new card.
      const { user, onContent } = setup({ initialContent: null });

      await user.type(screen.getByLabelText("Content"), "x");

      expect(lastContent(onContent)).toMatchObject({
        content_id: null,
        content_title: "",
        content_text: "x",
        content_tags: [],
      });
    });

    it("updates the existing card's title", async () => {
      const { user, onContent } = setup();
      await user.type(screen.getByLabelText("Title"), "!");
      expect(lastContent(onContent).content_title).toBe("Clean water!");
    });
  });

  describe("saving", () => {
    it("saves an edited card and reports success", async () => {
      const saveContent = vi.fn().mockResolvedValue(makeContent());
      const { user, onSaved } = setup({ saveContent });

      await user.click(screen.getByRole("button", { name: "Save" }));

      expect(saveContent).toHaveBeenCalledWith(1, {
        content_title: "Clean water",
        content_text: "Boil water before drinking.",
        content_metadata: {},
        content_tags: [],
        related_contents_id: [],
      });
      await waitFor(() => expect(onSaved).toHaveBeenCalledWith("Content edited successfully"));
      // isSaved flips to true, which disables the button until the next edit.
      expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    });

    it("reports creation for a new card", async () => {
      const saveContent = vi.fn().mockResolvedValue(makeContent({ content_id: 50 }));
      const { user, onSaved } = setup({ initialContent: null, saveContent });

      await user.type(screen.getByLabelText("Title"), "T");
      await user.type(screen.getByLabelText("Content"), "B");
      await user.click(screen.getByRole("button", { name: "Save" }));

      expect(saveContent).toHaveBeenCalledWith(null, expect.objectContaining({ content_title: "T" }));
      await waitFor(() => expect(onSaved).toHaveBeenCalledWith("Content created successfully"));
    });

    it("does not report success if the API returns no id", async () => {
      const saveContent = vi.fn().mockResolvedValue(makeContent({ content_id: null }));
      const { user, onSaved } = setup({ saveContent });

      await user.click(screen.getByRole("button", { name: "Save" }));
      await waitFor(() => expect(saveContent).toHaveBeenCalled());
      expect(onSaved).not.toHaveBeenCalled();
    });

    it.each([
      ["a quota error (403)", { status: 403, message: "Content limit reached" }, "Content limit reached"],
      ["any other error", { status: 500, message: "Server exploded" }, "Server exploded"],
      ["an error without a message", { status: 500 }, "Failed to save content. Please try again later."],
    ])("shows %s", async (_label, error, shown) => {
      const { user, onSaved } = setup({ saveContent: vi.fn().mockRejectedValue(error) });

      await user.click(screen.getByRole("button", { name: "Save" }));

      expect(await screen.findByRole("alert")).toHaveTextContent(shown);
      expect(onSaved).not.toHaveBeenCalled();
    });

    it("disables Save while saving", () => {
      setup({ isSaving: true });
      // The spinner's own label joins the button name, so match loosely.
      const save = screen.getByRole("button", { name: /Save/ });
      expect(save).toBeDisabled();
      expect(within(save).getByRole("status")).toBeInTheDocument();
    });
  });

  describe("tags", () => {
    it("shows the card's existing tags, ignoring unknown ids", () => {
      setup({ initialContent: makeContent({ content_tags: [2, 999] }) });
      expect(screen.getByText("water")).toBeInTheDocument();
      expect(screen.queryByText("hygiene")).not.toBeInTheDocument();
      expect(screen.getByLabelText("Tags (optional)")).toHaveAttribute("placeholder", "");
    });

    it("renders with lists still loading", () => {
      setup({ tags: undefined, contents: undefined });
      expect(screen.getByLabelText("Tags (optional)")).toHaveAttribute(
        "placeholder",
        "Find or create tags",
      );
    });

    it("adds an existing tag to the card", async () => {
      const { user, onContent } = setup();

      await user.type(screen.getByLabelText("Tags (optional)"), "hyg");
      await user.click(await screen.findByRole("option", { name: /hygiene/ }));

      expect(lastContent(onContent).content_tags).toEqual([1]);
    });

    it("starts a new card when tagging an empty form", async () => {
      const { user, onContent } = setup({ initialContent: null });

      await user.type(screen.getByLabelText("Tags (optional)"), "wat");
      await user.click(await screen.findByRole("option", { name: /water/ }));

      expect(lastContent(onContent)).toMatchObject({ content_id: null, content_tags: [2] });
    });

    it("offers to create a tag that doesn't exist, and adds it", async () => {
      const addTag = vi.fn().mockResolvedValue({ tag_id: 7, tag_name: "Fever" });
      const { user, onContent } = setup({ addTag });

      await user.type(screen.getByLabelText("Tags (optional)"), "Fever");
      await user.click(await screen.findByRole("option", { name: 'Create "Fever"' }));

      expect(addTag).toHaveBeenCalledWith("Fever");
      await waitFor(() => expect(lastContent(onContent).content_tags).toEqual([7]));
    });

    it("does not offer to create a tag that already exists (case-insensitive)", async () => {
      const { user } = setup();
      await user.type(screen.getByLabelText("Tags (optional)"), "HYGIENE");
      expect(screen.queryByRole("option", { name: /Create/ })).not.toBeInTheDocument();
    });

    it("toasts when creating a tag fails", async () => {
      const addTag = vi.fn().mockRejectedValue({ message: "Tag limit" });
      const { user } = setup({ addTag });

      await user.type(screen.getByLabelText("Tags (optional)"), "Fever");
      await user.click(await screen.findByRole("option", { name: 'Create "Fever"' }));

      await waitFor(() =>
        expect(toastAdd).toHaveBeenCalledWith({ title: "Tag limit", type: "error" }),
      );
    });

    it("deletes a tag after confirmation", async () => {
      const deleteTag = vi.fn().mockResolvedValue(undefined);
      const { user, onContent } = setup({
        initialContent: makeContent({ content_tags: [1, 2] }),
        deleteTag,
      });

      await user.click(screen.getByLabelText("Tags (optional)"));
      await user.click(await screen.findByRole("button", { name: "Delete tag hygiene" }));

      expect(
        await screen.findByRole("alertdialog", { name: 'Delete tag "hygiene"?' }),
      ).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Delete" }));

      expect(deleteTag).toHaveBeenCalledWith(1);
      await waitFor(() => expect(lastContent(onContent).content_tags).toEqual([2]));
      expect(toastAdd).toHaveBeenCalledWith({
        title: 'Tag "hygiene" deleted successfully',
        type: "success",
      });
    });

    it("keeps the tag when deletion is cancelled", async () => {
      const deleteTag = vi.fn();
      const { user } = setup({ deleteTag });

      await user.click(screen.getByLabelText("Tags (optional)"));
      await user.click(await screen.findByRole("button", { name: "Delete tag water" }));
      await user.click(await screen.findByRole("button", { name: "Cancel" }));

      await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
      expect(deleteTag).not.toHaveBeenCalled();
    });
  });

  describe("related contents", () => {
    it("shows the card's related contents and excludes the card itself", async () => {
      const { user } = setup({ initialContent: makeContent({ related_contents_id: [3, 999] }) });

      expect(screen.getByText("Latrine use")).toBeInTheDocument();

      await user.click(screen.getByLabelText("Related contents (optional)"));
      expect(await screen.findByRole("option", { name: "Hand washing" })).toBeInTheDocument();
      expect(screen.queryByRole("option", { name: "Clean water" })).not.toBeInTheDocument();
    });

    it("links a related content to the card", async () => {
      const { user, onContent } = setup();

      await user.type(screen.getByLabelText("Related contents (optional)"), "Hand");
      await user.click(await screen.findByRole("option", { name: "Hand washing" }));

      expect(lastContent(onContent).related_contents_id).toEqual([2]);
    });

    it("offers every content for a new card and doesn't create one on pick", async () => {
      const { user, onContent } = setup({ initialContent: null });

      await user.type(screen.getByLabelText("Related contents (optional)"), "Clean");
      await user.click(await screen.findByRole("option", { name: "Clean water" }));

      // No card exists yet, so nothing is written back.
      expect(onContent).not.toHaveBeenCalled();
      expect(screen.getByText("Clean water")).toBeInTheDocument();
    });
  });
});

describe("setSnackMessage / handleCustomError", () => {
  let toastAdd: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    toastAdd = vi.spyOn(toast, "add").mockImplementation(() => "id");
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows success for messages mentioning 'successfully', error otherwise", () => {
    setSnackMessage("Saved SUCCESSFULLY");
    setSnackMessage("Oops");
    expect(toastAdd).toHaveBeenNthCalledWith(1, { title: "Saved SUCCESSFULLY", type: "success" });
    expect(toastAdd).toHaveBeenNthCalledWith(2, { title: "Oops", type: "error" });
  });

  it("uses the error's message, a generic text for non-string messages, or the default", () => {
    handleCustomError({ message: "Bad tag" }, "default");
    handleCustomError({ message: { detail: "x" } }, "default");
    handleCustomError(null, "default");
    expect(toastAdd.mock.calls.map(([arg]: unknown[]) => (arg as { title: string }).title)).toEqual([
      "Bad tag",
      "An unknown error occurred",
      "default",
    ]);
  });
});
