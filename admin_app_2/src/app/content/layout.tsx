import NavBar from "@/components/NavBar";
import { ProtectedComponent } from "@/components/ProtectedComponent";
import AuthProvider from "@/utils/auth";
import React from "react";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ProtectedComponent>
      <NavBar />
      {children}
    </ProtectedComponent>
  );
}
