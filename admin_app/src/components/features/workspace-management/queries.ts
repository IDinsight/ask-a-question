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
 * Conventions (shared by every feature's queries.ts):
 * - Requests go through the generated client (src/client, from core_backend's
 *   OpenAPI spec) to the /bff proxy. Reads spread the generated `*Options()`;
 *   keys come from the generated `*QueryKey()` functions.
 * - Hooks stay disabled until the user has a token (the client attaches it).
 *   The token is NOT part of the query key; AuthProvider clears the whole cache
 *   when the user or workspace changes.
 * - Responses are reshaped with `select` (module-level, so the reference is stable).
 * - Mutations invalidate the keys whose data they change.
 * - Errors are CustomError (4xx) or Error (5xx/network); see utils/api.ts.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addExistingUser,
  checkIfUsernameExists,
  createNewUser,
  createWorkspaces,
  removeUserFromWorkspace,
  updateUser,
  updateWorkspace,
} from "@/client";
import {
  getUserOptions,
  getUserQueryKey,
  retrieveAllUsersInCurrentWorkspaceOptions,
  retrieveAllUsersInCurrentWorkspaceQueryKey,
  retrieveCurrentWorkspaceOptions,
  retrieveCurrentWorkspaceQueryKey,
} from "@/client/@tanstack/react-query.gen";
import type { UserRetrieve, WorkspaceRetrieve } from "@/client";
import { isCustomError, type CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import type { UserBody, UserBodyUpdate, UserRole, Workspace } from "./types";

/* ------------------------------------------------------------------ */
/* Query keys                                                          */
/* ------------------------------------------------------------------ */

/** Named aliases for the generated keys, shared with the integrations page. */
export const workspaceKeys = {
  /** GET /user/current-user: the signed-in user and their workspaces. */
  currentUser: () => getUserQueryKey(),
  /** GET /workspace/current-workspace */
  currentWorkspace: () => retrieveCurrentWorkspaceQueryKey(),
  /** GET /user/: users of the current workspace. */
  users: () => retrieveAllUsersInCurrentWorkspaceQueryKey(),
};

/* ------------------------------------------------------------------ */
/* Current user (sidebar workspace switcher)                           */
/* ------------------------------------------------------------------ */

export type CurrentUser = {
  user: { user_id: number; username: string };
  /** The user's workspaces, each with its `is_default` flag filled in. */
  workspaces: Workspace[];
};

/** Default flags come back as a list parallel to user_workspaces. */
const parseCurrentUser = (data: UserRetrieve): CurrentUser => ({
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
    ...getUserOptions(),
    select: parseCurrentUser,
    enabled: !!token,
  });
};

/* ------------------------------------------------------------------ */
/* Current workspace + its users (workspace management page)           */
/* ------------------------------------------------------------------ */

export const useCurrentWorkspaceQuery = () => {
  const { token } = useAuth();
  return useQuery({ ...retrieveCurrentWorkspaceOptions(), enabled: !!token });
};

/** Raw /user/ row: the user plus every workspace they belong to. */
type UserListRow = Pick<UserRetrieve, "user_id" | "username" | "user_workspaces">;

/**
 * Users of the current workspace. Raw rows are cached; the Wrapper turns them
 * into UserBody (role in this workspace, sorted) with `toWorkspaceUsers`,
 * because that depends on the workspace name and the signed-in username.
 */
export const useUserListQuery = () => {
  const { token } = useAuth();
  return useQuery({ ...retrieveAllUsersInCurrentWorkspaceOptions(), enabled: !!token });
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
 * HEAD /user/{username}: 200 = exists, 404 = free, anything else is an error.
 */
export const useCheckUsernameMutation = () =>
  useMutation({
    mutationFn: async (username: string): Promise<boolean> => {
      try {
        await checkIfUsernameExists({ path: { username } });
        return true;
      } catch (error) {
        if (isCustomError(error) && error.status === 404) return false;
        throw new Error("Error checking username");
      }
    },
  });

/** Create a brand-new user in the given workspace. Resolves with their recovery codes. */
export const useCreateUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      username: string;
      password: string;
      workspaceName: string;
      role: UserRole;
    }) => {
      const { data } = await createNewUser({
        body: {
          username: vars.username,
          password: vars.password,
          workspace_name: vars.workspaceName,
          role: vars.role,
        },
      });
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
  });
};

export const useAddUserToWorkspaceMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      username: string;
      workspaceName: string;
      role: UserRole;
    }): Promise<void> => {
      await addExistingUser({
        body: {
          username: vars.username,
          role: vars.role,
          workspace_name: vars.workspaceName,
          is_default_workspace: true,
        },
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspaceKeys.users() }),
  });
};

/**
 * Edit a user's role, or set a workspace as their default (sidebar). Both the
 * user list and the sidebar's current-user data can change, so refresh both.
 */
export const useEditUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { userId: number; user: UserBodyUpdate }) => {
      const { data } = await updateUser({
        path: { user_id: vars.userId },
        body: vars.user,
      });
      return data;
    },
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
 *
 * A 403 means the user is the workspace's last admin; it gets a friendlier
 * message than the backend's.
 */
export const useRemoveUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { userId: number; workspaceName: string }) => {
      try {
        const { data } = await removeUserFromWorkspace({
          path: { user_id: vars.userId },
          query: { remove_from_workspace_name: vars.workspaceName },
        });
        return data;
      } catch (error) {
        if (isCustomError(error) && error.status === 403) {
          throw {
            status: 403,
            message: "You cannot remove the last admin from the workspace.",
          } as CustomError;
        }
        throw error;
      }
    },
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
 * The API returns the created workspaces, or an empty list when the name is taken.
 */
export const useCreateWorkspaceMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (workspace: Workspace): Promise<WorkspaceRetrieve[]> => {
      const { data } = await createWorkspaces({
        body: {
          workspace_name: workspace.workspace_name,
          content_quota: workspace.content_quota,
          api_daily_quota: workspace.api_daily_quota,
        },
      });
      return data;
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
  });
};

/** Rename a workspace. The page heading and the sidebar list both show the name. */
export const useEditWorkspaceMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      workspaceId: number;
      workspace: Workspace;
    }): Promise<Workspace> => {
      const { data } = await updateWorkspace({
        path: { workspace_id: vars.workspaceId },
        body: {
          workspace_name: vars.workspace.workspace_name,
          content_quota: vars.workspace.content_quota,
          api_daily_quota: vars.workspace.api_daily_quota,
        },
      });
      // The response echoes the update; fall back to the requested name.
      return {
        ...vars.workspace,
        ...data,
        workspace_name: data.workspace_name ?? vars.workspace.workspace_name,
      };
    },
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentWorkspace() }),
        queryClient.invalidateQueries({ queryKey: workspaceKeys.currentUser() }),
      ]),
  });
};
