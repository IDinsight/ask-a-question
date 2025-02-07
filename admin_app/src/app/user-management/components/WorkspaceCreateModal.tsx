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
interface WorkspaceCreateProps {
  open: boolean;
  onClose: () => void;
  isEdit: boolean;
  existingWorkspace?: Workspace;
  onCreate: (workspace: Workspace) => Promise<Workspace>;
  loginWorkspace: (workspace: Workspace) => void;
}
const WorkspaceCreateModal = ({
  open,
  onClose,
  isEdit,
  existingWorkspace,
  onCreate,
  loginWorkspace,
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
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const workspaceName = data.get("workspace-name") as string;
    if (isFormValid(workspaceName)) {
      onCreate({
        workspace_name: workspaceName,
        content_quota: 100,
        api_daily_quota: 100,
      }).then((value: Workspace | Workspace[]) => {
        const workspace = Array.isArray(value) ? value[0] : value;
        loginWorkspace(workspace);
      });
      onClose();
    }
  };
  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="form-dialog-title">
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
              gap: 2,
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
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ maxWidth: "120px" }}
            >
              {isEdit ? "Edit Workspace" : "Create Workspace"}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
export default WorkspaceCreateModal;
