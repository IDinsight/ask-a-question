"use client";

import React from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Avatar from "@mui/material/Avatar";
import { sizes } from "@/utils";
import PersonIcon from "@mui/icons-material/Person";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Grid from "@mui/material/Grid";

const PersistentSearchBar = () => (
  <Box
    sx={{
      position: "fixed",
      bottom: 10,
      left: 10,
      right: 10,
      background: "white",
      boxShadow: "0 -2px 10px rgba(0,0,0,0.2)",
    }}
  >
    <TextField fullWidth label="Search" variant="outlined" />
  </Box>
);

interface Message {
  dateTime: string;
  type: "question" | "response";
  text: string;
  json?: string;
}

const dummyTexts: Message[] = [
  {
    dateTime: "2021-08-04T14:00:00",
    type: "question",
    text: "who let the dogs out?",
  },
  {
    dateTime: "2021-08-04T14:00:00",
    type: "response",
    text: `Donald J. Trump watched anxiously from the White House in April 2018 as \
        news broke about federal agents searching the home of Michael D. Cohen, \
        the man entrusted to conceal some of the president’s deepest secrets. \
        After initially coming to Mr. Cohen’s defense, Mr. Trump washed his \
        hands of his fixer within weeks, brushing aside Mr. Cohen’s feelers \
        about a pardon and disavowing his legal bills. Mr. Trump took a \
        different tack when prosecutors shifted their scrutiny to Allen H. \
        Weisselberg, the Trump family’s longtime financial gatekeeper. Mr. \
        Trump’s company paid Mr. Weisselberg’s legal bills and awarded him a $2 \
        million severance, with a condition: He could not voluntarily cooperate \
        with any law enforcement agency.`,
    json: "{'hello': 'world'}",
  },
];

interface MessageBoxProps {
  message: Message;
  index: number;
}

const MessageBox = (message: Message) => (
  <Box
    sx={{
      display: "flex",
      boxShadow: 0,
      py: 2,
      background: "white",
      justifyContent: "flex-start",
    }}
  >
    <Box width="100%">
      <Box>
        <Avatar
          alt="FA"
          sx={{
            mx: 2,
            my: 2,
            width: sizes.icons.medium,
            height: sizes.icons.medium,
            bgcolor:
              message.type === "question" ? "primary.main" : "secondary.main",
          }}
        >
          {message.type === "question" ? <PersonIcon /> : <SmartToyIcon />}
        </Avatar>
      </Box>
      <Box
        display="flex"
        flexDirection="column"
        sx={{
          mx: 2,
          my: 2,
        }}
      >
        <Typography variant="body1" align="left">
          {message.text}
        </Typography>
        <Typography variant="caption" align="right">
          json
        </Typography>
      </Box>
    </Box>
  </Box>
);

const Page = () => (
  <Box>
    {dummyTexts.map((message, index) => (
      <MessageBox key={index} {...message} />
    ))}
    <PersistentSearchBar />
  </Box>
);
export default Page;
