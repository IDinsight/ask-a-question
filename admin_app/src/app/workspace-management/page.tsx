"use client";
import { IconLock, IconPencil, IconUserPlus, IconUsersPlus } from "@tabler/icons-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import type { UserRole, Workspace } from "@/components/WorkspaceMenu";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
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
  const [adminUsername, setAdminUsername] = React.useState<string>(
    username || localStorage.getItem("username") || "",
  );
  // Same { message, severity } shape the old Snackbar used; shown by the Toaster in layout.tsx.
  const setSnackbarMessage = ({
    message,
    severity,
  }: {
    message: string;
    severity: "success" | "error" | "info" | "warning";
  }) => {
    if (message) toast.add({ title: message, type: severity });
  };
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

  // Show the recovery codes dialog whenever a new user's codes arrive
  useEffect(() => {
    setShowConfirmationModal(recoveryCodes.length > 0);
  }, [recoveryCodes]);

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
      <Empty className="h-full">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconLock />
          </EmptyMedia>
          <EmptyTitle className="text-base">Access denied</EmptyTitle>
          <EmptyDescription className="text-sm">
            Only workspace admins can manage the workspace and its users.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  function handleCreateModalClose(): void {
    setCurrentUser(null);
    setShowCreateModal(false);
  }



  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex items-center gap-1">
              <h1 className="text-2xl font-semibold tracking-tight break-words">
                {currentWorkspace?.workspace_name ?? "Workspace"}
              </h1>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Rename workspace"
                disabled={!currentWorkspace}
                onClick={() => setOpenEditWorkspaceModal(true)}
              >
                <IconPencil />
              </Button>
            </div>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Rename the workspace and choose who can use it.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                setFormType("add");
                setShowCreateModal(true);
              }}
            >
              <IconUsersPlus data-icon="inline-start" />
              Add existing user
            </Button>
            <Button
              size="lg"
              onClick={() => {
                setFormType("create");
                setShowCreateModal(true);
              }}
            >
              <IconUserPlus data-icon="inline-start" />
              Create new user
            </Button>
          </div>
        </header>

        <section aria-labelledby="users-heading" className="border bg-card shadow-xs">
          <h2 id="users-heading" className="border-b px-4 py-3 text-base font-semibold tracking-tight">
            Users
            {!loading && (
              <span className="ml-2 text-sm font-normal text-muted-foreground tabular-nums">
                {users.length}
              </span>
            )}
          </h2>
          {loading ? (
            <div className="flex flex-col gap-3 p-4" role="status" aria-label="Loading users">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="size-9 rounded-full" />
                  <Skeleton className="h-4 w-40" />
                </div>
              ))}
            </div>
          ) : (
            <ul>
              {users.map((user) => (
                <UserCard
                  key={user.user_id}
                  adminUsername={adminUsername}
                  userId={user.user_id!}
                  username={user.username}
                  userRole={
                    getUserRoleInWorkspace(
                      user.user_workspaces!,
                      currentWorkspace!.workspace_name,
                    ) || "read_only"
                  }
                  onRemoveUser={(userId) =>
                    handleRemoveUser(userId, currentWorkspace!.workspace_name)
                  }
                  onEditUser={() => handleEditUser(user)}
                />
              ))}
            </ul>
          )}
        </section>

        {currentWorkspace && (
          <WorkspaceCreateModal
            open={openEditWorkspaceModal}
            onClose={onWorkspaceModalClose}
            isEdit={true}
            existingWorkspace={currentWorkspace}
            onCreate={(workspaceToEdit: Workspace) => {
              return editWorkspace(currentWorkspace.workspace_id!, workspaceToEdit, token!);
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
            return addUserToWorkspace(username, currentWorkspace!.workspace_name, role, token!);
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
          dialogTitle="User created"
        />
      </div>
    </div>
  );
};

export default UserManagement;
