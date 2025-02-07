import * as React from "react";
import AddIcon from "@mui/icons-material/Add";
import Paper from "@mui/material/Paper";
import Divider from "@mui/material/Divider";
import MenuList from "@mui/material/MenuList";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import { IconButton, Menu, Tooltip, Typography } from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import SettingsIcon from "@mui/icons-material/Settings";
import { appColors, sizes } from "@/utils";
export type Workspace = {
  workspace_id: number;
  workspace_name: string;
};

interface WorkspaceMenuProps {
  currentWorkspaceName: string;
  getWorkspaces: () => Promise<Workspace[]>;
  setOpenCreateWorkspaceModal: (value: boolean) => void;
}

const WorkspaceMenu = ({
  currentWorkspaceName,
  getWorkspaces,
  setOpenCreateWorkspaceModal,
}: WorkspaceMenuProps) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorEl(null);
  };

  React.useEffect(() => {
    getWorkspaces().then((returnedWorkspaces: Workspace[]) => {
      setWorkspaces(returnedWorkspaces);
    });
  }, []);

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
            {currentWorkspaceName}
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
            Current Workspace: {currentWorkspaceName}
          </Typography>
          <MenuItem>
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
              Admin
            </span>
          </MenuItem>
          <Divider />

          <Typography
            variant="subtitle2"
            sx={{ padding: "8px 16px", fontWeight: "bold", color: "gray" }}
          >
            Switch Workspace
          </Typography>
          {workspaces.map((workspace) => (
            <MenuItem key={workspace.workspace_id}>
              <ListItemIcon>
                <LibraryBooksIcon />
              </ListItemIcon>
              <ListItemText>{workspace.workspace_name}</ListItemText>
              <span
                style={{
                  border: `1px solid ${appColors.primary}`,
                  borderRadius: "4px",
                  padding: "2px 4px",
                  marginLeft: "auto",
                  color: appColors.primary,
                }}
              >
                Admin
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
    </Paper>
  );
};
export default WorkspaceMenu;
