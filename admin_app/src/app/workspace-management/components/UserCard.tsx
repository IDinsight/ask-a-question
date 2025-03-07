import React, { useState } from "react";
import {
  Avatar,
  Typography,
  ListItem,
  IconButton,
  ListItemIcon,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Button,
} from "@mui/material";
import Edit from "@mui/icons-material/Edit";
import GroupRemoveIcon from "@mui/icons-material/GroupRemove";
import { UserRole } from "@/components/WorkspaceMenu";
import PersonRemoveIcon from "@mui/icons-material/PersonRemove";

interface UserCardProps {
  index: number;
  adminUsername: string;
  userId: number;
  username: string;
  userRole: UserRole;
  isLastItem: boolean;
  hoveredIndex: number;
  setHoveredIndex: (index: number) => void;
  onRemoveUser: (userId: number) => void;
  onEditUser: () => void;
}

const UserCard: React.FC<UserCardProps> = ({
  index,
  username,
  adminUsername,
  userId,
  userRole,
  isLastItem,
  hoveredIndex,
  setHoveredIndex,
  onRemoveUser,
  onEditUser,
}) => {
  const [open, setOpen] = useState(false);
  const lastItemRef = React.useRef<HTMLLIElement>(null);

  const getUserInitials = (name: string) => {
    const initials = name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase();
    return initials;
  };

  const handleOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleConfirmRemove = () => {
    onRemoveUser(userId);
    handleClose();
  };

  return (
    <>
      <ListItem
        key={index}
        ref={isLastItem ? lastItemRef : null}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          marginBottom: 2,
          paddingBottom: 1,
          overflowWrap: "break-word",
          hyphens: "auto",
          whiteSpace: "pre-wrap",
        }}
        disablePadding
        onMouseEnter={() => setHoveredIndex(index)}
        onMouseLeave={() => setHoveredIndex(-1)}
        secondaryAction={
          index === hoveredIndex && (
            <>
              <IconButton
                edge="end"
                aria-label="edit"
                sx={{ marginRight: 0.5 }}
                onClick={() => onEditUser()}
              >
                <Edit fontSize="small" color="primary" />
              </IconButton>
              <IconButton
                edge="end"
                aria-label="remove user"
                title="Remove user from Workspace"
                onClick={handleOpen}
              >
                <GroupRemoveIcon fontSize="small" color="primary" />
              </IconButton>
            </>
          )
        }
      >
        <ListItemIcon>
          <Avatar sx={{ bgcolor: "primary.main" }}>{getUserInitials(username)}</Avatar>
        </ListItemIcon>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <Typography variant="body1" style={{ display: "flex", alignItems: "center" }}>
            {username}
            {username == adminUsername && (
              <Typography
                variant="body2"
                color="textSecondary"
                style={{ marginLeft: 8 }}
              >
                (You)
              </Typography>
            )}
          </Typography>
          <Typography variant="body2">
            {userRole == "admin" ? "Admin" : "Read only"}{" "}
          </Typography>
        </div>
      </ListItem>

      <Dialog
        open={open}
        onClose={handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          Remove user <strong>{username}</strong> from workspace?
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            If the current workspace is the only workspace for this user, the user will
            be <strong> deleted from the system</strong>.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
          <Button onClick={handleClose} variant="outlined" color="primary">
            Cancel
          </Button>
          <Button
            onClick={handleConfirmRemove}
            variant="contained"
            color="error"
            startIcon={<PersonRemoveIcon />}
            autoFocus
          >
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export { UserCard };
