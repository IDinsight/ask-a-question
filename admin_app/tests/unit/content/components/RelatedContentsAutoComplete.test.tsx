import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { RelatedContentsAutoComplete } from "@/components/features/content/components/RelatedContentsAutoComplete";
import type { Content } from "@/components/features/content/types";

const makeContent = (id: number | null, title: string): Content => ({
  content_id: id,
  display_number: id ?? 0,
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

const contents = [
  makeContent(1, "Malaria prevention"),
  makeContent(2, "Measles vaccine"),
  makeContent(3, "Nutrition for toddlers"),
];

describe("RelatedContentsAutoComplete", () => {
  it("shows a placeholder when nothing is selected", () => {
    render(
      <RelatedContentsAutoComplete
        contents={contents}
        selectedContents={[]}
        handleContentChange={vi.fn()}
      />,
    );
    const input = screen.getByLabelText("Related contents (optional)");
    expect(input).toHaveAttribute("placeholder", "Find content");
  });

  it("shows selected contents as chips and hides the placeholder", () => {
    render(
      <RelatedContentsAutoComplete
        contents={contents}
        selectedContents={[contents[1]]}
        handleContentChange={vi.fn()}
      />,
    );
    expect(screen.getByText("Measles vaccine")).toBeInTheDocument();
    expect(screen.getByLabelText("Related contents (optional)")).toHaveAttribute(
      "placeholder",
      "",
    );
  });

  it("filters by title and adds the picked content to the selection", async () => {
    const user = userEvent.setup();
    const handleContentChange = vi.fn();
    render(
      <RelatedContentsAutoComplete
        contents={contents}
        selectedContents={[contents[0]]}
        handleContentChange={handleContentChange}
      />,
    );

    await user.type(screen.getByLabelText("Related contents (optional)"), "Mea");

    // Only the matching title is offered.
    expect(await screen.findByRole("option", { name: "Measles vaccine" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Nutrition for toddlers" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("option", { name: "Measles vaccine" }));
    expect(handleContentChange).toHaveBeenLastCalledWith([contents[0], contents[1]]);
  });

  it("says when nothing matches", async () => {
    const user = userEvent.setup();
    render(
      <RelatedContentsAutoComplete
        contents={contents}
        selectedContents={[]}
        handleContentChange={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("Related contents (optional)"), "zzz");
    expect(await screen.findByText("No contents found")).toBeInTheDocument();
  });

  it("matches unsaved contents (no id) by title", async () => {
    const user = userEvent.setup();
    const handleContentChange = vi.fn();
    // An unsaved content is selected; picking it again should deselect it,
    // which only works if equality falls back to the title.
    const unsaved = makeContent(null, "Draft card");
    render(
      <RelatedContentsAutoComplete
        contents={[unsaved, ...contents]}
        selectedContents={[makeContent(null, "Draft card")]}
        handleContentChange={handleContentChange}
      />,
    );

    await user.type(screen.getByLabelText("Related contents (optional)"), "Draft");
    await user.click(await screen.findByRole("option", { name: "Draft card" }));
    expect(handleContentChange).toHaveBeenLastCalledWith([]);
  });
});
