import React, { useEffect, useState } from "react";

import { Close, Send } from "@mui/icons-material";
import {
  Box,
  CircularProgress,
  IconButton,
  Paper,
  Typography,
  TextField,
  Fade,
  Avatar,
  Link,
  Modal,
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import PersonIcon from "@mui/icons-material/Person";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import TypingAnimation from "@/components/TypingAnimation";

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
  showLLMResponseToggle,
  getResponse,
}: {
  closeSidebar: () => void;
  showLLMResponseToggle: boolean;
  getResponse: (
    question: string,
    generateLLMResponse: boolean,
    session_id: number,
  ) => Promise<any>;
}) => {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<string>("");
  const [generateLLMResponse, setGenerateLLMResponse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<number>(
    Math.floor(Math.random() * 10000000),
  );
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
    setSessionId(Math.floor(Math.random() * 10000000));
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
    const responsePromise = getResponse(question, generateLLMResponse, sessionId);
    responsePromise
      .then((response) => {
        const responseMessage = {
          dateTime: new Date().toISOString(),
          type: "response",
          content: response.llm_response,
          json: response,
        } as ResponseMessage;
        setMessages((prevMessages) => [...prevMessages, responseMessage]);
      })

      .catch((error: Error) => {
        const errorMessage = "LLM Response failed.";
        setError(errorMessage);
        processErrorMessage(error);
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
          overflowY: "auto",
          flexGrow: 1,
          maxHeight: "500px",
        }}
      >
        {messages.map((message, index) => (
          <MessageBox key={index} {...message} />
        ))}
        {loading ? <TypingAnimation /> : null}
        <div ref={bottomRef}></div>
      </Box>
      <Box display="flex" justifyContent="flex-end" margin={1}>
        <Tooltip title="Reset conversation" aria-label="reset">
          <IconButton onClick={handleReset} sx={{ color: appColors.primary }}>
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
            sx={{ color: generateLLMResponse ? "#5480D1" : appColors.primary }}
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
  const avatarOrder = message.type === "question" ? 2 : 0;
  const contentOrder = 1;
  const messageBubbleStyles = {
    py: 2,
    px: 3,
    borderRadius: "20px",
    bgcolor:
      message.type === "question" ? appColors.secondary : appColors.dashboardSecondary,
    boxShadow: 0,
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
      <Avatar
        alt="FA"
        sx={{
          mx: 2,
          my: 1,
          width: sizes.icons.medium,
          height: sizes.icons.medium,
          bgcolor: "primary.main",
          order: avatarOrder,
        }}
      >
        {message.type === "question" ? <PersonIcon /> : <AutoAwesomeIcon />}
      </Avatar>
      <Box sx={messageBubbleStyles}>
        <Typography component={"span"} variant="body1" align="left">
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
            sx={{ cursor: "pointer", display: "block" }}
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
