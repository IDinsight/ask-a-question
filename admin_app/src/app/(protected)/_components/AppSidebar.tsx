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
import { SidebarMenuTrigger } from "@/app/(protected)/_components/SidebarMenuTrigger";
import WorkspaceMenu from "@/app/(protected)/_components/WorkspaceMenu";
import type { Workspace } from "@/app/(protected)/workspace-management/types";
import WorkspaceCreateModal from "@/app/(protected)/workspace-management/_components/WorkspaceCreateModal";
import {
  createWorkspace,
  editUser,
  getUser,
  UserBodyUpdate,
} from "@/app/(protected)/workspace-management/api";

// ---------------------------------------------------------------------------
// Placeholder data
//
// UI only for now: these numbers are hard-coded until the API exposes them.
// See admin_app/README.md ("Sidebar: API work") for what is needed.
// ---------------------------------------------------------------------------
const PLACEHOLDER_COUNTS = { content: 0, urgencyRules: 0 };
const PLACEHOLDER_USAGE = {
  contentCards: { used: 0, quota: 50 },
  apiCallsToday: { used: 0, quota: 100 },
};
// TODO: replace with the real contact/support link once decided.
const CONTACT_HREF = "#contact";

type NavItem = {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  count?: number;
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
        count: PLACEHOLDER_COUNTS.content,
        isActive: (pathname) => pathname.startsWith("/content"),
      },
      {
        title: "Urgency detection",
        href: "/urgency-rules",
        icon: IconBolt,
        count: PLACEHOLDER_COUNTS.urgencyRules,
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

/** Main app navigation: workspace switcher, nav groups, usage, account menu. */
export function AppSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const dashboardPage = searchParams.get("page") ?? "overview";
  const { token, loginWorkspace } = useAuth();
  const [openCreateWorkspaceModal, setOpenCreateWorkspaceModal] = React.useState(false);

  return (
    <Sidebar aria-label="Workspace navigation">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <WorkspaceMenu
              getUserInfo={() => getUser(token!)}
              setOpenCreateWorkspaceModal={setOpenCreateWorkspaceModal}
              editUser={(userId, user: UserBodyUpdate) =>
                editUser(userId, user, token!)
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
                    {item.count !== undefined && (
                      <SidebarMenuBadge>{item.count}</SidebarMenuBadge>
                    )}
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <WorkspaceUsage />
        <SidebarMenu>
          <SidebarMenuItem>
            <AccountMenu />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      {/* Opened from the workspace switcher. */}
      <WorkspaceCreateModal
        open={openCreateWorkspaceModal}
        onClose={() => setOpenCreateWorkspaceModal(false)}
        isEdit={false}
        onCreate={(workspace: Workspace) => createWorkspace(workspace, token!)}
        loginWorkspace={(workspace: Workspace) =>
          loginWorkspace(workspace.workspace_name, pathname)
        }
      />
    </Sidebar>
  );
}

/** Usage card: content cards and daily API calls against workspace quotas. */
function WorkspaceUsage() {
  const { contentCards, apiCallsToday } = PLACEHOLDER_USAGE;
  return (
    <div className="mx-2 mb-1 flex flex-col gap-3 border border-sidebar-border p-3 text-xs">
      <div className="font-medium">Workspace usage</div>
      <UsageMeter label="Content cards" unit="content cards" {...contentCards} />
      <UsageMeter label="API calls today" unit="daily API calls" {...apiCallsToday} />
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
  quota: number;
}) {
  // Clamp to 0–100 so an over-quota workspace doesn't overflow the bar.
  const pct = quota > 0 ? Math.min(100, Math.max(0, (used / quota) * 100)) : 0;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-sidebar-foreground/70">
        <span>{label}</span>
        <b className="font-medium text-sidebar-foreground tabular-nums">
          {used} / {quota}
        </b>
      </div>
      <div
        className="h-1 w-full bg-sidebar-accent"
        role="img"
        aria-label={`${used} of ${quota} ${unit} used`}
      >
        <i className="block h-full bg-sidebar-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Account menu at the bottom of the sidebar. */
function AccountMenu() {
  const { logout, username } = useAuth();
  // username is lost on a hard refresh; auth stores it in localStorage on login.
  const [displayName, setDisplayName] = React.useState<string | null>(username);

  React.useEffect(() => {
    setDisplayName(username ?? localStorage.getItem("username"));
  }, [username]);

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
        <span className="truncate text-sm font-medium">{displayName ?? "Account"}</span>
        <IconSelector className="ml-auto text-sidebar-foreground/70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent side="top" align="start" className="min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Signed in as {displayName}</DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout}>
          <IconLogout />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
