import React from "react";
import { Modal, Typography, Box, Fade } from "@mui/material";
import { appColors, sizes } from "@/utils";
import { Layout } from "./Layout";
import { Close } from "@mui/icons-material";

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
      sx={{ display: "flex", alignItems: "center", justifyContent: "center" }}
    >
      <Fade in={!!open}>
        <Box
          sx={{
            width: "70%",
            height: "70%",
            backgroundColor: appColors.background,
            p: sizes.baseGap,
            pl: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox
            flexDirection={"row"}
            justifyContent={"space-between"}
          >
            <Layout.Spacer horizontal />
            <Close onClick={onClose} />
          </Layout.FlexBox>
          <Typography variant="h5" color={"primary"}>
            Content #142{" "}
          </Typography>
        </Box>
      </Fade>
    </Modal>
  );
};

export default ContentViewModal;
