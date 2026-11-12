/**
 * TanStack Query hooks for workspace management and the signed-in shell.
 *
 * Two callers:
 * - WorkspaceManagementWrapper (the /workspace-management page);
 * - the shared app shell in src/components/common (AppSidebar → WorkspaceMenu),
 *   which shows the current user's workspaces and can edit the user or create
 *   a workspace.
 * Both read the same query keys, so a mutation on one side updates the other.
 *
 * Conventions (same as dashboard/queries.ts):
 * - Hooks read the auth token themselves and stay disabled until it exists.
 * - The token is NOT part of the query key; AuthProvider clears the whole cache
 *   when the user or workspace changes.
 * - Responses are reshaped with `select` (module-level, so the reference is stable).
 * - Mutations invalidate the keys whose data they change.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/utils/auth";
import {
  addUserToWorkspace,
  checkIfUsernameExists,
  createNewUser,
  createWorkspace,
  editUser,
  editWorkspace,
  getCurrentWorkspace,
  getUser,
  getUserList,
  removeUserFromWorkspace,
} from "./api";
import type { UserBody, UserBodyUpdate } from "./api";
import type { UserRole, Workspace } from "./types";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

export const workspaceKeys = {
  all: ["workspace-management"] as const,
  /** GET /user/current-user: the signed-in user and their workspaces. */
  currentUser: () => [...workspaceKeys.all, "current-user"] as const,
  /** GET /workspace/current-workspace */
  currentWorkspace: () => [...workspaceKeys.all, "current-workspace"] as const,
  /** GET /user/: users of the current workspace. */
  users: () => [...workspaceKeys.all, "users"] as const,
};

/* ------------------------------------------------------------------ */
/* Current user (sidebar workspace switcher)                           */
/* ------------------------------------------------------------------ */

/** Raw /user/current-user response. Default flags are a list parallel to user_workspaces. */
type CurrentUserResponse = {
  user_id: number;
  username: string;
  user_workspaces?: Workspace[];
  is_default_workspace?: boolean[];
};

export type CurrentUser = {
  user: { user_id: number; username: string };
  /** The user's workspaces, each with its `is_default` flag filled in. */
  workspaces: Workspace[];
};

const parseCurrentUser = (data: CurrentUserResponse): CurrentUser => ({
  user: { user_id: data.user_id, username: data.username },
  // Copy each workspace rather than mutating the cached response.
  workspaces: (data.user_workspaces ?? []).map((workspace, index) => ({
    ...workspace,
    is_default: data.is_default_workspace ? data.is_default_workspace[index] : false,
  })),
});

export const useCurrentUserQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: workspaceKeys.currentUser(),
    queryFn: (): Promise<CurrentUserResponse> => getUser(token!),
    select: parseCurrentUser,
    enabled: !!token,
  });
};

/* ------------------------------------------------------------------ */
/* Current workspace + its users (workspace management page)           */
/* ------------------------------------------------------------------ */

export const useCurrentWorkspaceQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: workspaceKeys.currentWorkspace(),
    queryFn: (): Promise<Workspace> => getCurrentWorkspace(token!),
    enabled: !!token,
  });
};

/** Raw /user/ row: the user plus every workspace they belong to. */
type UserListRow = { user_id: number; username: string; user_workspaces: Workspace[] };

/**
 * Users of the current workspace. Raw rows are cached; the Wrapper turns them
 * into UserBody (role in this workspace, sorted) with `toWorkspaceUsers`,
 * because that depends on the workspace name and the signed-in username.
 */
export const useUserListQuery = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: workspaceKeys.users(),
    queryFn: (): Promise<UserListRow[]> => getUserList(token!),
    enabled: !!token,
  });
};

/**
 * Give each user their role in `workspaceName` and sort by username, with the
 * signed-in admin (`adminUsername`) always at the top.
 */
export const toWorkspaceUsers = (
  rows: UserListRow[],
  workspaceName: string | undefined,
  adminUsername: string,
): UserBody[] =>
  rows
    .map((user) => ({
      username: user.username,
      user_id: user.user_id,
      user_workspaces: user.user_workspaces,
      role: user.user_workspaces.find(
        (workspace) => workspace.workspace_name === workspaceName,
      )?.user_role as UserRole,
    }))
    .sort((a, b) => {
      if (a.username === adminUsername) return -1;
      if (b.username === adminUsername) return 1;
      return a.username.localeCompare(b.username);
    });

/* ------------------------------------------------------------------ */
/* User mutations                                                      */
/* ------------------------------------------------------------------ */

/**
 * "Verify" in the add-user dialog: does this username exist anywhere?
 * A mutation rather than a query because it runs on a button click and the
 * answer should come from the server every time (no cached result).
 */
export const useCheckUsernameMutation = () => {
  const { token } = useAuth();
  return useMutation({
    mutationFn: (username: string) => checkIfUsernameExists(username, token!),
  });
};

/** Create a brand-new user in the given workspace. Resolves with their recovery codes. */
export const useCreateUserMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      username: string;
      password: string;
      workspaceName: string;
      role: UserRole;
    }): Promise<{ recovery_codes?: string[] }> =>
      createNewUser(
        vars.username,
        vars.password,
        vars.workspaceName,
        vars.role,
        token!,
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
  });
};

export const useAddUserToWorkspaceMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { username: string; workspaceName: string; role: UserRole }) =>
      addUserToWorkspace(vars.username, vars.workspaceName, vars.role, token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
  });
};

/**
 * Edit a user's role, or set a workspace as their default (sidebar). Both the
 * user list and the sidebar's current-user data can change, so refresh both.
 */
export const useEditUserMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { userId: number; user: UserBodyUpdate }) =>
      editUser(vars.userId, vars.user, token!),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
      ]),
  });
};

/**
 * Remove a user from a workspace. The list is refreshed whether or not this
 * worked (the old code refetched in `.finally`). Removing yourself also
 * changes your own workspaces, so the sidebar data is refreshed too.
 */
export const useRemoveUserMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      userId: number;
      workspaceName: string;
    }): Promise<{
      require_workspace_switch?: boolean;
      default_workspace_name: string;
    }> => removeUserFromWorkspace(vars.userId, vars.workspaceName, token!),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
      ]),
  });
};

/* ------------------------------------------------------------------ */
/* Workspace mutations                                                 */
/* ------------------------------------------------------------------ */

/**
 * Create a workspace (sidebar). It shows up in the sidebar's workspace list.
 * The API returns the workspace, or an empty list when the name is taken.
 */
export const useCreateWorkspaceMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (workspace: Workspace): Promise<Workspace> =>
      createWorkspace(workspace, token!),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
  });
};

/** Rename a workspace. The page heading and the sidebar list both show the name. */
export const useEditWorkspaceMutation = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      workspaceId: number;
      workspace: Workspace;
    }): Promise<Workspace> => editWorkspace(vars.workspaceId, vars.workspace, token!),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentWorkspace() }),
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
      ]),
  });
};
