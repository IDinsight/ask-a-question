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
      <Box sx={{ display: "flex", flexDirection: "column", height: "100vh" }}>
        <NavBar />
        <Box sx={{ flexGrow: 1, overflow: "auto", paddingTop: "60px" }}>{children}</Box>
      </Box>
    </ProtectedComponent>
  );
}
