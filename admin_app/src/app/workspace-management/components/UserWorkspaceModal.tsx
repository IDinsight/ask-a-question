"use client";

import type React from "react";
import { useState, useCallback, useMemo, useEffect } from "react";
import {
  Avatar,
  Dialog,
  DialogContent,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  MenuItem,
} from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

import { UserBody } from "../api";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { UserRole } from "@/components/WorkspaceMenu";

interface UserCreateModalProps {
  open: boolean;
  onClose: () => void;
  adminUsername: string;
  checkUserExists: (username: string) => Promise<boolean>;
  addUserToWorkspace: (username: string, role: UserRole) => Promise<void>;
  createUser: (username: string, password: string, role: UserRole) => Promise<any>;
  formType: "add" | "create" | "edit";
  editUser?: (username: string, role: UserRole) => Promise<void>;
  users: UserBody[];
  user?: UserBody;
  setSnackMessage: React.Dispatch<
    React.SetStateAction<{
      message: string;
      severity: "success" | "error" | "info" | "warning";
    }>
  >;
  onContinue: (data: string[]) => void;
}

const UserCreateModal: React.FC<UserCreateModalProps> = ({
  open,
  onClose,
  adminUsername,
  checkUserExists,
  addUserToWorkspace,
  createUser,
  editUser,
  formType,
  users,
  user,
  setSnackMessage,
  onContinue,
}) => {
  const { logout: logout } = useAuth();
  const [username, setUsername] = useState<string>(user?.username || "");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");

  const [role, setRole] = useState<UserRole>("read_only");
  const [userExists, setUserExists] = useState<boolean | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{
    text: string;
    severity: "error" | "warning" | "info" | "success";
  } | null>(null);

  const isUserInWorkspace = useMemo(
    () => users.some((u) => u.username === username),
    [users, username],
  );
  const handleClose = useCallback(() => {
    setUsername("");
    setPassword("");
    setConfirmPassword("");
    setRole("read_only");
    setUserExists(null);
    setIsVerified(false);
    setLoading(false);
    setError(null);
    onClose();
  }, [onClose]);

  const handleVerifyUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const exists = await checkUserExists(username);
      setUserExists(exists);
      if (!exists) {
        setError({
          text: `User ${username} does not exist. You can create it below.`,
          severity: "info",
        });
      }
      if (isUserInWorkspace) {
        setError({
          text: `User ${username} is already in the workspace.`,
          severity: "error",
        });
      } else {
        setIsVerified(true);
      }
    } catch (err) {
      setError({ text: "Error verifying user.", severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [username, checkUserExists]);

  const validateInputs = useCallback(() => {
    if (!username) {
      setError({ text: "Username is required.", severity: "error" });
      return false;
    }
    if (formType == "create") {
      if (!password) {
        setError({ text: "Password is required.", severity: "error" });
        return false;
      }
      if (password !== confirmPassword) {
        setError({ text: "Passwords do not match.", severity: "error" });
        setPassword("");
        setConfirmPassword("");
        return false;
      }
    }
    setError(null);
    return true;
  }, [username, password, confirmPassword, formType]);

  const handleError = (error: any) => {
    let errorMsg = "Error processing request";
    if (error) {
      const customError = error as CustomError;
      if (customError.message) {
        errorMsg = customError.message;
      }
      setError({ text: errorMsg, severity: "error" });
    }
  };
  const actions: Record<"add" | "create" | "edit", () => Promise<void> | undefined> = {
    create: async () =>
      await createUser(username, password, role).then((data) => {
        if (data.recovery_codes) {
          onContinue(data.recovery_codes);
        }
      }),
    add: async () => {
      if (isVerified && userExists) {
        await addUserToWorkspace(username, role);
      } else if (isVerified && !userExists) {
        await createUser(username, password, role).then((data) => {
          if (data.recovery_codes) {
            onContinue(data.recovery_codes);
          }
        });
      } else {
        setError({
          text: "Unable to add user.",
          severity: "error",
        });
      }
    },
    edit: async () => {
      if (editUser) {
        await editUser(username, role);
        if (username == adminUsername && role !== "admin") {
          logout();
        }
      } else {
        setError({
          text: "Edit user function is not defined.",
          severity: "error",
        });
      }
    },
  };

  const handleAction = useCallback(async () => {
    if (!validateInputs()) return;
    setLoading(true);
    setError(null);
    try {
      await actions[formType]?.();
      setSnackMessage({
        message: `User successfully ${
          formType === "add" ? "added" : formType === "edit" ? "edited" : formType + "d"
        }`,
        severity: "success",
      });
      setTimeout(() => {
        onClose();
      }, 300);
    } catch (error) {
      handleError(error);
    } finally {
      setLoading(false);
    }
  }, [
    formType,
    username,
    password,
    confirmPassword,
    role,
    isVerified,
    userExists,
    addUserToWorkspace,
    createUser,
    editUser,
  ]);

  const getTitle = (formType: "add" | "create" | "edit") => {
    const titles = {
      add: "Add Existing User",
      create: "Create User",
      edit: "Edit User",
    };
    return titles[formType] || "Create User";
  };

  const getButtonTitle = (formType: "add" | "create" | "edit") => {
    const buttonTitles = {
      add: "Add To Workspace",
      create: "Create",
      edit: "Edit",
    };
    return buttonTitles[formType] || "Create";
  };

  useEffect(() => {
    if (formType === "edit" && user) {
      setUsername(user.username);
      if (user.role) {
        setRole(user.role);
      }
    }
  }, [user, formType, user?.role]);

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogContent>
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          flexDirection="column"
          gap={2}
          margin="auto"
          sx={{ paddingInline: 2, paddingBottom: 2 }}
        >
          <Avatar sx={{ bgcolor: "secondary.main", margin: "0 auto" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography variant="h6" align="center">
            {getTitle(formType)}
          </Typography>
          {/* {formType === "edit" && user?.username === adminUsername && (
            <Alert severity="warning" sx={{ width: "200px" }}>
              Editing the current user will require to log in again.
            </Alert>
          )} */}
          <Box display="flex" gap={1} width="100%">
            <TextField
              disabled={formType === "edit"}
              fullWidth
              label="Username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setIsVerified(false);
              }}
            />
            {formType == "add" && (
              <Button onClick={handleVerifyUser} disabled={loading || !username}>
                {isVerified && userExists ? (
                  <VerifiedIcon color="success" fontSize="large" />
                ) : (
                  "Verify"
                )}
              </Button>
            )}
          </Box>
          {error && <Alert severity={error.severity}>{error.text}</Alert>}
          {(isVerified && userExists === false) || formType == "create" ? (
            <>
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <TextField
                fullWidth
                label="Confirm Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </>
          ) : null}
          {(formType == "add" && isVerified) ||
          formType === "create" ||
          (formType == "edit" && user && user.role) ? (
            <TextField
              select
              fullWidth
              label="Role"
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              SelectProps={{
                native: false,
              }}
              disabled={formType == "edit" && user?.username === adminUsername}
            >
              <MenuItem value="admin">Admin</MenuItem>
              <MenuItem value="read_only">Read Only</MenuItem>
            </TextField>
          ) : null}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 1,
              width: "100%",
            }}
          >
            <Button variant="outlined" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button
              variant="contained"
              color="primary"
              disabled={loading || (formType == "add" && !isVerified)}
              onClick={handleAction}
            >
              {getButtonTitle(formType)}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default UserCreateModal;
