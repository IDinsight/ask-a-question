import Link from "next/link";
import React, { useState } from "react";
import {
  IconChevronLeft,
  IconChevronRight,
  IconFileText,
  IconPlus,
} from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import type { Content, Tag } from "../types";
import { CARD_HEIGHT, CARD_MIN_WIDTH, ContentCard } from "./ContentCard";

// Spacing between cards in the grid, in px (matches `gap-2.5` / `p-2.5`).
const GRID_GAP = 10;

interface CardsGridProps {
  tags: Tag[];
  /** Cards to show, after search/tag filtering. */
  cards: Content[];
  /** Every card, used to look up related contents. */
  allCards: Content[];
  editAccess: boolean;
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  isLoading: boolean;
  /** Archives one card; the promise settles when the request does. */
  archiveContent: (content_id: number) => Promise<unknown>;
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number, error_message: string) => void;
}

/**
 * Paged grid of content cards. Page size adapts to the space available, so
 * each page fills the grid without scrolling.
 */
export const CardsGrid = ({
  tags,
  cards,
  allCards,
  editAccess,
  selectedContents,
  setSelectedContents,
  isLoading,
  archiveContent,
  onSuccessfulArchive,
  onFailedArchive,
}: CardsGridProps) => {
  const [page, setPage] = React.useState<number>(1);
  const [maxCardsPerPage, setMaxCardsPerPage] = useState(1);
  const maxPages = Math.ceil(cards.length / maxCardsPerPage);

  // Go back to page 1 whenever the card list changes (new search, filter or
  // data). Done during render rather than in an effect, per the React docs on
  // adjusting state when a prop changes. `cards` is memoised by the Wrapper,
  // so it only changes identity when its contents can have changed.
  const [pagedCards, setPagedCards] = useState(cards);
  if (pagedCards !== cards) {
    setPagedCards(cards);
    setPage(1);
  }

  const [columns, setColumns] = React.useState<number>(1);
  const gridRef = React.useRef<HTMLDivElement | null>(null);
  const resizeObserverRef = React.useRef<ResizeObserver | null>(null);

  // Work out how many cards fit in the visible grid area, so each page
  // fills the space without scrolling.
  const calculateMaxCardsPerPage = () => {
    if (!gridRef.current) return;

    // Remove the container padding, then fit cards plus the gap between them.
    const gridWidth = gridRef.current.clientWidth - 2 * GRID_GAP;
    const gridHeight = gridRef.current.clientHeight - 2 * GRID_GAP;
    const newColumns = Math.max(
      1,
      Math.floor((gridWidth + GRID_GAP) / (CARD_MIN_WIDTH + GRID_GAP)),
    );
    const rows = Math.max(
      1,
      Math.floor((gridHeight + GRID_GAP) / (CARD_HEIGHT + GRID_GAP)),
    );

    setColumns(newColumns);
    setMaxCardsPerPage(rows * newColumns);
  };

  // Callback ref: the grid only mounts after loading, so observe it when it
  // appears and stop observing when it goes away.
  const setGridRef = (node: HTMLDivElement | null) => {
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    gridRef.current = node;
    if (node) {
      calculateMaxCardsPerPage();
      const resizeObserver = new ResizeObserver(() => {
        setTimeout(calculateMaxCardsPerPage, 0);
      });
      resizeObserver.observe(node);
      resizeObserverRef.current = resizeObserver;
    }
  };

  // DOM sync only: recompute the page size when the window resizes.
  React.useEffect(() => {
    window.addEventListener("resize", calculateMaxCardsPerPage);
    return () => {
      window.removeEventListener("resize", calculateMaxCardsPerPage);
    };
  }, []);

  const getRelatedContent = (content_ids: number[]) => {
    return allCards.filter((content) =>
      content_ids.includes(content.content_id!),
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-[60vh] w-full items-center justify-center">
        <Spinner className="size-6" />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div
        ref={setGridRef}
        className="h-full w-full overflow-hidden border bg-muted/30"
        style={{ minHeight: CARD_HEIGHT * 1.1, maxHeight: CARD_HEIGHT * 4.5 }}
      >
        {cards.length === 0 ? (
          allCards.length === 0 ? (
            <Empty className="h-full">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconFileText />
                </EmptyMedia>
                <EmptyTitle>No content yet</EmptyTitle>
                <EmptyDescription>
                  Content you add here is what the search and chat services
                  answer from.
                </EmptyDescription>
              </EmptyHeader>
              {editAccess && (
                <EmptyContent>
                  <Button
                    nativeButton={false}
                    render={<Link href="/content/edit" />}
                  >
                    <IconPlus data-icon="inline-start" />
                    Add content
                  </Button>
                </EmptyContent>
              )}
            </Empty>
          ) : (
            <Empty className="h-full">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconFileText />
                </EmptyMedia>
                <EmptyTitle>No matching content</EmptyTitle>
                <EmptyDescription>
                  Try changing your search or tag filters.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )
        ) : (
          <div
            className="grid gap-2.5 p-2.5"
            style={{
              gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
            }}
          >
            {cards
              .slice(maxCardsPerPage * (page - 1), maxCardsPerPage * page)
              .map((item) =>
                item.content_id !== null ? (
                  <ContentCard
                    key={item.content_id}
                    title={item.content_title}
                    text={item.content_text}
                    content_id={item.content_id}
                    display_number={item.display_number}
                    last_modified={item.updated_datetime_utc}
                    tags={
                      tags
                        ? tags.filter((tag) =>
                            item.content_tags.includes(tag.tag_id),
                          )
                        : []
                    }
                    positive_votes={item.positive_votes}
                    negative_votes={item.negative_votes}
                    related_contents={getRelatedContent(
                      item.related_contents_id,
                    )}
                    onSuccessfulArchive={onSuccessfulArchive}
                    onFailedArchive={onFailedArchive}
                    archiveContent={archiveContent}
                    editAccess={editAccess}
                    isSelectMode={selectedContents.length > 0}
                    selectedContents={selectedContents}
                    setSelectedContents={setSelectedContents}
                    getRelatedContent={getRelatedContent}
                  />
                ) : null,
              )}
          </div>
        )}
      </div>

      {/* Page navigation */}
      <div className="flex w-full items-center pb-8">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Previous page"
            onClick={() => page > 1 && setPage(page - 1)}
            disabled={page <= 1}
          >
            <IconChevronLeft />
          </Button>
          <span className="text-sm tabular-nums text-muted-foreground">
            {maxPages === 0 ? 0 : page} of {maxPages}
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Next page"
            onClick={() => page < maxPages && setPage(page + 1)}
            disabled={page >= maxPages}
          >
            <IconChevronRight />
          </Button>
        </div>
      </div>
    </div>
  );
};
