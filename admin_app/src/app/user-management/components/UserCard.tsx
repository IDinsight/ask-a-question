import React from "react";
import { Avatar, Typography, ListItem, IconButton, ListItemIcon } from "@mui/material";
import LockResetIcon from "@mui/icons-material/LockReset";
import Edit from "@mui/icons-material/Edit";

interface UserCardProps {
  index: number;
  username: string;
  isAdmin: boolean;
  isLastItem: boolean;
  hoveredIndex: number;
  setHoveredIndex: (index: number) => void;
  onResetPassword: () => void;
  onEditUser: () => void;
}

const UserCard: React.FC<UserCardProps> = ({
  index,
  username,
  isAdmin,
  isLastItem,
  hoveredIndex,
  setHoveredIndex,
  onResetPassword,
  onEditUser,
}) => {
  const lastItemRef = React.useRef<HTMLLIElement>(null);
  const getUserInitials = (name: string) => {
    const initials = name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase();
    return initials;
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
                aria-label="reset password"
                onClick={() => onResetPassword()}
              >
                <LockResetIcon fontSize="small" color="primary" />
              </IconButton>
            </>
          )
        }
      >
        <ListItemIcon>
          <Avatar sx={{ bgcolor: "primary.main" }}>{getUserInitials(username)}</Avatar>
        </ListItemIcon>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <Typography variant="body1">{username}</Typography>
          <Typography variant="body2">{isAdmin ? "Admin" : "User"}</Typography>
        </div>
      </ListItem>
    </>
  );
};
export { UserCard };
