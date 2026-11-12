import React from "react";
import { IconAlertTriangle, IconTrash } from "@tabler/icons-react";

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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

/** Bulk delete confirmation. The user must type "delete" to enable it. */
export const ConfirmDeleteModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  selectedContentsCount: number;
}> = ({ open, onClose, onConfirm, selectedContentsCount }) => {
  const [confirmationText, setConfirmationText] = React.useState<string>("");
  const confirmed = confirmationText.toLowerCase() === "delete";

  const handleConfirm = () => {
    if (confirmed) {
      onConfirm();
      setConfirmationText("");
    }
  };

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          setConfirmationText("");
          onClose();
        }
      }}
    >
      <AlertDialogContent className="text-sm">
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <IconTrash />
          </AlertDialogMedia>
          <AlertDialogTitle>Confirm deletion</AlertDialogTitle>
          <AlertDialogDescription>
            You are about to permanently delete{" "}
            <strong className="text-foreground">{selectedContentsCount}</strong> content
            {selectedContentsCount === 1 ? "" : "s"}.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <Alert variant="destructive">
          <IconAlertTriangle />
          <AlertDescription>This action cannot be undone.</AlertDescription>
        </Alert>
        <Field>
          <FieldLabel htmlFor="confirm-delete-input">
            Type <strong>delete</strong> to confirm
          </FieldLabel>
          <Input
            id="confirm-delete-input"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            placeholder="delete"
            autoComplete="off"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleConfirm();
            }}
          />
        </Field>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={handleConfirm}
            disabled={!confirmed}
          >
            <IconTrash data-icon="inline-start" />
            Delete items
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};
