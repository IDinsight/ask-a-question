import { AppShell } from "@/components/AppShell";
import { Toaster } from "@/components/ui/toast";
import React from "react";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Toaster renders toasts raised anywhere under /dashboard via `toast.add(...)`.
  return (
    <Toaster timeout={5000}>
      <AppShell>{children}</AppShell>
    </Toaster>
  );
}
