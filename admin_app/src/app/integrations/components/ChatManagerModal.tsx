import React from "react";

import CloseIcon from "@mui/icons-material/Close";
import { Box, Fade, IconButton, Modal } from "@mui/material";

import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";

const ChatManagerModal = ({
  logo_src,
  ModalContent,
  open,
  onClose,
}: {
  logo_src: string;
  ModalContent: React.FC;
  open: boolean;
  onClose: () => void;
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
            minWidth: "300px",
            borderRadius: 2,
            backgroundColor: appColors.white,
            p: sizes.doubleBaseGap,
          }}
        >
          <Layout.FlexBox
            flexDirection={"row"}
            justifyContent={"space-between"}
            paddingLeft={sizes.baseGap}
          >
            <img src={logo_src} style={{ height: "40px" }} />
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Layout.FlexBox>
          <Layout.Spacer multiplier={2} />
          <Layout.FlexBox
            flexDirection={"column"}
            sx={{
              maxHeight: "70vh",
              p: sizes.baseGap,
              marginRight: sizes.baseGap,
              overflowY: "auto",
            }}
          >
            <ModalContent />
          </Layout.FlexBox>
        </Box>
      </Fade>
    </Modal>
  );
};

export default ChatManagerModal;
