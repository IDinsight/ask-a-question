"use client";
import React, { useEffect } from "react";
import {
  Box,
  Button,
  CircularProgress,
  List,
  Paper,
  Tooltip,
  Typography,
  Snackbar,
  Alert,
} from "@mui/material";
import { UserCard } from "./components/UserCard";
import {
  editUser,
  editWorkspace,
  getUserList,
  getCurrentWorkspace,
  resetPassword,
  addUserToWorkspace,
  checkIfUsernameExists,
  createNewUser,
  removeUserFromWorkspace,
} from "./api";
import { useAuth } from "@/utils/auth";
import { ConfirmationModal } from "./components/ConfirmationModal";
import type { UserBody, UserBodyUpdate } from "./api";
import { UserResetModal } from "./components/UserResetModal";
import { appColors, sizes } from "@/utils";
import { Layout } from "@/components/Layout";
import WorkspaceCreateModal from "./components/WorkspaceCreateModal";
import type { Workspace } from "@/components/WorkspaceMenu";
import UserSearchModal from "./components/UserWorkspaceModal";
import { usePathname } from "next/navigation";

const UserManagement: React.FC = () => {
  const { token, userRole, loginWorkspace } = useAuth();
  const pathname = usePathname();
  const [currentWorkspace, setCurrentWorkspace] = React.useState<Workspace | null>();
  const [users, setUsers] = React.useState<UserBody[]>([]);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<UserBody | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const [openEditWorkspaceModal, setOpenEditWorkspaceModal] =
    React.useState<boolean>(false);
  const [showConfirmationModal, setShowConfirmationModal] = React.useState(false);
  const [formType, setFormType] = React.useState<"add" | "create" | "edit">("add");
  const [hoveredIndex, setHoveredIndex] = React.useState<number>(-1);
  const [snackbarMessage, setSnackbarMessage] = React.useState<{
    message: string;
    severity: "success" | "error" | "info" | "warning";
  }>({ message: "", severity: "success" });
  React.useEffect(() => {
    fetchUserData();
  }, [token, showCreateModal, showEditModal]);
  const fetchUserData = React.useCallback(() => {
    setLoading(true);
    if (!token) return;

    getCurrentWorkspace(token)
      .then((fetchedWorkspace: Workspace) => {
        setCurrentWorkspace(fetchedWorkspace);

        return getUserList(token);
      })
      .then((data: any) => {
        const userData = data.map((user: any) => ({
          username: user.username,
          user_id: user.user_id,
          user_workspaces: user.user_workspaces,
          role: user.user_workspaces.find(
            (workspace: any) =>
              workspace.workspace_name === currentWorkspace?.workspace_name,
          )?.user_role,
        }));

        const sortedData = userData.sort((a: UserBody, b: UserBody) =>
          a.username.localeCompare(b.username),
        );

        setUsers(sortedData);
      })
      .catch((error) => {
        console.error("Error fetching user data:", error);
      })
      .finally(() => {
        setLoading(false);
      });
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

  const handleEditModalContinue = (newRecoveryCodes: string[]) => {
    setLoading(true);
    setShowEditModal(false);
    setSnackbarMessage({
      message: "User edited successfully",
      severity: "success",
    });
  };

  const handleResetPassword = (user: UserBody) => {
    setCurrentUser(user);
    // setShowUserResetModal(true);
  };

  const handleEditUser = (user: UserBody) => {
    setFormType("edit");
    setCurrentUser(user);
    setShowCreateModal(true);
  };

  const getUserRoleInWorkspace = (
    workspaces: Workspace[],
    workspaceName: string,
  ): "admin" | "read_only" | undefined => {
    const workspace = workspaces.find(
      (workspace) => workspace.workspace_name === workspaceName,
    );
    if (workspace) {
      return workspace.user_role as "admin" | "read_only";
    }
    return undefined;
  };

  const handleRemoveUser = (userId: number, workspaceName: string) => {
    setLoading(true);
    removeUserFromWorkspace(userId, workspaceName, token!)
      .then((data) => {
        console.log("data", data);

        if (data.require_workspace_switch) {
          loginWorkspace(data.default_workspace_name);
        }
        if (data.status && data.status === 403) {
          setSnackbarMessage({
            message: data.message,
            severity: "error",
          });
        } else {
          setSnackbarMessage({
            message: "User removed successfully",
            severity: "success",
          });
        }
      })
      .catch((error) => {
        console.error("Failed to remove user:", error);
        setSnackbarMessage({
          message: "Failed to remove user",
          severity: "error",
        });
      })
      .finally(() => {
        fetchUserData();
      });
  };
  if (userRole !== "admin") {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="80vh">
        <Typography variant="h6">[403] Access Denied</Typography>
      </Box>
    );
  }

  function handleUserModalClose(): void {
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
        height: "95vh",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
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
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Typography variant="h4">
              Manage Workspace: <strong>{currentWorkspace?.workspace_name}</strong>
            </Typography>
            <Button
              variant="contained"
              color="secondary"
              onClick={() => {
                setOpenEditWorkspaceModal(true);
              }}
            >
              Edit Workspace
            </Button>{" "}
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
                Add existing user to workspace
              </Button>
            </>
          </Tooltip>
          <Tooltip title="Edit workspace">
            <>
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  setFormType("create");
                  setShowCreateModal(true);
                }}
              >
                Create new user and add workspace
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
              paddingTop: 1,
              paddingBottom: 10,
              paddingInline: 3,
              minHeight: "65vh",
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
            <UserSearchModal
              open={showCreateModal}
              onClose={handleUserModalClose}
              checkUserExists={(username: string) => {
                return checkIfUsernameExists(username, token!);
              }}
              addUserToWorkspace={(username: string) => {
                return addUserToWorkspace(
                  username,
                  currentWorkspace!.workspace_name,
                  token!,
                );
              }}
              createUser={(
                username: string,
                password: string,
                role: "admin" | "read_only",
              ) => {
                return createNewUser(
                  username,
                  password,
                  currentWorkspace!.workspace_name,
                  role,
                  token!,
                );
              }}
              editUser={(username: string, role: "admin" | "read_only") => {
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
