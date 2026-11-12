import React, { createContext, useContext, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  IconBraces,
  IconChevronRight,
  IconSearch,
  IconThumbDown,
  IconThumbDownFilled,
  IconThumbUp,
  IconThumbUpFilled,
} from "@tabler/icons-react";

import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Message, MessageContent } from "@/components/ui/message";
import { Trace, TraceLine, TraceTitle } from "@/components/ui/trace";
import { TestSidebar } from "@/components/common/SidebarCommon";
import { JsonDialog } from "@/components/common/JsonDialog";
import {
  AssistantAvatar,
  IconButtonWithTooltip,
} from "@/components/common/AssistantParts";
import { MARKDOWN_CLASSES } from "./ContentModal";

/** One content card returned by the search service. */
interface SearchResult {
  index: string; // rank as returned by the API ("0" is the best match)
  id: number; // content_id of the card
  title: string;
  text: string;
}

interface SearchResultList {
  search_results: SearchResult[];
}

interface SearchResultListWithLLM extends SearchResultList {
  llm_response: string | null;
}

interface SearchResponseBoxData {
  dateTime: string;
  parsedData: SearchResultList | SearchResultListWithLLM | string; // string is for error messages
  rawJson: any;
}

interface SearchResponseBoxProps {
  loading: boolean;
  responseBoxData: SearchResponseBoxData | null;
  token: string | null;
}

type FeedbackSentimentType = "positive" | "negative";

/** Runs a test search; resolves with `{status, ...body}` (see useSearchMutation). */
type SearchFn = (question: string, generateLLMResponse: boolean) => Promise<any>;

/** Sends thumbs up/down feedback on a search response. */
type SendFeedbackFn = (args: {
  queryId: number;
  sentiment: FeedbackSentimentType;
  feedbackSecretKey: string;
}) => Promise<any>;

/**
 * TestSidebar (shared with urgency rules) renders `ResponseBox` itself, so the
 * feedback callback reaches SearchResponseBox through context rather than props.
 */
const SendFeedbackContext = createContext<SendFeedbackFn | null>(null);

/**
 * Turn the backend's `search_results` (an object keyed "0", "1", ...) into a
 * list ordered by rank.
 */
const toSearchResults = (contentResponse: unknown): SearchResult[] => {
  if (!contentResponse || typeof contentResponse !== "object") return [];
  return Object.entries(contentResponse as Record<string, any>)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([key, item]) => ({
      index: key,
      id: item.id,
      title: item.title,
      text: item.text,
    }));
};

const getSearchResponse = (
  search: SearchFn,
  question: string,
  generateLLMResponse: boolean,
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setResponse: React.Dispatch<React.SetStateAction<SearchResponseBoxData | null>>,
  // Passed in by TestSidebar; only used to skip sending while logged out.
  token: string | null,
) => {
  if (question === "" || !token) {
    return;
  }
  setLoading(true);
  search(question, generateLLMResponse)
    // getSearch spreads the response body onto its result, but its declared
    // type doesn't list those fields, so read it as `any`
    .then((response: any) => {
      if (response?.status === 200) {
        const search_results = toSearchResults(response.search_results);
        setResponse({
          dateTime: new Date().toISOString(),
          // Only include the answer when it was requested, so the UI knows
          // whether to show the answer block at all
          parsedData: generateLLMResponse
            ? { search_results, llm_response: response.llm_response }
            : { search_results },
          rawJson: response,
        });
      } else {
        console.error(`Error: ${response?.status}`, response);
        setResponse({
          dateTime: new Date().toISOString(),
          parsedData: `The search service returned an error (${response?.status}). Open the raw response for details.`,
          rawJson: response,
        });
      }
    })
    .catch((error: Error) => {
      console.error(error);
      setResponse({
        dateTime: new Date().toISOString(),
        parsedData: "The search request failed. Open the raw response for details.",
        rawJson: { error: error.message },
      });
    })
    .finally(() => {
      setLoading(false);
    });
};

/**
 * Compact, clickable preview of a reference: rank, title and the first two
 * lines of text. Clicking opens the full card in a dialog.
 */
