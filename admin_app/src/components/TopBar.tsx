"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { IconSearch } from "@tabler/icons-react";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Kbd } from "@/components/ui/kbd";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useAuth } from "@/utils/auth";

type Crumb = { label: string; href?: string };

// Dashboard sub-pages are chosen with ?page=<slug> (same names as the sidebar).
const DASHBOARD_TITLES: Record<string, string> = {
  overview: "Overview",
  "content-performance": "Content performance",
  "query-topics": "Query topics",
};

/**
 * Breadcrumb trail after the workspace name for the current route.
 * Titles match the sidebar labels. Unknown routes get no page crumb.
 */
const pageCrumbs = (pathname: string, searchParams: URLSearchParams): Crumb[] => {
  if (pathname.startsWith("/content/edit")) {
    return [
      { label: "Question answering", href: "/content" },
      { label: searchParams.get("content_id") ? "Edit content" : "Add content" },
    ];
  }
  if (pathname.startsWith("/content")) return [{ label: "Question answering" }];
  if (pathname.startsWith("/urgency-rules")) return [{ label: "Urgency detection" }];
  if (pathname.startsWith("/dashboard")) {
    return [{ label: DASHBOARD_TITLES[searchParams.get("page") ?? ""] ?? "Overview" }];
  }
  if (pathname.startsWith("/integrations")) return [{ label: "Integrations" }];
  if (pathname.startsWith("/workspace-management"))
    return [{ label: "Manage workspace" }];
  return [];
};

/**
 * Sticky bar above every signed-in page: sidebar toggle (mobile only),
 * breadcrumb, and a search / jump-to button.
 *
 * The search button is a placeholder: it isn't wired to anything yet.
 */
export function TopBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { workspaceName } = useAuth();
  const crumbs = pageCrumbs(pathname, searchParams);

  return (
    <header className="sticky top-0 z-20 flex shrink-0 flex-wrap items-center justify-between gap-3 border-b bg-card px-4 py-3 sm:px-8">
      <div className="flex min-w-0 items-center gap-2">
        <SidebarTrigger className="-ml-1 md:hidden" />
        <Breadcrumb className="min-w-0">
          <BreadcrumbList className="flex-nowrap text-[13px] text-muted-foreground">
            <BreadcrumbItem className="min-w-0">
              <span className="truncate">{workspaceName ?? "Workspace"}</span>
            </BreadcrumbItem>
            {crumbs.map((crumb, i) => (
              <React.Fragment key={crumb.label}>
                <BreadcrumbSeparator />
                <BreadcrumbItem className="min-w-0">
                  {crumb.href && i < crumbs.length - 1 ? (
                    <BreadcrumbLink
                      render={<Link href={crumb.href} />}
                      className="truncate"
                    >
                      {crumb.label}
                    </BreadcrumbLink>
                  ) : (
                    <BreadcrumbPage className="truncate font-medium">
                      {crumb.label}
                    </BreadcrumbPage>
                  )}
                </BreadcrumbItem>
              </React.Fragment>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Placeholder: search / jump-to isn't implemented yet */}
      <button
        type="button"
        aria-label="Search or jump to a page"
        className="flex h-9 items-center justify-between gap-2 border border-input px-3 text-sm text-muted-foreground shadow-xs outline-none hover:bg-muted focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30 sm:min-w-65"
      >
        <span className="flex items-center gap-2">
          <IconSearch className="size-3.75" aria-hidden="true" />
          <span className="hidden sm:inline">Search or jump to…</span>
        </span>
        <Kbd className="hidden border border-input sm:inline-flex">⌘K</Kbd>
      </button>
    </header>
  );
}
