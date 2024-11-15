import React from "react";
import {
  Avatar,
  Typography,
  Button,
  Card,
  CardContent,
  Link,
  ListItem,
  IconButton,
  ListItemIcon,
} from "@mui/material";
import LockResetIcon from "@mui/icons-material/LockReset";
import Edit from "@mui/icons-material/Edit";
import { Layout } from "@/components/Layout";
import { sizes } from "@/utils";

interface UserCardProps {
  username: string;
  isAdmin: boolean;
  onResetPassword: () => void;
  onEditUser: () => void;
}

const UserCard: React.FC<UserCardProps> = ({
  username,
  isAdmin,
  onResetPassword,
  onEditUser,
}) => {
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
      <Card sx={{ width: 250, padding: 2, textAlign: "center" }}>
        <CardContent>
          <Avatar
            sx={{
              width: 56,
              height: 56,
              margin: "0 auto",
              bgcolor: "primary.main",
            }}
          >
            {getUserInitials(username)}
          </Avatar>
          <Typography variant="h6" mt={2}>
            {username}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isAdmin ? "Admin" : "User"}
          </Typography>

          <Layout.FlexBox
            flexDirection={"row"}
            gap={sizes.baseGap}
            sx={{ alignItems: "center" }}
          >
            <Button onClick={onResetPassword} sx={{ textTransform: "none" }}>
              <LockResetIcon fontSize="small" />
              <Layout.Spacer horizontal multiplier={0.3} />
              Reset Password
            </Button>
            <Button component={Link} onClick={onEditUser}>
              <Edit fontSize="small" />
              <Layout.Spacer horizontal multiplier={0.3} />
              Edit
            </Button>
          </Layout.FlexBox>
        </CardContent>
      </Card>
    </>
  );
};
interface UserCardPropsNew {
  index: number;
  username: string;
  isAdmin: boolean;
  isLastItem: boolean;
  hoveredIndex: number;
  setHoveredIndex: (index: number) => void;
  onResetPassword: () => void;
  onEditUser: () => void;
}

const UserCardNew: React.FC<UserCardPropsNew> = ({
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
          <Typography variant="h6">{username}</Typography>
          <Typography variant="body1"> {isAdmin ? "Admin" : "User"}</Typography>
        </div>
      </ListItem>
    </>
  );
};
export { UserCard, UserCardNew };
