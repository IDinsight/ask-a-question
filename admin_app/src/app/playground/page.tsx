"use client";

import { apiCalls } from "@/utils/api";
import React, { useEffect, useRef, useState } from "react";

import { Layout } from "@/components/Layout";
import {
  ErrorSnackBar,
  Message,
  MessageBox,
  MessageSkeleton,
  PersistentSearchBar,
  QueryType,
  FeedbackSentimentType,
  ResponseSummary,
  UserMessage,
  ResponseMessage,
} from "./components/PlaygroundComponents";
import { Box } from "@mui/material";
import { useAuth } from "@/utils/auth";
const Page = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null); // Ref to scroll to bottom of chat

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const processEmbeddingsSearchResponse = (response: any) => {
    const contentResponse = response.search_results;
    const summaries: ResponseSummary[] = [];

    for (const key in contentResponse) {
      if (contentResponse.hasOwnProperty(key)) {
        const item = contentResponse[key];
        summaries.push({
          index: key,
          title: item.title,
          text: item.text,
        });
      }
    }

    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: summaries,
        json: response,
      },
    ]);
  };

  const processLLMSearchResponse = (response: any) => {
    const llmResponse = response.llm_response;
    console.log(response);
    const responseText = llmResponse
      ? llmResponse
      : `No LLM response. Reason: "${response.error_message}". See <json> for details.`;

    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: responseText,
        json: response,
      },
    ]);
  };

  const processUrgencyDetection = (response: any) => {
    const isUrgent: boolean = response.is_urgent;
    const responseText =
      isUrgent === null
        ? `No response. Reason:  See <json> for details.`
        : isUrgent
        ? "Urgent 🚨"
        : "Not Urgent 🟢";

    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: responseText,
        json: response,
      },
    ]);
  };

  const processNotOKResponse = (response: any) => {
    const responseText = `Error: ${response.status}. See <json> for details.`;
    console.error(responseText, response);
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: responseText,
        json: response,
      },
    ]);
  };

  const processErrorMessage = (error: Error) => {
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        dateTime: new Date().toISOString(),
        type: "response",
        content: "API call failed. See <json> for details.",
        json: `{error: ${error.message}}`,
      },
    ]);
  };

  const queryTypeDisplayNameMapping = {
    "embeddings-search": "Content Search",
    "llm-response": "AI Response",
    "urgency-detection": "Urgency Detection",
  };

  const onSend = (queryText: string, queryType: QueryType) => {
    if (queryText === "") {
      return;
    }

    setLoading(true);

    if (token) {
      const queryTypeDisplayName =
        queryTypeDisplayNameMapping[queryType] || queryType;
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          dateTime: new Date().toISOString(),
          type: "question",
          content: `${queryText}`,
          queryType: `${queryTypeDisplayName}`,
        } as UserMessage,
      ]);
      if (queryType === "embeddings-search") {
        apiCalls
          .getEmbeddingsSearch(queryText, token)
          .then((response) => {
            if (response.status === 200) {
              processEmbeddingsSearchResponse(response);
            } else {
              setError("Embeddings search failed.");
              processNotOKResponse(response);
              console.error(response);
            }
          })
          .catch((error: Error) => {
            setError("Embeddings search failed.");
            processErrorMessage(error);
            console.error(error);
          })
          .finally(() => {
            setLoading(false);
          });
      } else if (queryType === "llm-response") {
        apiCalls
          .getLLMResponse(queryText, token)
          .then((response) => {
            if (response.status === 200) {
              processLLMSearchResponse(response);
            } else {
              setError("LLM response failed.");
              processNotOKResponse(response);
              console.error(response);
            }
          })
          .catch((error: Error) => {
            setError("LLM response failed.");
            processErrorMessage(error);
            console.error(error);
          })
          .finally(() => {
            setLoading(false);
          });
      } else if (queryType == "urgency-detection") {
        apiCalls
          .getUrgencyDetection(queryText, token)
          .then((response) => {
            processUrgencyDetection(response);
          })
          .catch((error: Error) => {
            setError("Urgency Detection failed.");
            processErrorMessage(error);
            console.error(error);
          })
          .finally(() => {
            setLoading(false);
          });
      } else {
        throw new Error("Invalid search option selected");
      }
    }
  };

  const sendResponseFeedback = (
    message: ResponseMessage,
    feedback_sentiment: FeedbackSentimentType,
  ) => {
    if (token) {
      // Assuming message.json is a JSON string. Parse it if necessary.
      const jsonResponse =
        typeof message.json === "string"
          ? JSON.parse(message.json)
          : message.json;

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
    <>
      <Layout.Spacer multiplier={4} />
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        sx={{ height: "90vh", width: "100%", pb: 10, mt: 4 }}
      >
        <Box
          mb={10}
          sx={{
            width: "100%",
            maxWidth: "lg",
            pb: 10,
          }}
        >
          {messages.map((message, index) => (
            <MessageBox
              key={index}
              message={message}
              onFeedbackSend={sendResponseFeedback}
            />
          ))}
          {loading && <MessageSkeleton />}
          <div ref={bottomRef} />
        </Box>
        <ErrorSnackBar message={error} onClose={handleErrorClose} />
        <Box sx={{ width: "100%", maxWidth: "lg", px: 2 }}>
          <PersistentSearchBar onSend={onSend} />
        </Box>
      </Box>
    </>
  );
};

export default Page;
