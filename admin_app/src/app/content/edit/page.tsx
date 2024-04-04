"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft } from "@mui/icons-material";
import { Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField, Typography } from "@mui/material";
import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";

export interface Content extends EditContentBody {

  created_datetime_utc: string;
  updated_datetime_utc: string;
}

interface EditContentBody {
  content_id: number | null;
  content_title: string;
  content_text: string;
  language_id: number;
  content_metadata: Record<string, unknown>;
}

const AddEditContentPage = () => {
  const searchParams = useSearchParams();
  const content_id = Number(searchParams.get("content_id")) || null;
  const language_id = Number(searchParams.get("language_id")) || null;
  const [contentData, setContentData] = React.useState<{ [key: number]: Content }>({});
  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [showDialog, setShowDialog] = React.useState(false);
  const { token } = useAuth();
  React.useEffect(() => {
    if (!content_id) {
      setIsLoading(false);
      return;
    } else {
      apiCalls.getContent(content_id, null, token!).then((data) => {
        const contentDic: { [key: number]: Content } = data.reduce(
          (acc: { [key: number]: Content }, currentContent: Content) => {
            acc[currentContent.language_id] = currentContent;
            return acc;
          },
          {} as { [key: string]: Content }
        );
        setContentData(contentDic);
        setContent(language_id !== null ? contentDic[language_id] : null);
      });
      setIsLoading(false);
    }
  }, [content_id, token, refreshKey]);
  const handleSaveSuccess = () => {
    setRefreshKey(prevKey => prevKey + 1);
    setShowDialog(true);
  };
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
            contentId={content_id!}
            content={content}
            setContent={setContent}
            contentData={contentData}
            setContentData={setContentData}
            languageId={language_id!}
            onSaveSuccess={handleSaveSuccess} />
          <SavedContentDialog
            showModal={showDialog}
            setShowModal={setShowDialog}
            contentId={content_id ? content_id : null}
            languageId={content?.language_id || null}
            newContentId={content?.content_id || null} />

          <Layout.Spacer multiplier={1} />
        </Layout.FlexBox>
      </Layout.FlexBox>
    </FullAccessComponent>
  );
};

const ContentBox = ({
  contentId,
  content,
  setContent,
  contentData,
  setContentData,
  languageId,
  onSaveSuccess,
}: {
  contentId: number;
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  contentData: { [key: number]: Content };
  setContentData: React.Dispatch<React.SetStateAction<{ [key: number]: Content }>>;
  languageId: number;
  onSaveSuccess: () => void;

}) => {
  const [isSaved, setIsSaved] = React.useState(true);
  const [saveError, setSaveError] = React.useState(false);
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);

  const { token } = useAuth();

  const saveContent = async (content: Content) => {
    const body: EditContentBody = {
      content_id: content.content_id,
      content_title: content.content_title,
      content_text: content.content_text,
      language_id: content.language_id,
      content_metadata: content.content_metadata,
    };
    const promise =
      content.content_id === null
        ? apiCalls.addContent(body, token!)
        : apiCalls.editContent(content.content_id, content.language_id, body, token!);

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
      content_id: content?.content_id || contentId,
      created_datetime_utc: "",
      updated_datetime_utc: "",
      content_title: "",
      content_text: "",
      language_id: content?.language_id || 0,
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
    setContent(contentData[language_id]);
  };
  const handleNewLanguageSelect = (language_id: number) => {
    const emptyContent: Content = {
      content_id: content!.content_id || contentId,
      created_datetime_utc: "",
      updated_datetime_utc: "",
      content_title: "",
      content_text: "",
      language_id: language_id,
      content_metadata: {},
    };
    setContentData((prevContentData) => {
      const updatedContentData = { ...prevContentData, [language_id]: emptyContent };
      setContent(updatedContentData[language_id]);
      return updatedContentData;
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
        defaultLanguageId={content?.language_id || languageId}
        enabledLanguages={Object.keys(contentData).map(Number)}
        onMenuItemSelect={handleNewLanguageSelect}
        isEdit={true}
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
              const handleSaveContent = async (content: Content) => {
                const content_id = await saveContent(content);
                if (content_id) {
                  onSaveSuccess();

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
const SavedContentDialog = ({
  showModal,
  setShowModal,
  contentId,
  newContentId,
  languageId
}: {
  showModal: boolean;
  setShowModal: (show: boolean) => void;
  contentId: number | null;
  newContentId: number | null;
  languageId: number | null;
}) => {
  const router = useRouter();

  const getDialogTitle = () => {
    return contentId == null
      ? `New content #${newContentId} successfully added`
      : `Content #${contentId} successfully edited`;
  };
  const handleClose = () => {
    setShowModal(false);
  };

  const handleNo = () => {
    handleClose();
    router.push(`/content/?content_id=${contentId}&action=edit`);
  };

  const handleYes = () => {
    handleClose();

    const targetContentId = newContentId || contentId;
    router.push(
      `/content/edit` +
      `?content_id=${targetContentId}` +
      `&action=edit` +
      `&language_id=${languageId}`
    );
  };

  return (
    <Dialog open={showModal} onClose={handleClose}>
      <DialogTitle>{getDialogTitle()}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Would you like to add/edit a language version for this content?
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleNo}>No</Button>
        <Button onClick={handleYes} autoFocus>
          Yes
        </Button>
      </DialogActions>
    </Dialog>
  );
};
export default AddEditContentPage;
