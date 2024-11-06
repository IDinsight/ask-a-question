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
import { UserCard, UserCardNew } from "./components/UserCard";
import { editUser, getUserList } from "./api";
import { useAuth } from "@/utils/auth";
import { CreateUserModal, EditUserModal } from "./components/UserCreateModal";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { createUser, UserBody } from "./api";
import { UserResetModal } from "./components/UserResetModal";
import { appColors } from "@/utils";
const UserManagement: React.FC = () => {
  const { token } = useAuth();
  const [users, setUsers] = React.useState<UserBody[]>([]);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [showUserResetModal, setShowUserResetModal] = React.useState(false);
  const [userToEdit, setUserToEdit] = React.useState<UserBody | undefined>(undefined);
  const [loading, setLoading] = React.useState(true);
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const [showConfirmationModal, setShowConfirmationModal] = React.useState(false);
  const [hoveredIndex, setHoveredIndex] = React.useState<number>(-1);
  React.useEffect(() => {
    getUserList(token!).then((data) => {
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
    setUserToEdit(user);
    setShowUserResetModal(true);
  };

  const handleEditUser = (user: UserBody) => {
    setUserToEdit(user);
    setShowEditModal(true);
  };

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
              width: "100%",
              paddingTop: 1,
              paddingBottom: 10,
              paddingInline: 3,
              minHeight: "65vh",
              overflowY: "auto",
              border: 0.5,
              borderColor: "lightgrey",
            }}
          >
            {users.map((user, index) => {
              const isLastItem = index === users.length - 1;

              return (
                //   <Grid item xs={12} sm={6} md={4} lg={3} key={user.user_id}>
                //     {/* <UserCard
                //     username={user.username}
                //     isAdmin={user.is_admin}
                //     onResetPassword={() => handleResetPassword(user)}
                //     onEditUser={() => handleEditUser(user)}
                //   /> */}
                <List>
                  <UserCardNew
                    index={index}
                    username={user.username}
                    isAdmin={user.is_admin}
                    isLastItem={isLastItem}
                    hoveredIndex={hoveredIndex}
                    setHoveredIndex={setHoveredIndex}
                    onResetPassword={() => handleResetPassword(user)}
                    onEditUser={() => handleEditUser(user)}
                  />
                </List>
                //    </Grid>
              );
            })}

            <CreateUserModal
              open={showCreateModal}
              onClose={() => {
                setShowCreateModal(false);
              }}
              onContinue={handleRegisterModalContinue}
              registerUser={(user) => {
                return createUser(user, token!);
              }}
              buttonTitle="Confirm"
            />
            <EditUserModal
              open={showEditModal}
              onClose={() => {
                setShowEditModal(false);
              }}
              user={userToEdit}
              onContinue={handleEditModalContinue}
              registerUser={(user) => {
                return editUser(userToEdit!.user_id!, user, token!);
              }}
              title={`Edit User: ${userToEdit?.username}`}
              buttonTitle="Confirm"
            />
            <ConfirmationModal
              open={showConfirmationModal}
              onClose={() => {
                setShowConfirmationModal(false);
              }}
              recoveryCodes={recoveryCodes}
            />
            <UserResetModal
              open={showUserResetModal}
              onClose={() => {
                setShowUserResetModal(false);
              }}
              onContinue={() => {}}
              registerUser={(user) => {
                return editUser(userToEdit!.user_id!, user, token!);
              }}
              user={userToEdit}
            />
          </Paper>
        )}
      </Grid>
    </Grid>
  );
};

export default UserManagement;
