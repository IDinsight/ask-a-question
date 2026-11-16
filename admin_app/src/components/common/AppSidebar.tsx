"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  IconBolt,
  IconCategory,
  IconChartBar,
  IconLayoutDashboard,
  IconLogout,
  IconMessage,
  IconPlug,
  IconSelector,
  IconUser,
} from "@tabler/icons-react";
import { useAuth } from "@/utils/auth";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenuTrigger } from "@/components/common/SidebarMenuTrigger";
import WorkspaceMenu from "@/components/common/WorkspaceMenu";
import type { Workspace } from "@/components/features/workspace-management/types";
import { useLocalStorageItem } from "@/hooks/use-browser-state";
import WorkspaceCreateModal from "@/components/features/workspace-management/components/WorkspaceCreateModal";
import type { UserBodyUpdate } from "@/components/features/workspace-management/types";
import {
  useCreateWorkspaceMutation,
  useCurrentUserQuery,
  useEditUserMutation,
  useWorkspaceUsageQuery,
} from "@/components/features/workspace-management/queries";
import type { WorkspaceUsage as WorkspaceUsageData } from "@/client";

/** Stable fallback while the current user's workspaces load. */
const NO_WORKSPACES: Workspace[] = [];

// TODO: replace with the real contact/support link once decided.
const CONTACT_HREF = "#contact";

type NavItem = {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Which count from GET /workspace/current-workspace/usage to badge with. */
  countKey?: "content_cards_used" | "urgency_rules_count";
  /** Returns true when this item matches the current route. */
  isActive: (pathname: string, dashboardPage: string) => boolean;
};

type NavGroup = { label: string; items: NavItem[] };

// Dashboard sub-pages are selected with ?page=<slug>; "overview" is the default.
const dashboardItem = (
  title: string,
  slug: string,
  icon: NavItem["icon"],
): NavItem => ({
  title,
  href: `/dashboard?page=${slug}`,
  icon,
  isActive: (pathname, dashboardPage) =>
    pathname.startsWith("/dashboard") && dashboardPage === slug,
});

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Build",
    items: [
      {
        title: "Question answering",
        href: "/content",
        icon: IconMessage,
        countKey: "content_cards_used",
        isActive: (pathname) => pathname.startsWith("/content"),
      },
      {
        title: "Urgency detection",
        href: "/urgency-rules",
        icon: IconBolt,
        countKey: "urgency_rules_count",
        isActive: (pathname) => pathname.startsWith("/urgency-rules"),
      },
    ],
  },
  {
    label: "Insights",
    items: [
      dashboardItem("Overview", "overview", IconLayoutDashboard),
      dashboardItem("Content performance", "content-performance", IconChartBar),
      dashboardItem("Query topics", "query-topics", IconCategory),
    ],
  },
  {
    label: "Connect",
    items: [
      {
        title: "Integrations",
        href: "/integrations",
        icon: IconPlug,
        isActive: (pathname) => pathname.startsWith("/integrations"),
      },
    ],
  },
];

/**
 * Main app navigation: workspace switcher, nav groups, usage, account menu.
 *
 * The sidebar's data lives here: the signed-in user and their workspaces
 * (shared with /workspace-management through the same query keys), plus the
 * "set default workspace" and "create workspace" mutations. The parts below
 * (WorkspaceMenu, AccountMenu, WorkspaceCreateModal) only get props.
 */
