"use client";

import type React from "react";
import { useState, useCallback, useMemo, useEffect } from "react";
import {
  IconAlertCircle,
  IconCircleCheckFilled,
  IconInfoCircle,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Spinner } from "@/components/ui/spinner";

import { UserBody } from "../api";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { UserRole } from "@/components/WorkspaceMenu";

interface UserCreateModalProps {
  open: boolean;
  onClose: () => void;
  adminUsername: string;
  checkUserExists: (username: string) => Promise<boolean>;
  addUserToWorkspace: (username: string, role: UserRole) => Promise<void>;
  createUser: (username: string, password: string, role: UserRole) => Promise<any>;
  formType: "add" | "create" | "edit";
  editUser?: (username: string, role: UserRole) => Promise<void>;
  users: UserBody[];
  user?: UserBody;
  setSnackMessage: (message: {
    message: string;
    severity: "success" | "error" | "info" | "warning";
  }) => void;
  onContinue: (data: string[]) => void;
}

const UserCreateModal: React.FC<UserCreateModalProps> = ({
  open,
  onClose,
  adminUsername,
  checkUserExists,
  addUserToWorkspace,
  createUser,
  editUser,
  formType,
  users,
  user,
  setSnackMessage,
  onContinue,
}) => {
  const { logout: logout } = useAuth();
  const [username, setUsername] = useState<string>(user?.username || "");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");

  const [role, setRole] = useState<UserRole>("read_only");
  const [userExists, setUserExists] = useState<boolean | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{
    text: string;
    severity: "error" | "warning" | "info" | "success";
  } | null>(null);

  const isUserInWorkspace = useMemo(
    () => users.some((u) => u.username === username),
    [users, username],
  );
  const handleClose = useCallback(() => {
    setUsername("");
    setPassword("");
    setConfirmPassword("");
    setRole("read_only");
    setUserExists(null);
    setIsVerified(false);
    setLoading(false);
    setError(null);
    onClose();
  }, [onClose]);

  const handleVerifyUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const exists = await checkUserExists(username);
      setUserExists(exists);
      if (!exists) {
        setError({
          text: `User ${username} does not exist. You can create it below.`,
          severity: "info",
        });
      }
      if (isUserInWorkspace) {
        setError({
          text: `User ${username} is already in the workspace.`,
          severity: "error",
        });
      } else {
        setIsVerified(true);
      }
    } catch (err) {
      setError({ text: "Error verifying user.", severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [username, checkUserExists]);

  const validateInputs = useCallback(() => {
    if (!username) {
      setError({ text: "Username is required.", severity: "error" });
      return false;
    }
    if (formType == "create") {
      if (!password) {
        setError({ text: "Password is required.", severity: "error" });
        return false;
      }
      if (password !== confirmPassword) {
        setError({ text: "Passwords do not match.", severity: "error" });
        setPassword("");
        setConfirmPassword("");
        return false;
      }
    }
    setError(null);
    return true;
  }, [username, password, confirmPassword, formType]);

  const handleError = (error: any) => {
    let errorMsg = "Error processing request";
    if (error) {
      const customError = error as CustomError;
      if (customError.message) {
        errorMsg = customError.message;
      }
      setError({ text: errorMsg, severity: "error" });
    }
  };
  const actions: Record<"add" | "create" | "edit", () => Promise<void> | undefined> = {
    create: async () =>
      await createUser(username, password, role).then((data) => {
        if (data.recovery_codes) {
          onContinue(data.recovery_codes);
        }
      }),
    add: async () => {
      if (isVerified && userExists) {
        await addUserToWorkspace(username, role);
      } else if (isVerified && !userExists) {
        await createUser(username, password, role).then((data) => {
          if (data.recovery_codes) {
            onContinue(data.recovery_codes);
          }
        });
      } else {
        setError({
          text: "Unable to add user.",
          severity: "error",
        });
      }
    },
    edit: async () => {
      if (editUser) {
        await editUser(username, role);
        if (username == adminUsername && role !== "admin") {
          logout();
        }
      } else {
        setError({
          text: "Edit user function is not defined.",
          severity: "error",
        });
      }
    },
  };

  const handleAction = useCallback(async () => {
    if (!validateInputs()) return;
    setLoading(true);
    setError(null);
    try {
      await actions[formType]?.();
      setSnackMessage({
        message: `User successfully ${
          formType === "add" ? "added" : formType === "edit" ? "edited" : formType + "d"
        }`,
        severity: "success",
      });
      setTimeout(() => {
        onClose();
      }, 300);
    } catch (error) {
      handleError(error);
    } finally {
      setLoading(false);
    }
  }, [
    formType,
    username,
    password,
    confirmPassword,
    role,
    isVerified,
    userExists,
    addUserToWorkspace,
    createUser,
    editUser,
  ]);

  const getTitle = (formType: "add" | "create" | "edit") => {
    const titles = {
      add: "Add an existing user",
      create: "Create a user",
      edit: "Edit user",
    };
    return titles[formType] || "Create a user";
  };

  const getDescription = (formType: "add" | "create" | "edit") => {
    const descriptions = {
      add: "Check the username first, then choose their role in this workspace.",
      create:
        "The new user is added to this workspace. You’ll see their recovery codes once.",
      edit: "Change this user’s role in the workspace.",
    };
    return descriptions[formType];
  };

  const getButtonTitle = (formType: "add" | "create" | "edit") => {
    const buttonTitles = {
      add: "Add to workspace",
      create: "Create user",
      edit: "Save",
    };
    return buttonTitles[formType] || "Create user";
  };

  useEffect(() => {
    if (formType === "edit" && user) {
      setUsername(user.username);
      if (user.role) {
        setRole(user.role);
      }
    }
  }, [user, formType, user?.role]);

  const showPasswordFields =
    (isVerified && userExists === false) || formType == "create";
  const showRole =
    (formType == "add" && isVerified) ||
    formType === "create" ||
    (formType == "edit" && user && user.role);
  // Admins can't demote themselves here
  const roleLocked = formType == "edit" && user?.username === adminUsername;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="p-6 sm:max-w-md">
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (!(loading || (formType == "add" && !isVerified))) handleAction();
          }}
          className="flex flex-col gap-5"
        >
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              {getTitle(formType)}
            </DialogTitle>
            <DialogDescription className="text-sm">
              {getDescription(formType)}
            </DialogDescription>
          </DialogHeader>

          <Field>
            <FieldLabel htmlFor="user-username" className="text-sm">
              Username
            </FieldLabel>
            <div className="flex gap-2">
              <Input
                id="user-username"
                autoFocus={formType !== "edit"}
                autoComplete="off"
                disabled={formType === "edit"}
                value={username}
                className="h-10 text-sm md:text-sm"
                onChange={(e) => {
                  setUsername(e.target.value);
                  setIsVerified(false);
                }}
              />
              {formType == "add" &&
                (isVerified && userExists ? (
                  <span className="flex h-10 shrink-0 items-center gap-1.5 px-2 text-sm font-medium text-chart-1">
                    <IconCircleCheckFilled className="size-5" aria-hidden="true" />
                    Verified
                  </span>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-10 px-4"
                    onClick={handleVerifyUser}
                    disabled={loading || !username}
                  >
                    {loading && <Spinner data-icon="inline-start" />}
                    Verify
                  </Button>
                ))}
            </div>
          </Field>

          {error && (
            <Alert variant={error.severity === "error" ? "destructive" : "default"}>
              {error.severity === "error" ? (
                <IconAlertCircle aria-hidden="true" />
              ) : (
                <IconInfoCircle aria-hidden="true" />
              )}
              <AlertDescription
                className={
                  error.severity === "error" ? "text-sm text-destructive" : "text-sm"
                }
              >
                {error.text}
              </AlertDescription>
            </Alert>
          )}

          {showPasswordFields && (
            <>
              <Field>
                <FieldLabel htmlFor="user-password" className="text-sm">
                  Password
                </FieldLabel>
                <Input
                  id="user-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  className="h-10 text-sm md:text-sm"
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="user-confirm-password" className="text-sm">
                  Confirm password
                </FieldLabel>
                <Input
                  id="user-confirm-password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  className="h-10 text-sm md:text-sm"
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </Field>
            </>
          )}

          {showRole && (
            <Field>
              <FieldLabel htmlFor="user-role" className="text-sm">
                Role
              </FieldLabel>
              <NativeSelect
                id="user-role"
                className="w-full [&_select]:h-10 [&_select]:text-sm"
                value={role}
                disabled={roleLocked}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <NativeSelectOption value="admin">Admin</NativeSelectOption>
                <NativeSelectOption value="read_only">Read only</NativeSelectOption>
              </NativeSelect>
              {roleLocked && (
                <FieldDescription>You can’t change your own role.</FieldDescription>
              )}
            </Field>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="lg"
              disabled={loading || (formType == "add" && !isVerified)}
            >
              {loading && formType !== "add" && <Spinner data-icon="inline-start" />}
              {getButtonTitle(formType)}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default UserCreateModal;
