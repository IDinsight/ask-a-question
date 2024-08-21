import { keyframes } from "@emotion/react";
import styled from "@emotion/styled";
import React, { useState } from "react";

import {
  Alert,
  Box,
  Checkbox,
  CircularProgress,
  Fade,
  FormControlLabel,
  IconButton,
  Link,
  Modal,
  Paper,
  Snackbar,
  Typography,
} from "@mui/material";
import TextField from "@mui/material/TextField";

import {
  Close,
  Send,
  ThumbDownAlt,
  ThumbDownOffAlt,
  ThumbUpAlt,
  ThumbUpOffAlt,
} from "@mui/icons-material";

import { sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";

interface SearchResult {
  index: string;
  title: string;
  text: string;
}

interface MessageData {
  dateTime: string;
  message: SearchResult[] | string;
  json: string;
}

type FeedbackSentimentType = "positive" | "negative";

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

const MessageBox = ({
  loading,
  messageData,
  onFeedbackSend,
}: {
  loading: boolean;
  messageData: MessageData;
  onFeedbackSend: (
    messageData: MessageData,
    feedbackSentiment: FeedbackSentimentType,
  ) => void;
}) => {
  const [jsonModalOpen, setJsonModalOpen] = useState<boolean>(false);
  const toggleJsonModal = (): void => setJsonModalOpen(!jsonModalOpen);
  const [thumbsUp, setThumbsUp] = useState<boolean>(false);
  const [thumbsDown, setThumbsDown] = useState<boolean>(false);

  const feedbackMapping = {
    positive: {
      state: thumbsUp,
      setState: setThumbsUp,
      onIcon: <ThumbUpAlt fontSize="small" />,
      offIcon: <ThumbUpOffAlt fontSize="small" />,
    },
    negative: {
      state: thumbsDown,
      setState: setThumbsDown,
      onIcon: <ThumbDownAlt fontSize="small" />,
      offIcon: <ThumbDownOffAlt fontSize="small" />,
    },
  };

  const handleFeedback = (feedbackType: FeedbackSentimentType) => {
    const { state, setState } = feedbackMapping[feedbackType];

    if (state) {
      console.log(`Already sent ${feedbackType} feedback`);
    } else {
      setState(true);
      return onFeedbackSend(messageData, feedbackType);
    }
  };

  const feedbackButtonStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
  };

  const renderResults = (content: SearchResult[]) => {
    return content.map((c: SearchResult) => (
      <Box sx={{ paddingBottom: sizes.smallGap }} key={c.index}>
        <Typography component={"span"} variant="subtitle2">
          {Number(c.index) + 1}: {c.title}
        </Typography>
        <Typography variant="body2">{c.text}</Typography>
      </Box>
    ));
  };

  if (loading) {
    return <TypingAnimation />;
  } else {
    return (
      <>
        <Box display="flex" flexDirection="column" justifyContent="center">
          <Typography
            component={"span"}
            variant="body1"
            align="left"
            sx={{ width: "100%" }}
          >
            {/* check if AI response or search results */}
            {typeof messageData.message === "string"
              ? messageData.message
              : renderResults(messageData.message)}
          </Typography>
          <Box
            style={{
              marginTop: "5px",
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
            }}
          >
            {messageData.json.hasOwnProperty("feedback_secret_key") ? (
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
        </Box>

        <Modal
          open={jsonModalOpen}
          onClose={toggleJsonModal}
          aria-labelledby="modal-modal-title"
          aria-describedby="modal-modal-description"
        >
          <Fade in={jsonModalOpen}>
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
                  <Close />
                </IconButton>
              </Box>
              <Typography
                component={"span"}
                id="modal-modal-description"
                sx={{ marginTop: 2 }}
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
                  {"json" in messageData
                    ? JSON.stringify(messageData.json, null, 2)
                    : "No JSON message found"}
                </pre>
              </Typography>
            </Box>
          </Fade>
        </Modal>
      </>
    );
  }
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

const QuestionAnsweringSidebar = ({ onClose }: { onClose: () => void }) => {
  const [question, setQuestion] = useState("");
  const handleQuestionChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setQuestion(event.target.value);
  };

  const [generateLLMResponse, setGenerateLLMResponse] = useState(false);
  const toggleGenerateLLMResponse = () => {
    setGenerateLLMResponse((prev) => !prev);
  };

  const [response, setResponse] = useState<MessageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth();

  const processEmbeddingsSearchResponse = (response: any) => {
    const contentResponse = response.search_results;
    const search_results: SearchResult[] = [];

    for (const key in contentResponse) {
      if (contentResponse.hasOwnProperty(key)) {
        const item = contentResponse[key];
        search_results.push({
          index: key,
          title: item.title,
          text: item.text,
        });
      }
    }

    setResponse({
      dateTime: new Date().toISOString(),
      message: search_results,
      json: response,
    });
  };

  const processLLMSearchResponse = (response: any) => {
    setResponse({
      dateTime: new Date().toISOString(),
      message: response.llm_response,
      json: response,
    });
  };

  // const processUrgencyDetection = (response: any) => {
  //   const isUrgent: boolean = response.is_urgent;
  //   const responseText =
  //     isUrgent === null
  //       ? `No response. Reason:  See <json> for details.`
  //       : isUrgent
  //         ? "Urgent 🚨"
  //         : "Not Urgent 🟢";

  //   setResponse({
  //     dateTime: new Date().toISOString(),
  //     message: responseText,
  //     json: response,
  //   })
  // };

  const processNotOKResponse = (response: any) => {
    const responseText = `Error: ${response.status}. See <json> for details.`;
    console.error(responseText, response);
    setResponse({
      dateTime: new Date().toISOString(),
      message: responseText,
      json: response,
    });
  };

  const processErrorMessage = (error: Error) => {
    setResponse({
      dateTime: new Date().toISOString(),
      message: "API call failed. See <json> for details.",
      json: `{error: ${error.message}}`,
    });
  };

  const handleSendClick = (question: string, generateLLMResponse: boolean) => {
    if (question === "") {
      return;
    }
    setLoading(true);
    if (token) {
      apiCalls
        .getSearch(question, generateLLMResponse, token)
        .then((response) => {
          if (response.status === 200) {
            if (generateLLMResponse) {
              processLLMSearchResponse(response);
            } else {
              processEmbeddingsSearchResponse(response);
            }
          } else {
            setError("Search failed.");
            processNotOKResponse(response);
            console.error(response);
          }
        })
        .catch((error: Error) => {
          setError("Search failed.");
          processErrorMessage(error);
          console.error(error);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  };

  const sendResponseFeedback = (
    messageData: MessageData,
    feedback_sentiment: FeedbackSentimentType,
  ) => {
    if (token) {
      // Assuming message.json is a JSON string. Parse it if necessary.
      const jsonResponse =
        typeof messageData.json === "string"
          ? JSON.parse(messageData.json)
          : messageData.json;

      const queryID = jsonResponse.query_id;
      const feedbackSecretKey = jsonResponse.feedback_secret_key;

      apiCalls
        .postResponseFeedback(
          queryID,
          feedback_sentiment,
          feedbackSecretKey,
          token,
        )
        .then((response) => {
          console.log("Feedback sent successfully: ", response.message);
        })
        .catch((error: Error) => {
          setError("Failed to send response feedback.");
          console.error(error);
        });
    }
  };

  const handleErrorClose = (
    event?: React.SyntheticEvent | Event,
    reason?: string,
  ) => {
    if (reason === "clickaway") {
      return;
    }
    setError(null);
  };

  return (
    <Paper
      elevation={2}
      sx={{
        padding: 3,
        paddingTop: 4,
        height: "95vh",
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        marginBottom={4}
      >
        <Typography variant="h6">Test Question Answering</Typography>
        <IconButton onClick={onClose}>
          <Close />
        </IconButton>
      </Box>
      <Box
        display="flex"
        flexDirection="column"
        border={1}
        borderColor="grey.400"
        borderRadius={1}
        padding={2}
      >
        <TextField
          variant="standard"
          placeholder="Ask a question..."
          fullWidth
          value={question}
          onChange={handleQuestionChange}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSendClick(question, generateLLMResponse);
            }
          }}
          InputProps={{ disableUnderline: true }}
        />
        <Box
          display="flex"
          flexDirection="row"
          justifyContent="space-between"
          paddingTop={2}
          paddingRight={1}
        >
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
          <IconButton
            onClick={() => handleSendClick(question, generateLLMResponse)}
            color={generateLLMResponse ? "info" : "primary"}
            disabled={loading ? true : false}
          >
            {loading ? <CircularProgress size={24} /> : <Send />}
          </IconButton>
        </Box>
      </Box>
      <Box paddingTop={5} paddingInline={3}>
        {response && (
          <MessageBox
            loading={loading}
            messageData={response}
            onFeedbackSend={sendResponseFeedback}
          />
        )}
      </Box>
    </Paper>
  );
};

export { ErrorSnackBar, QuestionAnsweringSidebar };
