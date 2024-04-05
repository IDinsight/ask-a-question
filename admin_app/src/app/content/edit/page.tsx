"use client";
import { DeleteContentModal } from "@/components/ContentModal";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { FullAccessComponent } from "@/components/ProtectedComponent";
import { appColors, appStyles, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ChevronLeft, Delete } from "@mui/icons-material";
import { Button, CircularProgress, IconButton, Snackbar, TextField, Typography } from "@mui/material";
import Alert from "@mui/material/Alert";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";

export interface Content extends EditContentBody {
  content_text_id: number | null;
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
  const [contentId, setContentId] = React.useState<number | null>(content_id);
  const [languageId, setLanguageId] = React.useState<number | null>(language_id);
  const [content, setContent] = React.useState<Content | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [reloadTrigger, setReloadTrigger] = React.useState(0);
  const { token, accessLevel } = useAuth();
  const [snackMessage, setSnackMessage] = React.useState<string | null>(
    null,
  );
  const getSnackMessage = (
    action: string,
    content_id: number | null,
    language_id: number | null,
  ): string | null => {
    if (action === "delete") {
      return `Content #${content_id} with language_id:#${language_id} deleted successfully`;
    }
    else if (action == "edit" || action == "add") {
      return `Content #${content_id} with language_id:#${language_id} ${action}ed successfully`;
    }
    else {
      return null;
    }
  };
  React.useEffect(() => {
    if (!contentId) {
      setIsLoading(false);
      return;
    } else {
      apiCalls.getContent(contentId, null, token!).then((data) => {
        const contentDic: { [key: number]: Content } = data.reduce(
          (acc: { [key: number]: Content }, currentContent: Content) => {
            acc[currentContent.language_id] = currentContent;
            return acc;
          },
          {} as { [key: string]: Content }
        );
        setContentData(contentDic);
        setContent(languageId !== null ? contentDic[languageId] : null);
      });
      setIsLoading(false);
    }
  }, [contentId, token, reloadTrigger]);
  const handleSaveSuccess = (content: Content, action: string) => {
    setContentId(content.content_id);
    setLanguageId(content.language_id);
    setReloadTrigger(prev => prev + 1);
    setSnackMessage(getSnackMessage(action, content.content_id, content.language_id));


  };
  const handleDeleteSuccess = (content_id: number, language_id: number | null) => {
    setReloadTrigger(prev => prev + 1);
    setSnackMessage(getSnackMessage("delete", content_id, language_id));
    if (language_id) {
      setContentData(prevContentData => {
        const updatedContentData = { ...prevContentData };
        delete updatedContentData[language_id];
        if (Object.keys(updatedContentData).length === 0) {
          const router = useRouter();
          setTimeout(() => router
            .push(`/content?content_id=${content_id}&action=delete`), 0);
        }
        setLanguageId(Object.keys(updatedContentData).map(Number)[0]);
        return updatedContentData;
      });
    }
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
        <Header content_id={contentId} />
        <Layout.FlexBox
          flexDirection={"column"}
          sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
        >
          <Layout.Spacer multiplier={2} />
          <ContentBox
            contentId={contentId!}
            content={content}
            setContent={setContent}
            contentData={contentData}
            setContentData={setContentData}
            languageId={language_id!}
            onSaveSuccess={handleSaveSuccess}
            onDeleteSuccess={handleDeleteSuccess}
            setReloadTrigger={setReloadTrigger}
          />

          <Layout.Spacer multiplier={1} />
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
              severity="success"
              variant="filled"
              sx={{ width: "100%" }}
            >
              {snackMessage}
            </Alert>
          </Snackbar>
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
  onDeleteSuccess,
  setReloadTrigger
}: {
  contentId: number;
  content: Content | null;
  setContent: React.Dispatch<React.SetStateAction<Content | null>>;
  contentData: { [key: number]: Content };
  setContentData: React.Dispatch<React.SetStateAction<{ [key: number]: Content }>>;
  languageId: number;
  onSaveSuccess: (content: Content, action: string) => void;
  onDeleteSuccess: (content_id: number, language_id: number | null) => void;
  setReloadTrigger: React.Dispatch<React.SetStateAction<number>>;
}) => {
  const [isSaved, setIsSaved] = React.useState(true);
  const [saveError, setSaveError] = React.useState(false);
  const [errorText, setErrorText] = React.useState<string>("");
  const [isTitleEmpty, setIsTitleEmpty] = React.useState(false);
  const [isContentEmpty, setIsContentEmpty] = React.useState(false);
  const [openDeleteModal, setOpenDeleteModal] = React.useState<boolean>(false);
  const { token, accessLevel } = useAuth();
  const editAccess = accessLevel === "fullaccess";

  const saveContent = async (content: Content) => {
    const body: EditContentBody = {
      content_id: content.content_id,
      content_title: content.content_title,
      content_text: content.content_text,
      language_id: content.language_id,
      content_metadata: content.content_metadata,
    };
    if (body.language_id === 0) {
      setErrorText("Please select a language");
      setSaveError(true);
      return null;
    }
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

      content_text_id: content?.content_text_id || 0,
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
      content_text_id: 0,
      content_id: content?.content_id || contentId,
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
  const handleDeleteClick = () => {
    if (content) {
      if (content.content_text_id && content.content_text_id > 0) {
        setOpenDeleteModal(true)
      }
      else {
        setReloadTrigger(prev => prev + 1);
      }
    }

  }
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
        getLanguageList={() => {
          return apiCalls.getLanguageList(token!);
        }}
        onLanguageSelect={handleLanguageSelect}
        defaultLanguageId={content?.language_id || languageId}
        enabledLanguages={Object.keys(contentData).map(Number)}
        onMenuItemSelect={handleNewLanguageSelect}
        isEdit={true}
      />
      <Layout.Spacer multiplier={1} />
      <Layout.FlexBox
        {...appStyles.alignItemsCenter}
        flexDirection={"row"}
        justifyContent="space-between"
      >
        <Typography variant="body2">Title</Typography>
        <IconButton
          disabled={!editAccess}
          aria-label="delete"
          size="small"
          onClick={handleDeleteClick}
        >

          <Delete fontSize="inherit" />
        </IconButton>
      </Layout.FlexBox>
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
                const action = content.content_id === null ? "add" : "edit";
                if (content_id) {
                  if (content.content_id === null) {
                    content.content_id = content_id;
                  }
                  setContent(content);
                  onSaveSuccess(content, action);

                }
              };
              handleSaveContent(content);
            }
          }}
        >
          Save
        </Button>
        <Layout.Spacer horizontal multiplier={1} />
        {saveError ? (
          <Alert variant="outlined" severity="error" sx={{ px: 3, py: 0 }}>
            {errorText ? errorText : "Failed to save content"}
          </Alert>
        ) : null}
        <DeleteContentModal
          content_id={content?.content_id!}
          language_id={content?.language_id!}
          open={openDeleteModal}
          onClose={() => setOpenDeleteModal(false)}
          onSuccessfulDelete={onDeleteSuccess}
          onFailedDelete={(content_id: number, language_id: number | null) => {
            setErrorText(
              `Failed to delete content #${content_id} with language_id: #${language_id}`,
            );
            setSaveError(true);
          }}
          deleteContent={(content_id: number, language_id: number | null) => {
            return apiCalls.deleteContent(content_id, language_id, token!);
          }}
        />
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
        onClick={() => (router.push("/content"))}
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
