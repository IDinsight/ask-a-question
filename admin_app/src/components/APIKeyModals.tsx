import React from "react";
import {
  Button,
  CircularProgress,
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
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";

export const KeyRenewConfirmationModal = ({
  currentKey,
  open,
  onClose,
  onRenew,
  isLoading,
}: {
  currentKey: string;
  open: boolean;
  onClose: () => void;
  onRenew: () => void;
  isLoading: boolean;
}) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle>{"Are you sure you want to renew your API key?"}</DialogTitle>
    <DialogContent>
      <DialogContentText>
        If you proceed,
        <Typography component="span" style={{ fontWeight: "bold" }}>
          {` the current "${currentKey}" key will stop working. `}
        </Typography>
        You will need to update your applications with the new key.
      </DialogContentText>
    </DialogContent>
    <DialogActions sx={{ margin: 1 }}>
      <Button onClick={onClose} color="primary">
        Cancel
      </Button>
      <Button
        onClick={onRenew}
        autoFocus
        variant="contained"
        color="error"
        startIcon={<AutorenewIcon />}
      >
        {isLoading ? <CircularProgress size={24} color="inherit" /> : "Renew"}
      </Button>
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
}) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle>{"Save your new key"}</DialogTitle>
    <DialogContent>
      <DialogContentText>
        Please save this secret key somewhere safe and accessible. For security
        reasons,
        <Typography component="span" style={{ fontWeight: "bold" }}>
          {" you won't be able to view it again here. "}
        </Typography>
        If you lose this secret key, you'll need to generate a new one.
      </DialogContentText>
      <Layout.Spacer multiplier={1} />
      <DialogContentText>Note: The API key is 32 characters.</DialogContentText>
      <Layout.Spacer multiplier={2} />
      <Layout.FlexBox
        flexDirection="row"
        gap={sizes.baseGap}
        sx={{
          width: "80%",
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
          onClick={onCopy}
          startIcon={<ContentCopyIcon />}
        >
          Copy
        </Button>
      </Layout.FlexBox>
    </DialogContent>
    <DialogActions sx={{ margin: 1 }}>
      <Button onClick={onClose} color="primary">
        Close
      </Button>
    </DialogActions>
  </Dialog>
);
