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
import { Button, Card, CardContent, Grid, Typography } from "@mui/material";
import React, { useState } from "react";
import typebotLogo from "./images/typebot_logo.svg";
import turnLogo from "./images/turn_logo.png";
import glificLogo from "./images/glific_logo.png";
import ChatManagerModal from "./components/ChatManagerModal";

interface ChatManagerInfo {
  logo_src: string;
  name: string;
  text: string;
}

interface CardImageProps {
  src: string;
  alt: string;
}

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
      <ChatManagersSection />
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
  // const [currentKey, setCurrentKey] = useState("qwerty...");
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
      setNewKey(data.new_api_key);
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
      flexDirection="column"
      sx={{ maxWidth: 690, marginInline: 10 }}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h5" color="primary" style={{ fontWeight: "bold" }}>
        Your API Key
      </Typography>
      <Layout.FlexBox
        flexDirection="column"
        // alignItems="center"
        justifyContent="space-between"
        gap={sizes.doubleBaseGap}
      >
        <Typography variant="body1">
          You will need your API key to interact with AAQ from your chat
          manager. You can generate or re-generate your key here.
        </Typography>
        <Button
          variant="contained"
          onClick={handleConfirmationModalOpen}
          disabled={!editAccess}
          startIcon={<AutorenewIcon />}
          style={{ width: "220px", alignSelf: "center" }}
        >
          Generate New Key
        </Button>
        <KeyRenewConfirmationModal
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

const ChatManagersSection = () => {
  return (
    <Layout.FlexBox
      key={"chat-managers"}
      flexDirection="column"
      sx={{ maxWidth: 1000, marginInline: 10 }}
      gap={sizes.doubleBaseGap}
    >
      <Typography variant="h5" color="primary" style={{ fontWeight: "bold" }}>
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

const ChatManagersGrid = () => {
  const chatManagers: ChatManagerInfo[] = [
    {
      logo_src: typebotLogo.src,
      name: "Typebot",
      text: "Typebot is a chat manager.",
    },
    {
      logo_src: turnLogo.src,
      name: "Turn",
      text: "Turn is a chat manager.",
    },
    {
      logo_src: glificLogo.src,
      name: "Glific",
      text: "Glific is a chat manager.",
    },
  ];

  const [modalItem, setModalItem] = useState<ChatManagerInfo | null>(null);
  const handleItemClick = (item: ChatManagerInfo) => {
    setModalItem(item);
  };

  return (
    <>
      <Grid container spacing={sizes.baseGap} style={{ minWidth: 220 }}>
        {chatManagers.map((item, index) => (
          <Grid
            item
            xs={12}
            md={6}
            key={index}
            onClick={() => handleItemClick(item)}
          >
            <CardImageComponent src={item.logo_src} alt={item.name} />
          </Grid>
        ))}
      </Grid>
      {modalItem && (
        <ChatManagerModal
          logo_src={modalItem.logo_src}
          title={modalItem.name}
          text={modalItem.text}
          open={Boolean(modalItem)}
          onClose={() => setModalItem(null)}
        />
      )}
    </>
  );
};

const CardImageComponent: React.FC<CardImageProps> = ({ src, alt }) => (
  <Card
    style={{
      justifyContent: "center",
      alignItems: "center",
      display: "flex",
    }}
  >
    <CardContent
      style={{
        height: "200px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <img
        src={src}
        alt={alt}
        style={{ height: "50%", padding: 15, display: "block" }}
      />
    </CardContent>
  </Card>
);

export default IntegrationsPage;
