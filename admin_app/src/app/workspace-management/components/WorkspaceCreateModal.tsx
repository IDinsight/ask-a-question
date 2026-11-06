import React from "react";
import { IconAlertCircle, IconFolderPlus } from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Workspace } from "@/components/WorkspaceMenu";
import { CustomError } from "@/utils/api";

type SnackMessage = {
  message: string;
  severity: "success" | "error" | "info" | "warning";
};

interface WorkspaceCreateProps {
  open: boolean;
  onClose: () => void;
  isEdit: boolean;
  existingWorkspace?: Workspace;
  onCreate: (workspace: Workspace) => Promise<Workspace>;
  loginWorkspace: (workspace: Workspace) => void;
  /** Optional success notice (the workspace page shows it as a toast). */
  setSnackMessage?: (message: SnackMessage) => void;
}

/**
 * Create a workspace (from the sidebar's workspace switcher) or rename the
 * current one (from the workspace page). Logs into the workspace on success.
 */
const WorkspaceCreateModal = ({
  open,
  onClose,
  isEdit,
  existingWorkspace,
  onCreate,
  loginWorkspace,
  setSnackMessage,
}: WorkspaceCreateProps) => {
  const [errorMessage, setErrorMessage] = React.useState("");
  const [isWorkspaceNameEmpty, setIsWorkspaceNameEmpty] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const isFormValid = (workspaceName: string) => {
    if (workspaceName === "") {
      setIsWorkspaceNameEmpty(true);
      return false;
    }
    return true;
  };

  const handleClose = () => {
    setErrorMessage("");
    setIsWorkspaceNameEmpty(false);
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const workspaceName = ((data.get("workspace-name") as string) ?? "").trim();
    if (!isFormValid(workspaceName)) return;

    setSubmitting(true);
    try {
      const response = await onCreate({ workspace_name: workspaceName });
      // The API returns the workspace, or a list (empty when the name is taken).
      if ((Array.isArray(response) && response.length > 0) || response.workspace_name) {
        const workspace = Array.isArray(response) ? response[0] : response;
        loginWorkspace(workspace);
        setSnackMessage?.({
          message: isEdit ? "Workspace edited successfully" : "Workspace created successfully",
          severity: "success",
        });
        setTimeout(() => {
          onClose();
        }, 3000);
      } else if (Array.isArray(response) && response.length === 0) {
        setErrorMessage("Workspace name already exists");
      } else {
        setErrorMessage("Error creating workspace");
      }
    } catch (error) {
      const customError = error as CustomError;
      setErrorMessage(
        customError?.message || (isEdit ? "Error editing workspace" : "Error creating workspace"),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="p-6 sm:max-w-md">
        <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-5">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2.5 text-lg font-semibold">
              <IconFolderPlus className="size-5 text-muted-foreground" aria-hidden="true" />
              {isEdit ? "Rename workspace" : "Create a workspace"}
            </DialogTitle>
            <DialogDescription className="text-sm">
              {isEdit
                ? "Everyone in the workspace will see the new name."
                : "You’ll be the admin of the new workspace and switched into it."}
            </DialogDescription>
          </DialogHeader>

          {errorMessage && (
            <Alert variant="destructive">
              <IconAlertCircle aria-hidden="true" />
              <AlertDescription className="text-sm text-destructive">
                {errorMessage}
              </AlertDescription>
            </Alert>
          )}

          <Field data-invalid={isWorkspaceNameEmpty}>
            <FieldLabel htmlFor="workspace-name" className="text-sm">
              Workspace name
            </FieldLabel>
            <Input
              id="workspace-name"
              name="workspace-name"
              required
              autoFocus
              defaultValue={existingWorkspace?.workspace_name}
              aria-invalid={isWorkspaceNameEmpty}
              className="h-10 text-sm md:text-sm"
              onChange={() => setIsWorkspaceNameEmpty(false)}
            />
            {isWorkspaceNameEmpty && <FieldError>Please enter a workspace name</FieldError>}
          </Field>

          <DialogFooter>
            <Button type="button" variant="outline" size="lg" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting && <Spinner data-icon="inline-start" />}
              {isEdit ? "Save" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default WorkspaceCreateModal;
