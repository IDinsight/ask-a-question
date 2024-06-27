import { appColors, sizes } from "@/utils";
import {
  Box,
  Button,
  Fade,
  IconButton,
  Modal,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";

import { Layout } from "@/components/Layout";

const ChatManagerModalWrapper = ({
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
            width: "50%",
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
              mr: sizes.baseGap,
              overflowY: "auto",
              border: 1,
              borderColor: appColors.lightGrey,
              borderRadius: 3,
            }}
          >
            <ModalContent />
          </Layout.FlexBox>
        </Box>
      </Fade>
    </Modal>
  );
};

// make one of these for each chat manager and use it to populate the modal
const ChatManagerContentExample: React.FC = () => {
  return (
    <Layout.FlexBox
      flexDirection={"column"}
      padding={sizes.baseGap}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="subtitle1">Example Title</Typography>
      <Typography
        variant="body2"
        sx={{
          overflowWrap: "break-word",
          hyphens: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        Example Text
      </Typography>
      <Box display="flex" justifyContent="start">
        <Button
          variant="contained"
          color="primary"
          startIcon={<DownloadIcon />}
          sx={{ mb: sizes.baseGap }}
        >
          Download Template
        </Button>
      </Box>
    </Layout.FlexBox>
  );
};

export { ChatManagerModalWrapper, ChatManagerContentExample };
