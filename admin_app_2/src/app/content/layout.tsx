import NavBar from "@/components/NavBar";
import { ProtectedComponent } from "@/components/ProtectedComponent";
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
