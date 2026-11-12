"use client";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import { IconChevronLeft } from "@tabler/icons-react";

import { FullAccessComponent } from "@/components/common/ProtectedComponent";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  useContentListQuery,
  useContentQuery,
  useCreateTagMutation,
  useDeleteTagMutation,
  useSaveContentMutation,
  useTagListQuery,
} from "@/components/features/content/queries";
import { Content } from "@/components/features/content/types";
import { ContentBox, handleCustomError } from "./components/ContentBox";

/**
 * The /content/edit page (add a card, or edit one via ?content_id=). Owns:
 * - the content, tag and content-list queries and the save/tag mutations
 *   (see ../queries.ts);
 * - the card being edited and whether it has unsaved changes, which the back
 *   button and the form share.
 * ContentBox (the form) is presentational and gets everything through props.
 */
const ContentEditWrapper = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;
  const [content, setContent] = React.useState<Content | null>(null);
  const [openDiscardChangesModal, setOpenDiscardChangesModal] =
    React.useState(false);

  const [isSaved, setIsSaved] = React.useState(true);

  const router = useRouter();

  /* ---------- data ---------- */
  const contentQuery = useContentQuery(content_id);
  const tagList = useTagListQuery();
  const contentList = useContentListQuery();
  const createTag = useCreateTagMutation();
  const deleteTag = useDeleteTagMutation();
  const save = useSaveContentMutation();

  // Copy the fetched card into editable state once per content_id. Later
  // refetches (e.g. after saving) must not overwrite the user's edits.
  const [loadedId, setLoadedId] = React.useState<number | null>(null);
  if (contentQuery.data && loadedId !== content_id) {
    setLoadedId(content_id);
    setContent(contentQuery.data);
  }
  // As before, an existing card shows a spinner until it has loaded.
  const isLoading = content_id !== null && loadedId !== content_id;

  // Toast failed list loads (a side effect of the query result, not a fetch).
  React.useEffect(() => {
    if (!tagList.error) return;
    const errorMessage = "Error fetching tags";
    handleCustomError(tagList.error, errorMessage);
    console.error(errorMessage);
  }, [tagList.error]);
  React.useEffect(() => {
    if (!contentList.error) return;
    const errorMessage = "Error fetching contents";
    handleCustomError(contentList.error, errorMessage);
    console.error(errorMessage);
  }, [contentList.error]);

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <Spinner className="size-6" />
      </div>
    );
  }
  return (
    <FullAccessComponent>
      <div className="flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-8 md:py-10">
        <Header
          display_number={content?.display_number || null}
          onBack={() =>
            isSaved ? router.push("/content") : setOpenDiscardChangesModal(true)
          }
        />
        <ContentBox
          content={content}
          setContent={setContent}
          tags={tagList.data}
          contents={contentList.data}
          addTag={createTag.mutateAsync}
          deleteTag={deleteTag.mutateAsync}
          saveContent={(contentId, body) =>
            save.mutateAsync({ contentId, body })
          }
          isSaving={save.isPending}
          onSaved={(message) => {
            // The content list page shows this message after we redirect back.
            localStorage.setItem("editPageSnackMessage", message);
            router.push(`/content`);
          }}
          isSaved={isSaved}
          setIsSaved={setIsSaved}
        />
      </div>
      <DiscardChangesModal
        open={openDiscardChangesModal}
        onClose={() => {
          setOpenDiscardChangesModal(false);
        }}
        onConfirmDiscard={() => {
          router.push("/content");
        }}
      />
    </FullAccessComponent>
  );
};

const Header = ({
  display_number,
  onBack,
}: {
  display_number: number | null;
  onBack: () => void;
}) => {
  return (
    <div className="flex items-center gap-2">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Back to content"
        onClick={onBack}
      >
        <IconChevronLeft />
      </Button>
      <h1 className="text-2xl font-semibold tracking-tight">
        {display_number ? (
          <>
            Edit content{" "}
            <span className="text-muted-foreground">#{display_number}</span>
          </>
        ) : (
          "Add content"
        )}
      </h1>
    </div>
  );
};

const DiscardChangesModal = ({
  open,
  onClose,
  onConfirmDiscard,
}: {
  open: boolean;
  onClose: () => void;
  onConfirmDiscard: () => void;
}) => {
  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => !nextOpen && onClose()}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Discard changes?</AlertDialogTitle>
          <AlertDialogDescription>
            You have unsaved changes. Are you sure you want to discard them?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep editing</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onConfirmDiscard}>
            Discard
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
export default ContentEditWrapper;
