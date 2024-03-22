"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft } from "@mui/icons-material";
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Typography
} from "@mui/material";
import { } from "@mui/material";

import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";

export interface Content extends EditContentBody {
  content_text_id: number | null;
  created_datetime_utc: string;
  updated_datetime_utc: string;
}

interface EditContentBody {
  content_title: string;
  content_text: string;
  language_id: number;
  content_id: number | null
  content_metadata: Record<string, unknown>;
}

const AddEditContentPage = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;
  const content_text_id = Number(searchParams.get("content_text_id")) || null;

  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  const { token } = useAuth();
  React.useEffect(() => {
    if (!content_text_id) {
      setIsLoading(false);
      return;
    } else {
      apiCalls.getContent(content_text_id, token!).then((data) => {
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
        <Header content_id={content_text_id} />
        <Layout.FlexBox
          flexDirection={"column"}
          sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
        >
          <Layout.Spacer multiplier={2} />
          <ContentBox content={content} setContent={setContent} content_id={content_id} />
          <Layout.Spacer multiplier={1} />
        </Layout.FlexBox>
      </Layout.FlexBox>
    </FullAccessComponent>
  );
};

const ContentBox = ({
  content,
  setContent,
  content_id

}: {
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  content_id: number | null;
}) => {
  const [isSaved, setIsSaved] = React.useState(false);
  const [saveError, setSaveError] = React.useState(false);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [showModal, setShowModal] = React.useState(false);
  const [newContentId, setNewContentId] = React.useState<number | null>(null);


  const [selectedLanguageId, setSelectedLanguageId] = React.useState<number>(content?.language_id || 1);
  const { token } = useAuth();

  const router = useRouter();
  const saveContent = async (content: Content, content_id: number | null) => {
    const body: EditContentBody = {
      content_title: content.content_title,
      content_text: content.content_text,
      language_id: content.language_id,
      content_id: content_id,
      content_metadata: content.content_metadata,
    };

    const promise = apiCalls.addContent(body, token!)


    const result = promise
      .then((data) => {
        setIsSaved(true);
        setSaveError(false);
        setShowModal(true);
        setNewContentId(data.content_id);
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
      content_text_id: null,
      created_datetime_utc: "",
      updated_datetime_utc: "",
      content_title: "",
      content_text: "",
      language_id: selectedLanguageId,
      content_id: content_id,
      content_metadata: {},
    };


    setIsTitleEmpty(false);
    setIsContentEmpty(false);

    content
      ? setContent({ ...content, [key]: e.target.value })
      : setContent({ ...emptyContent, [key]: e.target.value });
    setIsSaved(false);
  };

  const handleLanguageSelect = (language_id: number) => {
    setContent((prevContent) => {
      if (prevContent === null) {
        // If prevContent is null, initialize it as needed
        return {
          content_text_id: null,
          created_datetime_utc: "",
          updated_datetime_utc: "",
          content_title: "",
          content_text: "",
          language_id: language_id,
          content_id: null,
          content_metadata: {},
        };
      } else {
        return {
          ...prevContent,
          content_text: "",
          content_title: "",
          language_id: language_id,
        };
      }
    });
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
        borderRadius: 4,
        p: sizes.baseGap,
      }}
    >
      <LanguageButtonBar
        expandable={true}
        onLanguageSelect={handleLanguageSelect}
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
      <Layout.Spacer multiplier={0.25} />
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
            if (!content) {
              setIsTitleEmpty(true);
              setIsContentEmpty(true);
            } else if (content.content_title === "") {
              setIsTitleEmpty(true);
            } else if (content.content_text === "") {
              setIsContentEmpty(true);
            } else {
              const handleSaveContent = async (content: Content, content_id: number | null) => {

                await saveContent(content, content_id);

              };
              handleSaveContent(content, content_id);
            }
          }
          }
        >
          Save
        </Button>
        <Dialog open={showModal} onClose={() => setShowModal(false)}>
          <DialogTitle>New content successfully added</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Would you like to add a new language version for this content?
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setShowModal(false);
              router.push(`/content/?content_id=${content_id}&action=view`);
            }}>No</Button>
            <Button onClick={() => {
              setShowModal(false);

              const targetContentId = newContentId || content_id;
              router.push(`/content/edit?content_id=${targetContentId}&action=add`);
            }} autoFocus>
              Yes
            </Button>
          </DialogActions>
        </Dialog>
        {saveError ? (
          <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
            Failed to save content.
          </Alert>
        ) : null}
        {isSaved ? (
          <Alert variant="outlined" severity="success" sx={{ px: 3, py: 0 }}>
            Successfully added new content
          </Alert>
        ) : null}
      </Layout.FlexBox>
    </Layout.FlexBox >


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
