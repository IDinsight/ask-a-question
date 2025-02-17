import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogContent,
  TextField,
  Typography,
} from "@mui/material";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import React from "react";
import { Workspace } from "@/components/WorkspaceMenu";
import { CustomError } from "@/utils/api";
interface WorkspaceCreateProps {
  open: boolean;
  onClose: () => void;
  isEdit: boolean;
  existingWorkspace?: Workspace;
  onCreate: (workspace: Workspace) => Promise<Workspace>;
  loginWorkspace: (workspace: Workspace) => void;
  setSnackMessage?: React.Dispatch<
    React.SetStateAction<{
      message: string;
      severity: "success" | "error" | "info" | "warning";
    }>
  >;
}
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
  const isFormValid = (workspaceName: string) => {
    if (workspaceName === "") {
      setIsWorkspaceNameEmpty(true);
      return false;
    }
    return true;
  };
  const handleClose = () => {
    setErrorMessage("");

    onClose();
  };
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const workspaceName = data.get("workspace-name") as string;
    if (isFormValid(workspaceName)) {
      try {
        const response = await onCreate({
          workspace_name: workspaceName,
        });
        if (
          (Array.isArray(response) && response.length > 0) ||
          response.workspace_name
        ) {
          const workspace = Array.isArray(response) ? response[0] : response;
          loginWorkspace(workspace);
          if (setSnackMessage) {
            setSnackMessage({
              message: isEdit
                ? "Workspace edited successfully"
                : "Workspace created successfully",
              severity: "success",
            });
          }
          setTimeout(() => {
            onClose();
          }, 3000);
        } else if (Array.isArray(response) && response.length === 0) {
          setErrorMessage("Workspace name already exists");
        } else {
          setErrorMessage("Error creating workspace");
        }
      } catch (error) {
        let errorMessage = isEdit
          ? "Error editing workspace"
          : "Error creating workspace";

        if (error) {
          const customError = error as CustomError;
          if (customError.message) {
            errorMessage = customError.message;
          }
          setErrorMessage(errorMessage);
        }
      }
    }
  };
  return (
    <Dialog open={open} onClose={handleClose} aria-labelledby="form-dialog-title">
      <DialogContent>
        <Box
          component="form"
          onSubmit={handleSubmit}
          noValidate
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1,
            alignItems: "center",
            padding: 3,
          }}
        >
          <Avatar sx={{ bgcolor: "secondary.main" }}>
            <CreateNewFolderIcon />
          </Avatar>
          <Typography variant="h5" align="center" marginBottom={5}>
            {isEdit ? "Edit Workspace" : "Create New Workspace"}
          </Typography>
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}

          <TextField
            margin="none"
            error={isWorkspaceNameEmpty}
            helperText={isWorkspaceNameEmpty ? "Please enter a workspace name" : " "}
            required
            fullWidth
            id="workspace-name"
            label="Workspace Name"
            name="workspace-name"
            defaultValue={existingWorkspace?.workspace_name}
            onChange={() => {
              setIsWorkspaceNameEmpty(false);
            }}
          />
          <Box display="flex" justifyContent="space-between" width="100%">
            <TextField
              disabled
              margin="none"
              required
              label="Content Quota"
              type="number"
              sx={{ width: "48%" }}
              value={existingWorkspace ? existingWorkspace.content_quota : ""}
            />
            <TextField
              disabled
              margin="none"
              required
              label="API Daily Quota"
              type="number"
              sx={{ width: "48%" }}
              value={existingWorkspace ? existingWorkspace.api_daily_quota : ""}
            />
          </Box>
          <Box
            width="100%"
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 2,
              gap: 5,
            }}
          >
            <Button
              onClick={() => onClose()}
              type="submit"
              fullWidth
              sx={{ maxWidth: "120px" }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="contained" sx={{ width: "auto" }}>
              {isEdit ? "Edit Workspace" : "Create Workspace"}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
export default WorkspaceCreateModal;
