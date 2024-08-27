import React, { useState } from "react";

import { Box, Fade, IconButton, Link, Modal, Typography } from "@mui/material";
import {
  Close,
  ThumbDownAlt,
  ThumbDownOffAlt,
  ThumbUpAlt,
  ThumbUpOffAlt,
} from "@mui/icons-material";

import { sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { TestSidebar } from "@/components/SidebarCommon";
import TypingAnimation from "@/components/TypingAnimation";

interface SearchResult {
  index: string;
  title: string;
  text: string;
}

interface SearchResultList {
  search_results: SearchResult[];
}

interface SearchResultListWithLLM extends SearchResultList {
  llm_response: string;
}

interface SearchResponseBoxData {
  dateTime: string;
  parsedData: SearchResultList | SearchResultListWithLLM | string; // string is for error messages
  rawJson: string;
}

interface SearchResponseBoxProps {
  loading: boolean;
  responseBoxData: SearchResponseBoxData | null;
  token: string | null;
}

type FeedbackSentimentType = "positive" | "negative";

const getSearchResponse = (
  question: string,
  generateLLMResponse: boolean,
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setResponse: React.Dispatch<React.SetStateAction<SearchResponseBoxData | null>>,
  token: string | null,
) => {
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

    const searchResultList: SearchResultList = {
      search_results: search_results,
    };
    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: searchResultList,
      rawJson: response,
    });
  };

  const processLLMSearchResponse = (response: any) => {
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

    const llmResponse: SearchResultListWithLLM = {
      search_results: search_results,
      llm_response: response.llm_response,
    };

    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: llmResponse,
      rawJson: response,
    });
  };

  const processNotOKResponse = (response: any) => {
    const responseText = `Error: ${response.status}. See <json> for details.`;
    console.error(responseText, response);
    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: responseText,
      rawJson: response,
    });
  };

  const processErrorMessage = (error: Error) => {
    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: "API call failed. See <json> for details.",
      rawJson: `{error: ${error.message}}`,
    });
  };

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
          processNotOKResponse(response);
          console.error(response);
        }
      })
      .catch((error: Error) => {
        processErrorMessage(error);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      });
  }
};

const RenderSearchResponse = ({
  parsedData,
}: {
  parsedData: SearchResultList | SearchResultListWithLLM;
}) => {
  return (
    <>
      {"llm_response" in parsedData && (
        <Box display="flex" flexDirection="column">
          <Typography
            component={"span"}
            variant="body1"
            paddingBottom={sizes.doubleBaseGap}
          >
            {parsedData.llm_response}
          </Typography>
          <Typography component={"span"} variant="subtitle1">
            References
          </Typography>
        </Box>
      )}
      {parsedData["search_results"].map((c: SearchResult) => (
        <Box sx={{ paddingBottom: sizes.smallGap }} key={c.index}>
          <Typography component={"span"} variant="subtitle2">
            {Number(c.index) + 1}: {c.title}
          </Typography>
          <Typography variant="body2">{c.text}</Typography>
        </Box>
      ))}
    </>
  );
};

const SearchResponseBox: React.FC<SearchResponseBoxProps> = ({
  loading,
  responseBoxData,
  token,
}) => {
  if (!responseBoxData) {
    return;
  }

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

  const sendResponseFeedback = (
    responseBoxData: SearchResponseBoxData,
    feedback_sentiment: FeedbackSentimentType,
    token: string | null,
  ) => {
    if (token) {
      // Assuming parsedData.rawJson is a JSON string. Parse it if necessary.
      const jsonResponse =
        typeof responseBoxData.rawJson === "string"
          ? JSON.parse(responseBoxData.rawJson)
          : responseBoxData.rawJson;

      const queryID = jsonResponse.query_id;
      const feedbackSecretKey = jsonResponse.feedback_secret_key;

      apiCalls
        .postResponseFeedback(queryID, feedback_sentiment, feedbackSecretKey, token)
        .then((response) => {
          console.log("Feedback sent successfully: ", response.parsedData);
        })
        .catch((error: Error) => {
          console.error(error);
        });
    }
  };

  const handleFeedback = (feedbackType: FeedbackSentimentType) => {
    const { state, setState } = feedbackMapping[feedbackType];

    if (state) {
      console.log(`Already sent ${feedbackType} feedback`);
    } else {
      setState(true);
      return sendResponseFeedback(responseBoxData, feedbackType, token);
    }
  };

  const feedbackButtonStyle = {
    background: "none",
    border: "none",
    cursor: "pointer",
  };

  if (loading) {
    return <TypingAnimation />;
  } else {
    return (
      <>
        <Box display="flex" flexDirection="column" justifyContent="center">
          {/* if type is string, there was an error */}
          {typeof responseBoxData.parsedData === "string" ? (
            <Typography variant="body1">{responseBoxData.parsedData}</Typography>
          ) : (
            <RenderSearchResponse parsedData={responseBoxData.parsedData} />
          )}
          <Box
            style={{
              marginTop: "5px",
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
            }}
          >
            {responseBoxData.rawJson.hasOwnProperty("feedback_secret_key") ? (
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
                  {"rawJson" in responseBoxData
                    ? JSON.stringify(responseBoxData.rawJson, null, 2)
                    : "No JSON data found"}
                </pre>
              </Typography>
            </Box>
          </Fade>
        </Modal>
      </>
    );
  }
};

const SearchSidebar = ({ closeSidebar }: { closeSidebar: () => void }) => {
  return (
    <TestSidebar
      title="Test Question Answering"
      closeSidebar={closeSidebar}
      showLLMResponseToggle={true}
      handleSendClick={getSearchResponse}
      ResponseBox={SearchResponseBox}
    />
  );
};

export type { SearchResponseBoxData };
export { SearchSidebar };
