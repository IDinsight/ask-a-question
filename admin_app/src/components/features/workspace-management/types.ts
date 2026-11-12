/** Workspace and role types shared by the auth provider, API calls and UI. */

export type Workspace = {
  workspace_id?: number;
  workspace_name: string;
  content_quota?: number | null;
  api_daily_quota?: number | null;
  user_role?: UserRole;
  is_default?: boolean;
};
export type UserRole = "read_only" | "admin";

/** A user as the workspace UI shows them: their role in the current workspace. */
export interface UserBody {
  user_id?: number;
  username: string;
  role: UserRole;
  is_default_workspace?: boolean[];
  user_workspaces?: Workspace[];
}

export interface UserBodyPassword extends UserBody {
  password: string;
}

/** Body for PUT /user/{user_id}: change a role or the default workspace. */
export interface UserBodyUpdate extends Omit<UserBody, "is_default_workspace"> {
  is_default_workspace?: boolean;
  workspace_name: string;
}
