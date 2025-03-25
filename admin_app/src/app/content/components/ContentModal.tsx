import { appColors, sizes } from "@/utils";
import { Close, Delete, Edit, ThumbDown, ThumbUp } from "@mui/icons-material";
import { Box, Button, Chip, Fade, IconButton, Modal, Typography } from "@mui/material";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "next/link";
import { Layout } from "@/components/Layout";
import { Tag } from "@/app/content/page";

const ContentViewModal = ({
  title,
  text,
  content_id,
  display_number,
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
  display_number: number;
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
            maxWidth: "md",
            borderRadius: 2,
            backgroundColor: appColors.white,
            padding: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox flexDirection={"row"} justifyContent={"space-between"}>
            <Typography variant="h5">Content #{display_number}</Typography>
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
                sx={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  py: sizes.smallGap,
                  alignItems: "center",
                  gap: sizes.smallGap,
                }}
              >
                {tags.map((tag) => (
                  <Chip key={tag.tag_id} label={tag.tag_name} />
                ))}
              </Layout.FlexBox>
            </Layout.FlexBox>
          )}
          <Layout.FlexBox
            flexDirection={"column"}
            sx={{
              maxHeight: "60vh", // this controls overall modal height too
              padding: sizes.baseGap,
              marginTop: 1,
              overflowY: "auto",
              border: 1,
              borderColor: appColors.lightGrey,
              borderRadius: 3,
            }}
          >
            <Typography variant="subtitle1" sx={{ marginBottom: sizes.baseGap }}>
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
          <Layout.FlexBox
            sx={{
              flexDirection: "row",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: sizes.baseGap,
              paddingTop: 2,
              paddingInline: 1,
            }}
          >
            <Button
              variant="contained"
              color="primary"
              disabled={!editAccess}
              component={Link}
              href={`/content/edit?content_id=${content_id}`}
              startIcon={<Edit />}
            >
              Edit
            </Button>
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
            <Layout.FlexBox
              sx={{
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
                gap: sizes.smallGap,
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
