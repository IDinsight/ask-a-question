import { AppShell } from "@/components/AppShell";
import { Toaster } from "@/components/ui/toast";
import React from "react";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Toaster renders toasts raised anywhere under /integrations via `toast.add(...)`.
  return (
    <Toaster timeout={6000}>
      <AppShell>{children}</AppShell>
    </Toaster>
  );
}
