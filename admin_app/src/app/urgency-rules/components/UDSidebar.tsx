import React, { useState } from "react";
import { IconAlertTriangle, IconBolt, IconCircleCheck } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { JsonDialog } from "@/components/JsonDialog";
import { TestSidebar } from "@/components/SidebarCommon";
import TypingAnimation from "@/components/TypingAnimation";
import { apiCalls } from "@/utils/api";

interface UDResults {
  is_urgent: boolean;
  matched_rules: string[];
}

interface UDResponseBoxData {
  dateTime: string;
  parsedData: UDResults | string; // string is for error messages
  rawJson: string;
}

interface UDResponseBoxProps {
  loading: boolean;
  responseBoxData: UDResponseBoxData | null;
}

const getUDResponse = (
  question: string,
  generateLLMResponse: boolean, // Unused. Has to match signature of getSearchResponse
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setResponse: React.Dispatch<React.SetStateAction<UDResponseBoxData | null>>,
  token: string | null,
) => {
  const processUDResponse = (response: any) => {
    const udResults: UDResults = {
      is_urgent: response.is_urgent,
      matched_rules: response.matched_rules,
    };

    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: udResults,
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
      .getUrgencyDetection(question, token)
      .then((response) => {
        processUDResponse(response);
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

/** Urgent / not urgent, plus the rules that matched. */
const RenderUDResponse = ({ parsedData }: { parsedData: UDResults }) => {
  const single = parsedData.matched_rules.length === 1;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Classification
        </h3>
        {parsedData.is_urgent ? (
          <span className="flex items-center gap-1.5 text-base font-semibold text-urgent">
            <IconAlertTriangle className="size-4" aria-hidden="true" />
            Urgent
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-base font-semibold">
            <IconCircleCheck
              className="size-4 text-muted-foreground"
              aria-hidden="true"
            />
            Not urgent
          </span>
        )}
      </div>
      {parsedData.is_urgent && (
        <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {single ? "Matched Rule" : "Matched Rules"}
        </h3>
      )}
      {parsedData.matched_rules.length > 0 && (
        // A bulleted list only when there's more than one rule
        <ul className={single ? "flex flex-col" : "flex list-disc flex-col gap-2 pl-5"}>
          {parsedData.matched_rules.map((text: string, i: number) => (
            <li key={i}>{text}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

const UDResponseBox: React.FC<UDResponseBoxProps> = ({ loading, responseBoxData }) => {
  // Hooks must run before any early return.
  const [jsonModalOpen, setJsonModalOpen] = useState<boolean>(false);

  if (loading) {
    return <TypingAnimation />;
  }

  if (!responseBoxData) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconBolt />
          </EmptyMedia>
          <EmptyTitle>Test your rules</EmptyTitle>
          <EmptyDescription>
            Type a sample message to see whether it would be flagged as urgent.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* A string means the request failed */}
        {typeof responseBoxData.parsedData === "string" ? (
          <p>{responseBoxData.parsedData}</p>
        ) : (
          <RenderUDResponse parsedData={responseBoxData.parsedData} />
        )}
        <div className="flex items-center justify-end">
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

const UDSidebar = ({ closeSidebar }: { closeSidebar: () => void }) => {
  return (
    <TestSidebar
      title="Test Urgency Detection"
      closeSidebar={closeSidebar}
      showLLMResponseToggle={false}
      handleSendClick={getUDResponse}
      ResponseBox={UDResponseBox}
    />
  );
};

export { UDSidebar };
export type { UDResponseBoxData };
