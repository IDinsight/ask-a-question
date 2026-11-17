import React, { useState } from "react";
import {
  IconAlertTriangle,
  IconBolt,
  IconBraces,
  IconCircleCheck,
  IconExclamationCircle,
} from "@tabler/icons-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Trace, TraceLine, TraceTitle } from "@/components/ui/trace";
import { IconButtonWithTooltip } from "@/components/common/AssistantParts";
import { JsonDialog } from "@/components/common/JsonDialog";
import { TestSidebar } from "@/components/common/SidebarCommon";
import type { UrgencyDetectionResponse } from "../types";

interface UDResults {
  is_urgent: boolean;
  matched_rules: string[];
}

interface UDResponseBoxData {
  dateTime: string;
  parsedData: UDResults | string; // string is for error messages
  rawJson: unknown;
}

interface UDResponseBoxProps {
  loading: boolean;
  responseBoxData: UDResponseBoxData | null;
}

/** Raw detection result, as UDSidebar's `onDetect` resolves it. */
type UDResponse = UrgencyDetectionResponse;

/**
 * Build the TestSidebar send handler. TestSidebar owns the panel's loading and
 * response state; the request itself comes from the Wrapper (`onDetect`, the
 * urgency-detection mutation), so this child never calls the API.
 */
const makeUDSendHandler =
  (onDetect: (message: string) => Promise<UDResponse>, canDetect: boolean) =>
  (
    question: string,
    _generateLLMResponse: boolean, // Unused. Has to match signature of getSearchResponse
    setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    setResponse: React.Dispatch<React.SetStateAction<UDResponseBoxData | null>>,
  ) => {
    if (question === "" || !canDetect) {
      return;
    }
    setLoading(true);
    onDetect(question)
      .then((response) => {
        setResponse({
          dateTime: new Date().toISOString(),
          parsedData: {
            is_urgent: response.is_urgent,
            // Guard against a missing list so the render never crashes
            matched_rules: response.matched_rules ?? [],
          },
          rawJson: response,
        });
      })
      .catch((error: Error) => {
        console.error(error);
        setResponse({
          dateTime: new Date().toISOString(),
          parsedData: error.message || "The urgency detection request failed.",
          rawJson: { error: error.message },
        });
      })
      .finally(() => {
        setLoading(false);
      });
  };

/** Urgent / not urgent as an alert, then the rules that matched. */
const RenderUDResponse = ({ parsedData }: { parsedData: UDResults }) => {
  const count = parsedData.matched_rules.length;

  return (
    <div className="flex flex-col gap-4">
      {parsedData.is_urgent ? (
        // Amber "urgent" token, matching the rest of the urgency page
        <Alert className="border-urgent/40 bg-urgent/5 text-urgent *:data-[slot=alert-description]:text-urgent/90">
          <IconAlertTriangle />
          <AlertTitle className="text-sm">Urgent</AlertTitle>
          <AlertDescription>
            {count === 1 ? "1 rule matched" : `${count} rules matched`} this
            message.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert>
          <IconCircleCheck className="text-muted-foreground" />
          <AlertTitle className="text-sm">Not urgent</AlertTitle>
          <AlertDescription>No rules matched this message.</AlertDescription>
        </Alert>
      )}

      {count > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {count === 1 ? "Matched rule" : `Matched rules (${count})`}
          </h3>
          <ol className="flex flex-col gap-2">
            {parsedData.matched_rules.map((text, i) => (
              <li
                key={i}
                className="flex items-start gap-2 border bg-background px-3 py-2.5"
              >
                <IconBolt
                  className="mt-0.5 size-3.5 shrink-0 text-urgent"
                  aria-hidden="true"
                />
                <span className="min-w-0 text-sm wrap-break-word whitespace-pre-wrap">
                  {text}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
};

const UDResponseBox: React.FC<UDResponseBoxProps> = ({
  loading,
  responseBoxData,
}) => {
  // Hooks must run before any early return.
  const [jsonModalOpen, setJsonModalOpen] = useState<boolean>(false);

  if (loading) {
    return (
      <Trace role="status">
        <TraceLine status="running">
          <TraceTitle>Checking your rules...</TraceTitle>
        </TraceLine>
      </Trace>
    );
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
          <Alert variant="destructive">
            <IconExclamationCircle />
            <AlertTitle className="text-sm">Request failed</AlertTitle>
            <AlertDescription>{responseBoxData.parsedData}</AlertDescription>
          </Alert>
        ) : (
          <RenderUDResponse parsedData={responseBoxData.parsedData} />
        )}
        <div className="flex items-center justify-end">
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

const UDSidebar = ({
  closeSidebar,
  onDetect,
  canDetect,
}: {
  closeSidebar: () => void;
  /** Classify a message (the Wrapper's urgency-detection mutation). */
  onDetect: (message: string) => Promise<UDResponse>;
  /** False until signed in; sending does nothing until then (as before). */
  canDetect: boolean;
}) => {
  return (
    <TestSidebar
      title="Test Urgency Detection"
      closeSidebar={closeSidebar}
      showLLMResponseToggle={false}
      handleSendClick={makeUDSendHandler(onDetect, canDetect)}
      ResponseBox={UDResponseBox}
    />
  );
};

export { UDSidebar };
export type { UDResponseBoxData };
