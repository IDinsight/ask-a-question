"use client";
import React from "react";
import {
  Box,
  Button,
  CircularProgress,
  Grid,
  List,
  Paper,
  Typography,
} from "@mui/material";
import { UserCardNew } from "./components/UserCard";
import { editUser, getUserList, resetPassword, UserBodyPassword } from "./api";
import { useAuth } from "@/utils/auth";
import { CreateUserModal, EditUserModal } from "./components/UserCreateModal";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { createUser, UserBody } from "./api";
import { UserResetModal } from "./components/UserResetModal";
import { appColors } from "@/utils";
import { Layout } from "@/components/Layout";

const UserManagement: React.FC = () => {
  const { token, role } = useAuth();
  const [users, setUsers] = React.useState<UserBody[]>([]);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [showUserResetModal, setShowUserResetModal] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<UserBody | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
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
  }, [loading]);
  React.useEffect(() => {
    if (recoveryCodes.length > 0) {
      setShowConfirmationModal(true);
    } else {
      setShowConfirmationModal(false);
    }
  }, [recoveryCodes]);
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
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <Typography variant="h4" color="error">
          [403] Access Denied
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container sx={{ padding: 3 }}>
      <Grid
        item
        xs={12}
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingBottom: 2,
        }}
      >
        <Box>
          <Typography variant="h4">Manage User</Typography>
          <Typography variant="body1" align="left" color={appColors.darkGrey}>
            Add and edit user passwords.
          </Typography>
        </Box>
        <Button
          variant="contained"
          color="primary"
          onClick={() => {
            setShowCreateModal(true);
          }}
        >
          Add User
        </Button>
      </Grid>
      <Grid item xs={12}>
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" height="100%">
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Paper
            elevation={0}
            sx={{
              marginLeft: 10,
              marginRight: 10,
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
                  <UserCardNew
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
      </Grid>
    </Grid>
  );
};

export default UserManagement;
