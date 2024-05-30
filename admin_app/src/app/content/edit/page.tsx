"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft } from "@mui/icons-material";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";

import { Button, CircularProgress, TextField, Typography } from "@mui/material";
import Alert from "@mui/material/Alert";
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
        <Header content_id={content_id} />
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
          />
          <Layout.Spacer multiplier={1} />
        </Layout.FlexBox>
      </Layout.FlexBox>
    </FullAccessComponent>
  );
};

const ContentBox = ({
  content,
  setContent,
  getTagList,
  addTag,
}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  getTagList: () => Promise<Tag[]>;
  addTag: (tag: string) => Promise<Tag>;
}) => {
  const [isSaved, setIsSaved] = React.useState(true);
  const [saveError, setSaveError] = React.useState(false);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [contentTags, setContentTags] = React.useState<Tag[]>([]);
  const [availableTags, setAvailableTags] = React.useState<Tag[]>([]);
  const filter = createFilterOptions<Tag>();

  const { token } = useAuth();

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
      content_tags: contentTags.map((tag) => tag.tag_id),
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
    if (match) {
      tag = match[1];
      const data = addTag(tag).then((data: Tag) => {
        handleTagsChange([...contentTags, data]);
        setRefreshKey((prevKey) => prevKey + 1);
      });
    }
  };
  return (
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
      <LanguageButtonBar expandable={true} />
      <Layout.Spacer multiplier={2} />
      <Autocomplete
        multiple
        limitTags={3}
        id="tags-autocomplete"
        options={availableTags}
        getOptionLabel={(option) => option!.tag_name}
        value={contentTags}
        onChange={(event, updatedTags) => {
          handleTagsChange(updatedTags);
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            variant="outlined"
            label="Tags"
            placeholder="Add Tags"
          />
        )}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);

          // Add "add tag" option if the text entry does not exist in the list of tags
          const { inputValue } = params;
          const isExisting = options.some(
            (option) => inputValue === option.tag_name
          );
          if (inputValue !== "" && !isExisting) {
            filtered.push({ tag_id: 0, tag_name: `Add "${inputValue}"` });
          }

          return filtered;
        }}
        renderOption={(props, option) => {
          // If an option was added, render it as a button
          if (option.tag_name) {
            return (
              <li {...props}>
                <Button fullWidth onClick={() => handleNewTag(option.tag_name)}>
                  {option.tag_name}
                </Button>
              </li>
            );
          }
          return <li {...props}>{option.tag_name}</li>;
        }}
        sx={{ width: "500px" }}
      />
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
        <Button
          variant="contained"
          disabled={isSaved}
          color="primary"
          sx={[{ width: "5%" }]}
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
        </Button>
        {saveError ? (
          <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
            Failed to save content.
          </Alert>
        ) : null}
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const Header = ({ content_id }: { content_id: number | null }) => {
  const router = useRouter();

  return (
    <Layout.FlexBox flexDirection="row" {...appStyles.alignItemsCenter}>
      <ChevronLeft
        style={{ cursor: "pointer" }}
        onClick={() => (content_id ? router.back() : router.push("/content"))}
      />
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

export default AddEditContentPage;
