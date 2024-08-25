import NavBar from "@/components/NavBar";
import { ProtectedComponent } from "@/components/ProtectedComponent";
import React from "react";
import { Box } from "@mui/material";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ProtectedComponent>
      <NavBar />
      <Box paddingTop={"60px"}>{children}</Box>
    </ProtectedComponent>
  );
}
