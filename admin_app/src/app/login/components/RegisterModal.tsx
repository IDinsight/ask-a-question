import React, { useState } from "react";
import {
  Dialog,
  Box,
  TextField,
  Button,
  DialogContent,
  Typography,
  Grid,
  Avatar,
  DialogTitle,
  DialogContentText,
  DialogActions,
  Alert,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { Layout } from "@/components/Layout";

interface User {
  username: string;
}
interface RegisterModalProps {
  open: boolean;
  onClose: (event: {}, reason: string) => void;
  onContinue: () => void;
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
        onContinue();
      } else {
        setErrorMessage("Unexpected response from the server.");
      }
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
            margin="normal"
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
            mt={2}
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
      <DialogTitle>{"Register Admin User"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You need to register admin user before proceeding.
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
      <DialogTitle>Admin User Created</DialogTitle>
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
