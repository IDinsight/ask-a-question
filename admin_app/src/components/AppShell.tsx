"use client";

import * as React from "react";
import { AppSidebar } from "@/components/AppSidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { ProtectedComponent } from "@/components/ProtectedComponent";
import { TopBar } from "@/components/TopBar";

/**
 * Authenticated app frame: sidebar on the left; top bar (breadcrumb, search)
 * and page content on the right. On small screens the sidebar becomes a
 * sheet opened from the top bar.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedComponent>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="h-svh overflow-auto">
          <TopBar />
          {children}
        </SidebarInset>
      </SidebarProvider>
    </ProtectedComponent>
  );
}
