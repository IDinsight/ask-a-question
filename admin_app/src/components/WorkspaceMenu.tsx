import * as React from "react";
import AddIcon from "@mui/icons-material/Add";
import Paper from "@mui/material/Paper";
import Divider from "@mui/material/Divider";
import MenuList from "@mui/material/MenuList";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Menu,
  Tooltip,
  Typography,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import SettingsIcon from "@mui/icons-material/Settings";
import { appColors, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";

export type User = {
  user_id: number;
  username: string;

  user_workspaces: Workspace[];
};
export type Workspace = {
  workspace_id?: number;
  workspace_name: string;
  content_quota?: number;
  api_daily_quota?: number;
  user_role?: string;
};

interface WorkspaceMenuProps {
  currentWorkspaceName: string;
  getUserInfo: () => Promise<User>;
  setOpenCreateWorkspaceModal: (value: boolean) => void;
  loginWorkspace: (workspace: Workspace) => void;
}

const WorkspaceMenu = ({
  currentWorkspaceName,
  getUserInfo,
  setOpenCreateWorkspaceModal,
  loginWorkspace,
}: WorkspaceMenuProps) => {
  const { workspaceName, userRole } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = React.useState<Workspace | null>(
    null,
  );
  const [openConfirmSwitchWorkspaceDialog, setOpenConfirmSwitchWorkspaceDialog] =
    React.useState(false);
  const [persistedWorkspaceName, setPersistedWorkspaceName] =
    React.useState<string>("");
  const [persistedUserRole, setPersistedUserRole] = React.useState<string | null>(null);
  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorEl(null);
  };
  const handleCloseConfirmSwitchWorkspaceDialog = () => {
    setOpenConfirmSwitchWorkspaceDialog(false);
  };
  const handleWorkspaceClick = (workspace: Workspace) => {
    setSelectedWorkspace(workspace);
    setOpenConfirmSwitchWorkspaceDialog(true);
  };
  const handleConfirmSwitchWorkspace = async (workspace: Workspace) => {
    loginWorkspace(workspace);
    handleCloseConfirmSwitchWorkspaceDialog();
  };

  React.useEffect(() => {
    getUserInfo().then((returnedUser: User) => {
      setWorkspaces(returnedUser.user_workspaces);
    });
  }, []);
  React.useEffect(() => {
    // Save user to local storage when it changes
    if (workspaceName) {
      localStorage.setItem("workspaceName", workspaceName);
    }
    // Save role to local storage when it changes
    if (userRole != null) {
      localStorage.setItem("userRole", userRole);
    }
  }, [workspaceName]);
  React.useEffect(() => {
    // Retrieve user from local storage on component mount
    const storedWorkspace = localStorage.getItem("workspaceName");
    if (storedWorkspace) {
      setPersistedWorkspaceName(storedWorkspace);
    }
    const storedRole = localStorage.getItem("role");
    if (storedRole) {
      if (storedRole === "admin" || storedRole === "read_only") {
        setPersistedUserRole(storedRole);
      }
    }
  }, [workspaceName]);

  return (
    <Paper
      sx={{
        backgroundColor: appColors.primary,
        border: `1px solid ${appColors.white}`,
        margin: sizes.baseGap,
      }}
    >
      <Tooltip title="Open settings">
        <IconButton onClick={handleOpenUserMenu}>
          <WorkspacesIcon
            sx={{
              width: sizes.icons.medium,
              height: sizes.icons.medium,
              color: appColors.white,
            }}
          />
          <span style={{ fontSize: sizes.baseGap, color: appColors.white }}>
            {persistedWorkspaceName}
          </span>

          <KeyboardArrowDownIcon
            sx={{
              color: appColors.white,
              width: sizes.icons.medium,
              height: sizes.icons.medium,
            }}
          />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={handleCloseUserMenu}
      >
        <MenuList dense>
          <Typography
            variant="subtitle2"
            sx={{ padding: "8px 16px", fontWeight: "bold", color: "gray" }}
          >
            Current Workspace: {persistedWorkspaceName}
          </Typography>
          {persistedUserRole === "admin" && (
            <MenuItem
              onClick={() => {
                window.location.href = "/user-management";
              }}
              disabled={persistedUserRole !== "admin"}
            >
              <ListItemIcon>
                <SettingsIcon />
              </ListItemIcon>
              <ListItemText>Manage Workspace</ListItemText>
              <span
                style={{
                  border: `1px solid ${appColors.primary}`,
                  borderRadius: "4px",
                  padding: "2px 4px",
                  marginLeft: "8px",
                  color: appColors.primary,
                }}
              >
                {persistedUserRole === "admin" ? "Admin" : "Read only"}
              </span>
            </MenuItem>
          )}
          <Divider />

          <Typography
            variant="subtitle2"
            sx={{ padding: "8px 16px", fontWeight: "bold", color: "gray" }}
          >
            Switch Workspace
          </Typography>
          {workspaces.map((workspace) => (
            <MenuItem
              key={workspace.workspace_id}
              disabled={workspace.workspace_name === persistedWorkspaceName}
            >
              <ListItemIcon>
                <LibraryBooksIcon />
              </ListItemIcon>
              <ListItemText
                onClick={(event) => {
                  handleWorkspaceClick(workspace);
                }}
              >
                {workspace.workspace_name}
              </ListItemText>
              <span
                style={{
                  border: `1px solid ${appColors.primary}`,
                  borderRadius: "4px",
                  padding: "2px 4px",
                  marginLeft: "auto",
                  color: appColors.primary,
                }}
              >
                {workspace.user_role === "admin" ? "Admin" : "Read only"}
              </span>
            </MenuItem>
          ))}
          <Divider />
          <MenuItem>
            <ListItemIcon>
              <AddIcon />
            </ListItemIcon>
            <ListItemText
              onClick={() => {
                setOpenCreateWorkspaceModal(true);
              }}
            >
              Create new workspace
            </ListItemText>
          </MenuItem>
        </MenuList>
      </Menu>
      <ConfirmSwitchWorkspaceDialog
        open={openConfirmSwitchWorkspaceDialog}
        onClose={handleCloseConfirmSwitchWorkspaceDialog}
        onConfirm={handleConfirmSwitchWorkspace}
        workspace={selectedWorkspace!}
      />
    </Paper>
  );
};
const ConfirmSwitchWorkspaceDialog = ({
  open,
  onClose,
  onConfirm,
  workspace,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: (workspace: Workspace) => void;
  workspace: Workspace;
}) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Confirm Switch</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Are you sure you want to switch to the workspace:{" "}
          <strong>{workspace?.workspace_name}</strong>?
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Cancel
        </Button>
        <Button
          onClick={() => {
            onConfirm(workspace);
          }}
          color="primary"
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WorkspaceMenu;
