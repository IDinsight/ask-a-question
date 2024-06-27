import React from "react";
// import YouTube from 'react-youtube';

import DownloadIcon from "@mui/icons-material/Download";
import { Box, Button, Typography } from "@mui/material";

import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";

// make one of these for each chat manager and use it to populate the modal
const ChatManagerContentExample: React.FC = () => {
  return (
    <Layout.FlexBox
      flexDirection={"column"}
      padding={sizes.baseGap}
      gap={sizes.doubleBaseGap}
    >
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
      <Box display="flex" justifyContent="start">
        <Button
          variant="contained"
          color="primary"
          startIcon={<DownloadIcon />}
          sx={{ mb: sizes.baseGap }}
        >
          Download Template
        </Button>
      </Box>
    </Layout.FlexBox>
  );
};

const TypebotModalContent: React.FC = () => {
  // const videoId = 'typebot-video-id';
  return (
    <Layout.FlexBox
      flexDirection={"column"}
      padding={sizes.baseGap}
      gap={sizes.baseGap}
    >
      <Typography variant="body1">
        In Typebot, you can use the "HTTPS request" card to call AAQ and receive
        its response.
      </Typography>
      <Typography variant="body2">
        To get a head start, you can download either of our templates below and
        load them into Typebot by going to "Create a typebot &gt; Import a file"
        and loading the downloaded template.
      </Typography>

      <Layout.Spacer />
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
      <Layout.Spacer />

      <Typography variant="body2" component="p" mt={2}>
        Once loaded, you need to update the "API_KEY" field inside the "HTTP
        request" card with your own API key before trying the flow.
      </Typography>

      {/* <Typography variant="body2" component="p" mt={2}>
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

export { ChatManagerContentExample, TypebotModalContent };
