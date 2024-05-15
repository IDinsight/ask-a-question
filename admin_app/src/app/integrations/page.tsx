"use client";
import {
  KeyRenewConfirmationModal,
  NewKeyModal,
} from "@/components/APIKeyModals";
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { Button, Typography } from "@mui/material";
import TextField from "@mui/material/TextField";
import React, { useState } from "react";

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
  const [isLoading, setIsLoading] = useState(false);

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
    setIsLoading(true);
    try {
      const data = await apiCalls.getNewAPIKey(token!);
      setNewKey(data.new_retrieval_key);
      setConfirmationModalOpen(false);
      setNewKeyModalOpen(true);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
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

        <KeyRenewConfirmationModal
          currentKey={currentKey}
          open={confirmationModalOpen}
          onClose={handleConfirmationModalClose}
          onRenew={handleRenew}
          isLoading={isLoading}
        />
        <NewKeyModal
          newKey={newKey}
          open={newKeyModalOpen}
          onClose={handleNewKeyModalClose}
          onCopy={handleNewKeyCopy}
        />
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
