"use client";
import { Layout } from "@/components/Layout";
import type { UserRole, Workspace } from "@/components/WorkspaceMenu";
import { appColors, sizes } from "@/utils";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import ModeEditIcon from "@mui/icons-material/ModeEdit";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  List,
  Paper,
  Snackbar,
  Tooltip,
  Typography,
} from "@mui/material";
import { usePathname } from "next/navigation";
import React, { useEffect } from "react";
import type { UserBody, UserBodyUpdate } from "./api";
import {
  addUserToWorkspace,
  checkIfUsernameExists,
  createNewUser,
  editUser,
  editWorkspace,
  getCurrentWorkspace,
  getUserList,
  removeUserFromWorkspace,
} from "./api";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { UserCard } from "./components/UserCard";
import UserCreateModal from "./components/UserWorkspaceModal";
import WorkspaceCreateModal from "./components/WorkspaceCreateModal";

const UserManagement: React.FC = () => {
  const { token, userRole, loginWorkspace, username } = useAuth();
  const pathname = usePathname();
  const [currentWorkspace, setCurrentWorkspace] = React.useState<Workspace | null>();
  const [users, setUsers] = React.useState<UserBody[]>([]);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<UserBody | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const [openEditWorkspaceModal, setOpenEditWorkspaceModal] =
    React.useState<boolean>(false);
  const [showConfirmationModal, setShowConfirmationModal] = React.useState(false);
  const [formType, setFormType] = React.useState<"add" | "create" | "edit">("add");
  const [hoveredIndex, setHoveredIndex] = React.useState<number>(-1);
  const [adminUsername, setAdminUsername] = React.useState<string>(
    username || localStorage.getItem("username") || "",
  );
  const [snackbarMessage, setSnackbarMessage] = React.useState<{
    message: string;
    severity: "success" | "error" | "info" | "warning";
  }>({ message: "", severity: "success" });
  React.useEffect(() => {
    fetchUserData();
  }, [token, showCreateModal]);

  const fetchUserData = React.useCallback(async () => {
    setLoading(true);
    if (!token) return;
    try {
      const fetchedWorkspace = await getCurrentWorkspace(token);
      setCurrentWorkspace(fetchedWorkspace);
      const data = await getUserList(token);
      const userData = data.map((user: any) => ({
        username: user.username,
        user_id: user.user_id,
        user_workspaces: user.user_workspaces,
        role: user.user_workspaces.find(
          (workspace: any) =>
            workspace.workspace_name === fetchedWorkspace?.workspace_name,
        )?.user_role,
      }));

      // Sort users by username, with the admin user always at the top
      const sortedData = userData.sort((a: UserBody, b: UserBody) => {
        if (a.username === adminUsername) return -1;
        if (b.username === adminUsername) return 1;
        return a.username.localeCompare(b.username);
      });

      setUsers(sortedData);
      setLoading(false);
    } catch (error: any) {
      console.error("Error fetching user data:", error);
    } finally {
      setLoading(false);
    }
  }, [token, currentWorkspace]);

  const onWorkspaceModalClose = () => {
    setOpenEditWorkspaceModal(false);
  };

  const handleCreateModalContinue = (newRecoveryCodes: string[]) => {
    setRecoveryCodes(newRecoveryCodes);
    setShowCreateModal(false);
    setSnackbarMessage({
      message: "User created successfully",
      severity: "success",
    });
  };

  const handleEditUser = (user: UserBody) => {
    setCurrentUser(user);
    setFormType("edit");
    setShowCreateModal(true);
  };

  const getUserRoleInWorkspace = (
    workspaces: Workspace[],
    workspaceName: string,
  ): UserRole | undefined => {
    const workspace = workspaces.find(
      (workspace) => workspace.workspace_name === workspaceName,
    );
    if (workspace) {
      return workspace.user_role as UserRole;
    }
    return undefined;
  };

  const handleRemoveUser = (userId: number, workspaceName: string) => {
    setLoading(true);
    const isOnlyAdmin =
      users.filter(
        (user) =>
          getUserRoleInWorkspace(user.user_workspaces!, workspaceName) === "admin" &&
          user.user_id !== userId,
      ).length === 0;

    if (isOnlyAdmin) {
      setSnackbarMessage({
        message: "You cannot remove the only admin from the workspace",
        severity: "error",
      });
      setLoading(false);
      return;
    }

    removeUserFromWorkspace(userId, workspaceName, token!)
      .then((data) => {
        if (data.require_workspace_switch) {
          loginWorkspace(data.default_workspace_name);
        }

        setSnackbarMessage({
          message: "User removed successfully",
          severity: "success",
        });
      })
      .catch((error) => {
        const customError = error as CustomError;
        let errorMessage = "Failed to remove user";
        if (customError.message) {
          errorMessage = customError.message;
        }

        console.error("Failed to remove user:", error);
        setSnackbarMessage({
          message: errorMessage,
          severity: "error",
        });
      })
      .finally(() => {
        fetchUserData();
      });
  };
  if (userRole !== "admin") {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100%">
        <Typography variant="h6">[403] Access Denied</Typography>
      </Box>
    );
  }

  function handleCreateModalClose(): void {
    setCurrentUser(null);
    setShowCreateModal(false);
  }

  const handleSnackbarClose = (
    event?: React.SyntheticEvent | Event,
    reason?: string,
  ) => {
    if (reason === "clickaway") {
      return;
    }
    setSnackbarMessage({ message: "", severity: "info" });
  };

  useEffect(() => {
    if (recoveryCodes.length > 0) {
      setShowConfirmationModal(true);
    } else {
      setShowConfirmationModal(false);
    }
  }, [recoveryCodes]);

  return (
    <Layout.FlexBox
      sx={{
        alignItems: "center",
        paddingTop: 5,
        paddingInline: 4,
        gap: sizes.baseGap,
        height: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          width: "100%",
          maxWidth: "lg",
          minWidth: "sm",
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            paddingBottom: 2,
            gap: 2,
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Typography
              variant="h4"
              sx={{
                wordBreak: "break-word",
                display: "inline-block",
                color: appColors.primary,
              }}
            >
              Manage Workspace: <strong>{currentWorkspace?.workspace_name}</strong>
            </Typography>
            <Tooltip title="Edit workspace name">
              <IconButton
                sx={{ color: appColors.primary }}
                onClick={() => {
                  setOpenEditWorkspaceModal(true);
                }}
              >
                <ModeEditIcon />
              </IconButton>
            </Tooltip>
          </Box>
          <Typography variant="body1" align="left" color={appColors.darkGrey}>
            Edit workspace and add/remove users to workspace
          </Typography>
        </Box>
        <Layout.FlexBox
          sx={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "flex-end",
            gap: sizes.tinyGap,
          }}
        >
          <Tooltip title="Add existing user to workspace">
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  setFormType("add");
                  setShowCreateModal(true);
                }}
              >
                Add existing user
              </Button>
            </>
          </Tooltip>
          <Tooltip title="Create user">
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  setFormType("create");
                  setShowCreateModal(true);
                }}
              >
                Create new user
              </Button>
            </>
          </Tooltip>
        </Layout.FlexBox>
        <Layout.Spacer />
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" height="100%">
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Paper
            elevation={0}
            sx={{
              flexGrow: 1,
              paddingTop: 1,
              marginBottom: 5,
              paddingInline: 3,
              overflowY: "auto",
              border: 0.5,
              borderColor: "lightgrey",
            }}
          >
            <List>
              {users.map((user, index) => (
                <Layout.FlexBox key={user.user_id}>
                  <UserCard
                    index={index}
                    adminUsername={adminUsername}
                    userId={user.user_id!}
                    username={user.username}
                    userRole={
                      getUserRoleInWorkspace(
                        user.user_workspaces!,
                        currentWorkspace!.workspace_name,
                      ) || "read_only"
                    }
                    isLastItem={index === users.length - 1}
                    hoveredIndex={hoveredIndex}
                    setHoveredIndex={setHoveredIndex}
                    onRemoveUser={(userId) =>
                      handleRemoveUser(userId, currentWorkspace!.workspace_name)
                    }
                    onEditUser={() => handleEditUser(user)}
                  />
                </Layout.FlexBox>
              ))}
            </List>
            {currentWorkspace && (
              <WorkspaceCreateModal
                open={openEditWorkspaceModal}
                onClose={onWorkspaceModalClose}
                isEdit={true}
                existingWorkspace={currentWorkspace}
                onCreate={(workspaceToEdit: Workspace) => {
                  return editWorkspace(
                    currentWorkspace.workspace_id!,
                    workspaceToEdit,
                    token!,
                  );
                }}
                loginWorkspace={(workspace: Workspace) => {
                  return loginWorkspace(workspace.workspace_name, pathname);
                }}
                setSnackMessage={setSnackbarMessage}
              />
            )}
            <UserCreateModal
              open={showCreateModal}
              onClose={handleCreateModalClose}
              adminUsername={adminUsername}
              checkUserExists={(username: string) => {
                return checkIfUsernameExists(username, token!);
              }}
              addUserToWorkspace={(username: string, role: string) => {
                return addUserToWorkspace(
                  username,
                  currentWorkspace!.workspace_name,
                  role,
                  token!,
                );
              }}
              createUser={(username: string, password: string, role: UserRole) => {
                return createNewUser(
                  username,
                  password,
                  currentWorkspace!.workspace_name,
                  role,
                  token!,
                );
              }}
              editUser={(username: string, role: UserRole) => {
                return editUser(
                  currentUser!.user_id!,
                  {
                    username,
                    role,
                    workspace_name: currentWorkspace?.workspace_name,
                  } as UserBodyUpdate,
                  token!,
                );
              }}
              setSnackMessage={setSnackbarMessage}
              onContinue={handleCreateModalContinue}
              formType={formType}
              users={users}
              user={currentUser ? currentUser : undefined}
            />
            <ConfirmationModal
              open={showConfirmationModal}
              onClose={() => {
                setShowConfirmationModal(false);
              }}
              recoveryCodes={recoveryCodes}
              dialogTitle="User Created"
            />
          </Paper>
        )}
      </Box>
      <Snackbar
        open={snackbarMessage.message !== ""}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbarMessage.severity}
          sx={{ width: "100%" }}
        >
          {snackbarMessage.message}
        </Alert>
      </Snackbar>
    </Layout.FlexBox>
  );
};

export default UserManagement;
