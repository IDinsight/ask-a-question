"use client";
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Typography,
} from "@mui/material";
import TextField from "@mui/material/TextField";
import React, { useState } from "react";
import { apiCalls } from "@/utils/api";

const IntegrationsPage = () => {
  const [currAccessLevel, setCurrAccessLevel] = React.useState("readonly");
  const { token, accessLevel } = useAuth();

  React.useEffect(() => {
    setCurrAccessLevel(accessLevel);
  }, [accessLevel]);

  return (
    <Layout.FlexBox alignItems="center" gap={sizes.baseGap}>
      <Layout.Spacer multiplier={3} />
      <KeyManagement
        token={token}
        editAccess={currAccessLevel === "fullaccess"}
      />
    </Layout.FlexBox>
  );
};
const KeyManagement = ({
  token,
  editAccess,
}: {
  token: string | null;
  editAccess: boolean;
}) => {
  const [currentKey, setCurrentKey] = useState("qwerty...");
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [newKeyModalOpen, setNewKeyModalOpen] = useState(false);
  const [newKey, setNewKey] = useState("");

  const handleNewKeyCopy = () => {
    navigator.clipboard.writeText(newKey);
  };

  const handleConfirmationModalOpen = () => {
    setConfirmationModalOpen(true);
  };
  const handleConfirmationModalClose = () => {
    setConfirmationModalOpen(false);
  };

  const handleNewKeyModalClose = () => {
    setNewKeyModalOpen(false);
  };
  const handleRenew = async () => {
    apiCalls.getNewAPIKey(token!).then((data) => {
      setNewKey(data.new_retrieval_key);
    });
    setConfirmationModalOpen(false);
    setNewKeyModalOpen(true);
  };

  return (
    <Layout.FlexBox
      key={"key-management"}
      flexDirection={"column"}
      sx={{
        display: "flex",
        alignSelf: "center",
        px: sizes.baseGap,
      }}
      gap={sizes.baseGap}
    >
      <Typography variant="h5" align="center" color="primary">
        Your API Key
      </Typography>
      <Layout.FlexBox
        flexDirection={"row"}
        sx={{
          display: "flex",
          alignSelf: "center",
          px: sizes.baseGap,
        }}
        gap={sizes.baseGap}
      >
        <TextField
          value={currentKey}
          disabled={true}
          inputProps={{
            style: { height: "36px", padding: "0 10px" },
          }}
        />
        <Button
          variant="contained"
          onClick={handleConfirmationModalOpen}
          disabled={!editAccess}
          startIcon={<AutorenewIcon />}
        >
          Renew
        </Button>

        <Dialog
          open={confirmationModalOpen}
          onClose={handleConfirmationModalClose}
        >
          <DialogTitle>
            {"Are you sure you want to renew your API key?"}
          </DialogTitle>
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
            <Button onClick={handleConfirmationModalClose} color="primary">
              Cancel
            </Button>
            <Button
              onClick={handleRenew}
              autoFocus
              variant="contained"
              color="error"
              startIcon={<AutorenewIcon />}
            >
              Renew
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={newKeyModalOpen} onClose={handleNewKeyModalClose}>
          <DialogTitle>{"Save your new key"}</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Please save this secret key somewhere safe and accessible. For
              security reasons,
              <Typography component="span" style={{ fontWeight: "bold" }}>
                {" you won't be able to view it again here. "}
              </Typography>
              If you lose this secret key, you'll need to generate a new one.
            </DialogContentText>
            <Layout.Spacer multiplier={1} />
            <DialogContentText>
              Note: The API key is 32-characters.
            </DialogContentText>
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
                autoFocus
                fullWidth
                value={newKey}
                inputProps={{
                  readOnly: true,
                  style: { height: "36px", padding: "0 10px" },
                }}
              />
              <Button
                variant="contained"
                onClick={handleNewKeyCopy}
                startIcon={<ContentCopyIcon />}
                autoFocus
              >
                Copy
              </Button>
            </Layout.FlexBox>
          </DialogContent>
          <DialogActions sx={{ margin: 1 }}>
            <Button onClick={handleNewKeyModalClose} color="primary">
              Close
            </Button>
          </DialogActions>
        </Dialog>
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

// const IntegrationsGrid = ({
//   token,
//   accessLevel,
// }: {
//   token: string | null;
//   accessLevel: string;
// }) => { }

export default IntegrationsPage;
