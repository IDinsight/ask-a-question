import React, { useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";
import { LoadingButton } from "@mui/lab";

export const KeyRenewConfirmationModal = ({
  open,
  currentKey,
  onClose,
  onRenew,
  isLoading,
}: {
  open: boolean;
  currentKey: string;
  onClose: () => void;
  onRenew: () => void;
  isLoading: boolean;
}) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle>{"Are you sure you want to renew the workspace API key?"}</DialogTitle>
    <DialogContent>
      <DialogContentText>
        {`If you proceed, your current key beginning with `}
        <Typography component="span" style={{ fontWeight: "bold" }}>
          "{currentKey}" will stop working
        </Typography>
        {` and you will need to update your applications with the new key.`}
      </DialogContentText>
    </DialogContent>
    <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
      <Button onClick={onClose} color="primary">
        Cancel
      </Button>
      <LoadingButton
        onClick={onRenew}
        autoFocus
        variant="contained"
        color="error"
        loading={isLoading}
        loadingPosition="start"
        startIcon={<AutorenewIcon />}
      >
        {isLoading ? "Generating..." : "Generate New Key"}
      </LoadingButton>
    </DialogActions>
  </Dialog>
);

export const NewKeyModal = ({
  newKey,
  open,
  onCopy,
  onClose,
}: {
  newKey: string;
  open: boolean;
  onCopy: () => void;
  onClose: () => void;
}) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClose = () => {
    setIsClicked(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogTitle>{"Save your new key"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Please save this secret key somewhere safe and accessible. For security
          reasons,
          <Typography component="span" style={{ fontWeight: "bold" }}>
            {" you won't be able to view the full key again here. "}
          </Typography>
          If you lose this secret key, you'll need to generate a new one.
        </DialogContentText>
        <Layout.Spacer multiplier={1} />
        <DialogContentText>Note: The API key has 32 characters.</DialogContentText>
        <Layout.Spacer multiplier={2} />
        <Layout.FlexBox
          flexDirection="row"
          gap={sizes.baseGap}
          sx={{
            width: "96%",
            margin: "auto",
          }}
        >
          <TextField
            value={newKey}
            variant="outlined"
            color="primary"
            fullWidth
            autoFocus
            inputProps={{
              readOnly: true,
              style: { height: "36px", padding: "0 10px" },
              onFocus: (event) => event.target.select(),
            }}
          />
          <Button
            variant="contained"
            onClick={() => {
              onCopy();
              setIsClicked(true);
            }}
            startIcon={isClicked ? <CheckIcon /> : <ContentCopyIcon />}
            style={{ paddingLeft: "20px", paddingRight: "20px" }}
          >
            {isClicked ? "Copied" : "Copy"}
          </Button>
        </Layout.FlexBox>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={handleClose} color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};
