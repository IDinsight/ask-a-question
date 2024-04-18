import { keyframes } from "@emotion/react";
import styled from "@emotion/styled";
import { SelectChangeEvent } from "@mui/material";
import React, { useState } from "react";

import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
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
import KeyIcon from "@mui/icons-material/Key";
import PersonIcon from "@mui/icons-material/Person";
import SendIcon from "@mui/icons-material/Send";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import TextField from "@mui/material/TextField";

type QueryType = "embeddings-search" | "llm-response";

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
}

interface ResponseMessage extends BaseMessage {
  type: "response";
  content: ResponseSummary[] | string;
  json: string;
}

type Message = UserMessage | ResponseMessage;

const PersistentSearchBar = ({
  onSend,
  openApiKeyDialog,
}: {
  onSend: (queryText: string, queryType: QueryType) => void;
  openApiKeyDialog: () => void;
}) => {
  const [selectedOption, setSelectedOption] =
    useState<QueryType>("embeddings-search");
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
          boxShadow: "0 -2px 10px rgba(0,0,0,0.2)",

          borderRadius: "12px",
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
              borderRadius: "12px",
            },
            startAdornment: (
              <InputAdornment position="start" sx={{ margin: 0 }}>
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
                    minWidth: 160,
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
                    <Typography variant="caption">Embedding Search</Typography>
                  </MenuItem>
                  <MenuItem value="llm-response">
                    <Typography variant="caption">LLM Search</Typography>
                  </MenuItem>
                </Select>

                <IconButton
                  aria-label="toggle password visibility"
                  edge="start"
                  sx={{
                    mx: 0.3,
                  }}
                  onClick={openApiKeyDialog}
                >
                  <KeyIcon />
                </IconButton>
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

// For 3-dot typing animation
const typing = keyframes`
  from { opacity: 0 }
  to { opacity: 1 }
`;
const Fader = styled("div")`
  animation: ${typing} 1s infinite;
  &:nth-of-type(2) {
    animation-delay: 0.2s;
  }
  &:nth-of-type(3) {
    animation-delay: 0.4s;
  }
`;
const TypingAnimation = () => {
  return (
    <Box sx={{ display: "flex", fontSize: "1.3rem" }}>
      <Fader>.</Fader>
      <Fader>.</Fader>
      <Fader>.</Fader>
    </Box>
  );
};

const MessageSkeleton = () => {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "top", // Ensures vertical alignment is centered
        boxShadow: 0,
        py: 2,
        px: 2,
        background: "white",
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

const MessageBox = (message: Message) => {
  const [open, setOpen] = useState(false);

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
  const modalStyle = {
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: "80%",
    maxHeight: "80%",
    flexGrow: 1,
    bgcolor: "background.paper",
    boxShadow: 24,
    p: 4,
    overflow: "scroll",
    borderRadius: "10px",
  };
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "top", // Ensures vertical alignment is centered
        boxShadow: 0,
        py: 2,
        px: 2,
        background: "white",
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
          bgcolor:
            message.type === "question" ? "primary.main" : "secondary.main",
        }}
      >
        {message.type === "question" ? <PersonIcon /> : <AutoAwesomeIcon />}
      </Avatar>
      <Box
        sx={{
          mx: 2,
          my: 1,
          flexGrow: 1, // Allows this box to grow and fill available space
          display: "flex",
          flexDirection: "column",
          justifyContent: "center", // Vertically centers the content if there's extra space
        }}
      >
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
        {message.hasOwnProperty("json") && (
          <Link
            onClick={toggleJsonModal}
            variant="caption"
            align="right"
            underline="hover"
            sx={{ cursor: "pointer" }}
          >
            {"<json>"}
          </Link>
        )}
      </Box>

      <Modal
        open={open}
        onClose={toggleJsonModal}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <Fade in={!!open}>
          <Box sx={modalStyle}>
            <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
              <IconButton onClick={toggleJsonModal}>
                <CloseIcon />
              </IconButton>
            </Box>
            <Typography
              component={"span"}
              id="modal-modal-description"
              sx={{ mt: 2 }}
            >
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
      <Alert
        onClose={onClose}
        severity="error"
        variant="filled"
        sx={{ width: "100%" }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
};

const ApiKeyDialog = ({
  open,
  handleClose,
  currApiKey,
  handleSave,
}: {
  open: boolean;
  handleClose: () => void;
  currApiKey: string | null;
  handleSave: (token: string) => void;
}) => {
  const [apiKey, setApiKey] = useState<string>(currApiKey ? currApiKey : "");

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      aria-labelledby="form-dialog-title"
    >
      <DialogContent>
        <DialogContentText sx={{ my: 2 }}>
          Please enter the key to access the search APIs.
        </DialogContentText>
        <TextField
          autoFocus
          margin="dense"
          id="name"
          label="API Key"
          type="text"
          fullWidth
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={() => handleSave(apiKey)}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};
export {
  ApiKeyDialog,
  ErrorSnackBar,
  MessageBox,
  MessageSkeleton,
  PersistentSearchBar,
};
export type {
  Message,
  QueryType,
  ResponseMessage,
  ResponseSummary,
  UserMessage,
};
