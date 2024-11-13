import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
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
import React, { useState } from "react";
import { UserBody } from "../api";
interface UserModalProps {
  open: boolean;
  onClose: () => void;
  onContinue: (data: any) => void;
  resetPassword: (
    username: string,
    recoveryCode: string,
    password: string,
  ) => Promise<any>;
  user: UserBody;
}

const UserResetModal = ({ open, onClose, resetPassword, user }: UserModalProps) => {
  const [errorMessage, setErrorMessage] = useState("");
  const [isRecoveryCodeEmpty, setIsRecoveryCodeEmpty] = React.useState(false);
  const [isConfirmPasswordEmpty, setIsConfirmPasswordEmpty] = React.useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = React.useState(false);

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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const recoveryCode = data.get("recovery-code") as string;
    const password = data.get("password") as string;
    const confirmPassword = data.get("confirm-password") as string;
    if (isFormValid(recoveryCode, password, confirmPassword)) {
      resetPassword(user?.username, recoveryCode, password);
      onClose();
    }
  };
  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="form-dialog-title">
      <DialogContent>
        <Box
          component="form"
          noValidate
          onSubmit={handleSubmit}
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
            Reset Password: {user?.username}
          </Typography>
          {errorMessage && (
            <Alert severity="error" sx={{ marginBottom: 2 }}>
              {errorMessage}
            </Alert>
          )}

          <TextField
            margin="normal"
            error={isRecoveryCodeEmpty}
            helperText={isRecoveryCodeEmpty ? "Please enter a recovery code" : " "}
            required
            fullWidth
            id="recovery-code"
            name="recovery-code"
            label="Recovery Code"
            onChange={() => {
              setIsRecoveryCodeEmpty(false);
            }}
          />

          <TextField
            margin="normal"
            error={isPasswordEmpty}
            helperText={isPasswordEmpty ? "Please enter a password" : " "}
            required
            fullWidth
            name="password"
            label="Password"
            type="password"
            onChange={() => {
              setIsPasswordEmpty(false);
            }}
          />

          <TextField
            margin="normal"
            error={isConfirmPasswordEmpty}
            helperText={isConfirmPasswordEmpty ? "Passwords do not match" : " "}
            required
            fullWidth
            label="Confirm Password"
            name="confirm-password"
            type="password"
            onChange={() => {
              setIsConfirmPasswordEmpty(false);
            }}
          />

          <Box mt={1} width="100%" display="flex" justifyContent="center">
            <Button
              onClick={() => onClose()}
              type="submit"
              fullWidth
              sx={{ maxWidth: "120px" }}
            >
              Cancel
            </Button>
            <Button
              //onClick={handleRegister}
              type="submit"
              fullWidth
              variant="contained"
              sx={{ maxWidth: "120px" }}
            >
              Confirm
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
export { UserResetModal };
