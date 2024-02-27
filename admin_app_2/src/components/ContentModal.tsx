import React from "react";
import { Modal, Typography, Box, Fade, Button } from "@mui/material";
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
            width: "70%",
            height: "70%",
            backgroundColor: appColors.white,
            p: sizes.baseGap,
            px: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox
            flexDirection={"row"}
            {...appStyles.justifyContentFlexEnd}
          >
            <Close onClick={onClose} />
          </Layout.FlexBox>
          <Typography variant="h5">Content #142 </Typography>

          <Layout.FlexBox
            flex={1}
            flexDirection={"row"}
            {...appStyles.justifyContentFlexEnd}
            sx={{
              height: "90%",
            }}
          >
            <Layout.FlexBox
              flex={2}
              flexDirection={"column"}
              sx={{ backgroundColor: appColors.white }}
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
                  This is the content of the page. It can be edited here.\n This
                  is the content of the page.
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
                      Edit
                    </Button>
                  </Link>
                  <Layout.Spacer horizontal multiplier={1} />
                  <Delete color="disabled" fontSize="small" />
                </Layout.FlexBox>
                <Layout.FlexBox
                  flexDirection={"row"}
                  gap={sizes.baseGap}
                  {...appStyles.alignItemsCenter}
                  {...appStyles.justifyContentCenter}
                  sx={{ pr: sizes.baseGap }}
                >
                  <RemoveRedEye fontSize="small" />
                  <Typography variant="body2">20</Typography>
                  <ThumbUp fontSize="small" />
                  <Typography variant="body2">12</Typography>
                  <ThumbDown fontSize="small" />
                  <Typography variant="body2">2</Typography>
                </Layout.FlexBox>
              </Layout.FlexBox>
            </Layout.FlexBox>

            <Layout.FlexBox
              flex={1}
              flexDirection={"column"}
              sx={{ height: "100%" }}
            >
              <Typography variant="h5">Attachments</Typography>
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">Image</Typography>
              <Box
                width={"100%"}
                height={"30%"}
                sx={{ backgroundColor: appColors.lightGrey }}
              />
              <Layout.Spacer multiplier={1} />
              <Typography variant="body2">Audio</Typography>
              <Box
                width={"100%"}
                height={"10%"}
                sx={{ backgroundColor: appColors.lightGrey }}
              />
            </Layout.FlexBox>
          </Layout.FlexBox>
        </Box>
      </Fade>
    </Modal>
  );
};

export default ContentViewModal;
