import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  IconMessageChatbot,
  IconRefresh,
  IconSend,
  IconSparkles,
  IconX,
} from "@tabler/icons-react";

import TypingAnimation from "@/components/TypingAnimation";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
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
  InputGroupInput,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "cn";
import { CustomError } from "@/utils/api";
import { MARKDOWN_CLASSES } from "./ContentModal";
import { JsonDialog } from "@/components/JsonDialog";

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
  const processErrorMessage = (error: CustomError) => {
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
      .catch((error: CustomError) => {
        processErrorMessage(error);
        setSnackMessage(error.message);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <aside className="flex h-full flex-col gap-4 border-l bg-card p-6 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Test chat</h2>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Close test chat"
          onClick={closeSidebar}
        >
          <IconX />
        </Button>
      </div>

      <div className="flex min-h-[200px] flex-1 flex-col gap-2 overflow-y-auto">
        {messages.length === 0 && !loading ? (
          <Empty>
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
          messages.map((message, index) => <MessageBox key={index} {...message} />)
        )}
        {loading ? (
          <div className="flex items-end gap-2">
            <BotAvatar />
            <TypingAnimation />
          </div>
        ) : null}
        <div ref={bottomRef}></div>
      </div>

      <div className="flex flex-col gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="self-end"
          onClick={handleReset}
          disabled={loading || messages.length === 0}
        >
          <IconRefresh data-icon="inline-start" />
          Reset chat
        </Button>
        <InputGroup className="h-10 bg-background">
          <InputGroupInput
            aria-label="Question"
            placeholder="Ask a question..."
            className="text-sm md:text-sm"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !loading && question !== "") {
                handleSendClick();
              }
            }}
          />
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              size="icon-sm"
              variant="default"
              aria-label="Send question"
              disabled={loading || question === ""}
              onClick={handleSendClick}
            >
              {loading ? <Spinner /> : <IconSend />}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </div>
    </aside>
  );
};

/** Round avatar marking messages from the assistant. */
const BotAvatar = () => (
  <Avatar size="sm" className="mb-1">
    <AvatarFallback className="bg-primary text-primary-foreground">
      <IconSparkles className="size-3.5" />
    </AvatarFallback>
  </Avatar>
);

const MessageBox = (message: Message) => {
  const [open, setOpen] = useState(false);
  const isQuestion = message.type === "question";

  return (
    <div className={cn("flex items-end gap-2", isQuestion ? "justify-end" : "justify-start")}>
      {!isQuestion && <BotAvatar />}

      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-3 py-2 break-words",
          isQuestion
            ? "rounded-br-sm bg-muted text-foreground"
            : "rounded-bl-sm bg-primary text-primary-foreground",
        )}
      >
        <div className={MARKDOWN_CLASSES}>
          <ReactMarkdown>
            {typeof message.content === "string" ? message.content : ""}
          </ReactMarkdown>
        </div>
        {"json" in message && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="mt-1 block w-full text-right text-xs underline-offset-2 opacity-80 hover:underline hover:opacity-100"
          >
            {"<json>"}
          </button>
        )}
      </div>

      {"json" in message && (
        <JsonDialog open={open} onOpenChange={setOpen} json={message.json} />
      )}
    </div>
  );
};
export { ChatSideBar };
