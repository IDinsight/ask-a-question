"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft } from "@mui/icons-material";
import { Autocomplete } from "@mui/material";

import { Button, CircularProgress, TextField, Typography } from "@mui/material";
import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";

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
interface Tag {
  tag_id: number;
  tag_name: string;
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
}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  getTagList: () => Promise<Tag[]>;
}) => {
  const [isSaved, setIsSaved] = React.useState(true);
  const [saveError, setSaveError] = React.useState(false);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [tags, setTags] = React.useState<Tag[]>([]);

  const [contentTags, setContentTags] = React.useState<Tag[]>([]);
  const [availableTags, setAvailableTags] = React.useState<Tag[]>([]);

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
                data.find((tag) => tag.tag_id === tag_id),
              )
            : [];
        setContentTags(
          defaultTags.filter((tag): tag is Tag => tag !== undefined),
        );
        setAvailableTags(data.filter((tag) => !defaultTags.includes(tag)));
      } catch (error) {
        console.error("Failed to fetch tags:", error);
      }
    };

    fetchTags();
  }, []);
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

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    key: keyof Content,
  ) => {
    const emptyContent: Content = {
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

    setIsTitleEmpty(false);
    setIsContentEmpty(false);

    content
      ? setContent({ ...content, [key]: e.target.value })
      : setContent({ ...emptyContent, [key]: e.target.value });
    setIsSaved(false);
  };
  const handleTagsChange = (
    event: React.SyntheticEvent,
    updatedTags: Tag[],
  ) => {
    setContentTags(updatedTags);
    setIsSaved(false);
    if (content) {
      setContent((prevContent: Content | null) => {
        return {
          ...prevContent!,
          content_tags: updatedTags.map((tag) => tag!.tag_id),
        };
      });
    }
    setAvailableTags(tags.filter((tag) => !updatedTags.includes(tag)));
  };

  return (
    <Layout.FlexBox>
      <Layout.Spacer multiplier={1} />
      <Autocomplete
        multiple
        limitTags={3}
        id="tags-autocomplete"
        options={availableTags}
        getOptionLabel={(option) => option!.tag_name}
        value={contentTags}
        onChange={handleTagsChange}
        renderInput={(params) => (
          <TextField
            {...params}
            variant="outlined"
            label="Tags"
            placeholder="Add Tags"
          />
        )}
        sx={{ width: "500px" }}
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
        <LanguageButtonBar expandable={true} />
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
                      `/content/?content_id=${content_id}&action=${actionType}`,
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
