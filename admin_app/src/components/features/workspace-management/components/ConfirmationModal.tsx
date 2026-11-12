import React, { useState } from "react";
import { IconCheck, IconCopy } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** Shows a new user's recovery codes once, with a copy-all button. */
const ConfirmationModal = ({
  open,
  onClose,
  recoveryCodes,
  dialogTitle = "Admin User Created",
  closeButtonText = "Close",
}: {
  open: boolean;
  onClose: () => void;
  recoveryCodes: string[];
  dialogTitle?: string;
  closeButtonText?: string;
}) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClose = () => {
    setIsClicked(false);
    onClose();
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
    } catch (err) {
      console.error("Failed to copy recovery codes: ", err);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="flex flex-col gap-5 p-6 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            {dialogTitle}
          </DialogTitle>
          <DialogDescription className="text-sm">
            The user has been successfully registered. Save the recovery codes
            below. You will not be able to see them again.
          </DialogDescription>
        </DialogHeader>
        <ul
          aria-label="Recovery codes"
          className="grid grid-cols-2 gap-1.5 border bg-muted p-3 text-center font-mono text-sm"
        >
          {recoveryCodes.map((code) => (
            <li key={code}>{code}</li>
          ))}
        </ul>
        <div className="flex justify-center">
          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              handleCopyToClipboard();
              setIsClicked(true);
            }}
          >
            {isClicked ? (
              <IconCheck data-icon="inline-start" />
            ) : (
              <IconCopy data-icon="inline-start" />
            )}
            {isClicked ? "Copied" : "Copy codes"}
          </Button>
        </div>
        <DialogFooter>
          <Button size="lg" onClick={handleClose} autoFocus>
            {closeButtonText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export { ConfirmationModal };
