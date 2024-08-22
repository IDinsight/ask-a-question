import React, { useState } from "react";

import {
  Box,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  IconButton,
  Paper,
  Typography,
} from "@mui/material";
import TextField from "@mui/material/TextField";

import { Close, Send } from "@mui/icons-material";

import { useAuth } from "@/utils/auth";

interface SearchResult {
  index: string;
  title: string;
  text: string;
}

interface SearchResultList {
  search_results: SearchResult[];
}

interface LLMResponse extends SearchResultList {
  llm_response: string;
}

interface MessageData {
  dateTime: string;
  message: SearchResultList | LLMResponse | string;
  json: string;
}

type FeedbackSentimentType = "positive" | "negative";

interface ResponseBoxProps {
  loading: boolean;
  messageData: MessageData;
  onFeedbackSend: (
    messageData: MessageData,
    feedbackSentiment: FeedbackSentimentType,
  ) => void;
}

const TestSidebar = ({
  closeSidebar,
  showLLMResponseToggle,
  handleSendClick,
  sendResponseFeedback,
  ResponseBox,
}: {
  closeSidebar: () => void;
  showLLMResponseToggle: boolean;
  handleSendClick: (
    question: string,
    generateLLMResponse: boolean,
    setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    setResponse: React.Dispatch<React.SetStateAction<MessageData | null>>,
    token: string | null,
  ) => void;
  sendResponseFeedback: (
    messageData: MessageData,
    feedbackSentiment: FeedbackSentimentType,
    token: string | null,
  ) => void;
  ResponseBox: React.FC<ResponseBoxProps>;
}) => {
  // question management
  const [question, setQuestion] = useState("");
  const handleQuestionChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setQuestion(event.target.value);
  };

  // response management
  const { token } = useAuth();
  const [response, setResponse] = useState<MessageData | null>(null);
  const [loading, setLoading] = useState(false);

  // AI response generation management
  const [generateLLMResponse, setGenerateLLMResponse] = useState(false);
  const toggleGenerateLLMResponse = () => {
    setGenerateLLMResponse((prev) => !prev);
  };

  const handleFeedbackSend = (
    messageData: MessageData,
    feedbackSentiment: FeedbackSentimentType,
  ) => {
    sendResponseFeedback(messageData, feedbackSentiment, token);
  };

  return (
    <Paper
      elevation={2}
      sx={{
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
        <Typography variant="h6">Test Question Answering</Typography>
        <IconButton onClick={closeSidebar}>
          <Close />
        </IconButton>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
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
            if (event.key === "Enter") {
              handleSendClick(
                question,
                generateLLMResponse,
                setLoading,
                setResponse,
                token,
              );
            }
          }}
          InputProps={{ disableUnderline: true }}
        />
        <Box
          display="flex"
          flexDirection="row"
          justifyContent="space-between"
          paddingTop={2}
        >
          {showLLMResponseToggle && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={generateLLMResponse}
                  onChange={toggleGenerateLLMResponse}
                  color="info"
                />
              }
              label="Also generate AI response"
            />
          )}
          <IconButton
            onClick={() =>
              handleSendClick(
                question,
                generateLLMResponse,
                setLoading,
                setResponse,
                token,
              )
            }
            color={generateLLMResponse ? "info" : "primary"}
            disabled={loading || question == "" ? true : false}
          >
            {loading ? <CircularProgress size={24} /> : <Send />}
          </IconButton>
        </Box>
      </Box>
      <Box
        sx={{
          marginTop: 4,
          marginBottom: 4,
          padding: 4,
          overflowY: "scroll",
          border: 1,
          borderRadius: 1,
          borderColor: "grey.400",
          flexGrow: 1,
          height: "60vh",
        }}
      >
        {response && (
          <ResponseBox
            loading={loading}
            messageData={response}
            onFeedbackSend={handleFeedbackSend}
          />
        )}
      </Box>
    </Paper>
  );
};

export { TestSidebar };
