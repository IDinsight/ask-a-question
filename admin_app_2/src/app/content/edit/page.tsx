"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { ChevronLeft } from "@mui/icons-material";
import { Button, CircularProgress, TextField, Typography } from "@mui/material";
import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";

interface Content extends EditContentBody {
  content_id: number | null;
  created_datetime_utc: string | null;
  updated_datetime_utc: string | null;
}

interface EditContentBody {
  content_title: string;
  content_text: string;
  content_language: string;
  content_metadata: Record<string, unknown>;
}

const AddEditContentPage = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;

  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  React.useEffect(() => {
    if (!content_id) {
      setIsLoading(false);
      return;
    } else {
      apiCalls.getContent(content_id).then((data) => {
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
    <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
      <Header content_id={content_id} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
      >
        <Layout.Spacer multiplier={2} />
        <ContentBox content={content} setContent={setContent} />
        <Layout.Spacer multiplier={1} />
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const ContentBox = ({
  content,
  setContent,
}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
}) => {
  const [isSaved, setIsSaved] = React.useState(true);
  const [saveError, setSaveError] = React.useState(false);
  const router = useRouter();
  const saveContent = async (content: Content) => {
    const body: EditContentBody = {
      content_title: content.content_title,
      content_text: content.content_text,
      content_language: content.content_language,
      content_metadata: content.content_metadata,
    };

    const promise =
      content.content_id === null
        ? apiCalls.addContent(body)
        : apiCalls.editContent(content.content_id, body);

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
      created_datetime_utc: null,
      updated_datetime_utc: null,
      content_title: "",
      content_text: "",
      content_language: "ENGLISH",
      content_metadata: {},
    };

    content
      ? setContent({ ...content, [key]: e.target.value })
      : setContent({ ...emptyContent, [key]: e.target.value });
    setIsSaved(false);
  };

  return (
    <Layout.FlexBox
      flexDirection={"column"}
      sx={{
        maxWidth: "800px",
        minWidth: "300px",
        border: 1,
        borderColor: appColors.darkGrey,
        borderRadius: 4,
        p: sizes.baseGap,
      }}
    >
      <LanguageButtonBar expandable={true} />
      <Layout.Spacer multiplier={1} />
      <Typography variant="body2">Title</Typography>
      <Layout.Spacer multiplier={0.5} />
      <TextField
        placeholder="Add a title"
        sx={{ backgroundColor: appColors.white }}
        value={content ? content.content_title : ""}
        onChange={(e) => handleChange(e, "content_title")}
      />
      <Layout.Spacer multiplier={2} />
      <Typography variant="body2">Content (max 2000 characters)</Typography>
      <Layout.Spacer multiplier={0.5} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ backgroundColor: appColors.white }}
      >
        <TextField
          multiline
          rows={15}
          placeholder="Add content"
          inputProps={{ maxLength: 2000 }}
          value={content ? content.content_text : ""}
          onChange={(e) => handleChange(e, "content_text")}
        />
      </Layout.FlexBox>
      <Layout.Spacer multiplier={1} />
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
            if (
              !content ||
              content.content_title === "" ||
              content.content_text === ""
            ) {
              alert("Please fill in both fields.");
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
  );
};

const Header = ({ content_id }: { content_id: number | null }) => {
  return (
    <Layout.FlexBox flexDirection="row" {...appStyles.alignItemsCenter}>
      <ChevronLeft
        style={{ cursor: "pointer" }}
        onClick={() => (window.location.href = "/content/")}
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
