import * as React from "react";
import AddIcon from "@mui/icons-material/Add";
import Paper from "@mui/material/Paper";
import Divider from "@mui/material/Divider";
import MenuList from "@mui/material/MenuList";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import ModeEditIcon from "@mui/icons-material/ModeEdit";
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
import SettingsIcon from "@mui/icons-material/Settings";
import { appColors, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
import { UserBody, UserBodyUpdate } from "@/app/workspace-management/api";

export type Workspace = {
  workspace_id?: number;
  workspace_name: string;
  content_quota?: number;
  api_daily_quota?: number;
  user_role?: UserRole;
  is_default?: boolean;
};
export type UserRole = "read_only" | "admin";

interface WorkspaceMenuProps {
  getUserInfo: () => Promise<UserBody>;
  setOpenCreateWorkspaceModal: (value: boolean) => void;
  editUser: (user_id: number, user: UserBodyUpdate) => Promise<any>;
  loginWorkspace: (workspace: Workspace) => void;
}

const WorkspaceMenu = ({
  getUserInfo,
  setOpenCreateWorkspaceModal,
  editUser,
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
  const [user, setUser] = React.useState<UserBody | null>(null);
  const [persistedWorkspaceName, setPersistedWorkspaceName] =
    React.useState<string>("");
  const [persistedUserRole, setPersistedUserRole] = React.useState<string | null>(null);
  const [openDefaultWorkspaceModal, setOpenDefaultWorkspaceModal] =
    React.useState<boolean>(false);
  const [openSuccessModal, setOpenSuccessModal] = React.useState<boolean>(false);
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
  const handleConfirmDefaultWorkspace = async (workspace: Workspace) => {
    const userId = user?.user_id;
    const updatedUser = {
      username: user?.username,
      is_default_workspace: true,
      workspace_name: workspace.workspace_name,
    } as UserBodyUpdate;
    editUser(userId!, updatedUser).then((response) => {
      if (response && response.username) {
        setOpenDefaultWorkspaceModal(false);
        setOpenSuccessModal(true);
      }
    });
  };

  React.useEffect(() => {
    getUserInfo().then((returnedUser: UserBody) => {
      setUser({
        user_id: returnedUser.user_id,
        username: returnedUser.username,
      } as UserBody);
      const workspacesData = returnedUser.user_workspaces as Workspace[];
      workspacesData.forEach((workspace, index) => {
        workspace.is_default = returnedUser.is_default_workspace
          ? returnedUser.is_default_workspace[index]
          : false;
      });
      setWorkspaces(returnedUser.user_workspaces!);
    });
  }, []);
  React.useEffect(() => {
    // Save workspace to local storage when it changes
    if (workspaceName) {
      localStorage.setItem("workspaceName", workspaceName);
    }
    // Save role to local storage when it changes
    if (userRole != null) {
      localStorage.setItem("userRole", userRole);
    }
  }, [workspaceName]);
  React.useEffect(() => {
    // Retrieve workspace from local storage on component mount
    const storedWorkspace = localStorage.getItem("workspaceName");
    if (storedWorkspace) {
      setPersistedWorkspaceName(storedWorkspace);
    }
    const storedRole = localStorage.getItem("userRole");
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
        borderRadius: "15px",
        paddingLeft: sizes.tinyGap,
        paddingRight: sizes.tinyGap,
        maxWidth: "fit-content",
      }}
    >
      <Tooltip title="Open settings">
        <IconButton onClick={handleOpenUserMenu}>
          <Typography
            style={{
              fontSize: sizes.baseGap,
              color: appColors.white,
              whiteSpace: "nowrap",
            }}
          >
            {persistedWorkspaceName.length > 20
              ? `${persistedWorkspaceName.substring(0, 20)}...`
              : persistedWorkspaceName}
          </Typography>

          <KeyboardArrowDownIcon
            sx={{
              color: appColors.white,
              width: sizes.icons.small,
              height: sizes.icons.small,
              paddingLeft: sizes.tinyGap,
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
          {persistedUserRole === "admin" && (
            <MenuItem
              onClick={() => {
                window.location.href = "/workspace-management";
              }}
              disabled={persistedUserRole !== "admin"}
            >
              <ListItemIcon>
                <SettingsIcon />
              </ListItemIcon>
              <ListItemText>Manage Workspace</ListItemText>
            </MenuItem>
          )}
          <Divider />

          <Typography
            variant="subtitle2"
            sx={{ padding: "4px 16px", fontWeight: "bold", color: "gray" }}
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
                {workspace.workspace_name.length > 30
                  ? `${workspace.workspace_name.substring(0, 30)}...`
                  : workspace.workspace_name}
              </ListItemText>
              <span
                style={{
                  border: `1px solid ${appColors.primary}`,
                  borderRadius: "12px",
                  padding: "2px 4px",
                  marginLeft: "auto",
                  color: appColors.primary,
                  backgroundColor:
                    workspace.user_role === "admin"
                      ? appColors.dashboardLightGray
                      : "transparent",
                }}
              >
                {workspace.user_role === "admin" ? "Admin" : "Read only"}
              </span>
            </MenuItem>
          ))}
          <Divider />
          <MenuItem disabled={persistedUserRole !== "admin"}>
            <ListItemIcon>
              <ModeEditIcon />
            </ListItemIcon>
            <ListItemText
              onClick={() => {
                setOpenDefaultWorkspaceModal(true);
              }}
            >
              Set current workspace as default
            </ListItemText>
          </MenuItem>
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
      {workspaces.find(
        (workspace) => workspace.workspace_name == persistedWorkspaceName,
      ) && (
        // TODO: Change this to just a pop-up toast
        <ConfirmDefaultWorkspaceDialog
          open={openDefaultWorkspaceModal}
          onClose={() => {
            setOpenDefaultWorkspaceModal(false);
          }}
          onConfirm={handleConfirmDefaultWorkspace}
          workspace={
            workspaces.find(
              (workspace) => workspace.workspace_name == persistedWorkspaceName,
            )!
          }
        />
      )}
      <DefaultWorkspaceSuccessModal
        open={openSuccessModal}
        onClose={() => {
          setOpenSuccessModal(false);
        }}
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
      <DialogTitle>
        Switch to workspace <strong>{workspace?.workspace_name}</strong>?
      </DialogTitle>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose} color="primary">
          Stay
        </Button>
        <Button
          onClick={() => {
            onConfirm(workspace);
          }}
          variant="contained"
          color="primary"
        >
          Switch
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const ConfirmDefaultWorkspaceDialog = ({
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
      <DialogTitle>
        Change default workspace to <strong>{workspace?.workspace_name}</strong>?
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          You will directly enter this workspace next time you log in.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose} color="primary">
          Cancel
        </Button>
        <Button
          onClick={() => {
            onConfirm(workspace);
          }}
          variant="contained"
          color="primary"
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
};
const DefaultWorkspaceSuccessModal = ({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogContent>
        <DialogContentText>Default workspace changed successfully.</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};
export default WorkspaceMenu;
