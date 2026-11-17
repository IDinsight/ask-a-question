"use client";
import React, { useMemo, useState } from "react";

import type { Content, Tag } from "@/components/features/content/types";
import { toast } from "@/components/ui/toast";
import { cn } from "cn";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { CardsGrid } from "./components/CardsGrid";
import { CardsUtilityStrip } from "./components/CardsUtilityStrip";
import { ChatSideBar } from "./components/ChatSideBar";
import { ConfirmDeleteModal } from "./components/ConfirmDeleteModal";
import { ContentViewModal } from "./components/ContentModal";
import { DownloadModal } from "./components/DownloadModal";
import { ImportFromCSVModal } from "./components/ImportFromCSVModal";
import { ImportFromPDFModal } from "./components/ImportFromPDFModal";
import { IndexingStatusModal } from "./components/IndexingStatusModal";
import { SearchSidebar } from "./components/SearchSidebar";
import {
  useArchiveContentMutation,
  useBulkArchiveContentMutation,
  useBulkUploadContentsMutation,
  useChatMutation,
  useContentListQuery,
  useDownloadContentsMutation,
  useIndexingHistoryQuery,
  useIndexingStatusQuery,
  useNextUnvalidatedCardQuery,
  usePostDocumentToIndexMutation,
  useResponseFeedbackMutation,
  useSearchMutation,
  useTagListQuery,
  useUnvalidatedCountQuery,
  useValidateContentMutation,
} from "./queries";
import { useShowIndexingStatusStore } from "./store";

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

/**
 * Stable fallbacks while queries load. A fresh `[]` each render would change
 * the filtered `cards` identity every render, and CardsGrid resets its page
 * whenever `cards` changes.
 */
const NO_CONTENTS: Content[] = [];
const NO_TAGS: Tag[] = [];

/** Message shown by the PDF status dialog when its data fails to load. */
const INDEXING_HISTORY_ERROR = "Failed to load indexing status.";

/**
 * The /content page. Owns:
 * - every content query/mutation (see ./queries.ts);
 * - search term and tag filter (cards are filtered client-side);
 * - selected cards, which dialog is open, and which test sidebar is open.
 * Child components are presentational and get everything through props.
 * The PDF status dialog's open flag stays in the zustand store (./store.ts).
 */
