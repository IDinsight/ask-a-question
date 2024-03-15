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
import Link from "next/link";
import LanguageButtonBar from "./LanguageButtonBar";
import { Layout } from "./Layout";

const ContentViewModal = ({
  title,
  text,
  content_id,
  last_modified,
  open,
  onClose,
}: {
  title: string;
  text: string;
  content_id: string;
  last_modified: string;
  open: boolean;
  onClose: () => void;
}) => {
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
            <LanguageButtonBar expandable={false} />
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
              <Typography variant="subtitle1">{title}</Typography>
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">{text}</Typography>
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
                <Link href={`/content/edit?content_id=${content_id}`}>
                  <Button variant="contained" color="primary">
                    <Edit />
                    <Layout.Spacer horizontal multiplier={0.4} />
                    Edit
                  </Button>
                </Link>
                <Layout.Spacer horizontal multiplier={1} />
                <Delete color="disabled" fontSize="small" />
              </Layout.FlexBox>
              <Layout.FlexBox
                {...appStyles.alignItemsCenter}
                flexDirection={"row"}
              >
                <Typography variant="body2" color={appColors.darkGrey}>
                  Last modified on{" "}
                  {new Date(last_modified).toLocaleString("en-UK", {
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

export default ContentViewModal;