const ReferenceCard = ({ result }: { result: SearchResult }) => {
  const [open, setOpen] = useState(false);
  const rank = Number(result.index) + 1;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group/ref flex w-full min-w-0 flex-col gap-1 border bg-background px-3 py-2.5 text-left transition-colors outline-none hover:border-foreground/20 hover:bg-muted/50 focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
      >
        <span className="flex w-full min-w-0 items-center gap-2">
          <span className="flex size-5 shrink-0 items-center justify-center bg-muted text-[10px] font-medium text-muted-foreground tabular-nums">
            {rank}
          </span>
          <span className="min-w-0 flex-1 truncate font-medium">{result.title}</span>
          <IconChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover/ref:translate-x-0.5" />
        </span>
        <span className="line-clamp-2 text-xs text-muted-foreground">
          {result.text}
        </span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex max-h-[80vh] flex-col gap-4 p-6 sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="pr-6 text-base font-semibold">
              {result.title}
            </DialogTitle>
            <DialogDescription>
              Reference {rank} · Content #{result.id}
            </DialogDescription>
          </DialogHeader>
          <div className={`min-h-0 flex-1 overflow-y-auto text-sm ${MARKDOWN_CLASSES}`}>
            <ReactMarkdown>{result.text}</ReactMarkdown>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

const RenderSearchResponse = ({
  parsedData,
}: {
  parsedData: SearchResultList | SearchResultListWithLLM;
}) => {
  const results = parsedData.search_results;

  return (
    <div className="flex flex-col gap-5">
      {"llm_response" in parsedData && (
        <Message>
          <AssistantAvatar />
          <MessageContent>
            <Bubble variant="outline" className="max-w-full">
              <BubbleContent className="text-sm">
                {parsedData.llm_response ? (
                  <div className={MARKDOWN_CLASSES}>
                    <ReactMarkdown>{parsedData.llm_response}</ReactMarkdown>
                  </div>
                ) : (
                  <span className="text-muted-foreground italic">
                    No answer text was returned.
                  </span>
                )}
              </BubbleContent>
            </Bubble>
          </MessageContent>
        </Message>
      )}

      <section className="flex flex-col gap-2">
        <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {"llm_response" in parsedData ? "References" : "Results"} ({results.length})
        </h3>
        {results.length === 0 ? (
          <p className="text-muted-foreground">No matching content was found.</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {results.map((result) => (
              <li key={result.index}>
                <ReferenceCard result={result} />
              </li>
            ))}
          </ol>
        )}
      </section>
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
  const sendFeedback = useContext(SendFeedbackContext);

  // Each new search is a new query, so clear the feedback given on the last one
  useEffect(() => {
    setThumbsUp(false);
    setThumbsDown(false);
  }, [responseBoxData]);

  if (loading) {
    return (
      <Trace role="status">
        <TraceLine status="running">
          <TraceTitle>Searching your content...</TraceTitle>
        </TraceLine>
      </Trace>
    );
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
    if (token && sendFeedback) {
      // rawJson is usually the parsed response object, but may be a string.
      const jsonResponse =
        typeof responseBoxData.rawJson === "string"
          ? JSON.parse(responseBoxData.rawJson)
          : responseBoxData.rawJson;

      const queryID = jsonResponse.query_id;
      const feedbackSecretKey = jsonResponse.feedback_secret_key;

      sendFeedback({
        queryId: queryID,
        sentiment: feedback_sentiment,
        feedbackSecretKey,
      })
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

  const canSendFeedback =
    responseBoxData.rawJson &&
    typeof responseBoxData.rawJson === "object" &&
    "feedback_secret_key" in responseBoxData.rawJson;

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* A string means the request failed */}
        {typeof responseBoxData.parsedData === "string" ? (
          <Bubble variant="destructive" className="max-w-full">
            <BubbleContent className="text-sm">
              {responseBoxData.parsedData}
            </BubbleContent>
          </Bubble>
        ) : (
          <RenderSearchResponse parsedData={responseBoxData.parsedData} />
        )}

        {/* Feedback and raw response actions */}
        <div className="flex items-center justify-end gap-0.5">
          {canSendFeedback && (
            <>
              <IconButtonWithTooltip
                label={thumbsUp ? "Marked helpful" : "Helpful"}
                size="icon-sm"
                pressed={thumbsUp}
                onClick={() => handleFeedback("positive")}
              >
                {thumbsUp ? <IconThumbUpFilled /> : <IconThumbUp />}
              </IconButtonWithTooltip>
              <IconButtonWithTooltip
                label={thumbsDown ? "Marked not helpful" : "Not helpful"}
                size="icon-sm"
                pressed={thumbsDown}
                onClick={() => handleFeedback("negative")}
              >
                {thumbsDown ? <IconThumbDownFilled /> : <IconThumbDown />}
              </IconButtonWithTooltip>
            </>
          )}
          <IconButtonWithTooltip
            label="View raw response"
            size="icon-sm"
            onClick={() => setJsonModalOpen(true)}
          >
            <IconBraces />
          </IconButtonWithTooltip>
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

const SearchSidebar = ({
  closeSidebar,
  search,
  sendFeedback,
}: {
  closeSidebar: () => void;
  search: SearchFn;
  sendFeedback: SendFeedbackFn;
}) => {
  return (
    <SendFeedbackContext.Provider value={sendFeedback}>
      <TestSidebar
        title="Test Search"
        closeSidebar={closeSidebar}
        showLLMResponseToggle={true}
        handleSendClick={(...args) => getSearchResponse(search, ...args)}
        ResponseBox={SearchResponseBox}
      />
    </SendFeedbackContext.Provider>
  );
};

export type { SearchResponseBoxData };
export { SearchSidebar };
