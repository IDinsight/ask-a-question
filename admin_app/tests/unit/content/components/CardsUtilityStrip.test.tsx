import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { CardsUtilityStrip } from "@/components/features/content/components/CardsUtilityStrip";
import type { Content, Tag } from "@/components/features/content/types";

const tags: Tag[] = [
  { tag_id: 1, tag_name: "health" },
  { tag_id: 2, tag_name: "nutrition" },
  { tag_id: 3, tag_name: "sanitation" },
];

const card = (id: number): Content => ({
  content_id: id,
  display_number: id,
  content_title: `Card ${id}`,
  content_text: "",
  content_tags: [],
  related_contents_id: [],
  content_metadata: {},
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-01T00:00:00Z",
});

type Props = React.ComponentProps<typeof CardsUtilityStrip>;
const renderStrip = (overrides: Partial<Props> = {}) => {
  const props: Props = {
    editAccess: true,
    searchTerm: "",
    setSearchTerm: vi.fn(),
    cards: [card(1), card(2)],
    tags,
    selectedContents: [],
    setSelectedContents: vi.fn(),
    filterTags: [],
    setFilterTags: vi.fn(),
    handleDelete: vi.fn(),
    openSearchSidebar: false,
    handleSidebarToggle: vi.fn(),
    openChatSidebar: false,
    handleChatSidebarToggle: vi.fn(),
    unvalidatedCardsCount: 0,
    onValidateClick: vi.fn(),
    indexingStatus: undefined,
    onIndexingStatusClick: vi.fn(),
    onDownloadClick: vi.fn(),
    onImportCSVClick: vi.fn(),
    onImportPDFClick: vi.fn(),
    ...overrides,
  };
  render(<CardsUtilityStrip {...props} />);
  return props;
};

