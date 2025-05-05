"use client";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
import { ChevronLeft, Delete } from "@mui/icons-material";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import { Tag } from "../types";
import { LoadingButton } from "@mui/lab";
import { CustomError } from "@/utils/api";
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Snackbar,
  TextField,
  Typography,
} from "@mui/material";
import {
  createContent,
  createTag,
  deleteTag,
  editContent,
  getContent,
  getContentList,
  getTagList,
} from "../api";
import { RelatedContentsAutoComplete } from "../components/RelatedContentsAutoComplete";
import { Content, EditContentBody } from "../types";

const AddEditContentPage = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;
  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [openDiscardChangesModal, setOpenDiscardChangesModal] = React.useState(false);

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
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
          width: "100%",
        }}
      >
        <CircularProgress />
      </div>
    );
  }
  return (
    <FullAccessComponent>
      <Layout.FlexBox
        sx={{
          flexDirection: "column",
          marginTop: 2,
          marginBottom: 1,
          p: sizes.doubleBaseGap,
          gap: sizes.baseGap,
        }}
      >
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
      </Layout.FlexBox>
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
  const [availableTags, setAvailableTags] = React.useState<Tag[]>([]);
  const [openDeleteModal, setOpenDeleteModal] = React.useState(false);
  const [tagToDelete, setTagToDelete] = React.useState<Tag | null>(null);
  const filter = createFilterOptions<Tag>();
  const [snackMessage, setSnackMessage] = React.useState<string | null>(null);
  const [contents, setContents] = React.useState<Content[]>([]);
  const [selectedContents, setSelectedContents] = React.useState<Content[]>([]);
  const { token } = useAuth();
  const [inputVal, setInputVal] = React.useState<string>("");
  const [highlightedOption, setHighlightedOption] = React.useState<Tag | null>();
  const [isSaving, setIsSaving] = React.useState(false);
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
        setContentTags(defaultTags.filter((tag): tag is Tag => tag !== undefined));
        setAvailableTags(data.filter((tag) => !defaultTags.includes(tag)));
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
                data.find((content: Content) => content.content_id === content_id),
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
        console.error("Content quota reached. Please contact support for assistance.");
        console.error("Error details:", customError.message);
        setErrorMessage(customError.message);
        setSaveError(true);
        return null;
      } else {
        console.error("Failed to save content. Please try again later.", error);
        setErrorMessage(
          customError.message || "Failed to save content. Please try again later.",
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
      {
        content.content_id
          ? setMainPageSnackMessage("Content edited successfully")
          : setMainPageSnackMessage("Content created successfully");
      }
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

    setAvailableTags(tags.filter((tag) => !updatedTags.includes(tag)));
  };
  const handleNewTag = (tag: string) => {
    const match = tag.match(/"([^"]*)"/);

    tag = match ? match[1] : tag;
    const isTagExists = tags.filter((t) => t.tag_name === tag);
    if (isTagExists.length == 0) {
      const data = addTag(tag).then((data: Tag) => {
        handleTagsChange([...contentTags, data]);
        setRefreshKey((prevKey) => prevKey + 1);
      });
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

  return (
    <Layout.FlexBox>
      <Dialog
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        aria-labelledby="confirm-delete-dialog-title"
        aria-describedby="confirm-delete-dialog-description"
      >
        <DialogTitle id="confirm-delete-dialog-title">
          Are you sure you want to delete tag {tagToDelete?.tag_name}?
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-delete-dialog-description">
            This tag will be removed from all contents and will no longer be an option.
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
          <Button onClick={() => setOpenDeleteModal(false)} color="primary">
            Cancel
          </Button>
          <Button
            onClick={() => handleDeleteTag()}
            autoFocus
            variant="contained"
            color="error"
            startIcon={<Delete />}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
      <Layout.Spacer />
      <Layout.FlexBox
        sx={{
          maxWidth: "md",
          minWidth: "sm",
          border: 0.5,
          borderColor: appColors.outline,
          borderRadius: 2,
          p: sizes.baseGap,
        }}
      >
        <Layout.Spacer multiplier={0.5} />
        <Typography variant="body1">Title</Typography>
        <Layout.Spacer multiplier={0.5} />
        <TextField
          required
          placeholder="Add a title (required)"
          inputProps={{ maxLength: 150 }}
          variant="outlined"
          error={isTitleEmpty}
          helperText={isTitleEmpty ? "Should not be empty" : " "}
          sx={{
            "& .MuiInputBase-root": { backgroundColor: appColors.white },
          }}
          value={content ? content.content_title : ""}
          onChange={(e) => handleChange(e, "content_title")}
        />
        <Typography variant="body1">Content</Typography>
        <Layout.Spacer multiplier={0.5} />
        <TextField
          required
          placeholder="Add content (required)"
          inputProps={{ maxLength: 2000 }}
          multiline
          rows={15}
          variant="outlined"
          error={isContentEmpty}
          helperText={isContentEmpty ? "Should not be empty" : " "}
          sx={{
            "& .MuiInputBase-root": { backgroundColor: appColors.white },
          }}
          value={content ? content.content_text : ""}
          onChange={(e) => handleChange(e, "content_text")}
        />
        <Layout.Spacer multiplier={0.25} />
        <Autocomplete
          selectOnFocus
          clearOnBlur
          handleHomeEndKeys
          multiple
          limitTags={3}
          id="tags-autocomplete"
          options={availableTags}
          getOptionLabel={(option) => option!.tag_name}
          noOptionsText="No tags found. Start typing to create one."
          value={contentTags}
          onChange={(event: React.SyntheticEvent, updatedTags: Tag[]) => {
            handleTagsChange(updatedTags);
          }}
          onHighlightChange={(event, option) => {
            setHighlightedOption(option);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              variant="outlined"
              label="Tags (optional)"
              placeholder="Find or create tags"
              onChange={(event) => setInputVal(event.target.value)}
              onKeyDown={(event) => {
                if (
                  !highlightedOption ||
                  highlightedOption.tag_name.startsWith('Add "')
                ) {
                  if (
                    event.key === "Enter" &&
                    inputVal &&
                    !availableTags.some(
                      (tag) => tag.tag_name.toUpperCase() === inputVal.toUpperCase(),
                    ) &&
                    !contentTags.some(
                      (tag) => tag.tag_name.toUpperCase() === inputVal.toUpperCase(),
                    )
                  ) {
                    event.preventDefault();

                    handleNewTag(inputVal);
                  }
                }
              }}
              InputProps={{
                ...params.InputProps,
                style: { backgroundColor: "white" },
              }}
            />
          )}
          filterOptions={(options, params) => {
            const filtered = filter(options, params);
            const { inputValue } = params;
            const isExisting = options.some(
              (option) => inputValue.toUpperCase() === option.tag_name,
            );

            const isSelected = contentTags.some(
              (tag) => inputValue.toUpperCase() === tag.tag_name,
            );

            if (inputValue !== "" && !isExisting && !isSelected) {
              filtered.push({ tag_id: 0, tag_name: `Create "${inputValue}"` });
            }

            return filtered;
          }}
          renderOption={(props, option) => {
            const { key, ...newProps } =
              props as React.HTMLAttributes<HTMLLIElement> & {
                key: React.Key;
              };
            const { onKeyDown, ...rest } = newProps;
            if (
              option.tag_name &&
              !availableTags.some(
                (tag) => tag.tag_name.toUpperCase() === option.tag_name.toUpperCase(),
              ) &&
              !contentTags.some(
                (tag) => tag.tag_name.toUpperCase() === option.tag_name.toUpperCase(),
              )
            ) {
              return (
                <li key={key} {...rest}>
                  <Button fullWidth onClick={() => handleNewTag(option.tag_name)}>
                    {option.tag_name}
                  </Button>
                </li>
              );
            }
            return (
              <li
                key={option.tag_id}
                {...rest}
                style={{
                  justifyContent: "space-between",
                }}
              >
                {option.tag_name}
                <IconButton
                  onClick={(e) => {
                    e.stopPropagation();
                    openDeleteConfirmModal(option);
                  }}
                >
                  <Delete fontSize="small" color="secondary" />
                </IconButton>
              </li>
            );
          }}
          sx={{ maxWidth: "500px" }}
          isOptionEqualToValue={(option, value) =>
            value.tag_name === option.tag_name || value.tag_name === ""
          }
        />
        <Layout.Spacer multiplier={1.25} />
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
        <Layout.Spacer multiplier={1.5} />
        <Layout.FlexBox flexDirection="row" sx={{ justifyContent: "space-between" }}>
          <LoadingButton
            variant="contained"
            disabled={isSaved}
            color="primary"
            sx={[{ width: "5%" }]}
            loading={isSaving}
            onClick={() => {
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
            }}
          >
            Save
          </LoadingButton>
          {saveError ? (
            <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
              {errorMessage}
            </Alert>
          ) : null}
          <Snackbar
            open={snackMessage !== null}
            autoHideDuration={6000}
            onClose={() => {
              setSnackMessage(null);
            }}
          >
            <Alert
              onClose={() => {
                setSnackMessage(null);
              }}
              severity={
                snackMessage &&
                typeof snackMessage === "string" &&
                snackMessage.toLowerCase().includes("successfully")
                  ? "success"
                  : "error"
              }
              variant="filled"
              sx={{ width: "100%" }}
            >
              {typeof snackMessage === "string"
                ? snackMessage
                : "An Error occurred, please try again"}
            </Alert>
          </Snackbar>
        </Layout.FlexBox>
      </Layout.FlexBox>
    </Layout.FlexBox>
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
    <Layout.FlexBox flexDirection="row" {...appStyles.alignItemsCenter}>
      <ChevronLeft style={{ cursor: "pointer" }} onClick={onBack} />
      <Layout.Spacer multiplier={1} horizontal />
      {display_number ? (
        <>
          <Typography variant="h5">Edit Content</Typography>
          <Layout.Spacer multiplier={2} horizontal />
          <Typography variant="h5">{`\u2022`}</Typography>
          <Layout.Spacer multiplier={2} horizontal />
          <Typography variant="h5">#{display_number}</Typography>
        </>
      ) : (
        <Typography variant="h5">Add Content</Typography>
      )}
    </Layout.FlexBox>
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
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="alert-dialog-discard-change-title"
      aria-describedby="alert-dialog-discard-change-description"
    >
      <DialogTitle id="alert-dialog-discard-change-title">Discard Changes</DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-discard-change-description">
          You have unsaved changes. Are you sure you want to discard them?
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose} color="primary" variant="contained">
          Cancel
        </Button>
        <Button onClick={onConfirmDiscard} color="error" autoFocus>
          Discard
        </Button>
      </DialogActions>
    </Dialog>
  );
};
export default AddEditContentPage;
