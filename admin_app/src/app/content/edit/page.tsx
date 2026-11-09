"use client";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import {
  IconAlertCircle,
  IconChevronLeft,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";

import { FullAccessComponent } from "@/components/ProtectedComponent";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Button } from "@/components/ui/button";
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
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/utils/auth";
import { CustomError } from "@/utils/api";
import {
  createContent,
  createTag,
  deleteTag,
  editContent,
  getContent,
  getContentList,
  getTagList,
} from "../api";
import { RelatedContentsAutoComplete } from "../_components/RelatedContentsAutoComplete";
import { Content, EditContentBody, Tag } from "../types";

/** A tag option; `isNew` marks the "Create …" entry for a tag that doesn't exist yet. */
type TagOption = Tag & { isNew?: boolean };

/**
 * Show a toast. Messages mentioning "successfully" show as success,
 * everything else as an error (same rule the old Snackbar used).
 */
const setSnackMessage = (message: string) => {
  toast.add({
    title: message,
    type: message.toLowerCase().includes("successfully") ? "success" : "error",
  });
};

const AddEditContentPage = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;
  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [openDiscardChangesModal, setOpenDiscardChangesModal] =
    React.useState(false);

  const [isSaved, setIsSaved] = React.useState(true);

  const router = useRouter();
  const { token } = useAuth();

  React.useEffect(() => {
    if (!content_id) {
      setIsLoading(false);
      return;
    } else {
      getContent(content_id, token!).then((data) => {
        setContent(data);
        setIsLoading(false);
      });
    }
  }, [content_id]);

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
          getTagList={() => {
            return getTagList(token!);
          }}
          addTag={(tag: string) => {
            return createTag(tag, token!);
          }}
          deleteTag={(tag_id: number) => {
            return deleteTag(tag_id, token!);
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

const ContentBox = ({
  content,
  setContent,
  getTagList,
  addTag,
  deleteTag,
  isSaved,
  setIsSaved,
}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  getTagList: () => Promise<Tag[]>;
  addTag: (tag: string) => Promise<Tag>;
  deleteTag: (tag_id: number) => Promise<[]>;
  isSaved: boolean;
  setIsSaved: React.Dispatch<React.SetStateAction<boolean>>;
}) => {
  const [saveError, setSaveError] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [contentTags, setContentTags] = React.useState<Tag[]>([]);
  const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
  const [tagToDelete, setTagToDelete] = React.useState<Tag | null>(null);
  const [contents, setContents] = React.useState<Content[]>([]);
  const [selectedContents, setSelectedContents] = React.useState<Content[]>([]);
  const { token } = useAuth();
  const [tagQuery, setTagQuery] = React.useState<string>("");
  const [isSaving, setIsSaving] = React.useState(false);
  const tagsAnchor = useComboboxAnchor();

  const handleCustomError = (error: unknown, defaultMessage: string) => {
    const customError = error as CustomError;
    let errorMessage = defaultMessage;
    if (customError && customError.message) {
      errorMessage =
        typeof customError.message === "string"
          ? customError.message
          : "An unknown error occurred";
    }
    setSnackMessage(errorMessage);
  };
  // The content list page shows this message after we redirect back.
  const setMainPageSnackMessage = (message: string): void => {
    localStorage.setItem("editPageSnackMessage", message);
  };

  const router = useRouter();
  React.useEffect(() => {
    const fetchTags = async () => {
      try {
        const data = await getTagList();
        setTags(data);
        const defaultTags =
          content && content.content_tags.length > 0
            ? content.content_tags.map((tag_id) =>
                data.find((tag) => tag.tag_id === tag_id),
              )
            : [];
        setContentTags(
          defaultTags.filter((tag): tag is Tag => tag !== undefined),
        );
      } catch (error) {
        const customError = error as CustomError;
        let errorMessage = "Error fetching tags";
        handleCustomError(customError, errorMessage);
        console.error(errorMessage);
      }
    };

    fetchTags();
  }, [refreshKey]);

  React.useEffect(() => {
    getContentList({
      token: token!,
    })
      .then((data) => {
        setContents(data);
        const defaultContents =
          content && content.related_contents_id.length > 0
            ? content.related_contents_id.map((content_id) =>
                data.find(
                  (content: Content) => content.content_id === content_id,
                ),
              )
            : [];
        setSelectedContents(
          defaultContents.filter(
            (content): content is Content => content !== undefined,
          ),
        );
      })
      .catch((error) => {
        const customError = error as CustomError;
        let errorMessage = "Error fetching contents";
        handleCustomError(customError, errorMessage);
        console.error(errorMessage);
      });
  }, [refreshKey]);

  const saveContent = async (content: Content): Promise<number | null> => {
    setIsSaving(true);

    const body: EditContentBody = {
      content_title: content.content_title,
      content_text: content.content_text,
      content_metadata: content.content_metadata,
      content_tags: content.content_tags,
      related_contents_id: content.related_contents_id,
    };

    try {
      const result =
        content.content_id === null
          ? await createContent(body, token!)
          : await editContent(content.content_id, body, token!);
      setIsSaved(true);
      setSaveError(false);
      return result.content_id;
    } catch (error: Error | any) {
      const customError = error as CustomError;
      if (error.status === 403) {
        // 403 here means the workspace's content quota is used up.
        console.error(
          "Content quota reached. Please contact support for assistance.",
        );
        console.error("Error details:", customError.message);
        setErrorMessage(customError.message);
        setSaveError(true);
        return null;
      } else {
        console.error("Failed to save content. Please try again later.", error);
        setErrorMessage(
          customError.message ||
            "Failed to save content. Please try again later.",
        );
        setSaveError(true);
        return null;
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveContent = async (content: Content) => {
    const content_id = await saveContent(content);
    if (content_id) {
      setMainPageSnackMessage(
        content.content_id
          ? "Content edited successfully"
          : "Content created successfully",
      );
      router.push(`/content`);
    }
  };

  function createEmptyContent(contentTags: Tag[]): Content {
    return {
      content_id: null,
      created_datetime_utc: "",
      updated_datetime_utc: "",
      positive_votes: 0,
      negative_votes: 0,
      display_number: 0,
      content_title: "",
      content_text: "",
      content_tags: contentTags.map((tag) => tag!.tag_id),
      content_metadata: {},
      related_contents_id: [],
    };
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    key: keyof Content,
  ) => {
    const emptyContent = createEmptyContent(contentTags);

    setIsTitleEmpty(false);
    setIsContentEmpty(false);

    content
      ? setContent({ ...content, [key]: e.target.value })
      : setContent({ ...emptyContent, [key]: e.target.value });
    setIsSaved(false);
  };

  const handleTagsChange = (updatedTags: Tag[]) => {
    setContentTags(updatedTags);
    setIsSaved(false);
    if (content) {
      setContent((prevContent: Content | null) => {
        return {
          ...prevContent!,
          content_tags: updatedTags.map((tag) => tag!.tag_id),
        };
      });
    } else {
      setContent(createEmptyContent(updatedTags));
    }
  };

  const handleNewTag = (tag: string) => {
    const isTagExists = tags.some(
      (t) => t.tag_name.toUpperCase() === tag.toUpperCase(),
    );
    if (!isTagExists) {
      addTag(tag)
        .then((data: Tag) => {
          handleTagsChange([...contentTags, data]);
          setRefreshKey((prevKey) => prevKey + 1);
        })
        .catch((error) =>
          handleCustomError(error, `Failed to create tag "${tag}"`),
        );
    } else {
      setSnackMessage(`Tag "${tag}" already exists`);
    }
  };

  const openDeleteConfirmModal = (tag: Tag) => {
    setTagToDelete(tag);
    setOpenDeleteModal(true);
  };
  const handleDeleteTag = () => {
    if (tagToDelete) {
      deleteTag(tagToDelete.tag_id).then(() => {
        setRefreshKey((prevKey) => prevKey + 1);
        setOpenDeleteModal(false);
        handleTagsChange(
          contentTags.filter((tag) => tag.tag_id !== tagToDelete.tag_id),
        );
        setSnackMessage(`Tag "${tagToDelete.tag_name}" deleted successfully`);
        setTagToDelete(null);
      });
    }
  };

  // Offer a "Create …" option when the typed text doesn't match any tag.
  const trimmedTagQuery = tagQuery.trim();
  const tagQueryMatchesExisting = tags.some(
    (tag) => tag.tag_name.toUpperCase() === trimmedTagQuery.toUpperCase(),
  );
  const tagOptions: TagOption[] =
    trimmedTagQuery && !tagQueryMatchesExisting
      ? [...tags, { tag_id: -1, tag_name: trimmedTagQuery, isNew: true }]
      : tags;

  // Keeps clicks on the per-tag delete button from also toggling the option.
  const stopEvent = (event: React.SyntheticEvent) => event.stopPropagation();

  const handleSave = () => {
    if (!content) {
      setIsTitleEmpty(true);
      setIsContentEmpty(true);
    } else if (content.content_title === "") {
      setIsTitleEmpty(true);
    } else if (content.content_text === "") {
      setIsContentEmpty(true);
    } else {
      handleSaveContent(content);
    }
  };

  return (
    <>
      <AlertDialog
        open={openDeleteModal}
        onOpenChange={(nextOpen) => !nextOpen && setOpenDeleteModal(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-destructive/10 text-destructive">
              <IconTrash />
            </AlertDialogMedia>
            <AlertDialogTitle>
              Delete tag &quot;{tagToDelete?.tag_name}&quot;?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This tag will be removed from all contents and will no longer be
              an option. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDeleteTag}
              autoFocus
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <section className="border bg-card p-6">
        <FieldGroup className="gap-5">
          <Field data-invalid={isTitleEmpty || undefined}>
            <FieldLabel htmlFor="content-title" className="text-sm">
              Title
            </FieldLabel>
            <Input
              id="content-title"
              required
              maxLength={150}
              placeholder="Add a title (required)"
              aria-invalid={isTitleEmpty || undefined}
              className="h-9 text-sm md:text-sm"
              value={content ? content.content_title : ""}
              onChange={(e) => handleChange(e, "content_title")}
            />
            {isTitleEmpty && <FieldError>Title should not be empty</FieldError>}
          </Field>

          <Field data-invalid={isContentEmpty || undefined}>
            <FieldLabel htmlFor="content-text" className="text-sm">
              Content
            </FieldLabel>
            <Textarea
              id="content-text"
              required
              maxLength={10000}
              rows={15}
              placeholder="Add content (required)"
              aria-invalid={isContentEmpty || undefined}
              className="min-h-72 text-sm md:text-sm"
              value={content ? content.content_text : ""}
              onChange={(e) => handleChange(e, "content_text")}
            />
            {isContentEmpty && (
              <FieldError>Content should not be empty</FieldError>
            )}
          </Field>

          <Field className="max-w-[500px]">
            <FieldLabel htmlFor="content-tags-input" className="text-sm">
              Tags (optional)
            </FieldLabel>
            <Combobox
              multiple
              autoHighlight
              items={tagOptions}
              value={contentTags}
              inputValue={tagQuery}
              onInputValueChange={setTagQuery}
              onValueChange={(next) => {
                const updated = next as TagOption[];
                // Picking the "Create …" option creates the tag instead.
                const newTag = updated.find((tag) => tag.isNew);
                if (newTag) {
                  handleNewTag(newTag.tag_name);
                  setTagQuery("");
                  return;
                }
                handleTagsChange(updated);
              }}
              itemToStringLabel={(tag: TagOption) => tag.tag_name}
              isItemEqualToValue={(a: TagOption, b: TagOption) =>
                a.tag_id === b.tag_id
              }
            >
              <ComboboxChips ref={tagsAnchor} className="min-h-9">
                <ComboboxValue>
                  {(values: Tag[]) => (
                    <>
                      {values.map((tag) => (
                        <ComboboxChip key={tag.tag_id}>
                          <span className="max-w-40 truncate">
                            {tag.tag_name}
                          </span>
                        </ComboboxChip>
                      ))}
                      <ComboboxChipsInput
                        id="content-tags-input"
                        placeholder={values.length ? "" : "Find or create tags"}
                      />
                    </>
                  )}
                </ComboboxValue>
              </ComboboxChips>
              <ComboboxContent anchor={tagsAnchor}>
                <ComboboxEmpty>
                  No tags found. Start typing to create one.
                </ComboboxEmpty>
                <ComboboxList>
                  {(tag: TagOption) =>
                    tag.isNew ? (
                      <ComboboxItem key="__new__" value={tag}>
                        <IconPlus />
                        Create &quot;{tag.tag_name}&quot;
                      </ComboboxItem>
                    ) : (
                      <ComboboxItem key={tag.tag_id} value={tag}>
                        <span className="min-w-0 flex-1 break-words">
                          {tag.tag_name}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          aria-label={`Delete tag ${tag.tag_name}`}
                          className="pointer-events-auto text-muted-foreground hover:text-destructive"
                          onPointerDown={stopEvent}
                          onPointerUp={stopEvent}
                          onMouseDown={stopEvent}
                          onMouseUp={stopEvent}
                          onClick={(event) => {
                            event.stopPropagation();
                            event.preventDefault();
                            openDeleteConfirmModal(tag);
                          }}
                        >
                          <IconTrash />
                        </Button>
                      </ComboboxItem>
                    )
                  }
                </ComboboxList>
              </ComboboxContent>
            </Combobox>
          </Field>

          <RelatedContentsAutoComplete
            contents={
              content && content.content_id
                ? contents.filter((c) => c.content_id !== content.content_id)
                : contents
            }
            selectedContents={selectedContents}
            handleContentChange={(value: Content[]) => {
              setSelectedContents(value);
              if (content) {
                setContent((prevContent: Content | null) => {
                  return {
                    ...prevContent!,
                    related_contents_id: value
                      .map((content) => content.content_id)
                      .filter((id): id is number => id !== null),
                  };
                });
              }
              setIsSaved(false);
            }}
          />
        </FieldGroup>

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <Button
            size="lg"
            className="h-10 px-5 text-sm"
            disabled={isSaved || isSaving}
            onClick={handleSave}
          >
            {isSaving && <Spinner data-icon="inline-start" />}
            Save
          </Button>
          {saveError && (
            <Alert variant="destructive" className="w-auto flex-1">
              <IconAlertCircle />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
        </div>
      </section>
    </>
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
export default AddEditContentPage;
