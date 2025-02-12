"use client";

import type React from "react";
import { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
} from "@mui/material";

interface UserSearchModalProps {
  open: boolean;
  onClose: () => void;
  checkUserExists: (username: string) => Promise<boolean>;
  addUserToWorkspace: (username: string) => Promise<void>;
  createUser: (username: string, password: string) => Promise<void>;
}

const UserSearchModal: React.FC<UserSearchModalProps> = ({
  open,
  onClose,
  checkUserExists,
  addUserToWorkspace,
  createUser,
}) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [userExists, setUserExists] = useState<boolean | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleVerifyUser = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const exists = await checkUserExists(username);
      console.log("User exists:", exists); // Debug log
      setUserExists(exists);
      setIsVerified(true);
    } catch (err) {
      console.error("Error verifying user:", err); // Debug log
      setError("Error verifying user.");
    } finally {
      setLoading(false);
    }
  }, [username, checkUserExists]);

  const handleAction = useCallback(async () => {
    if (!isVerified) return;

    if (userExists) {
      await addUserToWorkspace(username);
    } else {
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
      await createUser(username, password);
    }
    onClose();
  }, [
    isVerified,
    userExists,
    username,
    password,
    confirmPassword,
    addUserToWorkspace,
    createUser,
    onClose,
  ]);

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogContent>
        <Box display="flex" flexDirection="column" gap={2} width={350}>
          <Typography variant="h6" align="center">
            Add or Create User
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <Box display="flex" gap={1}>
            <TextField
              fullWidth
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <Button
              variant="contained"
              onClick={handleVerifyUser}
              disabled={loading || !username}
            >
              {loading ? "Checking..." : "Verify User"}
            </Button>
          </Box>
          {isVerified && userExists === false && (
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
          )}
          <Button
            variant="contained"
            color="primary"
            disabled={!isVerified}
            onClick={handleAction}
          >
            {userExists ? "Add User to Workspace" : "Create User"}
          </Button>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default UserSearchModal;
