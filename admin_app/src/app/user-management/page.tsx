"use client";
import React from "react";
import {
  Box,
  Button,
  CircularProgress,
  List,
  Paper,
  Tooltip,
  Typography,
} from "@mui/material";
import { UserCard } from "./components/UserCard";
import {
  editUser,
  editWorkspace,
  getUserList,
  getWorkspace,
  getWorkspaceList,
  resetPassword,
  UserBodyPassword,
} from "./api";
import { useAuth } from "@/utils/auth";
import { CreateUserModal, EditUserModal } from "./components/UserCreateModal";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { createUser, UserBody } from "./api";
import { UserResetModal } from "./components/UserResetModal";
import { appColors, sizes } from "@/utils";
import { Layout } from "@/components/Layout";
import WorkspaceCreateModal from "./components/WorkspaceCreateModal";
import { Workspace } from "@/components/WorkspaceMenu";
import { set } from "date-fns";

const UserManagement: React.FC = () => {
  const { token, username, role, workspaceName } = useAuth();
  const [currentWorkspace, setCurrentWorkspace] = React.useState<Workspace | null>();
  const [users, setUsers] = React.useState<UserBody[]>([]);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [showUserResetModal, setShowUserResetModal] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<UserBody | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const [openEditWorkspaceModal, setOpenEditWorkspaceModal] =
    React.useState<boolean>(false);
  const [showConfirmationModal, setShowConfirmationModal] = React.useState(false);
  const [hoveredIndex, setHoveredIndex] = React.useState<number>(-1);
  React.useEffect(() => {
    getUserList(token!).then((data: UserBody[]) => {
      const sortedData = data.sort((a: UserBody, b: UserBody) =>
        a.username.localeCompare(b.username),
      );
      setLoading(false);
      setUsers(sortedData);
    });
    getWorkspace(token!).then((data: Workspace) => {
      setCurrentWorkspace(data);
    });
  }, [loading]);
  React.useEffect(() => {
    if (recoveryCodes.length > 0) {
      setShowConfirmationModal(true);
    } else {
      setShowConfirmationModal(false);
    }
  }, [recoveryCodes]);
  const onWorkspaceModalClose = () => {
    setOpenEditWorkspaceModal(false);
  };
  const handleRegisterModalContinue = (newRecoveryCodes: string[]) => {
    setRecoveryCodes(newRecoveryCodes);
    setLoading(true);
    setShowCreateModal(false);
  };
  const handleEditModalContinue = (newRecoveryCodes: string[]) => {
    setLoading(true);
    setShowEditModal(false);
  };

  const handleResetPassword = (user: UserBody) => {
    setCurrentUser(user);
    setShowUserResetModal(true);
  };

  const handleEditUser = (user: UserBody) => {
    setCurrentUser(user);
    setShowEditModal(true);
  };

  if (role !== "admin") {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="80vh">
        <Typography variant="h6">[403] Access Denied</Typography>
      </Box>
    );
  }

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
            <Typography variant="h4">Manage Workspace</Typography>
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
                  setShowCreateModal(true);
                }}
              >
                Create new user to workspace
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
                    username={user.username}
                    isAdmin={user.is_admin}
                    isLastItem={index === users.length - 1}
                    hoveredIndex={hoveredIndex}
                    setHoveredIndex={setHoveredIndex}
                    onResetPassword={() => handleResetPassword(user)}
                    onEditUser={() => handleEditUser(user)}
                  />
                  <EditUserModal
                    open={showEditModal}
                    onClose={() => {
                      setShowEditModal(false);
                    }}
                    user={currentUser!}
                    isLoggedUser={currentUser?.username === username}
                    onContinue={handleEditModalContinue}
                    registerUser={(userToEdit: UserBody) => {
                      return editUser(currentUser!.user_id!, userToEdit, token!);
                    }}
                    title={`Edit User: ${currentUser?.username}`}
                    buttonTitle="Confirm"
                  />
                  <UserResetModal
                    open={showUserResetModal}
                    onClose={() => {
                      setShowUserResetModal(false);
                    }}
                    onContinue={() => {}}
                    resetPassword={(
                      username: string,
                      recoveryCode: string,
                      password: string,
                    ) => {
                      return resetPassword(username, recoveryCode, password, token!);
                    }}
                    user={currentUser!}
                  />
                </Layout.FlexBox>
              ))}
            </List>
            {currentWorkspace && (
              <WorkspaceCreateModal
                open={openEditWorkspaceModal}
                onClose={onWorkspaceModalClose}
                isEdit={true}
                onCreate={(name: string) => {
                  const workspace = {
                    workspace_id: currentWorkspace.workspace_id,
                    workspace_name: name,
                  } as Workspace;

                  return editWorkspace(1, workspace, token!);
                }}
                existingWorkspace={currentWorkspace}
              />
            )}
            <CreateUserModal
              open={showCreateModal}
              onClose={() => {
                setShowCreateModal(false);
              }}
              onContinue={handleRegisterModalContinue}
              registerUser={(user: UserBodyPassword | UserBody) => {
                return createUser(user as UserBodyPassword, token!);
              }}
              buttonTitle="Confirm"
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
    </Layout.FlexBox>
  );
};

export default UserManagement;
