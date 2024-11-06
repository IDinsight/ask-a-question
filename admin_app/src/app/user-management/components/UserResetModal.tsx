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
import { UserBody, UserBodyPassword } from "../api";
interface UserModalProps {
  open: boolean;
  onClose: () => void;
  onContinue: (data: any) => void;
  registerUser: (user: UserBodyPassword) => Promise<any>;
  user?: UserBody;
}
interface UseFormFields {
  username?: string;
  password?: string;
  confirmPassword?: string;
  contentLimit?: string;
  apiCallLimit?: string;
  is_admin?: boolean | false;
}
const useForm = (fields: Array<keyof UseFormFields>, initialUser?: UseFormFields) => {
  const initialFormData: UseFormFields = fields.reduce((data, field) => {
    const fieldValue =
      initialUser && initialUser[field] !== undefined ? initialUser[field] : "";
    return {
      ...data,
      [field]: fieldValue,
    };
  }, {} as UseFormFields);

  const initialErrors = fields.reduce(
    (errorState, field) => {
      errorState[field] = false;
      return errorState;
    },
    {} as Record<keyof UseFormFields, boolean> & {
      confirmPasswordMatch: boolean;
    },
  );
  initialErrors.confirmPasswordMatch = false;

  const [formData, setFormData] = useState<UseFormFields>(initialFormData);
  const [errors, setErrors] = useState(initialErrors);
  const validateForm = () => {
    const newErrors = {
      ...fields.reduce(
        (errorState, field) => {
          switch (field) {
            case "username":
              errorState.username = formData.username === "";
              break;
            case "password":
              errorState.password = formData.password === "";
              break;
            case "confirmPassword":
              errorState.confirmPassword = formData.confirmPassword === "";
              break;
            case "contentLimit":
              errorState.contentLimit = formData.contentLimit === "";
              break;
            case "apiCallLimit":
              errorState.apiCallLimit = formData.apiCallLimit === "";
              break;
          }
          return errorState;
        },
        {} as Record<keyof UseFormFields, boolean> & {
          confirmPasswordMatch: boolean;
        },
      ),
    };

    newErrors.confirmPasswordMatch = formData.password !== formData.confirmPassword;

    setErrors(newErrors);
    return Object.values(newErrors).every((value) => value === false);
  };

  const handleInputChange =
    (field: keyof UseFormFields) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = field === "is_admin" ? event.target.checked : event.target.value;
      setFormData((prevData) => ({ ...prevData, [field]: value }));
    };
  return { formData, setFormData, errors, validateForm, handleInputChange };
};

const UserResetModal = ({
  open,
  onClose,
  onContinue,
  registerUser,
  user,
}: UserModalProps) => {
  const [errorMessage, setErrorMessage] = useState("");

  React.useEffect(() => {
    // if (user) {
    //   setFormData({
    //     ...formData,
    //     username: user.username,
    //     is_admin: user.is_admin || false,
    //     contentLimit: user.content_quota ? user.content_quota.toString() : "",
    //     apiCallLimit: user.api_daily_quota
    //       ? user.api_daily_quota.toString()
    //       : "",
    //   });
    // }
  }, [user]);
  //   const handleRegister = async (event: React.MouseEvent<HTMLButtonElement>) => {
  //     event.preventDefault();
  //     if (validateForm()) {
  //       const user = {
  //         username: formData.username,
  //         is_admin: formData.is_admin || false,
  //         content_quota: parseInt(formData.contentLimit!),
  //         api_daily_quota: parseInt(formData.apiCallLimit!),
  //       } as UserBodyPassword;
  //       console.log(user, "user");
  //       const data = await registerUser(user);

  //       if (data && data.username) {
  //         onContinue(data.recovery_codes);
  //       } else {
  //         setErrorMessage("Unexpected response from the server.");
  //       }
  //     }
  //   };

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
            Reset Password
          </Typography>
          {errorMessage && (
            <Alert severity="error" sx={{ marginBottom: 2 }}>
              {errorMessage}
            </Alert>
          )}

          <TextField
            margin="normal"
            //   error={errors.username}
            //   helperText={errors.username ? "Please enter a username" : " "}
            required
            fullWidth
            label="Recovery code"
            //   value={formData.username}
            //   onChange={handleInputChange("username")}
          />

          <TextField
            margin="normal"
            //   error={errors.password}
            //   helperText={errors.password ? "Please enter a password" : " "}
            //   required
            fullWidth
            label="Password"
            type="password"
            //   value={formData.password}
            //   onChange={handleInputChange("password")}
          />

          <TextField
            margin="normal"
            //   error={errors.confirmPasswordMatch}
            //   helperText={
            //     errors.confirmPasswordMatch ? "Passwords do not match" : " "
            //   }
            required
            fullWidth
            label="Confirm Password"
            type="password"
            //   value={formData.confirmPassword}
            //   onChange={handleInputChange("confirmPassword")}
          />

          <Box mt={1} width="100%" display="flex" justifyContent="center">
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
