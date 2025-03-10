"use client";

import type React from "react";
import { useState } from "react";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogContent,
  TextField,
  Typography,
} from "@mui/material";
import { CustomError } from "@/utils/api";

interface UserModalProps {
  open: boolean;
  onClose: () => void;
  onContinue: (data: any) => void;
  resetPassword: (
    username: string,
    recoveryCode: string,
    password: string,
  ) => Promise<any>;
}

const UserResetModal = ({ open, onClose, resetPassword }: UserModalProps) => {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isUsernameEmpty, setIsUsernameEmpty] = useState(false);
  const [isRecoveryCodeEmpty, setIsRecoveryCodeEmpty] = useState(false);
  const [isConfirmPasswordEmpty, setIsConfirmPasswordEmpty] = useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = useState(false);

  const isFormValid = (
    recoveryCode: string,
    password: string,
    confirmPassword: string,
  ) => {
    if (recoveryCode === "") {
      setIsRecoveryCodeEmpty(true);
      return false;
    }
    if (password === "") {
      setIsPasswordEmpty(true);
      return false;
    }
    if (confirmPassword === "") {
      setIsConfirmPasswordEmpty(true);
      return false;
    }
    if (password !== confirmPassword) {
      setIsConfirmPasswordEmpty(true);
      return false;
    }
    return true;
  };

  const handleUsernameSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (username.trim() !== "") {
      setStep(2);
    } else {
      setIsUsernameEmpty(true);
    }
  };

  const handleResetSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const recoveryCode = data.get("recovery-code") as string;
    const password = data.get("password") as string;
    const confirmPassword = data.get("confirm-password") as string;
    if (isFormValid(recoveryCode, password, confirmPassword)) {
      try {
        const response = await resetPassword(username, recoveryCode, password);
        if (response && response.username) {
          setStep(3);
        } else if (response.status && response.status === 400) {
          setErrorMessage(response.data.detail);
        } else {
          setErrorMessage("Unable to reset password. Please try again later.");
        }
      } catch (error) {
        let errorMsg = "An unexpected error occurred. Please try again later.";
        const customError = error as CustomError;
        if (customError && customError.message) {
          errorMsg = customError.message;
        }
        setErrorMessage(errorMsg);
      }
    }
  };

  const handleClose = () => {
    setStep(1);
    setUsername("");
    setErrorMessage("");
    setIsUsernameEmpty(false);
    setIsRecoveryCodeEmpty(false);
    setIsConfirmPasswordEmpty(false);
    setIsPasswordEmpty(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} aria-labelledby="form-dialog-title">
      <DialogContent>
        {step === 1 && (
          <Box
            component="form"
            noValidate
            onSubmit={handleUsernameSubmit}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "24px",
            }}
          >
            <Avatar sx={{ bgcolor: "secondary.main", marginBottom: 3 }}>
              <LockOutlinedIcon />
            </Avatar>
            <Typography variant="h5" align="center" sx={{ marginBottom: 3 }}>
              Enter Username
            </Typography>
            <TextField
              error={isUsernameEmpty}
              helperText={isUsernameEmpty ? "Please enter a username" : " "}
              required
              fullWidth
              id="username"
              name="username"
              label="Username"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setIsUsernameEmpty(false);
              }}
            />
            <Box mt={1} width="100%" display="flex" justifyContent="center">
              <Button onClick={handleClose} sx={{ maxWidth: "120px", mr: 1 }}>
                Cancel
              </Button>
              <Button type="submit" variant="contained" sx={{ maxWidth: "120px" }}>
                Continue
              </Button>
            </Box>
          </Box>
        )}

        {step === 2 && (
          <Box
            component="form"
            noValidate
            onSubmit={handleResetSubmit}
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
              Reset Password: {username}
            </Typography>
            {errorMessage && (
              <Alert severity="error" sx={{ marginBottom: 2 }}>
                {errorMessage}
              </Alert>
            )}
            <TextField
              error={isRecoveryCodeEmpty}
              helperText={isRecoveryCodeEmpty ? "Please enter a recovery code" : " "}
              required
              fullWidth
              id="recovery-code"
              name="recovery-code"
              label="Recovery Code"
              onChange={() => setIsRecoveryCodeEmpty(false)}
            />
            <TextField
              error={isPasswordEmpty}
              helperText={isPasswordEmpty ? "Please enter a password" : " "}
              required
              fullWidth
              name="password"
              label="New Password"
              type="password"
              onChange={() => setIsPasswordEmpty(false)}
            />
            <TextField
              error={isConfirmPasswordEmpty}
              helperText={isConfirmPasswordEmpty ? "Passwords do not match" : " "}
              required
              fullWidth
              label="Confirm New Password"
              name="confirm-password"
              type="password"
              onChange={() => setIsConfirmPasswordEmpty(false)}
            />
            <Box mt={1} width="100%" display="flex" justifyContent="center">
              <Button
                onClick={() => {
                  setStep(1);
                  setErrorMessage("");
                }}
                sx={{ maxWidth: "120px", mr: 1 }}
              >
                Back
              </Button>
              <Button type="submit" variant="contained">
                Reset Password
              </Button>
            </Box>
          </Box>
        )}

        {step === 3 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "24px",
            }}
          >
            <Avatar sx={{ bgcolor: "success.main", marginBottom: 4 }}>
              <CheckCircleOutlineIcon />
            </Avatar>
            <Typography variant="h5" align="center" sx={{ marginBottom: 4 }}>
              Password Reset Successful
            </Typography>
            <Typography align="center" sx={{ marginBottom: 4 }}>
              Your password has been reset successfully. Please log in with your new
              password.
            </Typography>
            <Button
              onClick={handleClose}
              variant="contained"
              sx={{ maxWidth: "120px" }}
            >
              Close
            </Button>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export { UserResetModal };
