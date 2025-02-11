import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleVerifyUser = async () => {
    setLoading(true);
    setError("");
    try {
      const exists = await checkUserExists(username);
      setUserExists(exists);
    } catch (err) {
      setError("Error verifying user.");
    }
    setLoading(false);
  };

  const handleAction = async () => {
    if (userExists) {
      await addUserToWorkspace(username);
      onClose();
    } else {
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
      await createUser(username, password);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogContent>
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          gap={2}
          width={400}
          mx="auto"
        >
          <Typography variant="h6" align="center">
            Add or Create User to Workspace
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <Box display="flex" gap={1} width="100%">
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
              <CheckCircleIcon />
            </Button>
          </Box>
          {userExists === false && (
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
          <Box display="flex" gap={2} width="100%">
            <Button variant="outlined" color="primary" onClick={onClose} fullWidth>
              Cancel
            </Button>
            <Button
              variant="contained"
              color="primary"
              disabled={userExists === null}
              onClick={handleAction}
              fullWidth
            >
              {userExists ? "Add User to Workspace" : "Create User"}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default UserSearchModal;
