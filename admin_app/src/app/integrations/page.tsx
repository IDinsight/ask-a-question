"use client";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { Button, CircularProgress, Typography } from "@mui/material";
import React, { useState } from "react";
import { format } from "date-fns";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { createNewApiKey } from "./api";
import { useAuth } from "@/utils/auth";

import {
  KeyRenewConfirmationModal,
  NewKeyModal,
} from "./components/APIKeyModals";
import ChatManagersGrid from "./components/ChatManagerGrid";
import { LoadingButton } from "@mui/lab";
import { OpenInNew } from "@mui/icons-material";

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
      <Layout.Spacer multiplier={4} />
      <RestAPI />
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
    if (token) {
      const setApiKeyInfo = async () => {
        setKeyInfoFetchIsLoading(true);
        try {
          const data = await apiCalls.getUser(token!);
          setCurrentKey(data.api_key_first_characters);
          const formatted_api_update_date = format(
            data.api_key_updated_datetime_utc,
            "HH:mm, dd-MM-yyyy"
          );
          setCurrentKeyLastUpdated(formatted_api_update_date);
          setKeyInfoFetchIsLoading(false);
        } catch (error) {
          console.error(error);
          setKeyInfoFetchIsLoading(false);
        }
      };
      setApiKeyInfo();
    } else {
      setKeyInfoFetchIsLoading(false);
    }
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
    setKeyInfoFetchIsLoading(true);
    try {
      const data = await createNewApiKey(token!);
      setNewKey(data.new_api_key);
      setConfirmationModalOpen(false);
      setNewKeyModalOpen(true);
    } catch (error) {
      console.error(error);
    } finally {
      setKeyGenerationIsLoading(false);
      setKeyInfoFetchIsLoading(false);
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
              <br />
              Checking for current API key <CircularProgress size={10} />
            </Typography>
          ) : currentKey ? (
            <Typography variant="body1">
              Active API key reminder:{" "}
              <span style={{ fontWeight: "bold" }}>{`${currentKey}...`}</span>
              <br />
              Last updated: {currentKeyLastUpdated}
            </Typography>
          ) : (
            <Typography variant="body1">Generate your first API key</Typography>
          )}
          <LoadingButton
            variant="contained"
            onClick={currentKey ? handleConfirmationModalOpen : handleRenew}
            disabled={!editAccess}
            loading={keyGenerationIsLoading}
            loadingPosition="start"
            startIcon={<AutorenewIcon />}
            style={{
              width: "180px",
              alignSelf: "center",
              backgroundColor: keyGenerationIsLoading
                ? appColors.lightGrey
                : currentKey
                  ? appColors.error
                  : appColors.primary,
            }}
          >
            {currentKey ? `Regenerate Key` : "Generate Key"}
          </LoadingButton>
        </Layout.FlexBox>
        <KeyRenewConfirmationModal
          open={confirmationModalOpen}
          currentKey={currentKey}
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

const RestAPI = () => {
  return (
    <Layout.FlexBox
      key={"rest-api"}
      flexDirection="column"
      sx={{ maxWidth: 690, marginInline: 10 }}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h4" color="primary">
        REST API
      </Typography>
      <Typography variant="body1">
        You can use REST APIs to interact with AAQ from your own application,
        using the API key generated above as a Bearer token. Click on the link
        below to see the documentation.
      </Typography>
      <Layout.FlexBox
        flexDirection="column"
        alignItems={"center"}
        gap={sizes.baseGap}
      >
        <Typography variant="body1">
          <Button
            variant="outlined"
            color="primary"
            href="https://app.ask-a-question.com/api/docs"
            target="_blank"
            rel="noreferrer"
            endIcon={<OpenInNew />}
          >
            REST API Documentation
          </Button>
        </Typography>
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
