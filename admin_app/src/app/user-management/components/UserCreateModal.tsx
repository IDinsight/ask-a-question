import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  TextField,
  Typography,
} from "@mui/material";
import React, { useState } from "react";
import { UserBody, UserBodyPassword } from "../api";

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
interface UserModalProps {
  open: boolean;
  onClose: () => void;
  onContinue: (data: any) => void;
  registerUser: (user: UserBodyPassword | UserBody) => Promise<any>;
  fields?: Array<keyof UseFormFields>;
  title?: string;
  buttonTitle?: string;
  showCancel?: boolean;
  user?: UserBody;
  isLoggedUser?: boolean;
}

const UserModal = ({
  open,
  onClose,
  onContinue,
  registerUser,
  fields = ["username", "password", "confirmPassword"],
  title = "Register User",
  buttonTitle = "Register",
  showCancel = true,
  user,
  isLoggedUser = false,
}: UserModalProps) => {
  const { formData, setFormData, errors, validateForm, handleInputChange } = useForm(
    fields,
    user,
  );

  const [errorMessage, setErrorMessage] = useState("");

  React.useEffect(() => {
    if (user) {
      setFormData({
        ...formData,
        username: user.username,
        is_admin: user.is_admin || false,
        contentLimit: user.content_quota ? user.content_quota.toString() : "",
        apiCallLimit: user.api_daily_quota ? user.api_daily_quota.toString() : "",
      });
    }
  }, [user]);
  const handleRegister = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (validateForm()) {
      const newUser = user
        ? ({
            username: formData.username,
            is_admin: formData.is_admin || false,

            content_quota: parseInt(formData.contentLimit!),
            api_daily_quota: parseInt(formData.apiCallLimit!),
          } as UserBody)
        : ({
            username: formData.username,
            is_admin: formData.is_admin || false,
            password: formData.password,
            content_quota: parseInt(formData.contentLimit!),
            api_daily_quota: parseInt(formData.apiCallLimit!),
          } as UserBodyPassword);
      const data = await registerUser(newUser);

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
            gap: 1,
            alignItems: "center",
            padding: 3,
          }}
        >
          <Avatar sx={{ bgcolor: "secondary.main" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography variant="h5" align="center" marginBottom={5}>
            {title}
          </Typography>
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
          {fields.includes("username") && (
            <TextField
              margin="none"
              error={errors.username}
              helperText={errors.username ? "Please enter a username" : " "}
              required
              fullWidth
              label="Username"
              value={formData.username}
              onChange={handleInputChange("username")}
            />
          )}
          {fields.includes("password") && (
            <TextField
              margin="none"
              error={errors.password}
              helperText={errors.password ? "Please enter a password" : " "}
              required
              fullWidth
              label="Password"
              type="password"
              value={formData.password}
              onChange={handleInputChange("password")}
            />
          )}
          {fields.includes("confirmPassword") && (
            <TextField
              margin="none"
              error={errors.confirmPasswordMatch}
              helperText={errors.confirmPasswordMatch ? "Passwords do not match" : " "}
              required
              fullWidth
              label="Confirm Password"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange("confirmPassword")}
            />
          )}
          {fields.includes("contentLimit") && fields.includes("apiCallLimit") && (
            <Box display="flex" justifyContent="space-between" width="100%">
              <TextField
                margin="none"
                error={errors.contentLimit}
                helperText={errors.contentLimit ? "Enter content limit" : " "}
                required
                label="Content Limit"
                type="number"
                sx={{ width: "48%" }}
                value={formData.contentLimit}
                onChange={handleInputChange("contentLimit")}
              />
              <TextField
                margin="none"
                error={errors.apiCallLimit}
                helperText={errors.apiCallLimit ? "Enter API call limit" : " "}
                required
                label="API Call Limit"
                type="number"
                sx={{ width: "48%" }}
                value={formData.apiCallLimit}
                onChange={handleInputChange("apiCallLimit")}
              />
            </Box>
          )}
          {fields.includes("is_admin") && (
            <Box
              display="flex"
              alignItems="center"
              width="100%"
              sx={{ justifyContent: "flex-start" }}
            >
              <Checkbox
                disabled={isLoggedUser}
                checked={formData.is_admin || false}
                onChange={handleInputChange("is_admin")}
              />
              <Typography variant="body1">Admin User</Typography>
            </Box>
          )}
          <Box
            width="100%"
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 2,
              gap: 2,
            }}
          >
            {showCancel && (
              <Button
                onClick={() => onClose()}
                type="submit"
                fullWidth
                sx={{ maxWidth: "120px" }}
              >
                Cancel
              </Button>
            )}
            <Button
              onClick={handleRegister}
              type="submit"
              fullWidth
              variant="contained"
              sx={{ maxWidth: "120px" }}
            >
              {buttonTitle}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
const CreateUserModal = (props: Omit<UserModalProps, "fields">) => (
  <UserModal
    {...props}
    fields={[
      "username",
      "password",
      "confirmPassword",
      "contentLimit",
      "apiCallLimit",
      "is_admin",
    ]}
  />
);

const EditUserModal = (props: Omit<UserModalProps, "fields">) => (
  <UserModal
    {...props}
    fields={["username", "contentLimit", "apiCallLimit", "is_admin"]}
  />
);

export { UserModal, CreateUserModal, EditUserModal };
export type { UserModalProps };
