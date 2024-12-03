import CheckIcon from "@mui/icons-material/Check";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
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
import React, { useState } from "react";

interface User {
  username: string;
  recovery_codes: string[];
}
interface RegisterModalProps {
  open: boolean;
  onClose: (event: {}, reason: string) => void;
  onContinue: (recoveryCodes: string[]) => void;
  registerUser: (username: string, password: string) => Promise<User>;
}

function RegisterModal({
  open,
  onClose,
  onContinue,
  registerUser,
}: RegisterModalProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [errors, setErrors] = React.useState({
    username: false,
    password: false,
    confirmPassword: false,
    confirmPasswordMatch: false,
  });
  const validateForm = () => {
    const newErrors = {
      username: username === "",
      password: password === "",
      confirmPassword: confirmPassword === "",
      confirmPasswordMatch: password !== confirmPassword,
    };
    setErrors(newErrors);
    return Object.values(newErrors).every((value) => value === false);
  };
  const handleRegister = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (validateForm()) {
      console.log("Registering user");

      const data = await registerUser(username, password);
      if (data && data.username) {
        onContinue(data.recovery_codes);
      } else {
        setErrorMessage("Unexpected response from the server.");
      }
    }
  };

  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="form-dialog-title">
      <DialogContent>
        <Box
          component="form"
          noValidate
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "24px",
          }}
        >
          <Avatar sx={{ bgcolor: "secondary.main", marginBottom: 4 }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography variant="h5" align="center" sx={{ marginBottom: 4 }}>
            Register Admin User
          </Typography>
          <Box>
            {errorMessage && errorMessage != "" && (
              <Alert severity="error" sx={{ marginBottom: 2 }}>
                {errorMessage}
              </Alert>
            )}
          </Box>
          <TextField
            margin="normal"
            error={errors.username}
            helperText={errors.username ? "Please enter a username" : " "}
            required
            fullWidth
            id="register-username"
            label="Username"
            name="username"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <TextField
            margin="normal"
            error={errors.password}
            helperText={errors.password ? "Please enter a password" : " "}
            required
            fullWidth
            name="password"
            label="Password"
            type="password"
            id="register-password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <TextField
            required
            fullWidth
            name="confirm-password"
            label="Confirm Password"
            type="password"
            id="confirm-password"
            error={errors.confirmPasswordMatch}
            value={confirmPassword}
            helperText={errors.confirmPasswordMatch ? "Passwords do not match" : " "}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          <Box
            mt={1}
            width="100%"
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
          >
            <Button
              onClick={handleRegister}
              type="submit"
              fullWidth
              variant="contained"
              sx={{ maxWidth: "120px" }}
            >
              Register
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}

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

const ConfirmationModal = ({
  open,
  onClose,
  recoveryCodes,
}: {
  open: boolean;
  onClose: () => void;
  recoveryCodes: string[];
}) => {
  const [isClicked, setIsClicked] = useState(false);

  const handleClose = () => {
    setIsClicked(false);
    onClose();
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
    } catch (err) {
      console.error("Failed to copy recovery codes: ", err);
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Admin User Created</DialogTitle>
      <DialogContent>
        <DialogContentText>
          The admin user has been successfully registered. Please save the recovery
          codes below. You will not be able to see them again.
        </DialogContentText>
        <TextField
          fullWidth
          multiline
          margin="normal"
          value={recoveryCodes ? recoveryCodes.join("\n") : ""}
          InputProps={{
            readOnly: true,
            sx: {
              textAlign: "center",
            },
          }}
          inputProps={{
            style: { textAlign: "center" },
          }}
        />

        <Box display="flex" justifyContent="center" mt={2}>
          <Button
            variant="contained"
            onClick={() => {
              handleCopyToClipboard();
              setIsClicked(true);
            }}
            startIcon={isClicked ? <CheckIcon /> : <ContentCopyIcon />}
            style={{ paddingLeft: "20px", paddingRight: "20px" }}
          >
            {isClicked ? "Copied" : "Copy"}
          </Button>
        </Box>
      </DialogContent>

      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={handleClose} color="primary" variant="contained" autoFocus>
          Back to Login
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export { AdminAlertModal, RegisterModal, ConfirmationModal };
