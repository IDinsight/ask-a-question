import { PlayArrow } from "@mui/icons-material";
import { Typography } from "@mui/material";
import React from "react";
const chats = [
  {
    sender: "user",
    message: "Hello, how can I help you?",
  },
  {
    sender: "bot",
    message: "I am a bot",
  },
  {
    sender: "user",
    message: "I need help with my account",
  },
  {
    sender: "bot",
    message: "I can help you with that",
  },
];
const ChatBox = () => {
  return (
    <Typography variant="h3">
      <PlayArrow /> Chat with us
    </Typography>
  );
};

export default ChatBox;
