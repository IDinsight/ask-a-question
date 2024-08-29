"use client";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { Box, CircularProgress, Typography } from "@mui/material";
import React, { useState } from "react";
import { format } from "date-fns";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { createNewApiKey } from "./api";
import { useAuth } from "@/utils/auth";

import { KeyRenewConfirmationModal, NewKeyModal } from "./components/APIKeyModals";
import ConnectionsGrid from "./components/ConnectionsGrid";
import { LoadingButton } from "@mui/lab";

const IntegrationsPage = () => {
  const [currAccessLevel, setCurrAccessLevel] = React.useState("readonly");
  const { token, accessLevel } = useAuth();

  React.useEffect(() => {
    setCurrAccessLevel(accessLevel);
  }, [accessLevel]);

  return (
    <Layout.FlexBox sx={{ alignItems: "center" }}>
      <Box
        sx={{
          paddingTop: 5,
          paddingBottom: 10,
          paddingInline: 4,
          maxWidth: "lg",
        }}
      >
        <KeyManagement token={token} editAccess={currAccessLevel === "fullaccess"} />
        <Layout.Spacer multiplier={3} />
        <Connections />
      </Box>
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
    <Layout.FlexBox key={"key-management"} flexDirection="column" gap={sizes.baseGap}>
      <Typography variant="h4" color="primary">
        Your API Key
      </Typography>
      <Layout.FlexBox
        flexDirection="column"
        justifyContent="space-between"
        gap={sizes.baseGap}
      >
        <Typography variant="body1" color={appColors.darkGrey}>
          You will need your API key to interact with AAQ from your chat manager. You
          can generate a new key here, but keep in mind that any old key is invalidated
          if a new key is created.
        </Typography>
        <Typography variant="body1" color={appColors.darkGrey}>
          Daily API limit is 100.{" "}
          <a
            href="https://docs.ask-a-question.com/latest/contact_us/"
            style={{
              textDecoration: "underline",
              textDecorationColor: appColors.darkGrey,
              color: appColors.darkGrey,
            }}
          >
            Contact us
          </a>{" "}
          for more.
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

const Connections = () => {
  return (
    <Layout.FlexBox
      key={"chat-managers"}
      flexDirection="column"
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h4" color="primary">
        Connections
      </Typography>
      <Typography variant="body1" color={appColors.darkGrey}>
        Click on the connection of your choice to see instructions on how to use it with
        AAQ.
      </Typography>
      <ConnectionsGrid />
    </Layout.FlexBox>
  );
};

export default IntegrationsPage;
