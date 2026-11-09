import React from "react";

import { Toaster } from "@/components/ui/toast";
import { AppShell } from "./_components/AppShell";
import { ProtectedComponent } from "./_components/ProtectedComponent";

/**
 * Layout for every signed-in page (content, dashboard, integrations, urgency
 * rules, workspace management). Route groups don't change the URL, so these
 * still live at /content, /dashboard, etc.
 *
 * Auth: ProtectedComponent reads the token from the client-side auth context
 * and sends signed-out users to /login. It's a client component, so it
 * re-renders when the token changes, even though this layout itself doesn't
 * re-render on navigation. This is the basic version; a `proxy.ts` check can
 * be added later so unauthenticated requests are redirected before render.
 */
export default function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <ProtectedComponent>
      {/* One Toaster for the whole signed-in area; pages raise toasts with toast.add(...) */}
      <Toaster timeout={5000}>
        <AppShell>{children}</AppShell>
      </Toaster>
    </ProtectedComponent>
  );
}