export function AppSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const dashboardPage = searchParams.get("page") ?? "overview";
  const { loginWorkspace, workspaceName, userRole, logout, username } =
    useAuth();
  const [openCreateWorkspaceModal, setOpenCreateWorkspaceModal] =
    React.useState(false);

  const currentUser = useCurrentUserQuery();
  const editUser = useEditUserMutation();
  const createWorkspace = useCreateWorkspaceMutation();
  // Badge counts and usage meters. Undefined while loading or on error, in
  // which case badges and meters are hidden rather than showing a fake 0.
  const usage = useWorkspaceUsageQuery().data;

  return (
    <Sidebar aria-label="Workspace navigation">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <WorkspaceMenu
              user={currentUser.data?.user ?? null}
              workspaces={currentUser.data?.workspaces ?? NO_WORKSPACES}
              workspaceName={workspaceName}
              userRole={userRole}
              setOpenCreateWorkspaceModal={setOpenCreateWorkspaceModal}
              editUser={(userId, user: UserBodyUpdate) =>
                editUser.mutateAsync({ userId, user })
              }
              loginWorkspace={(workspace: Workspace) =>
                loginWorkspace(workspace.workspace_name, pathname)
              }
            />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarMenu>
              {group.items.map((item) => {
                const active = item.isActive(pathname, dashboardPage);
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      isActive={active}
                      render={
                        <Link
                          href={item.href}
                          aria-current={active ? "page" : undefined}
                        />
                      }
                    >
                      <item.icon />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                    {item.countKey && usage && (
                      <SidebarMenuBadge>
                        {usage[item.countKey]}
                      </SidebarMenuBadge>
                    )}
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        {usage && <WorkspaceUsage usage={usage} />}
        <SidebarMenu>
          <SidebarMenuItem>
            <AccountMenu username={username} onLogout={logout} />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      {/* Opened from the workspace switcher. */}
      <WorkspaceCreateModal
        open={openCreateWorkspaceModal}
        onClose={() => setOpenCreateWorkspaceModal(false)}
        isEdit={false}
        onCreate={(workspace: Workspace) =>
          createWorkspace.mutateAsync(workspace)
        }
        loginWorkspace={(workspace: Workspace) =>
          loginWorkspace(workspace.workspace_name, pathname)
        }
      />
    </Sidebar>
  );
}

/** Usage card: content cards and daily API calls against workspace quotas. */
function WorkspaceUsage({ usage }: { usage: WorkspaceUsageData }) {
  return (
    <div className="mx-2 mb-1 flex flex-col gap-3 border border-sidebar-border p-3 text-xs">
      <div className="font-medium">Workspace usage</div>
      <UsageMeter
        label="Content cards"
        unit="content cards"
        used={usage.content_cards_used}
        quota={usage.content_quota ?? null}
      />
      <UsageMeter
        label="API calls today"
        unit="daily API calls"
        used={usage.api_calls_used_today}
        quota={usage.api_daily_quota ?? null}
      />
      <a
        href={CONTACT_HREF}
        className="text-sidebar-primary underline-offset-2 hover:underline"
      >
        Need more? Contact us
      </a>
    </div>
  );
}

function UsageMeter({
  label,
  unit,
  used,
  quota,
}: {
  label: string;
  unit: string;
  used: number;
  /** null = no limit for this workspace. */
  quota: number | null;
}) {
  // Clamp to 0–100 so an over-quota workspace doesn't overflow the bar.
  // An unlimited quota shows an empty bar.
  const pct =
    quota !== null && quota > 0
      ? Math.min(100, Math.max(0, (used / quota) * 100))
      : 0;
  const quotaLabel = quota === null ? "∞" : quota;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-sidebar-foreground/70">
        <span>{label}</span>
        <b className="font-medium text-sidebar-foreground tabular-nums">
          {used} / {quotaLabel}
        </b>
      </div>
      <div
        className="h-1 w-full bg-sidebar-accent"
        role="img"
        aria-label={
          quota === null
            ? `${used} ${unit} used, no limit`
            : `${used} of ${quota} ${unit} used`
        }
      >
        <i
          className="block h-full bg-sidebar-primary"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/** Account menu at the bottom of the sidebar. */
function AccountMenu({
  username,
  onLogout,
}: {
  username: string | null;
  onLogout: () => void;
}) {
  // username is lost on a hard refresh; auth stores it in localStorage on login.
  const storedUsername = useLocalStorageItem("username");
  const displayName = username ?? storedUsername;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <SidebarMenuTrigger
            size="lg"
            aria-label="Account menu"
            className="data-popup-open:bg-sidebar-accent"
          />
        }
      >
        <span className="flex size-8 shrink-0 items-center justify-center border border-sidebar-border bg-sidebar-accent text-sidebar-foreground/70">
          <IconUser />
        </span>
        <span className="truncate text-sm font-medium">
          {displayName ?? "Account"}
        </span>
        <IconSelector className="ml-auto text-sidebar-foreground/70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent side="top" align="start" className="min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Signed in as {displayName}</DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onLogout}>
          <IconLogout />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