const ContentWrapper = () => {
  const { token, userRole } = useAuth();
  const editAccess = userRole === "admin";

  /* ---------- UI state ---------- */
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const [filterTags, setFilterTags] = React.useState<Tag[]>([]);
  const [openSearchSidebar, setOpenSideBar] = useState(false);
  const [openChatSidebar, setOpenChatSideBar] = useState(false);
  const [selectedContents, setSelectedContents] = React.useState<number[]>([]);
  const [openBulkDeleteModal, setOpenBulkDeleteModal] =
    React.useState<boolean>(false);
  const [showValidateModal, setShowValidateModal] = useState(false);
  const [openDownloadModal, setOpenDownloadModal] = useState(false);
  const [openCSVModal, setOpenCSVModal] = useState(false);
  const [openPDFModal, setOpenPDFModal] = useState(false);
  const { isOpen: openIndexHistoryModal, setIsOpen: setOpenIndexHistoryModal } =
    useShowIndexingStatusStore();

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

  /* ---------- data ---------- */
  const contentList = useContentListQuery();
  const tagList = useTagListQuery();
  const indexingStatus = useIndexingStatusQuery();
  const unvalidatedCount = useUnvalidatedCountQuery();
  const nextUnvalidated = useNextUnvalidatedCardQuery(
    showValidateModal && (unvalidatedCount.data ?? 0) > 0,
  );
  const indexingHistory = useIndexingHistoryQuery(openIndexHistoryModal);

  const archive = useArchiveContentMutation();
  const bulkArchive = useBulkArchiveContentMutation();
  const validate = useValidateContentMutation();
  const download = useDownloadContentsMutation();
  const csvUpload = useBulkUploadContentsMutation();
  const pdfUpload = usePostDocumentToIndexMutation();
  const search = useSearchMutation();
  const chat = useChatMutation();
  const feedback = useResponseFeedbackMutation();

  const allCards = contentList.data ?? NO_CONTENTS;
  const tags = tagList.data ?? NO_TAGS;
  // Only show the spinner on the first load (refetches keep the old cards).
  const isLoading = !!token && contentList.isPending;

  // Filtering happens client-side: title/text match AND (no tag
  // filter OR the card has at least one of the chosen tags).
  const cards = useMemo(
    () =>
      allCards.filter((card: Content) => {
        const matchesSearchTerm =
          card.content_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          card.content_text.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesAnyTag = filterTags.some((fTag) =>
          card.content_tags.includes(fTag.tag_id),
        );

        return matchesSearchTerm && (filterTags.length === 0 || matchesAnyTag);
      }),
    [allCards, searchTerm, filterTags],
  );

  // Side effects of the list load (not data fetching): report a failed load,
  // and show the message the edit page leaves here before redirecting back.
  const listError = contentList.error;
  React.useEffect(() => {
    if (!listError) return;
    const customError = listError as unknown as CustomError;
    console.error("Failed to fetch content:", listError);
    setSnackMessage({
      message:
        customError.message ||
        "Failed to fetch content. Please try refreshing the page.",
      color: "error",
    });
  }, [listError]);

  React.useEffect(() => {
    if (!contentList.isSuccess) return;
    const message = localStorage.getItem("editPageSnackMessage");
    if (message) {
      setSnackMessage({ message: message, color: "success" });
      localStorage.removeItem("editPageSnackMessage");
    }
  }, [contentList.isSuccess]);

  /* ---------- handlers ---------- */
  const handleBulkDeleteModalClose = () => {
    setOpenBulkDeleteModal(false);
    setSelectedContents([]);
  };

  const handleDelete = (contentIds: number[]) => {
    bulkArchive.mutate(contentIds, {
      onSuccess: ({ successCount, failedContentIds }) => {
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
        // Leave the failed ones selected so the user can retry.
        setSelectedContents(failedContentIds);
      },
      onError: (error) => {
        console.error("Unexpected error during batch deletion:", error);
        setSnackMessage({
          message:
            "An unexpected error occurred during deletion. Please try again later.",
          color: "error",
        });
        setSelectedContents([]);
      },
      onSettled: () => setOpenBulkDeleteModal(false),
    });
  };

  const nextCard = nextUnvalidated.data;

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
              Add, edit, and test content for question-answering. Questions sent
              to the search service will retrieve results from here. Content
              limit is 50.{" "}
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
            handleDelete={() => {
              setOpenBulkDeleteModal(true);
            }}
            openSearchSidebar={openSearchSidebar}
            handleSidebarToggle={handleSidebarToggle}
            openChatSidebar={openChatSidebar}
            handleChatSidebarToggle={handleChatSidebarToggle}
            unvalidatedCardsCount={unvalidatedCount.data}
            onValidateClick={() => setShowValidateModal(true)}
            indexingStatus={indexingStatus.data}
            onIndexingStatusClick={() => setOpenIndexHistoryModal(true)}
            onDownloadClick={() => setOpenDownloadModal(true)}
            onImportCSVClick={() => setOpenCSVModal(true)}
            onImportPDFClick={() => setOpenPDFModal(true)}
          />
          <CardsGrid
            tags={tags}
            allCards={allCards}
            cards={cards}
            editAccess={editAccess}
            selectedContents={selectedContents}
            setSelectedContents={setSelectedContents}
            isLoading={isLoading}
            archiveContent={archive.mutateAsync}
            onSuccessfulArchive={() => {
              setSnackMessage({
                message: `Content removed successfully`,
                color: "success",
              });
            }}
            onFailedArchive={(_content_id: number, error_message: string) => {
              setSnackMessage({
                message: error_message,
                color: "error",
              });
            }}
          />
          <ConfirmDeleteModal
            open={openBulkDeleteModal}
            onClose={handleBulkDeleteModalClose}
            onConfirm={() => {
              handleDelete(selectedContents);
            }}
            selectedContentsCount={selectedContents.length}
          />

          {/* Dialogs opened from the toolbar */}
          {(unvalidatedCount.data ?? 0) > 0 && (
            <ContentViewModal
              title={nextCard?.content_title}
              text={nextCard?.content_text}
              content_id={nextCard?.content_id}
              display_number={nextCard?.display_number}
              last_modified={nextCard?.updated_datetime_utc}
              tags={[{ tag_id: 0, tag_name: "Unavailable" }]}
              positive_votes={nextCard?.positive_votes}
              negative_votes={nextCard?.negative_votes}
              open={showValidateModal}
              onClose={() => setShowValidateModal(false)}
              onApprove={(content_id) => validate.mutate(content_id)}
              onReject={(content_id) => archive.mutate(content_id)}
              editAccess={editAccess}
              validation_mode={true}
              related_contents={nextCard?.related_contents || []}
              onRelatedContentClick={() => {
                setSnackMessage({
                  message:
                    "Related contents cannot be viewed in validation mode",
                  color: "warning",
                });
              }}
            />
          )}
          {typeof indexingStatus.data === "boolean" && (
            <IndexingStatusModal
              open={openIndexHistoryModal}
              onClose={() => setOpenIndexHistoryModal(false)}
              indexEntries={indexingHistory.data ?? []}
              loading={indexingHistory.isFetching}
              error={indexingHistory.isError ? INDEXING_HISTORY_ERROR : null}
            />
          )}
          <DownloadModal
            open={openDownloadModal}
            onClose={() => setOpenDownloadModal(false)}
            fetchContents={download.mutateAsync}
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
          <ImportFromCSVModal
            open={openCSVModal}
            onClose={() => setOpenCSVModal(false)}
            uploadCsv={csvUpload.mutateAsync}
          />
          <ImportFromPDFModal
            open={openPDFModal}
            onClose={() => setOpenPDFModal(false)}
            postDocument={pdfUpload.mutateAsync}
            onCheckStatus={() => setOpenIndexHistoryModal(true)}
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
        <SearchSidebar
          closeSidebar={handleSidebarClose}
          search={(question, generateLLMResponse) =>
            search.mutateAsync({ question, generateLLMResponse })
          }
          sendFeedback={feedback.mutateAsync}
        />
      </div>
      <div
        className={cn(
          "h-full w-full shrink-0 md:w-5/12 lg:w-1/3",
          !openChatSidebar && "hidden",
        )}
      >
        <ChatSideBar
          closeSidebar={handleChatSidebarClose}
          getResponse={(question: string, session_id?: number) =>
            chat.mutateAsync({ question, sessionId: session_id })
          }
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

export default ContentWrapper;
