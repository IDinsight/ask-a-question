import { appColors, appStyles, sizes } from "@/utils";
import {
  Close,
  Delete,
  Edit,
  RemoveRedEye,
  ThumbDown,
  ThumbUp,
} from "@mui/icons-material";
import { Box, Button, Fade, Modal, Typography } from "@mui/material";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "next/link";
import React from "react";

import LanguageButtonBar from "./LanguageButtonBar";
import { Layout } from "./Layout";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { Content } from "@/app/content/edit/page";


const ContentViewModal = ({
  content_id,
  defaultLanguageId,
  open,
  onClose,
  editAccess,
}: {
  content_id: number;
  defaultLanguageId: number;
  open: boolean;
  onClose: () => void;
  editAccess: boolean;
}) => {
  const [contentData, setContentData] = React.useState<{ [key: number]: any }>({});
  const [contentTextData, setContentTextData] = React.useState<Content | null>(null);
  const [enabledLanguages, setEnabledLanguages] = React.useState<number[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const handleLanguageSelect = (language_id: number) => {
    setContentTextData(contentData[language_id]);
  };
  const { token } = useAuth();
  React.useEffect(() => {
    const fetchData = async () => {
      if (open) {
        setLoading(true);
        setError(null);  // Reset error state on new fetch
        try {
          const dataList = await apiCalls.getContent(content_id, null, token!);
          const transformedData: { [key: string]: any } = dataList.reduce((acc: { [key: number]: any }, item: any) => {
            const { language_id, ...rest } = item;
            acc[language_id] = rest;
            return acc;
          }, {});

          setContentData(transformedData);
          setEnabledLanguages(Object.keys(transformedData).map(Number))
          setContentTextData(transformedData[defaultLanguageId]);
          setLoading(false);
        } catch (err) {
          setError((err as Error).message || "Something went wrong");
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [open, content_id, token]);
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
              onLanguageSelect={handleLanguageSelect}
              defaultLanguageId={defaultLanguageId}
              enabledLanguages={enabledLanguages} />
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
              <Typography variant="subtitle1">{contentTextData?.content_title}</Typography>
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">{contentTextData?.content_text}</Typography>
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
                  href={`/content/edit?content_id=${content_id}`}
                >
                  <Edit />
                  <Layout.Spacer horizontal multiplier={0.4} />
                  Edit
                </Button>
                <Layout.Spacer horizontal multiplier={1} />
              </Layout.FlexBox>
              <Layout.FlexBox
                {...appStyles.alignItemsCenter}
                flexDirection={"row"}
              >
                <Typography variant="body2" color={appColors.darkGrey}>
                  Last modified on{" "}
                  {new Date(contentTextData?.updated_datetime_utc!).toLocaleString(undefined, {
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
          </Layout.FlexBox>
        </Box>
      </Fade>
    </Modal>
  );
};

const DeleteContentModal = ({
  content_id,
  open,
  onClose,
  onSuccessfulDelete,
  onFailedDelete,
  deleteContent,
}: {
  content_id: number;
  open: boolean;
  onClose: () => void;
  onSuccessfulDelete: (content_id: number) => void;
  onFailedDelete: (content_id: number) => void;
  deleteContent: (content_id: number) => Promise<any>;
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
            const handleDeleteContent = async (content_id: number) => {
              const results = deleteContent(content_id)
                .then((res) => {
                  onSuccessfulDelete(content_id);
                })
                .catch((err) => {
                  console.log("error", err);
                  onFailedDelete(content_id);
                });
            };
            handleDeleteContent(Number(content_id));
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
