"use client";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft } from "@mui/icons-material";
import { LoadingButton } from "@mui/lab";
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Snackbar,
  TextField,
  Typography,
} from "@mui/material";
import Alert from "@mui/material/Alert";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import { Tag } from "../page";

export interface Content extends EditContentBody {
  content_id: number | null;
  positive_votes: number;
  negative_votes: number;
  created_datetime_utc: string;
  updated_datetime_utc: string;
}

interface EditContentBody {
  content_title: string;
  content_text: string;
  content_language: string;
  content_tags: number[];
  content_metadata: Record<string, unknown>;
}

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
      apiCalls.getContent(content_id, token!).then((data) => {
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
          height: "100vh",
          width: "100%",
        }}
      >
        <CircularProgress />
      </div>
    );
  }
  return (
    <FullAccessComponent>
      <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
        <Header
          content_id={content_id}
          onBack={() =>
            isSaved ? router.push("/content") : setOpenDiscardChangesModal(true)
          }
        />
        <Layout.FlexBox
          flexDirection={"column"}
          sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
        >
          <Layout.Spacer multiplier={2} />
          <ContentBox
            content={content}
            setContent={setContent}
            getTagList={() => {
              return apiCalls.getTagList(token!);
            }}
            addTag={(tag: string) => {
              return apiCalls.createTag(tag, token!);
            }}
            isSaved={isSaved}
            setIsSaved={setIsSaved}
          />
          <Layout.Spacer multiplier={1} />
        </Layout.FlexBox>
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
  isSaved,
  setIsSaved,
}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  getTagList: () => Promise<Tag[]>;
  addTag: (tag: string) => Promise<Tag>;
  isSaved: boolean;
  setIsSaved: React.Dispatch<React.SetStateAction<boolean>>;
}) => {
  const [saveError, setSaveError] = React.useState(false);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [contentTags, setContentTags] = React.useState<Tag[]>([]);
  const [availableTags, setAvailableTags] = React.useState<Tag[]>([]);
  const filter = createFilterOptions<Tag>();
  const [snackMessage, setSnackMessage] = React.useState<string | null>(null);

  const { token } = useAuth();
  const [inputVal, setInputVal] = React.useState<string>("");
  const [highlightedOption, setHighlightedOption] =
    React.useState<Tag | null>();
  const [isSaving, setIsSaving] = React.useState(false);

  const router = useRouter();
  React.useEffect(() => {
    const fetchTags = async () => {
      try {
        const data = await getTagList();
        setTags(data);
        const defaultTags =
          content && content.content_tags.length > 0
            ? content.content_tags.map((tag_id) =>
                data.find((tag) => tag.tag_id === tag_id)
              )
            : [];
        setContentTags(
          defaultTags.filter((tag): tag is Tag => tag !== undefined)
        );
        setAvailableTags(data.filter((tag) => !defaultTags.includes(tag)));
      } catch (error) {
        console.error("Failed to fetch tags:", error);
      }
    };

    fetchTags();
  }, [refreshKey]);
  const saveContent = async (content: Content) => {
    setIsSaving(true);
    const body: EditContentBody = {
      content_title: content.content_title,
      content_text: content.content_text,
      content_language: content.content_language,
      content_metadata: content.content_metadata,
      content_tags: content.content_tags,
    };

    const promise =
      content.content_id === null
        ? apiCalls.createContent(body, token!)
        : apiCalls.editContent(content.content_id, body, token!);

    const result = promise
      .then((data) => {
        setIsSaved(true);
        setSaveError(false);
        return data.content_id;
      })
      .catch((error: Error) => {
        console.error("Error processing content:", error);
        setSaveError(true);
        return null;
      })
      .finally(() => {
        setIsSaving(false);
      });

    return await result;
  };
  function createEmptyContent(contentTags: Tag[]): Content {
    return {
      content_id: null,
      created_datetime_utc: "",
      updated_datetime_utc: "",
      positive_votes: 0,
      negative_votes: 0,
      content_title: "",
      content_text: "",
      content_tags: contentTags.map((tag) => tag!.tag_id),
      content_language: "ENGLISH",
      content_metadata: {},
    };
  }
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    key: keyof Content
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
  return (
    <Layout.FlexBox>
      <Layout.Spacer multiplier={1} />
      <Autocomplete
        autoSelect
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
            label="Tags"
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
                    (tag) =>
                      tag.tag_name.toUpperCase() === inputVal.toUpperCase()
                  ) &&
                  !contentTags.some(
                    (tag) =>
                      tag.tag_name.toUpperCase() === inputVal.toUpperCase()
                  )
                ) {
                  event.preventDefault();
                  handleNewTag(inputVal);
                }
              }
            }}
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const { inputValue } = params;
          const isExisting = options.some(
            (option) => inputValue.toUpperCase() === option.tag_name
          );

          const isSelected = contentTags.some(
            (tag) => inputValue.toUpperCase() === tag.tag_name
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
              (tag) =>
                tag.tag_name.toUpperCase() === option.tag_name.toUpperCase()
            ) &&
            !contentTags.some(
              (tag) =>
                tag.tag_name.toUpperCase() === option.tag_name.toUpperCase()
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
            <li key={option.tag_id} {...rest}>
              {option.tag_name}
            </li>
          );
        }}
        sx={{ width: "500px" }}
        isOptionEqualToValue={(option, value) =>
          value.tag_name === option.tag_name || value.tag_name === ""
        }
      />
      <Layout.Spacer multiplier={2} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{
          maxWidth: "800px",
          minWidth: "300px",
          border: 1,
          borderColor: appColors.darkGrey,
          backgroundColor: appColors.lightGrey,
          borderRadius: 2,
          p: sizes.baseGap,
        }}
      >
        {/* <LanguageButtonBar expandable={true} /> */}
        <Layout.Spacer multiplier={1} />
        <Typography variant="body2">Title</Typography>
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
        <Typography variant="body2">Content</Typography>
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
        <Layout.FlexBox
          flexDirection="row"
          sx={{ justifyContent: "space-between" }}
        >
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
                const handleSaveContent = async (content: Content) => {
                  const content_id = await saveContent(content);
                  if (content_id) {
                    const actionType = content.content_id ? "edit" : "add";
                    router.push(
                      `/content/?content_id=${content_id}&action=${actionType}`
                    );
                  }
                };
                handleSaveContent(content);
              }
            }}
          >
            Save
          </LoadingButton>
          {saveError ? (
            <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
              Failed to save content.
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
              severity="error"
              variant="filled"
              sx={{ width: "100%" }}
            >
              {snackMessage}
            </Alert>
          </Snackbar>
        </Layout.FlexBox>
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const Header = ({
  content_id,
  onBack,
}: {
  content_id: number | null;
  onBack: () => void;
}) => {
  return (
    <Layout.FlexBox flexDirection="row" {...appStyles.alignItemsCenter}>
      <ChevronLeft style={{ cursor: "pointer" }} onClick={onBack} />
      <Layout.Spacer multiplier={1} horizontal />
      {content_id ? (
        <>
          <Typography variant="h5">Edit Content</Typography>
          <Layout.Spacer multiplier={2} horizontal />
          <Typography variant="h5">{`\u2022`}</Typography>
          <Layout.Spacer multiplier={2} horizontal />
          <Typography variant="h5">#{content_id}</Typography>
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
      <DialogTitle id="alert-dialog-discard-change-title">
        Discard Changes
      </DialogTitle>
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
