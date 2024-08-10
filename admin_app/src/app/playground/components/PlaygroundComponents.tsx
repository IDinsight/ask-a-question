import { SelectChangeEvent } from "@mui/material";
import React, { useState } from "react";

import {
  Alert,
  Avatar,
  Box,
  Fade,
  IconButton,
  InputAdornment,
  Link,
  MenuItem,
  Modal,
  Select,
  Snackbar,
  Typography,
} from "@mui/material";

import { appColors, sizes } from "@/utils";
import CloseIcon from "@mui/icons-material/Close";
import PersonIcon from "@mui/icons-material/Person";
import SendIcon from "@mui/icons-material/Send";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import TextField from "@mui/material/TextField";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import ThumbUpOffAltIcon from "@mui/icons-material/ThumbUpOffAlt";
import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";
import ThumbDownOffAltIcon from "@mui/icons-material/ThumbDownOffAlt";
import TypingAnimation from "@/components/Common";

type QueryType = "embeddings-search" | "llm-response" | "urgency-detection";

type FeedbackSentimentType = "positive" | "negative";

interface ResponseSummary {
  index: string;
  title: string;
  text: string;
}

interface BaseMessage {
  dateTime: string;
  type: "question" | "response";
}

interface UserMessage extends BaseMessage {
  type: "question";
  content: string;
  queryType: string;
}

interface ResponseMessage extends BaseMessage {
  type: "response";
  content: ResponseSummary[] | string;
  json: string;
}

type Message = UserMessage | ResponseMessage;

const PersistentSearchBar = ({
  onSend,
}: {
  onSend: (queryText: string, queryType: QueryType) => void;
}) => {
  const [selectedOption, setSelectedOption] = useState<QueryType>("embeddings-search");
  const [queryText, setQueryText] = useState<string>("");

  const handleSelectChange = (event: SelectChangeEvent<unknown>) => {
    setSelectedOption(event.target.value as QueryType);
  };
  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      onSend(queryText, selectedOption);
      setQueryText("");
    }
  };
  return (
    <Box
      sx={{
        position: "fixed",
        bottom: 10,
        width: "100%",
        maxWidth: "lg",
        left: "50%",
        transform: "translateX(-50%)",
        px: 2,
      }}
    >
      <Box
        sx={{
          display: "flex",
          background: "white",
          boxShadow: "0 0px 5px rgba(0,0,0,0.2)",
          borderRadius: "10px",
        }}
      >
        <TextField
          fullWidth
          aria-label="search"
          placeholder="Ask a question..."
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyDown={handleKeyDown}
          sx={{
            width: "100%",
          }}
          InputProps={{
            style: {
              borderRadius: "10px",
            },
            startAdornment: (
              <InputAdornment position="start" sx={{ margin: 0, marginRight: 1 }}>
                <Select
                  value={selectedOption}
                  onChange={handleSelectChange}
                  displayEmpty
                  inputProps={{ "aria-label": "Without label" }}
                  size="small"
                  sx={{
                    marginRight: 1,
                    marginTop: 2,
                    marginBottom: 2,
                    marginLeft: 0,
                    width: 170,
                    background: "paper",
                    "& .MuiOutlinedInput-notchedOutline": {
                      borderRight: 1,
                      borderLeft: 0,
                      borderTop: 0,
                      borderBottom: 0,
                      borderRadius: 0,
                      borderColor: appColors.lightGrey,
                      "& .Mui-focused": {
                        borderColor: "transparent",
                      },
                    },
                  }}
                >
                  <MenuItem value="embeddings-search" autoFocus={true}>
                    <Typography variant="body2">Content Search</Typography>
                  </MenuItem>
                  <MenuItem value="llm-response">
                    <Typography variant="body2">AI Response</Typography>
                  </MenuItem>
                  <MenuItem value="urgency-detection">
                    <Typography variant="body2">Urgency Detection</Typography>
                  </MenuItem>
                </Select>
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end" sx={{ pr: 2 }}>
                <IconButton
                  onClick={() => {
                    onSend(queryText, selectedOption);
                    setQueryText("");
                  }}
                  edge="end"
                >
                  <SendIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Box>
    </Box>
  );
};

const MessageSkeleton = () => {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "top",
        boxShadow: 0,
        py: 2,
        px: 2,
        width: "100%",
      }}
    >
      <Avatar
        alt="FA"
        sx={{
          mx: 2,
          my: 1,
          width: sizes.icons.medium,
          height: sizes.icons.medium,
          bgcolor: "secondary.main",
        }}
      >
        <AutoAwesomeIcon />
      </Avatar>
      <Box
        sx={{
          display: "flex",
          py: 0.5,
          px: 1.5,
        }}
      >
        <TypingAnimation />
      </Box>
    </Box>
  );
};

