import React, { useState } from "react";
import {
  Dialog,
  Box,
  TextField,
  Button,
  DialogContent,
  Typography,
  Alert,
  Grid,
  Avatar,
  Snackbar,
  DialogTitle,
  DialogContentText,
  DialogActions,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { Layout } from "@/components/Layout";

interface RegisterModalProps {
  open: boolean;
  onClose: (event: {}, reason: string) => void;
  onContinue: () => void;
  registerUser: (username: string, password: string) => void;
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
  const [snackMessage, setSnackMessage] = React.useState<string | null>(null);
  const [errors, setErrors] = React.useState({
    username: false,
    password: false,
    confirmPassword: false,
    confirmPasswordMatch: true,
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
  const handleRegister = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    console.log("Starting user");
    if (validateForm()) {
      console.log("Registering user");
      registerUser(username, password);
      onClose({}, "");
      onContinue();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="form-dialog-title">
      <DialogContent>
        <Box>
          <Grid
            item
            sx={{
              display: { xs: "none", sm: "flex", md: "flex" },
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Avatar sx={{ bgcolor: "secondary.main", marginBottom: 4 }}>
              <LockOutlinedIcon />
            </Avatar>
          </Grid>
          <Grid
            item
            sx={{
              display: { xs: "flex", sm: "none", md: "none" },
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <img
              src="../../logo-light.png"
              alt="Logo"
              style={{
                minWidth: "200px",
                maxWidth: "80%",
                marginBottom: 80,
              }}
            />
            <Layout.Spacer multiplier={4} />
          </Grid>
          <Typography variant="h5" align="center">
            Register
          </Typography>
        </Box>

        <Box
          component="form"
          noValidate
          width={"300px"}
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "24px",
          }}
        >
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
            margin="normal"
            required
            fullWidth
            name="confirm-password"
            label="Confirm Password"
            type="password"
            id="confirm-password"
            error={!errors.confirmPasswordMatch}
            value={confirmPassword}
            helperText={!errors.confirmPasswordMatch ? "Passwords do not match" : " "}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          <Box mt={2} width="100%">
            <Button
              onClick={handleRegister}
              type="submit"
              variant="contained"
              sx={{ width: "120px", mr: 1 }}
            >
              Register
            </Button>
          </Box>
        </Box>
      </DialogContent>
      <Snackbar
        open={snackMessage !== null}
        autoHideDuration={4000}
        onClose={() => {
          setSnackMessage(null);
        }}
      >
        <Alert
          onClose={() => {
            setSnackMessage(null);
          }}
          severity={
            snackMessage?.toLowerCase().includes("successfully") ? "success" : "error"
          }
          variant="filled"
          sx={{ width: "100%" }}
        >
          {snackMessage}
        </Alert>
      </Snackbar>
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
      <DialogTitle>{"Add Admin User"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You need to add an admin user before continuing.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onContinue} color="primary" autoFocus>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
};
const ConfirmationModal = ({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>User Created</DialogTitle>
      <DialogContent>
        <DialogContentText>
          The admin user has been successfully registered.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Back to Login
        </Button>
      </DialogActions>
    </Dialog>
  );
};
export { AdminAlertModal, RegisterModal, ConfirmationModal };
