"use client";

import * as React from "react";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";

/**
 * Authenticated app frame: sidebar on the left; top bar (breadcrumb, search)
 * and page content on the right. On small screens the sidebar becomes a
 * sheet opened from the top bar. The auth check lives in (protected)/layout.tsx.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-svh overflow-auto">
        <TopBar />
        {children}
      </SidebarInset>
    </SidebarProvider>
  );
}
