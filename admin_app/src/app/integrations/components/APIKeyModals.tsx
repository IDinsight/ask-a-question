import React, { useState } from "react";
import {
  IconAlertTriangle,
  IconCheck,
  IconCopy,
  IconRefresh,
} from "@tabler/icons-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";

/** Confirm before rotating the key, since the old key stops working at once. */
export const KeyRenewConfirmationModal = ({
  open,
  currentKey,
  onClose,
  onRenew,
  isLoading,
}: {
  open: boolean;
  currentKey: string;
  onClose: () => void;
  onRenew: () => void;
  isLoading: boolean;
}) => (
  <AlertDialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
    <AlertDialogContent className="p-6">
      <AlertDialogHeader>
        <AlertDialogMedia className="text-destructive">
          <IconAlertTriangle />
        </AlertDialogMedia>
        <AlertDialogTitle className="text-base">
          Regenerate the workspace API key?
        </AlertDialogTitle>
        <AlertDialogDescription className="text-sm">
          Your current key beginning with{" "}
          <b className="font-mono font-semibold text-foreground">{currentKey}</b> will
          stop working straight away. You’ll need to update your applications with the
          new key.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel size="lg" disabled={isLoading}>
          Cancel
        </AlertDialogCancel>
        <AlertDialogAction
          size="lg"
          variant="destructive"
          onClick={onRenew}
          disabled={isLoading}
          autoFocus
        >
          {isLoading ? (
            <Spinner data-icon="inline-start" />
          ) : (
            <IconRefresh data-icon="inline-start" />
          )}
          {isLoading ? "Generating…" : "Generate new key"}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
);

/** Shows a newly generated key once, with a copy button. */
export const NewKeyModal = ({
  newKey,
  open,
  onCopy,
  onClose,
}: {
  newKey: string;
  open: boolean;
  onCopy: () => void;
  onClose: () => void;
}) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClose = () => {
    setIsClicked(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="flex flex-col gap-5 p-6 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">Save your new key</DialogTitle>
          <DialogDescription className="text-sm">
            Save this secret key somewhere safe and accessible.{" "}
            <b className="font-semibold text-foreground">
              You won’t be able to view the full key again here.
            </b>{" "}
            If you lose it, you’ll need to generate a new one. The key has 32
            characters.
          </DialogDescription>
        </DialogHeader>
        <div className="flex gap-2">
          <input
            value={newKey}
            readOnly
            autoFocus
            aria-label="New API key"
            onFocus={(event) => event.target.select()}
            className="h-9 min-w-0 flex-1 border border-input bg-transparent px-3 font-mono text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
          />
          <Button
            size="lg"
            onClick={() => {
              onCopy();
              setIsClicked(true);
            }}
          >
            {isClicked ? (
              <IconCheck data-icon="inline-start" />
            ) : (
              <IconCopy data-icon="inline-start" />
            )}
            {isClicked ? "Copied" : "Copy"}
          </Button>
        </div>
        <DialogFooter>
          <Button variant="outline" size="lg" onClick={handleClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