const MessageBox = ({
  message,
  onFeedbackSend,
}: {
  message: Message;
  onFeedbackSend: (
    message: ResponseMessage,
    feedbackSentiment: FeedbackSentimentType,
  ) => void;
}) => {
  const [open, setOpen] = useState(false);
  const [thumbsUp, setThumbsUp] = useState(false);
  const [thumbsDown, setThumbsDown] = useState(false);

  const feedbackMapping = {
    positive: {
      state: thumbsUp,
      setState: setThumbsUp,
      onIcon: <ThumbUpAltIcon fontSize="small" />,
      offIcon: <ThumbUpOffAltIcon fontSize="small" />,
    },
    negative: {
      state: thumbsDown,
      setState: setThumbsDown,
      onIcon: <ThumbDownAltIcon fontSize="small" />,
      offIcon: <ThumbDownOffAltIcon fontSize="small" />,
    },
  };

  const handleFeedback = (feedbackType: FeedbackSentimentType) => {
    const { state, setState } = feedbackMapping[feedbackType];

    if (state) {
      console.log(`Already sent ${feedbackType} feedback`);
    } else {
      setState(true);
      return onFeedbackSend(message as ResponseMessage, feedbackType);
    }
  };

  const feedbackButtonStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
  };

  const renderResults = (content: ResponseSummary[]) => {
    return content.map((c: ResponseSummary) => (
      <Box sx={{ pb: sizes.smallGap }} key={c.index}>
        <Typography component={"span"} variant="subtitle2">
          {Number(c.index) + 1}: {c.title}
        </Typography>
        <Typography variant="body2">{c.text}</Typography>
      </Box>
    ));
  };
  const toggleJsonModal = () => setOpen(!open);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "top",
        boxShadow: 0,
        py: 2,
        px: 2,
        width: "100%",
      }}
    >
      <Avatar
        alt="FA"
        sx={{
          mx: 2,
          my: 1,
          width: sizes.icons.medium,
          height: sizes.icons.medium,
          bgcolor: message.type === "question" ? "primary.main" : "secondary.main",
        }}
      >
        {message.type === "question" ? <PersonIcon /> : <AutoAwesomeIcon />}
      </Avatar>
      <Box
        sx={{
          mx: 2,
          my: 1,
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        {message.type === "question" && (
          <Typography component={"span"} variant="body2" align="left" color="grey">
            {`${(message as UserMessage).queryType}`}
          </Typography>
        )}
        <Typography
          component={"span"}
          variant="body1"
          align="left"
          sx={{ width: "100%" }}
        >
          {typeof message.content === "string"
            ? message.content
            : renderResults(message.content)}
        </Typography>
        {message.type == "response" ? (
          <Box
            style={{
              marginTop: "5px",
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
            }}
          >
            {message.json.hasOwnProperty("feedback_secret_key") ? (
              <Box sx={{ marginRight: "8px" }}>
                <IconButton
                  aria-label="thumbs up"
                  onClick={() => handleFeedback("positive")}
                  style={feedbackButtonStyle}
                >
                  {feedbackMapping.positive.state == true
                    ? feedbackMapping.positive.onIcon
                    : feedbackMapping.positive.offIcon}
                </IconButton>
                <IconButton
                  aria-label="thumbs down"
                  onClick={() => handleFeedback("negative")}
                  style={feedbackButtonStyle}
                >
                  {feedbackMapping.negative.state == true
                    ? feedbackMapping.negative.onIcon
                    : feedbackMapping.negative.offIcon}
                </IconButton>
              </Box>
            ) : null}
            <Link
              onClick={toggleJsonModal}
              variant="caption"
              align="right"
              underline="hover"
              sx={{ cursor: "pointer" }}
            >
              {"<json>"}
            </Link>
          </Box>
        ) : null}
      </Box>

      <Modal
        open={open}
        onClose={toggleJsonModal}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <Fade in={!!open}>
          <Box
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: "80%",
              maxHeight: "80%",
              flexGrow: 1,
              p: 4,
              boxShadow: 24,
              overflow: "scroll",
              borderRadius: "10px",
              bgcolor: "background.paper",
            }}
          >
            <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
              <IconButton onClick={toggleJsonModal}>
                <CloseIcon />
              </IconButton>
            </Box>
            <Typography component={"span"} id="modal-modal-description" sx={{ mt: 2 }}>
              <pre
                style={{
                  backgroundColor: "#f5f5f5",
                  border: "1px solid #ccc",
                  padding: "10px",
                  borderRadius: "10px",
                  overflowX: "auto",
                  fontFamily: "Courier, monospace",
                }}
              >
                {"json" in message
                  ? JSON.stringify(message.json, null, 2)
                  : "No JSON message found"}
              </pre>
            </Typography>
          </Box>
        </Fade>
      </Modal>
    </Box>
  );
};

const ErrorSnackBar = ({
  message,
  onClose,
}: {
  message: string | null;
  onClose: () => void;
}) => {
  return (
    <Snackbar
      open={message ? true : false}
      autoHideDuration={6000}
      onClose={onClose}
      anchorOrigin={{ vertical: "top", horizontal: "right" }}
    >
      <Alert onClose={onClose} severity="error" variant="filled" sx={{ width: "100%" }}>
        {message}
      </Alert>
    </Snackbar>
  );
};

export { ErrorSnackBar, MessageBox, MessageSkeleton, PersistentSearchBar };
export type {
  Message,
  QueryType,
  FeedbackSentimentType,
  ResponseMessage,
  ResponseSummary,
  UserMessage,
};
