import { appColors, appStyles, sizes } from "@/utils";
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

const ChatManagerModal = ({
  logo_src,
  title,
  text,
  open,
  onClose,
}: {
  logo_src: string;
  title: string;
  text: string;
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
            maxHeight: "80vh",
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
          <Layout.Spacer />
          <Layout.FlexBox
            flexDirection={"column"}
            padding={sizes.baseGap}
            gap={sizes.doubleBaseGap}
          >
            <Typography variant="subtitle1">{title}</Typography>
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
        </Box>
      </Fade>
    </Modal>
  );
};

export default ChatManagerModal;
