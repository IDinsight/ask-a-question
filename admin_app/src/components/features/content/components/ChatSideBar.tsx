import React, { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  IconArrowUp,
  IconBraces,
  IconCheck,
  IconCopy,
  IconFileText,
  IconMessageChatbot,
  IconRefresh,
  IconX,
} from "@tabler/icons-react";

import { Bubble, BubbleContent } from "@/components/ui/bubble";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { Message, MessageContent, MessageFooter } from "@/components/ui/message";
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller";
import {
  Trace,
  TraceCollapsible,
  TraceCollapsibleContent,
  TraceCollapsibleTrigger,
  TraceIcon,
  TraceLine,
  TraceTitle,
} from "@/components/ui/trace";
import { Spinner } from "@/components/ui/spinner";
import { JsonDialog } from "@/components/common/JsonDialog";
import { CustomError } from "@/utils/api";
import {
  AssistantAvatar,
  IconButtonWithTooltip,
} from "@/components/common/AssistantParts";
import { MARKDOWN_CLASSES } from "./ContentModal";

/** One content card the chat service retrieved to answer a question. */
interface SearchResult {
  id: number;
  title: string;
  text: string;
  distance: number;
}

interface UserMessage {
  id: string;
  type: "question";
  content: string;
}

interface ResponseMessage {
  id: string;
  type: "response";
  content: string;
  // Content cards used for the answer, in the order the backend ranked them
  sources: SearchResult[];
  json: unknown;
  isError?: boolean;
}

type ChatMessage = UserMessage | ResponseMessage;

/**
 * Turn the backend's `search_results` (an object keyed "0", "1", ...) into a
 * ranked list. Assumes the keys are the rank order, as the API returns them.
 */
const toSources = (searchResults: unknown): SearchResult[] => {
  if (!searchResults || typeof searchResults !== "object") return [];
  return Object.entries(searchResults as Record<string, SearchResult>)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([, result]) => result);
};

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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  // Counter for stable message ids; the scroller tracks items by id
  const nextId = useRef(0);
  const newId = () => String(nextId.current++);

  const canSend = !loading && question.trim() !== "";

  const handleReset = () => {
    setMessages([]);
    setSessionId(null);
  };

  const handleSend = () => {
    if (!canSend) return;
    const text = question.trim();
    setQuestion("");
    setMessages((prev) => [...prev, { id: newId(), type: "question", content: text }]);
    setLoading(true);

    const responsePromise = sessionId
      ? getResponse(text, sessionId)
      : getResponse(text);
    responsePromise
      .then((response) => {
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            type: "response",
            content: response.llm_response ?? "",
            sources: toSources(response.search_results),
            json: response,
          },
        ]);
        if (sessionId === null) {
          setSessionId(response.session_id);
        }
      })
      .catch((error: CustomError) => {
        // Show the failure in the thread too, so the conversation reads correctly
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            type: "response",
            content:
              "The chat service couldn't answer this. Open the raw response for details.",
            sources: [],
            json: { error: error.message },
            isError: true,
          },
        ]);
        setSnackMessage(error.message);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <aside className="flex h-full flex-col border-l bg-card text-sm">
      {/* Header: title plus new-chat and close actions */}
      <div className="flex items-center justify-between gap-2 border-b px-6 py-4">
        <div className="flex min-w-0 flex-col">
          <h2 className="text-base font-semibold">Test chat</h2>
          <p className="text-xs text-muted-foreground">
            Answers come from your published content.
          </p>
        </div>
        <div className="flex items-center gap-1">
          <IconButtonWithTooltip
            label="New chat"
            onClick={handleReset}
            disabled={loading || messages.length === 0}
          >
            <IconRefresh />
          </IconButtonWithTooltip>
          <IconButtonWithTooltip label="Close test chat" onClick={closeSidebar}>
            <IconX />
          </IconButtonWithTooltip>
        </div>
      </div>

      {/* Thread. Keeps following new replies unless the user scrolls up. */}
      <MessageScrollerProvider autoScroll>
        <MessageScroller className="flex-1">
          <MessageScrollerViewport>
            <MessageScrollerContent className="px-6 py-6">
              {messages.length === 0 && !loading ? (
                <Empty className="my-auto">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <IconMessageChatbot />
                    </EmptyMedia>
                    <EmptyTitle>Start a test conversation</EmptyTitle>
                    <EmptyDescription>
                      Ask a question to see how the chat service answers using your
                      content.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : (
                messages.map((message) => (
                  // Anchor on questions so a new question scrolls near the top
                  <MessageScrollerItem
                    key={message.id}
                    messageId={message.id}
                    scrollAnchor={message.type === "question"}
                  >
                    {message.type === "question" ? (
                      <QuestionTurn message={message} />
                    ) : (
                      <ResponseTurn message={message} />
                    )}
                  </MessageScrollerItem>
                ))
              )}
              {loading && (
                <MessageScrollerItem messageId="pending">
                  <PendingTurn />
                </MessageScrollerItem>
              )}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      {/* Composer. Enter sends, Shift+Enter adds a new line. */}
      <form
        className="border-t px-6 pt-4 pb-6"
        onSubmit={(event) => {
          event.preventDefault();
          handleSend();
        }}
      >
        <InputGroup className="bg-background">
          <InputGroupTextarea
            aria-label="Question"
            placeholder="Ask a question..."
            rows={2}
            className="max-h-40 min-h-0 text-sm md:text-sm"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <InputGroupAddon align="block-end">
            <span className="text-xs text-muted-foreground">
              Shift + Enter for a new line
            </span>
            <InputGroupButton
              type="submit"
              size="icon-sm"
              variant="default"
              className="ml-auto"
              aria-label="Send question"
              disabled={!canSend}
            >
              {/* Spinner while waiting for the reply; the button is disabled then */}
              {loading ? <Spinner /> : <IconArrowUp />}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </form>
    </aside>
  );
};

