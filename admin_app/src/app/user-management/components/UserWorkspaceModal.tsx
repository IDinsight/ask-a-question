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
} from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

import { UserBody } from "../api";

interface UserSearchModalProps {
  open: boolean;
  onClose: () => void;
  checkUserExists: (username: string) => Promise<boolean>;
  addUserToWorkspace: (username: string) => Promise<void>;
  createUser: (
    username: string,
    password: string,
    role: "admin" | "read_only",
  ) => Promise<any>;
  formType: "add" | "create" | "edit";
  editUser?: (username: string, role: "admin" | "read_only") => Promise<void>;
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

const UserSearchModal: React.FC<UserSearchModalProps> = ({
  open,
  onClose,
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
  const [username, setUsername] = useState<string>(user?.username || "");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [role, setRole] = useState<"admin" | "read_only">("read_only");
  const [userExists, setUserExists] = useState<boolean | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{
    text: string;
    severity: "error" | "warning" | "info" | "success";
  } | null>(null);
  // const initialState = {
  //   username: "",
  //   password: "",
  //   confirmPassword: "",
  //   role: "read_only" as "admin" | "read_only",
  //   userExists: null,
  //   isVerified: false,
  //   loading: false,
  //   error: "",
  // };
  // const [state, setState] = useState(initialState);
  const isUserInWorkspace = useMemo(
    () => users.some((u) => u.username === username),
    [users, username],
  );
  const handleClose = useCallback(() => {
    //setState(initialState);
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
        return false;
      }
    }
    setError(null);
    return true;
  }, [username, password, confirmPassword, formType]);

  const actions: Record<"add" | "create" | "edit", () => Promise<void> | undefined> = {
    create: async () => await createUser(username, password, role),
    add: async () => {
      if (isVerified && userExists) {
        await addUserToWorkspace(username);
      } else if (isVerified && !userExists) {
        await createUser(username, password, role).then((data) => {
          onContinue(data.recovery_codes);
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
        message: `User successfully ${formType === "add" ? "added" : formType + "d"}`,
        severity: "success",
      });
      setTimeout(() => {
        onClose();
      }, 300);
    } catch {
      setError({ text: "Error processing request.", severity: "error" });
    } finally {
      setLoading(false);
      handleClose();
    }
  }, [
    formType,
    username,
    password,
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
      console.log(user);
      setUsername(user.username);
      setRole(user.role);
    }
  }, [user, formType]);
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
        >
          <Avatar sx={{ bgcolor: "secondary.main", margin: "0 auto" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography variant="h6" align="center">
            {getTitle(formType)}
          </Typography>
          {error && <Alert severity={error.severity}>{error.text}</Alert>}
          <Box display="flex" gap={1}>
            <TextField
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
                  <VerifiedIcon color="primary" fontSize="large" />
                ) : (
                  "Verify"
                )}
              </Button>
            )}
          </Box>
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
          <TextField
            select
            fullWidth
            label="Role"
            value={role}
            onChange={(e) => setRole(e.target.value as "admin" | "read_only")}
            SelectProps={{
              native: true,
            }}
          >
            <option value="admin">Admin</option>
            <option value="read_only">Read Only</option>
          </TextField>
          <Box display="flex" justifyContent="space-between">
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

export default UserSearchModal;
