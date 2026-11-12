import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { CardsGrid } from "@/components/features/content/components/CardsGrid";
import type { Content, Tag } from "@/components/features/content/types";

const makeContent = (
  id: number,
  overrides: Partial<Content> = {},
): Content => ({
  content_id: id,
  display_number: id,
  content_title: `Card ${id}`,
  content_text: `Body ${id}`,
  content_tags: [1],
  related_contents_id: [],
  content_metadata: {},
  positive_votes: 0,
  negative_votes: 0,
  created_datetime_utc: "2024-01-01T00:00:00Z",
  updated_datetime_utc: "2024-01-01T00:00:00Z",
  ...overrides,
});

const tags: Tag[] = [{ tag_id: 1, tag_name: "health" }];
const threeCards = [makeContent(1), makeContent(2), makeContent(3)];

type Props = React.ComponentProps<typeof CardsGrid>;
const baseProps = (overrides: Partial<Props> = {}): Props => ({
  tags,
  cards: threeCards,
  allCards: threeCards,
  editAccess: true,
  selectedContents: [],
  setSelectedContents: vi.fn(),
  isLoading: false,
  archiveContent: vi.fn().mockResolvedValue(undefined),
  onSuccessfulArchive: vi.fn(),
  onFailedArchive: vi.fn(),
  ...overrides,
});

const cardTitles = () =>
  screen.queryAllByRole("heading", { level: 3 }).map((h) => h.textContent);

// jsdom has no layout, so clientWidth/Height are 0 → 1 card per page unless
// a test fakes a size.
const fakeGridSize = (width: number, height: number) => {
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(width);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(
    height,
  );
};

describe("CardsGrid", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    render(<CardsGrid {...baseProps({ isLoading: true })} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(cardTitles()).toEqual([]);
  });

  it("shows an add-content prompt when there is no content at all", () => {
    render(<CardsGrid {...baseProps({ cards: [], allCards: [] })} />);
    expect(screen.getByText("No content yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add content" })).toHaveAttribute(
      "href",
      "/content/edit",
    );
    expect(screen.getByText("0 of 0")).toBeInTheDocument();
  });

  it("hides the add-content prompt without edit access", () => {
    render(
      <CardsGrid
        {...baseProps({ cards: [], allCards: [], editAccess: false })}
      />,
    );
    expect(screen.getByText("No content yet")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Add content" }),
    ).not.toBeInTheDocument();
  });

  it("says nothing matches when filters hide every card", () => {
    render(<CardsGrid {...baseProps({ cards: [] })} />);
    expect(screen.getByText("No matching content")).toBeInTheDocument();
  });

  it("pages through cards one page at a time", async () => {
    const user = userEvent.setup();
    render(<CardsGrid {...baseProps()} />);

    const prev = screen.getByRole("button", { name: "Previous page" });
    const next = screen.getByRole("button", { name: "Next page" });

    expect(cardTitles()).toEqual(["Card 1"]);
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
    expect(prev).toBeDisabled();

    await user.click(next);
    await user.click(next);
    expect(cardTitles()).toEqual(["Card 3"]);
    expect(screen.getByText("3 of 3")).toBeInTheDocument();
    expect(next).toBeDisabled();

    await user.click(prev);
    expect(cardTitles()).toEqual(["Card 2"]);
  });

  it("goes back to page 1 when the card list changes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<CardsGrid {...baseProps()} />);
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(screen.getByText("2 of 3")).toBeInTheDocument();

    rerender(<CardsGrid {...baseProps({ cards: [...threeCards] })} />);
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
  });

  it("fits as many cards as the grid has room for", () => {
    // 2 columns × 2 rows: width/height leave room for two 280×210 cards each way.
    fakeGridSize(600, 460);
    const five = [1, 2, 3, 4, 5].map((id) => makeContent(id));
    render(<CardsGrid {...baseProps({ cards: five, allCards: five })} />);
    expect(cardTitles()).toEqual(["Card 1", "Card 2", "Card 3", "Card 4"]);
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
  });

  it("recalculates the page size on window resize", () => {
    render(<CardsGrid {...baseProps()} />);
    expect(cardTitles()).toHaveLength(1);

    fakeGridSize(900, 230);
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(cardTitles()).toHaveLength(3);
  });

  it("recalculates when the grid itself is resized, and stops observing on unmount", () => {
    vi.useFakeTimers();
    // Capture the ResizeObserver the grid creates so we can fire it.
    let fire: () => void = () => {};
    const disconnect = vi.fn();
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(cb: () => void) {
          fire = cb;
        }
        observe() {}
        disconnect = disconnect;
      },
    );

    const { rerender } = render(<CardsGrid {...baseProps()} />);
    fakeGridSize(900, 230);
    act(() => {
      fire();
      vi.runAllTimers(); // the callback defers the measurement with setTimeout
    });
    expect(cardTitles()).toHaveLength(3);

    // Switching to the loading state unmounts the grid node.
    rerender(<CardsGrid {...baseProps({ isLoading: true })} />);
    expect(disconnect).toHaveBeenCalled();

    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("removes its resize listener on unmount", () => {
    const remove = vi.spyOn(window, "removeEventListener");
    const { unmount } = render(<CardsGrid {...baseProps()} />);
    unmount();
    expect(remove).toHaveBeenCalledWith("resize", expect.any(Function));
  });

  it("skips cards without an id and copes with missing tags", () => {
    fakeGridSize(900, 230);
    const cards = [makeContent(1), { ...makeContent(2), content_id: null }];
    render(
      <CardsGrid
        {...baseProps({
          cards,
          allCards: cards,
          tags: undefined as unknown as Tag[],
        })}
      />,
    );
    expect(cardTitles()).toEqual(["Card 1"]);
    expect(screen.queryByText("health")).not.toBeInTheDocument();
  });

  it("passes related contents and select mode through to cards", async () => {
    const user = userEvent.setup();
    fakeGridSize(900, 230);
    const cards = [
      makeContent(1, { related_contents_id: [2] }),
      makeContent(2),
    ];
    render(
      <CardsGrid
        {...baseProps({ cards, allCards: cards, selectedContents: [2] })}
      />,
    );

    // Select mode: the selected card's checkbox is ticked.
    expect(
      screen.getByRole("checkbox", { name: "Select content #2" }),
    ).toBeChecked();

    // Opening card 1 lists card 2 as related; clicking it looks up its relations.
    await user.click(
      screen.getByRole("button", { name: "Open content #1: Card 1" }),
    );
    await user.click(screen.getByRole("button", { name: "Card 2" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Content #2");
  });
});
