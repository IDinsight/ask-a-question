import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
        <pre className="min-h-0 flex-1 overflow-auto border bg-muted p-3 font-mono text-xs">
          {json === undefined ? "No JSON data found" : JSON.stringify(json, null, 2)}
        </pre>
      </DialogContent>
    </Dialog>
  );
};
