import React, { useState } from "react";
import {
  IconSearch,
  IconThumbDown,
  IconThumbDownFilled,
  IconThumbUp,
  IconThumbUpFilled,
} from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { apiCalls } from "@/utils/api";
import { TestSidebar } from "@/components/SidebarCommon";
import TypingAnimation from "@/components/TypingAnimation";
import { JsonDialog } from "./JsonDialog";

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
        if (response?.status === 200) {
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
    <div className="flex flex-col gap-4">
      {"llm_response" in parsedData && (
        <>
          <p className="leading-relaxed">{parsedData.llm_response}</p>
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            References
          </h3>
        </>
      )}
      <ol className="flex flex-col gap-3">
        {parsedData["search_results"].map((c: SearchResult) => (
          <li key={c.index} className="flex flex-col gap-1">
            <span className="font-medium">
              {Number(c.index) + 1}: {c.title}
            </span>
            <span className="text-muted-foreground">{c.text}</span>
          </li>
        ))}
      </ol>
    </div>
  );
};

const SearchResponseBox: React.FC<SearchResponseBoxProps> = ({
  loading,
  responseBoxData,
  token,
}) => {
  // Hooks must run before any early return.
  const [jsonModalOpen, setJsonModalOpen] = useState<boolean>(false);
  const [thumbsUp, setThumbsUp] = useState<boolean>(false);
  const [thumbsDown, setThumbsDown] = useState<boolean>(false);

  if (loading) {
    return <TypingAnimation />;
  }

  if (!responseBoxData) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconSearch />
          </EmptyMedia>
          <EmptyTitle>Test your content</EmptyTitle>
          <EmptyDescription>
            Ask a question to see which contents the search service returns.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  const feedbackMapping = {
    positive: { state: thumbsUp, setState: setThumbsUp },
    negative: { state: thumbsDown, setState: setThumbsDown },
  };

  const sendResponseFeedback = (
    responseBoxData: SearchResponseBoxData,
    feedback_sentiment: FeedbackSentimentType,
    token: string | null,
  ) => {
    if (token) {
      // rawJson is usually the parsed response object, but may be a string.
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

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* A string means the request failed */}
        {typeof responseBoxData.parsedData === "string" ? (
          <p>{responseBoxData.parsedData}</p>
        ) : (
          <RenderSearchResponse parsedData={responseBoxData.parsedData} />
        )}
        <div className="flex items-center justify-end gap-1">
          {responseBoxData.rawJson.hasOwnProperty("feedback_secret_key") ? (
            <>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Helpful"
                aria-pressed={thumbsUp}
                onClick={() => handleFeedback("positive")}
              >
                {thumbsUp ? <IconThumbUpFilled /> : <IconThumbUp />}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Not helpful"
                aria-pressed={thumbsDown}
                onClick={() => handleFeedback("negative")}
              >
                {thumbsDown ? <IconThumbDownFilled /> : <IconThumbDown />}
              </Button>
            </>
          ) : null}
          <Button variant="link" size="xs" onClick={() => setJsonModalOpen(true)}>
            {"<json>"}
          </Button>
        </div>
      </div>

      <JsonDialog
        open={jsonModalOpen}
        onOpenChange={setJsonModalOpen}
        json={responseBoxData.rawJson}
      />
    </>
  );
};

const SearchSidebar = ({ closeSidebar }: { closeSidebar: () => void }) => {
  return (
    <TestSidebar
      title="Test Search"
      closeSidebar={closeSidebar}
      showLLMResponseToggle={true}
      handleSendClick={getSearchResponse}
      ResponseBox={SearchResponseBox}
    />
  );
};

export type { SearchResponseBoxData };
export { SearchSidebar };
