import React, { useEffect, useState } from "react";

import TypingAnimation from "@/components/TypingAnimation";
import { Close, Send } from "@mui/icons-material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloseIcon from "@mui/icons-material/Close";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import {
  Avatar,
  Box,
  CircularProgress,
  Fade,
  IconButton,
  Link,
  Modal,
  Paper,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { appColors, sizes } from "@/utils";

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

const ChatSideBar = ({
  closeSidebar,
  getResponse,
  setSnackMessage,
}: {
  closeSidebar: () => void;
  getResponse: (question: string, session_id?: number) => Promise<any>;
  setSnackMessage: (message: string) => void;
}) => {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const bottomRef = React.useRef<HTMLDivElement>(null); // Ref to scroll to bottom of chat

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);
  const handleQuestionChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setQuestion(event.target.value);
  };

  const processErrorMessage = (error: Error) => {
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: "API call failed. See JSON for details.",
        json: `{error: ${error.message}}`,
      },
    ]);
  };
  const handleReset = () => {
    setMessages([]);
    setSessionId(null);
  };
  const handleSendClick = () => {
    setQuestion("");
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "question",
        content: question,
      } as UserMessage,
    ]);
    setLoading(true);
    const responsePromise = sessionId
      ? getResponse(question, sessionId)
      : getResponse(question);
    responsePromise
      .then((response) => {
        const responseMessage = {
          dateTime: new Date().toISOString(),
          type: "response",
          content: response.llm_response,
          json: response,
        } as ResponseMessage;

        setMessages((prevMessages) => [...prevMessages, responseMessage]);
        if (sessionId === null) {
          setSessionId(response.session_id);
        }
      })
      .catch((error: Error) => {
        processErrorMessage(error);
        setSnackMessage(error.message);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <Paper
      elevation={2}
      sx={{
        display: "flex",
        flexDirection: "column",
        padding: 3,
        paddingTop: 4,
        height: "100%",
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        marginBottom={4}
      >
        <Typography variant="h6">Test Chat</Typography>
        <IconButton onClick={closeSidebar}>
          <Close />
        </IconButton>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          flexGrow: 1,
          flexShrink: 1,
          height: 0,
          minHeight: "200px",
          padding: 2,
          overflowY: "auto",
        }}
      >
        {messages.map((message, index) => (
          <MessageBox key={index} {...message} />
        ))}
        {loading ? (
          <Box display="flex" alignItems="center">
            <Avatar
              alt="FA"
              sx={{
                mr: 1,
                my: 1,
                width: sizes.icons.medium,
                height: sizes.icons.medium,
                bgcolor: "primary.main",
              }}
            >
              <AutoAwesomeIcon />
            </Avatar>
            <TypingAnimation />
          </Box>
        ) : null}
        <div ref={bottomRef}></div>
      </Box>
      <Box display="flex" justifyContent="flex-end" margin={1}>
        <Tooltip title="Reset conversation" aria-label="reset">
          <IconButton
            onClick={handleReset}
            sx={{ color: appColors.primary }}
            disabled={loading}
          >
            <RestartAltIcon />
            <Typography variant="body2">Reset chat</Typography>
          </IconButton>
        </Tooltip>
      </Box>
      <Box
        sx={{
          padding: 2,
          border: 1,
          borderRadius: 1,
          borderColor: "grey.400",
        }}
      >
        <TextField
          variant="standard"
          placeholder="Ask a question..."
          fullWidth
          value={question}
          onChange={handleQuestionChange}
          onKeyDown={(event) => {
            if (event.key === "Enter" && loading === false) {
              handleSendClick();
            }
          }}
          InputProps={{ disableUnderline: true }}
        />
        <Box
          display="flex"
          flexDirection="row"
          justifyContent="flex-end"
          paddingTop={2}
        >
          <IconButton
            onClick={handleSendClick}
            sx={{ color: appColors.primary }}
            disabled={loading || question == "" ? true : false}
          >
            {loading ? <CircularProgress size={24} /> : <Send />}
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
};
const MessageBox = (message: Message) => {
  const [open, setOpen] = useState(false);
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
  const avatarOrder = message.type === "question" ? 2 : 0;
  const contentOrder = 1;
  const messageBubbleStyles = {
    py: 1.5,
    px: 2,
    borderRadius: "15px",
    bgcolor: message.type === "question" ? appColors.lightGrey : appColors.primary,
    color: message.type === "question" ? "black" : "white",
    maxWidth: "75%",
    wordBreak: "break-word",
    order: contentOrder,
  };
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: message.type === "question" ? "flex-end" : "flex-start",
        mb: 1,
      }}
    >
      {message.type === "response" && (
        <Avatar
          alt="FA"
          sx={{
            mr: 1,
            my: 1,
            width: sizes.icons.medium,
            height: sizes.icons.medium,
            bgcolor: "primary.main",
            alignSelf: "flex-end",
            order: avatarOrder,
          }}
        >
          <AutoAwesomeIcon />
        </Avatar>
      )}

      <Box sx={messageBubbleStyles}>
        <Typography component={"span"} variant="body1" align="left">
          {typeof message.content === "string" ? message.content : null}
        </Typography>
        {message.hasOwnProperty("json") && (
          <Link
            onClick={toggleJsonModal}
            variant="caption"
            align="right"
            underline="hover"
            sx={{ cursor: "pointer", display: "block", color: appColors.white }}
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
export { ChatSideBar };
