import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  RadioGroup,
  FormControlLabel,
  Radio,
} from "@mui/material";
import { Workspace } from "./WorkspaceMenu";

interface DefaultWorkspaceModalProps {
  visible: boolean;
  workspaces: Workspace[];
  selectedWorkspace: Workspace;
  onCancel: () => void;
  onConfirm: (workspace: Workspace) => void;
}

const DefaultWorkspaceModal: React.FC<DefaultWorkspaceModalProps> = ({
  visible,
  workspaces,
  selectedWorkspace,
  onCancel,
  onConfirm,
}) => {
  const [defaultWorkspace, setDefaulltWorkspace] = useState<Workspace>(
    workspaces.find((workspace) => workspace.is_default) || workspaces[0],
  );

  const handleSelectChange = (event: SelectChangeEvent<string>) => {
    //setDefaulltWorkspace(event.target.value as string);
  };

  const handleConfirm = () => {
    if (selectedWorkspace) {
      onConfirm(defaultWorkspace);
    }
  };
  console.log("selectedWorkspace", selectedWorkspace);

  return (
    <Dialog open={visible} onClose={onCancel}>
      <DialogTitle>Change default workspace</DialogTitle>
      <DialogContent>
        <FormControl component="fieldset">
          <RadioGroup
            value={defaultWorkspace?.workspace_id || null}
            onChange={handleSelectChange}
          >
            {workspaces.map((workspace) => (
              <FormControlLabel
                key={workspace.workspace_id}
                value={workspace.workspace_id}
                control={<Radio />}
                label={workspace.workspace_name}
              />
            ))}
          </RadioGroup>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleConfirm} color="primary" disabled={!selectedWorkspace}>
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DefaultWorkspaceModal;
