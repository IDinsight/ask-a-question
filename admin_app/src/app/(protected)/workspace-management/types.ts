/** Workspace and role types shared by the auth provider, API calls and UI. */

export type Workspace = {
  workspace_id?: number;
  workspace_name: string;
  content_quota?: number;
  api_daily_quota?: number;
  user_role?: UserRole;
  is_default?: boolean;
};
export type UserRole = "read_only" | "admin";
