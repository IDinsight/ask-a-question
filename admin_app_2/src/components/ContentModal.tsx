import React from "react";
import { Modal, Typography, Box, Fade, Button, Chip } from "@mui/material";
import { appColors, appStyles, sizes } from "@/utils";
import { Layout } from "./Layout";
import {
  Close,
  Delete,
  Edit,
  RemoveRedEye,
  ThumbDown,
  ThumbUp,
} from "@mui/icons-material";
import LanguageButtonBar from "./LanguageButtonBar";
import Link from "next/link";
import Image from "next/image";

const ContentViewModal = ({
  open,
  onClose,
}: {
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
            <Typography variant="h5">Content #142</Typography>
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
              <Typography variant="subtitle1">
                Question or Title goes here
              </Typography>
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">
                This is the content of the page. It can be edited here. This is
                the content of the page.
              </Typography>
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
                <Link href={`/add-faq?contentID=142`}>
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
                  Last edited 1 June 12:30 PM
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