describe("CardsUtilityStrip", () => {
  describe("page actions (nothing selected)", () => {
    it("launches the test sidebars", async () => {
      const user = userEvent.setup();
      const props = renderStrip();
      await user.click(screen.getByRole("button", { name: "Test search" }));
      await user.click(screen.getByRole("button", { name: "Test chat" }));
      expect(props.handleSidebarToggle).toHaveBeenCalled();
      expect(props.handleChatSidebarToggle).toHaveBeenCalled();
    });

    it("disables a test launcher while its sidebar is open", () => {
      renderStrip({ openSearchSidebar: true, openChatSidebar: true });
      expect(
        screen.getByRole("button", { name: "Test search" }),
      ).toBeDisabled();
      expect(screen.getByRole("button", { name: "Test chat" })).toBeDisabled();
    });

    it("hides Validate cards and PDF status by default", () => {
      renderStrip({ unvalidatedCardsCount: undefined });
      expect(
        screen.queryByRole("button", { name: /Validate cards/ }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /PDF/ }),
      ).not.toBeInTheDocument();
    });

    it("shows Validate cards with the pending count", async () => {
      const user = userEvent.setup();
      const props = renderStrip({ unvalidatedCardsCount: 4 });
      const button = screen.getByRole("button", { name: /Validate cards/ });
      expect(button).toHaveTextContent("4");
      await user.click(button);
      expect(props.onValidateClick).toHaveBeenCalled();
    });

    it("shows a spinner while a PDF is processing", async () => {
      const user = userEvent.setup();
      const props = renderStrip({ indexingStatus: true });
      const button = screen.getByRole("button", { name: /Processing PDF/ });
      expect(
        screen.getByRole("status", { name: "Loading" }),
      ).toBeInTheDocument();
      await user.click(button);
      expect(props.onIndexingStatusClick).toHaveBeenCalled();
    });

    it("shows the PDF status button when idle", () => {
      renderStrip({ indexingStatus: false });
      expect(
        screen.getByRole("button", { name: "PDF upload status" }),
      ).toBeInTheDocument();
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });

    it("downloads all contents", async () => {
      const user = userEvent.setup();
      const props = renderStrip();
      await user.click(
        screen.getByRole("button", { name: "Download all contents" }),
      );
      expect(props.onDownloadClick).toHaveBeenCalled();
    });

    it("links New to the editor and offers CSV and PDF imports", async () => {
      const user = userEvent.setup();
      const props = renderStrip();
      expect(screen.getByRole("button", { name: "New" })).toHaveAttribute(
        "href",
        "/content/edit",
      );

      await user.click(
        screen.getByRole("button", { name: "Import or generate cards" }),
      );
      await user.click(
        await screen.findByRole("menuitem", { name: "Import cards from CSV" }),
      );
      expect(props.onImportCSVClick).toHaveBeenCalled();

      await user.click(
        screen.getByRole("button", { name: "Import or generate cards" }),
      );
      await user.click(
        await screen.findByRole("menuitem", {
          name: "Generate cards from PDF",
        }),
      );
      expect(props.onImportPDFClick).toHaveBeenCalled();
    });

    it("disables add, import and download without edit access", () => {
      renderStrip({ editAccess: false });
      const newButton = screen.getByRole("button", { name: "New" });
      expect(newButton).toBeDisabled();
      expect(newButton).not.toHaveAttribute("href");
      expect(
        screen.getByRole("button", { name: "Import or generate cards" }),
      ).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "Download all contents" }),
      ).toBeDisabled();
    });
  });

  describe("bulk actions (cards selected)", () => {
    it("shows the selection count and replaces the page actions", () => {
      renderStrip({ selectedContents: [1] });
      expect(screen.getByText("1 selected")).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Test search" }),
      ).not.toBeInTheDocument();
    });

    it("selects all shown cards, deselects all, and deletes", async () => {
      const user = userEvent.setup();
      const props = renderStrip({ selectedContents: [1] });

      await user.click(screen.getByRole("button", { name: "Select all" }));
      expect(props.setSelectedContents).toHaveBeenCalledWith([1, 2]);

      await user.click(screen.getByRole("button", { name: "Deselect all" }));
      expect(props.setSelectedContents).toHaveBeenCalledWith([]);

      await user.click(screen.getByRole("button", { name: "Delete" }));
      expect(props.handleDelete).toHaveBeenCalled();
    });

    it("disables bulk actions without edit access", () => {
      renderStrip({ selectedContents: [1], editAccess: false });
      for (const name of ["Select all", "Deselect all", "Delete"]) {
        expect(screen.getByRole("button", { name })).toBeDisabled();
      }
    });
  });

  describe("search and tag filter", () => {
    it("passes search input to the parent", async () => {
      const user = userEvent.setup();
      const props = renderStrip();
      await user.type(
        screen.getByRole("searchbox", { name: "Search content" }),
        "x",
      );
      expect(props.setSearchTerm).toHaveBeenCalledWith("x");
    });

    it("shows the first filter tag as a chip and counts the rest", () => {
      renderStrip({ filterTags: [tags[0], tags[1], tags[2]] });
      expect(screen.getByText("health")).toBeInTheDocument();
      expect(screen.getByText("+2")).toBeInTheDocument();
      expect(
        screen.getByRole("combobox", { name: "Filter by tag" }),
      ).toHaveAttribute("placeholder", "");
    });

    it("adds a tag picked from the list", async () => {
      const user = userEvent.setup();
      const props = renderStrip();
      const input = screen.getByRole("combobox", { name: "Filter by tag" });
      expect(input).toHaveAttribute("placeholder", "Filter by tag");

      await user.click(input);
      await user.click(
        await screen.findByRole("option", { name: "nutrition" }),
      );

      expect(props.setFilterTags).toHaveBeenCalledWith([tags[1]]);
    });

    it("says when no tag matches the typed text", async () => {
      const user = userEvent.setup();
      renderStrip();
      await user.type(
        screen.getByRole("combobox", { name: "Filter by tag" }),
        "zzz",
      );
      expect(await screen.findByText("No tags found")).toBeInTheDocument();
    });
  });
});
