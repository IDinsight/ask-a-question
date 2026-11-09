"use client";
import Link from "next/link";
import React, { useState } from "react";
import {
  IconAlertTriangle,
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconDownload,
  IconFileText,
  IconFileTypeCsv,
  IconFileTypePdf,
  IconPlayerPlay,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";

import type { Content, Tag } from "@/app/content/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonGroup, ButtonGroupSeparator } from "@/components/ui/button-group";
import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "cn";
import { apiCalls, CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import {
  archiveContent,
  getContentList,
  getTagList,
  useGetIndexingStatus,
  useGetNextUnvalidatedCard,
  useGetUnvalidatedCardsCount,
} from "./api";
import { ChatSideBar } from "./components/ChatSideBar";
import { CARD_HEIGHT, CARD_MIN_WIDTH, ContentCard } from "./components/ContentCard";
import { DownloadModal } from "./components/DownloadModal";
import { ImportFromCSVModal } from "./components/ImportFromCSVModal";
import { ImportFromPDFModal } from "./components/ImportFromPDFModal";
import { IndexingStatusModal } from "./components/IndexingStatusModal";
import { SearchBar, SearchBarProps } from "./components/SearchBar";
import { SearchSidebar } from "./components/SearchSidebar";
import { useShowIndexingStatusStore } from "./store/indexingStatusStore";
import { ContentViewModal } from "./components/ContentModal";

type SnackMessage = {
  message: string | null;
  color: "success" | "info" | "warning" | "error" | undefined;
};

/**
 * Show a toast. Kept with the old Snackbar's `{ message, color }` shape so
 * callers didn't need to change. Rendered by the Toaster in content/layout.tsx.
 */
const setSnackMessage = ({ message, color }: SnackMessage) => {
  if (message) toast.add({ title: message, type: color });
};

// Spacing between cards in the grid, in px (matches `gap-2.5` / `p-2.5`).
const GRID_GAP = 10;

interface TagsFilterProps {
  tags: Tag[];
  filterTags: Tag[];
  setFilterTags: React.Dispatch<React.SetStateAction<Tag[]>>;
}

interface CardsUtilityStripProps extends TagsFilterProps, SearchBarProps {
  editAccess: boolean;
  cards: Content[];
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  setRefreshKey: React.Dispatch<React.SetStateAction<number>>;
  handleDelete: () => void;
}

interface CardsGridProps {
  tags: Tag[];
  cards: Content[];
  allCards: Content[];
  token: string | null;
  editAccess: boolean;
  openSearchSidebar: boolean;
  handleSidebarToggle: () => void;
  openChatSidebar: boolean;
  handleChatSidebarToggle: () => void;
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  isLoading: boolean;
  setRefreshKey: React.Dispatch<React.SetStateAction<number>>;
}

const CardsPage = () => {
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [filterTags, setFilterTags] = React.useState<Tag[]>([]);
  const [editAccess, setEditAccess] = React.useState(false);
  const { token, userRole } = useAuth();

  const [openSearchSidebar, setOpenSideBar] = useState(false);
  const [openChatSidebar, setOpenChatSideBar] = useState(false);
  const [cards, setCards] = React.useState<Content[]>([]);
  const [allCards, setAllCards] = React.useState<Content[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [selectedContents, setSelectedContents] = React.useState<number[]>([]);
  const [openBulkDeleteModal, setOpenBulkDeleteModal] = React.useState<boolean>(false);
  const handleSidebarToggle = () => {
    setOpenChatSideBar(false);
    setOpenSideBar(!openSearchSidebar);
  };
  const handleChatSidebarToggle = () => {
    setOpenSideBar(false);
    setOpenChatSideBar(!openChatSidebar);
  };
  const handleChatSidebarClose = () => {
    setOpenChatSideBar(false);
  };
  const handleSidebarClose = () => {
    setOpenChatSideBar(false);
    setOpenSideBar(false);
  };
  const sidebarOpen = openSearchSidebar || openChatSidebar;

  React.useEffect(() => {
    if (token) {
      const fetchTags = async () => {
        const data = await getTagList(token);
        setTags(data);
      };
      fetchTags();
    } else {
      setTags([]);
    }
    setEditAccess(userRole === "admin");
  }, [userRole, token]);

  const handleBulkDeleteModalClose = () => {
    setOpenBulkDeleteModal(false);
    setSelectedContents([]);
  };

  const handleDelete = async (selectedContents: number[]) => {
    // Archive in batches so we don't fire dozens of requests at once.
    const BATCH_SIZE = 20;
    let successCount = 0;
    let failedContentIds: number[] = [];

    try {
      for (let i = 0; i < selectedContents.length; i += BATCH_SIZE) {
        const batch = selectedContents.slice(i, i + BATCH_SIZE);

        await Promise.all(
          batch.map(async (content_id) => {
            try {
              await archiveContent(content_id, token!);
              successCount++;
              return { success: true, content_id };
            } catch (error) {
              console.error(`Failed to delete content ID ${content_id}:`, error);
              failedContentIds.push(content_id);
              return { success: false, content_id };
            }
          }),
        );
      }

      if (failedContentIds.length === 0) {
        setSnackMessage({
          message: `Successfully deleted ${successCount} content${
            successCount > 1 ? "s" : ""
          }`,
          color: "success",
        });
      } else {
        setSnackMessage({
          message: `Deleted ${successCount} content${
            successCount > 1 ? "s" : ""
          }, failed to delete ${failedContentIds.length}`,
          color: "warning",
        });
      }
    } catch (error) {
      console.error("Unexpected error during batch deletion:", error);
      setSnackMessage({
        message:
          "An unexpected error occurred during deletion. Please try again later.",
        color: "error",
      });
    } finally {
      // Leave the failed ones selected so the user can retry.
      setSelectedContents(failedContentIds);
      setOpenBulkDeleteModal(false);
      setRefreshKey((prevKey) => prevKey + 1);
    }
  };

  React.useEffect(() => {
    if (token) {
      getContentList({ token: token, skip: 0 })
        .then((data) => {
          setAllCards(data);
          // Filtering happens client-side: title/text match AND (no tag
          // filter OR the card has at least one of the chosen tags).
          const filteredData = data.filter((card: Content) => {
            const matchesSearchTerm =
              card.content_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
              card.content_text.toLowerCase().includes(searchTerm.toLowerCase());

            const matchesAnyTag = filterTags.some((fTag) =>
              card.content_tags.includes(fTag.tag_id),
            );

            return matchesSearchTerm && (filterTags.length === 0 || matchesAnyTag);
          });

          setCards(filteredData);
          setIsLoading(false);

          // The edit page leaves a message here before redirecting back.
          const message = localStorage.getItem("editPageSnackMessage");
          if (message) {
            setSnackMessage({
              message: message,
              color: "success",
            });
            localStorage.removeItem("editPageSnackMessage");
          }
        })
        .catch((error) => {
          const customError = error as CustomError;
          console.error("Failed to fetch content:", error);
          setSnackMessage({
            message:
              customError.message ||
              "Failed to fetch content. Please try refreshing the page.",
            color: "error",
          });
          setIsLoading(false);
        });
    } else {
      setCards([]);
      setIsLoading(false);
    }
  }, [searchTerm, filterTags, token, refreshKey]);

  return (
    <div className="flex min-h-0 flex-1">
      {/* On small screens an open test sidebar takes over the whole page */}
      <div
        className={cn(
          "h-full min-w-0 flex-1 px-4 pt-8 sm:px-8 md:pt-10",
          sidebarOpen && "hidden md:block",
        )}
      >
        <div className="mx-auto flex h-full w-full max-w-6xl flex-col">
          <header className="flex flex-col gap-2 pb-6">
            <h1 className="text-2xl font-semibold tracking-tight">
              Question Answering
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Add, edit, and test content for question-answering. Questions sent to the
              search service will retrieve results from here. Content limit is 50.{" "}
              <a
                href="https://docs.ask-a-question.com/latest/contact_us/"
                className="underline underline-offset-4 hover:text-foreground"
              >
                Contact us
              </a>{" "}
              for more.
            </p>
          </header>
          <CardsUtilityStrip
            editAccess={editAccess}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            cards={cards}
            tags={tags}
            selectedContents={selectedContents}
            setSelectedContents={setSelectedContents}
            filterTags={filterTags}
            setFilterTags={setFilterTags}
            setRefreshKey={setRefreshKey}
            handleDelete={() => {
              setOpenBulkDeleteModal(true);
            }}
          />
          <CardsGrid
            tags={tags}
            allCards={allCards}
            cards={cards}
            token={token}
            editAccess={editAccess}
            openSearchSidebar={openSearchSidebar}
            handleSidebarToggle={handleSidebarToggle}
            openChatSidebar={openChatSidebar}
            handleChatSidebarToggle={handleChatSidebarToggle}
            selectedContents={selectedContents}
            setSelectedContents={setSelectedContents}
            isLoading={isLoading}
            setRefreshKey={setRefreshKey}
          />
          <ConfirmDeleteModal
            open={openBulkDeleteModal}
            onClose={handleBulkDeleteModalClose}
            onConfirm={() => {
              handleDelete(selectedContents);
            }}
            selectedContentsCount={selectedContents.length}
          />
        </div>
      </div>
      {/* Sidebars stay mounted while hidden so a test chat survives closing */}
      <div
        className={cn(
          "h-full w-full shrink-0 md:w-5/12 lg:w-1/3",
          !openSearchSidebar && "hidden",
        )}
      >
        <SearchSidebar closeSidebar={handleSidebarClose} />
      </div>
      <div
        className={cn(
          "h-full w-full shrink-0 md:w-5/12 lg:w-1/3",
          !openChatSidebar && "hidden",
        )}
      >
        <ChatSideBar
          closeSidebar={handleChatSidebarClose}
          getResponse={(question: string, session_id) => {
            return session_id
              ? apiCalls.getChat(question, true, token!, session_id)
              : apiCalls.getChat(question, true, token!);
          }}
          setSnackMessage={(message: string) => {
            setSnackMessage({
              message: message,
              color: "error",
            });
          }}
        />
      </div>
    </div>
  );
};

const CardsUtilityStrip: React.FC<CardsUtilityStripProps> = ({
  editAccess,
  searchTerm,
  setSearchTerm,
  cards,
  tags,
  selectedContents,
  setSelectedContents,
  filterTags,
  setFilterTags,
  setRefreshKey,
  handleDelete,
}) => {
  const { token } = useAuth();
  const [openDownloadModal, setOpenDownloadModal] = React.useState<boolean>(false);
  const { setIsOpen: setOpenIndexHistoryModal } = useShowIndexingStatusStore();
  const [showContentModal, setShowContentModal] = React.useState(false);

  const { data: indexingStatus } = useGetIndexingStatus(token!);
  const { data: unvalidatedCardsCount } = useGetUnvalidatedCardsCount(token!);
  const { data: nextUnvalidatedCard } = useGetNextUnvalidatedCard(
    token!,
    showContentModal && unvalidatedCardsCount > 0,
  );

  const handleSelectAll = () => {
    const allContentIds = cards.map((card) => card.content_id!);
    setSelectedContents(allContentIds);
  };

  const handleDeSelectAll = () => {
    setSelectedContents([]);
  };

  return (
    <div className="flex w-full flex-wrap items-end justify-between gap-4 pb-4">
      {/* Left: search and tag filter */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-[220px]">
          <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        </div>
        <TagsFilter tags={tags} filterTags={filterTags} setFilterTags={setFilterTags} />
      </div>

      {/* Right: bulk actions while cards are selected, otherwise page actions */}
      {selectedContents.length > 0 ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {selectedContents.length} selected
          </span>
          <Button
            variant="outline"
            size="lg"
            onClick={handleSelectAll}
            disabled={!editAccess}
          >
            Select all
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={handleDeSelectAll}
            disabled={!editAccess}
          >
            Deselect all
          </Button>
          <Button
            variant="destructive"
            size="lg"
            onClick={handleDelete}
            disabled={!editAccess}
          >
            <IconTrash data-icon="inline-start" />
            Delete
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {unvalidatedCardsCount > 0 && (
            <>
              <Button
                variant="outline"
                size="lg"
                onClick={() => setShowContentModal(true)}
              >
                Validate cards
                <Badge variant="destructive">{unvalidatedCardsCount}</Badge>
              </Button>
              <ContentViewModal
                title={nextUnvalidatedCard?.content_title}
                text={nextUnvalidatedCard?.content_text}
                content_id={nextUnvalidatedCard?.content_id}
                display_number={nextUnvalidatedCard?.display_number}
                last_modified={nextUnvalidatedCard?.updated_datetime_utc}
                tags={[{ tag_id: 0, tag_name: "Unavailable" }]}
                positive_votes={nextUnvalidatedCard?.positive_votes}
                negative_votes={nextUnvalidatedCard?.negative_votes}
                open={showContentModal}
                onClose={() => setShowContentModal(false)}
                setRefreshKey={setRefreshKey}
                editAccess={editAccess}
                validation_mode={true}
                related_contents={nextUnvalidatedCard?.related_contents || []}
                onRelatedContentClick={() => {
                  setSnackMessage({
                    message: "Related contents cannot be viewed in validation mode",
                    color: "warning",
                  });
                }}
              />
            </>
          )}
          {typeof indexingStatus === "boolean" && (
            <>
              <Button
                variant="outline"
                size="lg"
                onClick={() => setOpenIndexHistoryModal(true)}
              >
                {indexingStatus === true && <Spinner data-icon="inline-start" />}
                {indexingStatus === true ? "Processing PDF" : "PDF upload status"}
              </Button>
              <IndexingStatusModal />
            </>
          )}
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="icon-lg"
                  aria-label="Download all contents"
                  disabled={!editAccess}
                  onClick={() => setOpenDownloadModal(true)}
                />
              }
            >
              <IconDownload />
            </TooltipTrigger>
            <TooltipContent>Download all contents</TooltipContent>
          </Tooltip>
          <AddButtonWithDropdown editAccess={editAccess} />
          <DownloadModal
            open={openDownloadModal}
            onClose={() => setOpenDownloadModal(false)}
            onFailedDownload={(error_message) => {
              setSnackMessage({
                message: error_message,
                color: "error",
              });
            }}
            onNoDataFound={() => {
              setSnackMessage({
                message: `No data to download`,
                color: "info",
              });
            }}
          />
        </div>
      )}
    </div>
  );
};

/**
 * Multi-select tag filter. Shows the first chosen tag as a chip and
 * "+N" for the rest, so the toolbar doesn't grow as tags are added.
 */
const TagsFilter: React.FC<TagsFilterProps> = ({ tags, filterTags, setFilterTags }) => {
  const anchor = useComboboxAnchor();
  return (
    <Combobox
      multiple
      autoHighlight
      items={tags}
      value={filterTags}
      onValueChange={(updatedTags) => setFilterTags(updatedTags as Tag[])}
      itemToStringLabel={(tag: Tag) => tag.tag_name}
      isItemEqualToValue={(a: Tag, b: Tag) => a.tag_id === b.tag_id}
    >
      <ComboboxChips ref={anchor} className="min-h-9 w-[240px] flex-nowrap bg-card">
        <ComboboxValue>
          {(values: Tag[]) => (
            <>
              {values.slice(0, 1).map((tag) => (
                <ComboboxChip key={tag.tag_id}>
                  <span className="max-w-24 truncate">{tag.tag_name}</span>
                </ComboboxChip>
              ))}
              {values.length > 1 && (
                <span className="shrink-0 text-xs text-muted-foreground">
                  +{values.length - 1}
                </span>
              )}
              <ComboboxChipsInput
                aria-label="Filter by tag"
                placeholder={values.length ? "" : "Filter by tag"}
                className="min-w-10"
              />
            </>
          )}
        </ComboboxValue>
      </ComboboxChips>
      <ComboboxContent anchor={anchor}>
        <ComboboxEmpty>No tags found</ComboboxEmpty>
        <ComboboxList>
          {(tag: Tag) => (
            <ComboboxItem key={tag.tag_id} value={tag}>
              <span className="break-words">{tag.tag_name}</span>
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
};

/** "New" button plus a dropdown for the bulk import options. */
const AddButtonWithDropdown: React.FC<{ editAccess: boolean }> = ({ editAccess }) => {
  const [openCSVModal, setOpenCSVModal] = useState(false);
  const [openPDFModal, setOpenPDFModal] = useState(false);

  return (
    <>
      {/* Split button: "New" opens the editor, the arrow opens the import menu */}
      <ButtonGroup aria-label="Add content">
        {editAccess ? (
          <Button size="lg" nativeButton={false} render={<Link href="/content/edit" />}>
            <IconPlus data-icon="inline-start" />
            New
          </Button>
        ) : (
          <Button size="lg" disabled>
            <IconPlus data-icon="inline-start" />
            New
          </Button>
        )}
        {/* Visible divider between the two halves (both are filled navy) */}
        <ButtonGroupSeparator className="bg-primary-foreground/30" />
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                size="icon-lg"
                aria-label="Import or generate cards"
                disabled={!editAccess}
              />
            }
          >
            <IconChevronDown />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-52">
            <DropdownMenuItem onClick={() => setOpenCSVModal(true)}>
              <IconFileTypeCsv />
              Import cards from CSV
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setOpenPDFModal(true)}>
              <IconFileTypePdf />
              Generate cards from PDF
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </ButtonGroup>
      <ImportFromCSVModal open={openCSVModal} onClose={() => setOpenCSVModal(false)} />
      <ImportFromPDFModal open={openPDFModal} onClose={() => setOpenPDFModal(false)} />
    </>
  );
};

const CardsGrid = ({
  tags,
  cards,
  allCards,
  token,
  editAccess,
  openSearchSidebar,
  handleSidebarToggle,
  openChatSidebar,
  handleChatSidebarToggle,
  selectedContents,
  setSelectedContents,
  isLoading,
  setRefreshKey,
}: CardsGridProps) => {
  const [page, setPage] = React.useState<number>(1);
  const [maxCardsPerPage, setMaxCardsPerPage] = useState(1);
  const [maxPages, setMaxPages] = React.useState<number>(
    Math.ceil(cards.length / maxCardsPerPage),
  );

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

  React.useEffect(() => {
    window.addEventListener("resize", calculateMaxCardsPerPage);
    return () => {
      window.removeEventListener("resize", calculateMaxCardsPerPage);
    };
  }, []);

  React.useEffect(() => {
    setMaxPages(Math.ceil(cards.length / maxCardsPerPage));
  }, [cards, maxCardsPerPage]);

  React.useEffect(() => {
    setPage(1);
  }, [cards]);

  const getRelatedContent = (content_ids: number[]) => {
    return allCards.filter((content) => content_ids.includes(content.content_id!));
  };

  const onSuccessfulArchive = () => {
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content removed successfully`,
      color: "success",
    });
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
                  Content you add here is what the search and chat services answer from.
                </EmptyDescription>
              </EmptyHeader>
              {editAccess && (
                <EmptyContent>
                  <Button nativeButton={false} render={<Link href="/content/edit" />}>
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
            style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
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
                        ? tags.filter((tag) => item.content_tags.includes(tag.tag_id))
                        : []
                    }
                    positive_votes={item.positive_votes}
                    negative_votes={item.negative_votes}
                    related_contents={getRelatedContent(item.related_contents_id)}
                    onSuccessfulArchive={onSuccessfulArchive}
                    onFailedArchive={(content_id: number, error_message: string) => {
                      setSnackMessage({
                        message: error_message,
                        color: "error",
                      });
                    }}
                    archiveContent={(content_id: number) => {
                      return archiveContent(content_id, token!);
                    }}
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

      {/* Page navigation and test sidebar launchers */}
      <div className="flex w-full flex-wrap items-center justify-between gap-4 pb-8">
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
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="lg"
            disabled={openSearchSidebar}
            onClick={handleSidebarToggle}
          >
            <IconPlayerPlay data-icon="inline-start" />
            Test search
          </Button>
          <Button
            variant="secondary"
            size="lg"
            disabled={openChatSidebar}
            onClick={handleChatSidebarToggle}
          >
            <IconPlayerPlay data-icon="inline-start" />
            Test chat
          </Button>
        </div>
      </div>
    </div>
  );
};

/** Bulk delete confirmation. The user must type "delete" to enable it. */
const ConfirmDeleteModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  selectedContentsCount: number;
}> = ({ open, onClose, onConfirm, selectedContentsCount }) => {
  const [confirmationText, setConfirmationText] = React.useState<string>("");
  const confirmed = confirmationText.toLowerCase() === "delete";

  const handleConfirm = () => {
    if (confirmed) {
      onConfirm();
      setConfirmationText("");
    }
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          setConfirmationText("");
          onClose();
        }
      }}
    >
      <AlertDialogContent className="text-sm">
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <IconTrash />
          </AlertDialogMedia>
          <AlertDialogTitle>Confirm deletion</AlertDialogTitle>
          <AlertDialogDescription>
            You are about to permanently delete{" "}
            <strong className="text-foreground">{selectedContentsCount}</strong> content
            {selectedContentsCount === 1 ? "" : "s"}.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <Alert variant="destructive">
          <IconAlertTriangle />
          <AlertDescription>This action cannot be undone.</AlertDescription>
        </Alert>
        <Field>
          <FieldLabel htmlFor="confirm-delete-input">
            Type <strong>delete</strong> to confirm
          </FieldLabel>
          <Input
            id="confirm-delete-input"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder="delete"
            autoComplete="off"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleConfirm();
            }}
          />
        </Field>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={handleConfirm}
            disabled={!confirmed}
          >
            <IconTrash data-icon="inline-start" />
            Delete items
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default CardsPage;
