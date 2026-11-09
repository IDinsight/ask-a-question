"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  IconCheck,
  IconPlus,
  IconSelector,
  IconSettings,
  IconStar,
} from "@tabler/icons-react";
import { useAuth } from "@/utils/auth";
import { UserBody, UserBodyUpdate } from "@/app/workspace-management/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { SidebarMenuTrigger } from "@/components/SidebarMenuTrigger";

export type Workspace = {
  workspace_id?: number;
  workspace_name: string;
  content_quota?: number;
  api_daily_quota?: number;
  user_role?: UserRole;
  is_default?: boolean;
};
export type UserRole = "read_only" | "admin";

interface WorkspaceMenuProps {
  getUserInfo: () => Promise<UserBody>;
  setOpenCreateWorkspaceModal: (value: boolean) => void;
  editUser: (user_id: number, user: UserBodyUpdate) => Promise<any>;
  loginWorkspace: (workspace: Workspace) => void;
}

/**
 * Workspace switcher shown at the top of the app sidebar.
 *
 * The trigger shows the current workspace; the dropdown lets the user switch
 * workspace, set the current one as their default, create a new one, and
 * (admins only) open workspace management.
 */
const WorkspaceMenu = ({
  getUserInfo,
  setOpenCreateWorkspaceModal,
  editUser,
  loginWorkspace,
}: WorkspaceMenuProps) => {
  const router = useRouter();
  const { workspaceName, userRole } = useAuth();
  const [workspaces, setWorkspaces] = React.useState<Workspace[]>([]);
  const [user, setUser] = React.useState<UserBody | null>(null);

  // Auth context resets on a hard refresh, so fall back to the values the
  // auth provider writes to localStorage.
  const [persistedWorkspaceName, setPersistedWorkspaceName] = React.useState("");
  const [persistedUserRole, setPersistedUserRole] = React.useState<UserRole | null>(
    null,
  );

  // Dialog state: which workspace the user wants to switch to, and whether
  // the "set as default" confirmation / success dialogs are open.
  const [switchTarget, setSwitchTarget] = React.useState<Workspace | null>(null);
  const [confirmDefaultOpen, setConfirmDefaultOpen] = React.useState(false);
  const [defaultSuccessOpen, setDefaultSuccessOpen] = React.useState(false);

  React.useEffect(() => {
    getUserInfo().then((returnedUser: UserBody) => {
      setUser({
        user_id: returnedUser.user_id,
        username: returnedUser.username,
      } as UserBody);
      // The API returns default flags as a list parallel to user_workspaces.
      const workspacesData = (returnedUser.user_workspaces ?? []) as Workspace[];
      workspacesData.forEach((workspace, index) => {
        workspace.is_default = returnedUser.is_default_workspace
          ? returnedUser.is_default_workspace[index]
          : false;
      });
      setWorkspaces(workspacesData);
    });
    // Only fetch once on mount; getUserInfo is a new closure every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (workspaceName) localStorage.setItem("workspaceName", workspaceName);
    if (userRole != null) localStorage.setItem("userRole", userRole);

    const storedWorkspace = localStorage.getItem("workspaceName");
    if (storedWorkspace) setPersistedWorkspaceName(storedWorkspace);
    const storedRole = localStorage.getItem("userRole");
    if (storedRole === "admin" || storedRole === "read_only") {
      setPersistedUserRole(storedRole);
    }
  }, [workspaceName, userRole]);

  const isAdmin = persistedUserRole === "admin";
  const currentWorkspace = workspaces.find(
    (workspace) => workspace.workspace_name === persistedWorkspaceName,
  );

  const handleConfirmDefaultWorkspace = async () => {
    if (!user?.user_id || !currentWorkspace) return;
    const updatedUser = {
      username: user.username,
      is_default_workspace: true,
      workspace_name: currentWorkspace.workspace_name,
    } as UserBodyUpdate;
    const response = await editUser(user.user_id, updatedUser);
    if (response && response.username) {
      setConfirmDefaultOpen(false);
      setDefaultSuccessOpen(true);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <SidebarMenuTrigger
              size="lg"
              aria-label="Switch workspace"
              className="data-popup-open:bg-sidebar-accent"
            />
          }
        >
          {/* Square initial badge for the workspace */}
          <span className="flex size-8 shrink-0 items-center justify-center bg-sidebar-primary text-sm font-semibold text-sidebar-primary-foreground">
            {persistedWorkspaceName.charAt(0).toUpperCase() || "?"}
          </span>
          <span className="flex min-w-0 flex-col leading-tight">
            <b className="truncate text-sm font-semibold">
              {persistedWorkspaceName || "Workspace"}
            </b>
            <span className="truncate text-xs text-sidebar-foreground/70">
              Ask a Question
            </span>
          </span>
          <IconSelector className="ml-auto text-sidebar-foreground/70" />
        </DropdownMenuTrigger>

        <DropdownMenuContent className="min-w-64" align="start" side="bottom">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Switch workspace</DropdownMenuLabel>
            {workspaces.map((workspace) => {
              const isCurrent = workspace.workspace_name === persistedWorkspaceName;
              return (
                <DropdownMenuItem
                  key={workspace.workspace_id ?? workspace.workspace_name}
                  disabled={isCurrent}
                  onClick={() => setSwitchTarget(workspace)}
                >
                  <span className="flex size-5 shrink-0 items-center justify-center border text-[10px] font-semibold">
                    {workspace.workspace_name.charAt(0).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1 truncate">
                    {workspace.workspace_name}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {workspace.user_role === "admin" ? "Admin" : "Read only"}
                  </span>
                  {isCurrent && <IconCheck />}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem
              disabled={!isAdmin || !currentWorkspace}
              onClick={() => setConfirmDefaultOpen(true)}
            >
              <IconStar />
              Set current workspace as default
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setOpenCreateWorkspaceModal(true)}>
              <IconPlus />
              Create new workspace
            </DropdownMenuItem>
            {isAdmin && (
              <DropdownMenuItem onClick={() => router.push("/workspace-management")}>
                <IconSettings />
                Manage workspace
              </DropdownMenuItem>
            )}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Confirm switching workspace */}
      <AlertDialog
        open={switchTarget !== null}
        onOpenChange={(open) => !open && setSwitchTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Switch to <strong>{switchTarget?.workspace_name}</strong>?
            </AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Stay</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (switchTarget) loginWorkspace(switchTarget);
                setSwitchTarget(null);
              }}
            >
              Switch
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Confirm setting the current workspace as default */}
      <AlertDialog open={confirmDefaultOpen} onOpenChange={setConfirmDefaultOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Make <strong>{currentWorkspace?.workspace_name}</strong> your default?
            </AlertDialogTitle>
            <AlertDialogDescription>
              You will go straight to this workspace next time you log in.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDefaultWorkspace}>
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Default workspace changed */}
      <AlertDialog open={defaultSuccessOpen} onOpenChange={setDefaultSuccessOpen}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Default workspace changed</AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Close</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default WorkspaceMenu;
