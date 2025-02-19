import CheckIcon from "@mui/icons-material/Check";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from "@mui/material";
import React, { useState } from "react";
const ConfirmationModal = ({
  open,
  onClose,
  recoveryCodes,
  dialogTitle = "Admin User Created",

  closeButtonText = "Close",
}: {
  open: boolean;
  onClose: () => void;
  recoveryCodes: string[];
  dialogTitle?: string;
  closeButtonText?: string;
}) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClose = () => {
    setIsClicked(false);
    onClose();
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
    } catch (err) {
      console.error("Failed to copy recovery codes: ", err);
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{dialogTitle}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          The user has been successfully registered. Please save the recovery codes
          below. You will not be able to see them again.
        </DialogContentText>
        <TextField
          fullWidth
          multiline
          margin="normal"
          value={recoveryCodes ? recoveryCodes.join("\n") : ""}
          InputProps={{
            readOnly: true,
            sx: {
              textAlign: "center",
            },
          }}
          inputProps={{
            style: { textAlign: "center" },
          }}
        />

        <Box display="flex" justifyContent="center" mt={2}>
          <Button
            variant="contained"
            onClick={() => {
              handleCopyToClipboard();
              setIsClicked(true);
            }}
            startIcon={isClicked ? <CheckIcon /> : <ContentCopyIcon />}
            style={{ paddingLeft: "20px", paddingRight: "20px" }}
          >
            {isClicked ? "Copied" : "Copy"}
          </Button>
        </Box>
      </DialogContent>

      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={handleClose} color="primary" variant="contained" autoFocus>
          {closeButtonText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
export { ConfirmationModal };