/** The tester's question: right-aligned, filled bubble. */
const QuestionTurn = ({ message }: { message: UserMessage }) => (
  <Message align="end">
    <MessageContent>
      <Bubble align="end" variant="default">
        <BubbleContent className="text-sm whitespace-pre-wrap">
          {message.content}
        </BubbleContent>
      </Bubble>
    </MessageContent>
  </Message>
);

/**
 * The chat service's reply: markdown answer, the content cards it drew on,
 * and actions to copy the answer or inspect the raw response.
 */
const ResponseTurn = ({ message }: { message: ResponseMessage }) => {
  const [jsonOpen, setJsonOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <Message>
      <AssistantAvatar />
      <MessageContent>
        <Bubble
          variant={message.isError ? "destructive" : "outline"}
          className="max-w-[90%]"
        >
          <BubbleContent className="text-sm">
            {message.content ? (
              <div className={MARKDOWN_CLASSES}>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            ) : (
              <span className="text-muted-foreground italic">
                No answer text was returned.
              </span>
            )}
          </BubbleContent>
        </Bubble>

        {message.sources.length > 0 && <SourcesTrace sources={message.sources} />}

        <MessageFooter className="gap-0.5 px-0">
          {!message.isError && message.content && (
            <IconButtonWithTooltip
              label={copied ? "Copied" : "Copy answer"}
              onClick={handleCopy}
              size="icon-sm"
            >
              {copied ? <IconCheck /> : <IconCopy />}
            </IconButtonWithTooltip>
          )}
          <IconButtonWithTooltip
            label="View raw response"
            onClick={() => setJsonOpen(true)}
            size="icon-sm"
          >
            <IconBraces />
          </IconButtonWithTooltip>
        </MessageFooter>
      </MessageContent>
      <JsonDialog open={jsonOpen} onOpenChange={setJsonOpen} json={message.json} />
    </Message>
  );
};

/** Collapsible list of the content cards retrieved for an answer. */
const SourcesTrace = ({ sources }: { sources: SearchResult[] }) => (
  <Trace>
    <TraceCollapsible>
      <TraceCollapsibleTrigger>
        <TraceLine>
          <TraceIcon>
            <IconFileText />
          </TraceIcon>
          <TraceTitle>
            Used {sources.length} content {sources.length === 1 ? "card" : "cards"}
          </TraceTitle>
        </TraceLine>
      </TraceCollapsibleTrigger>
      <TraceCollapsibleContent>
        <Trace>
          {sources.map((source) => (
            <TraceLine key={source.id} title={source.text}>
              <TraceIcon>
                <IconFileText />
              </TraceIcon>
              <TraceTitle>{source.title}</TraceTitle>
            </TraceLine>
          ))}
        </Trace>
      </TraceCollapsibleContent>
    </TraceCollapsible>
  </Trace>
);

/** Placeholder turn shown while waiting for the chat service. */
const PendingTurn = () => (
  <Message>
    <AssistantAvatar />
    {/* Same height as a one-line bubble so the text centres on the avatar */}
    <MessageContent className="min-h-[38px] justify-center">
      <Trace role="status">
        <TraceLine status="running">
          <TraceTitle>Searching your content...</TraceTitle>
        </TraceLine>
      </Trace>
    </MessageContent>
  </Message>
);

export { ChatSideBar };
