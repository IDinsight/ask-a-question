"use client";

import * as React from "react";
import { AppSidebar } from "@/components/AppSidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ProtectedComponent } from "@/components/ProtectedComponent";

/**
 * Authenticated app frame: sidebar on the left, page content on the right.
 * On small screens the sidebar becomes a sheet opened from the top bar.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedComponent>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="h-svh overflow-auto">
          {/* Mobile-only top bar with the sidebar toggle */}
          <header className="flex h-12 shrink-0 items-center border-b px-2 md:hidden">
            <SidebarTrigger />
          </header>
          {children}
        </SidebarInset>
      </SidebarProvider>
    </ProtectedComponent>
  );
}
