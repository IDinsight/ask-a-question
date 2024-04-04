import { appColors, appStyles, sizes } from "@/utils";
import {
  Close,
  Delete,
  Edit,
  RemoveRedEye,
  ThumbDown,
  ThumbUp,
} from "@mui/icons-material";
import { Alert, Box, Button, Fade, IconButton, Modal, Snackbar, Typography } from "@mui/material";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "next/link";
import React from "react";

import LanguageButtonBar from "./LanguageButtonBar";
import { Layout } from "./Layout";
import { Content } from "@/app/content/edit/page";
import { useRouter } from "next/router";


const ContentViewModal = ({
  content_id,
  defaultLanguageId,
  getContentData,
  getLanguageList,
  deleteLanguageVersion,
  open,
  onClose,
  editAccess,
}: {
  content_id: number;
  defaultLanguageId: number;
  getContentData: (content_id: number) => Promise<any>;
  getLanguageList: () => Promise<any>;
  deleteLanguageVersion:
  (content_id: number, language_id: number | null) => Promise<any>;
  open: boolean;
  onClose: () => void;
  editAccess: boolean;
}) => {
  const [contentData, setContentData] = React.useState<{ [key: number]: any }>({});
  const [content, setContent] = React.useState<Content | null>(null);
  const [enabledLanguages, setEnabledLanguages] = React.useState<number[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [openDeleteModal, setOpenDeleteModal] = React.useState<boolean>(false);
  const [reloadTrigger, setReloadTrigger] = React.useState(0);

  const getSnackMessage = (
    content_id: number | null,
    language_id: number | null,
  ): string | null => {
    return `Content #${content_id} with language_id:#${language_id} deleted successfully`;
  };
  const [snackMessage, setSnackMessage] = React.useState<string | null>(
    null,
  );
  const handleLanguageSelect = (language_id: number) => {
    setContent(contentData[language_id]);
  };
  React.useEffect(() => {
    const fetchData = async () => {
      if (open) {
        setLoading(true);
        setError(null);
        try {
          getContentData(content_id).then((data) => {
            const contentDic: { [key: number]: Content } = data.reduce(
              (acc: { [key: number]: Content }, currentContent: Content) => {
                acc[currentContent.language_id] = currentContent;
                return acc;
              },
              {} as { [key: string]: Content }
            );
            setContentData(contentDic);
            setEnabledLanguages(Object.keys(contentDic).map(Number))
            setContent(
              contentDic[defaultLanguageId] ? contentDic[defaultLanguageId] :
                Object.values(contentDic)[0]);
          });
          setLoading(false);
        } catch (err) {
          setError((err as Error).message || "Something went wrong");
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [open, content_id, reloadTrigger]);
  const onSuccessfulDelete = (content_id: number, language_id: number | null) => {
    setLoading(true);
    setReloadTrigger(prev => prev + 1);
    setSnackMessage(getSnackMessage(content_id, language_id));
    if (language_id) {
      setContentData(prevContentData => {
        const updatedContentData = { ...prevContentData };
        delete updatedContentData[language_id];
        if (Object.keys(updatedContentData).length === 0) {
          const router = useRouter();
          setTimeout(() => router
            .push(`/content?content_id=${content_id}&action=delete`), 0);

        }

        return updatedContentData;
      });
    }
  };
  const onDeleteLanguageVersion = async () => {
    if (content) {
      const result = await deleteLanguageVersion(content_id, content.language_id);

    }
  };

  return (
    <Modal
      open={open as boolean}
      onClose={onClose}
      sx={[
        { display: "flex" },
        appStyles.alignItemsCenter,
        appStyles.justifyContentCenter,
      ]}
    >
      <Fade in={!!open}>
        <Box
          sx={{
            height: "80%",
            width: "80%",
            minWidth: "500px",
            backgroundColor: appColors.white,
            p: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox
            flexDirection={"row"}
            {...appStyles.justifyContentSpaceBetween}
          >
            <Typography variant="h5">Content #{content_id}</Typography>
            <Close onClick={onClose} />
          </Layout.FlexBox>

          <Layout.Spacer multiplier={1} />

          <Layout.FlexBox
            flexDirection={"column"}
            sx={{
              height: "80%",
            }}
          >
            <LanguageButtonBar
              expandable={false}
              getLanguageList={getLanguageList}
              onLanguageSelect={handleLanguageSelect}
              defaultLanguageId={defaultLanguageId}
              enabledLanguages={enabledLanguages}
              isEdit={false} />
            <Layout.FlexBox
              flex={1}
              flexDirection={"column"}
              sx={{
                p: sizes.baseGap,
                mr: sizes.baseGap,
                overflowY: "auto",
                border: 1,
                borderColor: appColors.outline,
                borderRadius: 1,
              }}
            >

              <Layout.Spacer multiplier={1} />
              <Typography variant="subtitle1">{content?.content_title}</Typography>
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">{content?.content_text}</Typography>
            </Layout.FlexBox>
            <Layout.Spacer multiplier={1} />
            <Layout.FlexBox
              flexDirection={"row"}
              gap={sizes.smallGap}
              {...appStyles.justifyContentSpaceBetween}
            >
              <Layout.FlexBox
                {...appStyles.alignItemsCenter}
                flexDirection={"row"}
              >
                <Button
                  variant="contained"
                  color="primary"
                  disabled={!editAccess}
                  component={Link}
                  href={`/content/edit?content_id=${content_id}&language_id=${content ? content.language_id : defaultLanguageId}`}
                >
                  <Edit />
                  <Layout.Spacer horizontal multiplier={0.4} />
                  Edit
                </Button>
                <Layout.Spacer horizontal multiplier={1} />
                <IconButton
                  disabled={!editAccess}
                  aria-label="delete"
                  size="small"
                  onClick={() => setOpenDeleteModal(true)}
                >
                  <Delete fontSize="inherit" />
                </IconButton>
                <Layout.Spacer horizontal multiplier={1} />
              </Layout.FlexBox>
              <Layout.FlexBox
                {...appStyles.alignItemsCenter}
                flexDirection={"row"}
              >
                <Typography variant="body2" color={appColors.darkGrey}>
                  Last modified on{" "}
                  {new Date(content?.updated_datetime_utc!).toLocaleString(undefined, {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "numeric",
                    minute: "numeric",
                    hour12: false,
                  })}
                </Typography>
              </Layout.FlexBox>
              <Layout.FlexBox
                flexDirection={"row"}
                gap={sizes.baseGap}
                {...appStyles.alignItemsCenter}
                {...appStyles.justifyContentCenter}
                sx={{ pr: sizes.baseGap }}
              >
                <RemoveRedEye fontSize="small" color="disabled" />
                <Typography variant="body2">_</Typography>
                <ThumbUp fontSize="small" color="disabled" />
                <Typography variant="body2">_</Typography>
                <ThumbDown fontSize="small" color="disabled" />
                <Typography variant="body2">_</Typography>
              </Layout.FlexBox>
            </Layout.FlexBox>
            <DeleteContentModal
              content_id={content?.content_id!}
              language_id={content?.language_id!}
              open={openDeleteModal}
              onClose={() => setOpenDeleteModal(false)}
              onSuccessfulDelete={onSuccessfulDelete}
              onFailedDelete={(content_id: number, language_id: number | null) => {
                setSnackMessage(
                  `Failed to delete content #${content_id} with language_id: #${language_id}`,
                );
              }}
              deleteContent={onDeleteLanguageVersion}
            />
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
        </Box>
      </Fade>
    </Modal>
  );
};

const DeleteContentModal = ({
  content_id,
  language_id,
  open,
  onClose,
  onSuccessfulDelete,
  onFailedDelete,
  deleteContent,
}: {
  content_id: number;
  language_id: number | null;
  open: boolean;
  onClose: () => void;
  onSuccessfulDelete: (content_id: number, language_id: number | null) => void;
  onFailedDelete: (content_id: number, language_id: number | null) => void;
  deleteContent: (content_id: number, language_id: number | null) => Promise<any>;
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      <DialogTitle id="alert-dialog-title">
        {"Are you sure you want to delete this content?"}
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description">
          Deleting this content will remove it from the database. This action
          cannot be undone.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ margin: 1 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={() => {
            const handleDeleteContent = async (content_id: number, language_id: number | null) => {
              const results = deleteContent(content_id, language_id)
                .then((res) => {
                  onSuccessfulDelete(content_id, language_id);
                })
                .catch((err) => {
                  console.log("error", err);
                  onFailedDelete(content_id, language_id);
                });
            };
            handleDeleteContent(Number(content_id), language_id);
            onClose();
          }}
          autoFocus
          variant="contained"
          color="error"
          startIcon={<Delete />}
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export { ContentViewModal, DeleteContentModal };
