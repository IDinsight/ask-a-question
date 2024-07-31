import { appColors, sizes } from "@/utils";
import { Close, Delete, Edit, ThumbDown, ThumbUp } from "@mui/icons-material";
import {
  Box,
  Button,
  Chip,
  Fade,
  IconButton,
  Modal,
  Typography,
} from "@mui/material";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "next/link";
import LanguageButtonBar from "./LanguageButtonBar";
import { Layout } from "./Layout";
import { Tag } from "@/app/content/page";

const ContentViewModal = ({
  title,
  text,
  content_id,
  positive_votes,
  negative_votes,
  last_modified,
  tags,
  open,
  onClose,
  editAccess,
}: {
  title: string;
  text: string;
  content_id: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
  open: boolean;
  onClose: () => void;
  editAccess: boolean;
}) => {
  return (
    <Modal
      open={open as boolean}
      onClose={onClose}
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Fade in={!!open}>
        <Box
          sx={{
            width: "60%",
            minWidth: "600px",
            borderRadius: 2,
            backgroundColor: appColors.white,
            p: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox
            flexDirection={"row"}
            justifyContent={"space-between"}
          >
            <Typography variant="h5">Content #{content_id}</Typography>
            <IconButton onClick={onClose}>
              <Close />
            </IconButton>
          </Layout.FlexBox>
          <Layout.Spacer multiplier={0.5} />
          {tags && tags.length > 0 && (
            <Layout.FlexBox
              flexDirection={"column"}
              sx={{
                my: sizes.smallGap,
              }}
            >
              <Typography variant="subtitle1" gutterBottom>
                Tags
              </Typography>
              <Layout.FlexBox
                flexDirection={"row"}
                gap={sizes.smallGap}
                sx={{
                  overflowX: "auto",
                  py: sizes.smallGap,
                  alignItems: "center",
                }}
              >
                {tags.map((tag) => (
                  <Chip key={tag.tag_id} label={tag.tag_name} />
                ))}
              </Layout.FlexBox>
            </Layout.FlexBox>
          )}
          <Layout.Spacer multiplier={0.5} />
          {/* <LanguageButtonBar expandable={false} /> */}
          <Layout.FlexBox
            flexDirection={"column"}
            sx={{
              maxHeight: "60vh", // this controls overall modal height too
              p: sizes.baseGap,
              mr: sizes.baseGap,
              overflowY: "auto",
              border: 1,
              borderColor: appColors.lightGrey,
              borderRadius: 3,
            }}
          >
            <Typography variant="subtitle1" sx={{ mb: sizes.baseGap }}>
              {title}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                overflowWrap: "break-word",
                hyphens: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {text}
            </Typography>
          </Layout.FlexBox>
          <Layout.Spacer multiplier={2} />
          <Layout.FlexBox
            flexDirection={"row"}
            justifyContent={"space-between"}
            alignItems={"center"}
            gap={sizes.smallGap}
          >
            <Layout.FlexBox flexDirection={"row"} alignItems={"center"}>
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
              flexDirection={"row"}
              justifyContent={"space-between"}
            >
              <Typography variant="body2" color={appColors.darkGrey}>
                Last modified{" "}
                {new Date(last_modified).toLocaleString(undefined, {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                  hour: "numeric",
                  minute: "numeric",
                  hour12: true,
                })}
              </Typography>
            </Layout.FlexBox>
            <Layout.FlexBox
              flexDirection={"row"}
              gap={sizes.baseGap}
              sx={{
                pr: sizes.baseGap,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ThumbUp fontSize="small" color="disabled" />
              <Typography variant="body2" sx={{ color: appColors.darkGrey }}>
                {positive_votes}
              </Typography>
              <ThumbDown fontSize="small" color="disabled" />
              <Typography variant="body2" sx={{ color: appColors.darkGrey }}>
                {negative_votes}
              </Typography>
            </Layout.FlexBox>
          </Layout.FlexBox>
        </Box>
      </Fade>
    </Modal>
  );
};

const ArchiveContentModal = ({
  content_id,
  open,
  onClose,
  onSuccessfulArchive,
  onFailedArchive,
  archiveContent,
}: {
  content_id: number;
  open: boolean;
  onClose: () => void;
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number) => void;
  archiveContent: (content_id: number) => Promise<any>;
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      <DialogTitle id="alert-dialog-title">
        Are you sure you want to remove this content?
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="alert-dialog-description">
          Removing this content will mean that it can no longer be accessed.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={() => {
            const handleArchiveContent = async (content_id: number) => {
              const results = archiveContent(content_id)
                .then((res) => {
                  onSuccessfulArchive(content_id);
                })
                .catch((err) => {
                  console.log("error", err);
                  onFailedArchive(content_id);
                });
            };
            handleArchiveContent(Number(content_id));
            onClose();
          }}
          autoFocus
          variant="contained"
          color="error"
          startIcon={<Delete />}
        >
          Remove
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export { ContentViewModal, ArchiveContentModal };
