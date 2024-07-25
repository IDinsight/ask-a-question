import NavBar from "@/components/NavBar";
import { ProtectedComponent } from "@/components/ProtectedComponent";
import React from "react";
import Grid from "@mui/material/Grid";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ProtectedComponent>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <NavBar />
        </Grid>
        <Grid item xs={12}>
          {children}
        </Grid>
      </Grid>
    </ProtectedComponent>
  );
}
