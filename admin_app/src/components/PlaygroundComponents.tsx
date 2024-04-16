import React, { useState } from "react";
import { SelectChangeEvent } from "@mui/material";

import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Avatar,
  Skeleton,
  Button,
  Modal,
  Link,
  Fade,
  InputAdornment,
  MenuItem,
  Select,
  IconButton,
  Snackbar,
  Alert,
} from "@mui/material";

import CloseIcon from "@mui/icons-material/Close";
import { appColors, appStyles, sizes } from "@/utils";
import TextField from "@mui/material/TextField";
import PersonIcon from "@mui/icons-material/Person";
import KeyIcon from "@mui/icons-material/Key";
import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Grid from "@mui/material/Grid";

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

interface MessageBoxProps {
  message: Message;
  index: number;
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
        left: 0,
        right: 0,
        background: "white",
        boxShadow: "0 -2px 10px rgba(0,0,0,0.2)",
        display: "flex",
        alignItems: "center",
        mx: 2,
      }}
    >
      <TextField
        fullWidth
        aria-label="search"
        placeholder="Ask a question..."
        value={queryText}
        onChange={(e) => setQueryText(e.target.value)}
        onKeyDown={handleKeyDown}
        sx={{ px: 0 }}
        InputProps={{
          style: {
            padding: 3,
            borderRadius: 0,
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
        <SmartToyIcon />
      </Avatar>
      <Skeleton
        sx={{
          mx: 2,
          my: 1,
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center", // Vertically centers the content if there's extra space
        }}
        variant="text"
        width={100}
        height={60}
      />
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
    flexGrow: 1,
    bgcolor: "background.paper",
    boxShadow: 24,
    p: 4,
  };
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "top", // Ensures vertical alignment is centered
        boxShadow: 0,
        py: 2,
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
        {message.type === "question" ? <PersonIcon /> : <SmartToyIcon />}
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
              <pre>
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
export type {
  Message,
  ResponseSummary,
  UserMessage,
  ResponseMessage,
  QueryType,
};
export {
  MessageBox,
  PersistentSearchBar,
  MessageSkeleton,
  ErrorSnackBar,
  ApiKeyDialog,
};
