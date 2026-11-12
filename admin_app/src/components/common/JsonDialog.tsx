"use client";

import {
  CodeBlock,
  CodeBlockActions,
  CodeBlockContent,
  CodeBlockCopyButton,
  CodeBlockHeader,
  CodeBlockLine,
  CodeBlockTitle,
} from "@/components/ui/code-block";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useHighlightedCode } from "@/hooks/use-highlighted-code";

/**
 * Pretty-print the response. Some callers pass an already-serialised string,
 * so parse those first to get consistent indentation; anything that isn't
 * valid JSON is shown as-is.
 */
const formatJson = (json: unknown): string => {
  if (json === undefined) return "No JSON data found";
  if (typeof json === "string") {
    try {
      return JSON.stringify(JSON.parse(json), null, 2);
    } catch {
      return json;
    }
  }
  return JSON.stringify(json, null, 2);
};

/**
 * Shows the raw API response behind a test search or chat message.
 * Used by the test sidebars on the content and urgency rules pages.
 */
export const JsonDialog = ({
  open,
  onOpenChange,
  json,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  json: unknown;
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] flex-col gap-4 p-6 sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">Raw response</DialogTitle>
        </DialogHeader>
        {/* Only mount (and highlight) while the dialog is open */}
        {open && <JsonCodeBlock value={formatJson(json)} />}
      </DialogContent>
    </Dialog>
  );
};

/** Syntax-highlighted, line-numbered JSON with a copy button. */
const JsonCodeBlock = ({ value }: { value: string }) => {
  // One React node per line; plain strings until the highlighter has loaded
  const lines = useHighlightedCode(value, "json");

  return (
    <CodeBlock size="sm" className="min-h-0 flex-1">
      <CodeBlockHeader>
        <CodeBlockTitle>JSON</CodeBlockTitle>
        <CodeBlockActions>
          <CodeBlockCopyButton value={value} />
        </CodeBlockActions>
      </CodeBlockHeader>
      <CodeBlockContent lineNumbers wrap className="min-h-0 flex-1">
        {lines.map((line, index) => (
          <CodeBlockLine key={index}>{line}</CodeBlockLine>
        ))}
      </CodeBlockContent>
    </CodeBlock>
  );
};
