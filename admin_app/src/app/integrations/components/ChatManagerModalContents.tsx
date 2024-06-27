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
  // const videoId = 'typebot-video-id';
  return (
    <Layout.FlexBox flexDirection={"column"} gap={sizes.baseGap}>
      <Typography variant="body1">
        In Typebot, you can use the "HTTPS request" card to call AAQ and receive
        its response.
      </Typography>
      <Typography variant="body2" mb={sizes.baseGap}>
        To get a head start, you can download either of our templates below and
        load them into Typebot by going to "Create a typebot &gt; Import a file"
        and loading the downloaded template.
      </Typography>

      <Box display="flex" justifyContent="center">
        <Button variant="outlined" color="primary" startIcon={<DownloadIcon />}>
          AI RESPONSE WITH FEEDBACK
        </Button>
      </Box>
      <Box display="flex" justifyContent="center">
        <Button variant="outlined" color="primary" startIcon={<DownloadIcon />}>
          FAQ RESPONSE WITH FEEDBACK
        </Button>
      </Box>

      <Typography variant="body2" mt={sizes.doubleBaseGap}>
        Once loaded, you need to update the{" "}
        <code style={{ color: "tomato" }}>API_KEY</code> field inside the "HTTP
        request" card with your own API key before trying the flow.
      </Typography>

      {/* <Typography variant="body2">
        The video below walks you through how to set up Typebot with AAQ:
      </Typography>
      <Card variant="outlined" sx={{ mt: 2 }}>
        <CardContent>
          <YouTube videoId={videoId} />
        </CardContent>
      </Card> */}
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
          href="https://idinsight.github.io/aaq-core/integrations/chat_managers/turn.io/turn/"
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
          href="https://idinsight.github.io/aaq-core/integrations/chat_managers/glific/glific/"
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
