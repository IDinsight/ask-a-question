import React from "react";
// import YouTube from 'react-youtube';

import DownloadIcon from "@mui/icons-material/Download";
import { Box, Button, Typography } from "@mui/material";
import Link from "next/link";

import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";

// make one of these for each chat manager and use it to populate the modal
const ChatManagerContentExample: React.FC = () => {
  return (
    <Layout.FlexBox flexDirection={"column"} gap={sizes.doubleBaseGap}>
      <Typography variant="subtitle1">Example Title</Typography>
      <Typography
        variant="body2"
        sx={{
          overflowWrap: "break-word",
          hyphens: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        Example Text
      </Typography>
    </Layout.FlexBox>
  );
};

const TypebotModalContent: React.FC = () => {
  return (
    <Layout.FlexBox flexDirection={"column"} gap={sizes.baseGap}>
      <Typography variant="body1">
        In Typebot, you can use the "HTTPS request" card to call AAQ and receive
        its response.
      </Typography>
      <Typography variant="body1" mb={sizes.baseGap}>
        To get a head start, you can download our template below and load it
        into Typebot by going to "Create a typebot &gt; Import a file".
      </Typography>

      <Box display="flex" justifyContent="center">
        <Button
          variant="outlined"
          color="primary"
          startIcon={<DownloadIcon />}
          href="https://github.com/IDinsight/ask-a-question/blob/e75c7fec20373a8db5f5c8771b069aa7fac576a8/chat_managers/typebot/llm_response_flow.json"
          target="_blank"
          rel="noopener noreferrer"
        >
          AI RESPONSE WITH FEEDBACK
        </Button>
      </Box>

      <Typography variant="body1" mt={sizes.doubleBaseGap}>
        Once loaded, you need to update the{" "}
        <code style={{ color: "tomato" }}>API_KEY</code> field inside the "HTTP
        request" card with your own API key before trying the flow.
      </Typography>
    </Layout.FlexBox>
  );
};

const TurnModalContent: React.FC = () => {
  return (
    <Layout.FlexBox flexDirection={"column"} gap={sizes.doubleBaseGap}>
      <Typography variant="subtitle1">Under Construction...</Typography>
      <Typography
        variant="body2"
        sx={{
          overflowWrap: "break-word",
          hyphens: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        For now, please refer to our{" "}
        <Link
          href="https://docs.ask-a-question.com/integrations/chat_managers/turn.io/turn/"
          target="_blank"
          rel="noopener noreferrer"
        >
          documentation
        </Link>{" "}
        for instructions on how to connect Turn to AAQ.
      </Typography>
    </Layout.FlexBox>
  );
};

const GlificModalContent: React.FC = () => {
  return (
    <Layout.FlexBox flexDirection={"column"} gap={sizes.doubleBaseGap}>
      <Typography variant="subtitle1">Under Construction...</Typography>
      <Typography
        variant="body2"
        sx={{
          overflowWrap: "break-word",
          hyphens: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        For now, please refer to our{" "}
        <Link
          href="https://docs.ask-a-question.com/integrations/chat_managers/glific/glific/"
          target="_blank"
          rel="noopener noreferrer"
        >
          documentation
        </Link>{" "}
        for instructions on how to connect Glific to AAQ.
      </Typography>
    </Layout.FlexBox>
  );
};

export {
  ChatManagerContentExample,
  GlificModalContent,
  TurnModalContent,
  TypebotModalContent,
};
