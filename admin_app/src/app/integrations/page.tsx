"use client";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { Button, CircularProgress, Grid, Typography } from "@mui/material";
import React, { useState } from "react";
import { format } from "date-fns";

import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";

import {
  KeyRenewConfirmationModal,
  NewKeyModal,
} from "./components/APIKeyModals";
import ChatManagersGrid from "./components/ChatManagerGrid";

const IntegrationsPage = () => {
  const [currAccessLevel, setCurrAccessLevel] = React.useState("readonly");
  const { token, accessLevel } = useAuth();

  React.useEffect(() => {
    setCurrAccessLevel(accessLevel);
  }, [accessLevel]);

  return (
    <Layout.FlexBox alignItems="center">
      <Layout.Spacer multiplier={5} />
      <KeyManagement
        token={token}
        editAccess={currAccessLevel === "fullaccess"}
      />
      <Layout.Spacer multiplier={4} />
      <ChatManagers />
      <Layout.Spacer multiplier={6} />
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
  const [keyInfoFetchIsLoading, setKeyInfoFetchIsLoading] = useState(true);
  const [currentKey, setCurrentKey] = useState("");
  const [currentKeyLastUpdated, setCurrentKeyLastUpdated] = useState("");
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [newKeyModalOpen, setNewKeyModalOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [keyGenerationIsLoading, setKeyGenerationIsLoading] = useState(false);

  React.useEffect(() => {
    const setApiKeyInfo = async () => {
      setKeyInfoFetchIsLoading(true);
      try {
        const data = await apiCalls.getUser(token!);
        setCurrentKey(data.api_key_first_characters);
        const formatted_api_update_date = format(
          data.api_key_updated_datetime_utc,
          "HH:mm, dd-MM-yyyy",
        );
        setCurrentKeyLastUpdated(formatted_api_update_date);
        setKeyInfoFetchIsLoading(false);
      } catch (error) {
        console.error(error);
        setKeyInfoFetchIsLoading(false);
      }
    };
    setApiKeyInfo();
  }, [token, newKey]);

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
    setKeyGenerationIsLoading(true);
    try {
      const data = await apiCalls.createNewApiKey(token!);
      setNewKey(data.new_api_key);
      setConfirmationModalOpen(false);
      setNewKeyModalOpen(true);
    } catch (error) {
      console.error(error);
    } finally {
      setKeyGenerationIsLoading(false);
    }
  };

  return (
    <Layout.FlexBox
      key={"key-management"}
      flexDirection="column"
      sx={{ maxWidth: 690, marginInline: 10 }}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h4" color="primary">
        Your API Key
      </Typography>
      <Layout.FlexBox
        flexDirection="column"
        justifyContent="space-between"
        gap={sizes.doubleBaseGap}
      >
        <Typography variant="body1">
          You will need your API key to interact with AAQ from your chat
          manager. You can generate a new key here, but keep in mind that any
          old key is invalidated if a new key is created.
        </Typography>
        <Layout.FlexBox
          flexDirection="column"
          alignItems={"center"}
          gap={sizes.baseGap}
        >
          {keyInfoFetchIsLoading ? (
            <Typography variant="body1">
              Checking for current API key <CircularProgress size={10} />
            </Typography>
          ) : currentKey ? (
            <Typography variant="body1">
              Active API key snippet:{" "}
              <span style={{ fontWeight: "bold" }}>{`${currentKey}...`}</span>
              <br />
              Last updated: {currentKeyLastUpdated}
            </Typography>
          ) : (
            <Typography variant="body1">
              Generate your first API key:
            </Typography>
          )}
          <Button
            variant="contained"
            onClick={handleConfirmationModalOpen}
            disabled={!editAccess}
            startIcon={<AutorenewIcon />}
            style={{
              width: "200px",
              alignSelf: "center",
              backgroundColor: currentKey ? appColors.error : appColors.primary,
            }}
          >
            {currentKey ? `Regenerate Key` : "Generate Key"}
          </Button>
        </Layout.FlexBox>
        <KeyRenewConfirmationModal
          open={confirmationModalOpen}
          onClose={handleConfirmationModalClose}
          onRenew={handleRenew}
          isLoading={keyGenerationIsLoading}
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

const ChatManagers = () => {
  return (
    <Layout.FlexBox
      key={"chat-managers"}
      flexDirection="column"
      sx={{ maxWidth: 1000, marginInline: 10 }}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h4" color="primary">
        Chat Managers
      </Typography>
      <Typography variant="body1">
        Click on the chat manager of your choice to see instructions on how to
        connect it to AAQ.
      </Typography>
      <ChatManagersGrid />
    </Layout.FlexBox>
  );
};

export default IntegrationsPage;
