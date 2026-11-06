import React from "react";
import { IconDownload, IconExternalLink } from "@tabler/icons-react";

import { buttonVariants } from "@/components/ui/button";

/** Inline code token, e.g. the API key placeholder to replace. */
const Code = ({ children }: { children: React.ReactNode }) => (
  <code className="bg-muted px-1 py-0.5 font-mono text-[0.85em] text-destructive">
    {children}
  </code>
);

/**
 * Link styled as an outline button that opens an external resource in a new tab.
 * A plain <a> (not <Button render>) so it keeps the link role for screen readers.
 */
const ExternalButton = ({
  href,
  icon = "external",
  children,
}: {
  href: string;
  icon?: "external" | "download";
  children: React.ReactNode;
}) => (
  <div className="flex justify-center">
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={buttonVariants({ variant: "outline", size: "lg" })}
    >
      {icon === "download" && <IconDownload data-icon="inline-start" />}
      {children}
      {icon === "external" && <IconExternalLink data-icon="inline-end" />}
    </a>
  </div>
);

const DocsLink = ({ href }: { href: string }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="font-medium text-primary underline underline-offset-4"
  >
    documentation
  </a>
);

const TypebotModalContent: React.FC = () => (
  <div className="flex flex-col gap-4">
    <p>
      In Typebot, you can use the &quot;HTTPS request&quot; card to call AAQ and receive
      its response.
    </p>
    <p>
      To get a head start, you can download our template below and load it into Typebot
      by going to &quot;Create a typebot &gt; Import a file&quot;.
    </p>
    <ExternalButton
      icon="download"
      href="https://github.com/IDinsight/ask-a-question/blob/e75c7fec20373a8db5f5c8771b069aa7fac576a8/chat_managers/typebot/typebot_demo_flow.json"
    >
      AI response with feedback
    </ExternalButton>
    <p>
      Once loaded, you need to update the <Code>API_KEY</Code> field inside the
      &quot;HTTP request&quot; card with your own API key before trying the flow.
    </p>
  </div>
);

const TurnModalContent: React.FC = () => (
  <div className="flex flex-col gap-4">
    <p>
      The quickest way to get started with Turn is to use the AAQ Playbook. Just replace{" "}
      <Code>API_KEY</Code> in the API call card with your own API key.
    </p>
    <ExternalButton href="https://whatsapp.turn.io/app/playbooks/db700074-7db3-4cfb-b73c-87e628ddc1d2">
      Open Turn Playbook
    </ExternalButton>
    <p>
      You can also refer to our{" "}
      <DocsLink href="https://docs.ask-a-question.com/integrations/chat_managers/turn.io/turn/" />{" "}
      for more detailed instructions on how to connect Turn to AAQ.
    </p>
  </div>
);

const GlificModalContent: React.FC = () => (
  <div className="flex flex-col gap-4">
    <p>
      You can download a pre-made flow from the link below, and <Code>Import</Code> it
      into Glific. Then replace <Code>INSERT_AAQ_API_KEY</Code> in Authorization with
      your own API key.
    </p>
    <ExternalButton href="https://github.com/IDinsight/ask-a-question/blob/main/chat_managers/glific/search_flow_without_feedback.json">
      Open Glific Flow
    </ExternalButton>
    <p>
      You can also refer to our{" "}
      <DocsLink href="https://docs.ask-a-question.com/latest/integrations/chat_managers/glific/glific/" />{" "}
      for more detailed instructions on how to import the flow and get going with
      Glific.
    </p>
  </div>
);

const RestApiContent: React.FC = () => (
  <div className="flex flex-col gap-4">
    <p>
      You can use REST APIs to interact with AAQ from your own application, using your
      workspace API key as a Bearer token. Click on the link below to see the
      documentation.
    </p>
    <ExternalButton href="https://app.ask-a-question.com/api/docs">
      REST API documentation
    </ExternalButton>
  </div>
);

export { GlificModalContent, TurnModalContent, TypebotModalContent, RestApiContent };
