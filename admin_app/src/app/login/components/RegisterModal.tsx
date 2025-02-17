import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import React, { useCallback, useState } from "react";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

interface UserSearchModalProps {
  open: boolean;
  onClose: () => void;
  registerUser: (username: string, password: string) => Promise<any>;
  onContinue: (data: string[]) => void;
}
const RegisterModal: React.FC<UserSearchModalProps> = ({
  open,
  onClose,
  registerUser,
  onContinue,
}) => {
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validateInputs = useCallback(() => {
    if (!username) {
      setError("Username is required.");
      return false;
    }
    if (!password) {
      setError("Password is required.");
      return false;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return false;
    }

    setError("");
    return true;
  }, [username, password, confirmPassword]);

  const handleAction = useCallback(async () => {
    if (!validateInputs()) return;
    setLoading(true);
    setError("");
    try {
      registerUser(username, password).then((data) => {
        onContinue(data.recovery_codes);
      });
    } catch {
      setError("Error processing request.");
    } finally {
      setLoading(false);
      onClose();
    }
  }, [username, password, registerUser]);

  return (
    <Dialog open={open} onClose={onClose}>
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
            Register first user
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <Box display="flex" gap={1}>
            <TextField
              fullWidth
              label="Username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
              }}
            />
          </Box>

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
          <Box display="flex" justifyContent="space-between">
            <Button
              variant="contained"
              color="primary"
              disabled={loading}
              onClick={handleAction}
            >
              Register
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

const AdminAlertModal = ({
  open,
  onClose,
  onContinue,
}: {
  open: boolean;
  onClose: (event: {}, reason: string) => void;
  onContinue: () => void;
}) => {
  return (
    <Dialog open={open} onClose={onClose} disableEscapeKeyDown={true}>
      <DialogTitle>{"Initial Setup"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You need to register an admin user before proceeding.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onContinue} color="primary" variant="contained" autoFocus>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export { AdminAlertModal, RegisterModal };
