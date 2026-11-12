import React, { useState } from "react";
import { IconSend, IconX } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/utils/auth";

/**
 * Side panel for trying a question against the API (used by the content
 * page's "Test search" and the urgency rules page). The caller supplies the
 * request (`handleSendClick`) and how to render its result (`ResponseBox`).
 * `T` is the response data shape (SearchResponseBoxData or UDResponseBoxData).
 */
const TestSidebar = <T,>({
  title,
  closeSidebar,
  showLLMResponseToggle,
  handleSendClick,
  ResponseBox,
}: {
  title: string;
  closeSidebar: () => void;
  showLLMResponseToggle: boolean;
  handleSendClick: (
    question: string,
    generateLLMResponse: boolean,
    setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    setResponse: React.Dispatch<React.SetStateAction<T | null>>,
    token: string | null,
  ) => void;
  ResponseBox: React.FC<{
    loading: boolean;
    responseBoxData: T | null;
    token: string | null;
  }>;
}) => {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [generateLLMResponse, setGenerateLLMResponse] = useState(false);
  const [response, setResponse] = useState<T | null>(null);
  const { token } = useAuth();

  const send = () =>
    handleSendClick(
      question,
      generateLLMResponse,
      setLoading,
      setResponse,
      token,
    );

  return (
    <aside className="flex h-full flex-col gap-6 border-l bg-card p-6 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Close ${title}`}
          onClick={closeSidebar}
        >
          <IconX />
        </Button>
      </div>

      <div className="flex flex-col gap-3">
        <InputGroup className="h-10 bg-background">
          <InputGroupInput
            aria-label="Question"
            placeholder="Ask a question..."
            className="text-sm md:text-sm"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !loading && question !== "") send();
            }}
          />
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              size="icon-sm"
              variant="default"
              aria-label="Send question"
              disabled={loading || question === ""}
              onClick={send}
            >
              {loading ? <Spinner /> : <IconSend />}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
        {showLLMResponseToggle && (
          <Label className="flex items-center gap-2 text-sm font-normal">
            <Checkbox
              checked={generateLLMResponse}
              onCheckedChange={(checked) => setGenerateLLMResponse(checked)}
            />
            Also generate AI response
          </Label>
        )}
      </div>

      {ResponseBox && (
        <div className="flex min-h-50 flex-1 flex-col overflow-y-auto border-t pt-4">
          <ResponseBox
            loading={loading}
            responseBoxData={response}
            token={token}
          />
        </div>
      )}
    </aside>
  );
};

export { TestSidebar };
