import type { Metadata } from "next";
import { Inter } from "next/font/google";
//import "./globals.css";
import NavBar from "@/components/NavBar";
import theme from "@/theme";
import { AuthProvider } from "@/utils/auth";
import { CssBaseline, ThemeProvider } from "@mui/material";
import React from "react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ask A Question",
  description: "Admin application to manage content and glean insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="initial-scale=1, width=device-width" />
      </head>
      <body className={inter.className}>
        <AuthProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <NavBar />
            {children}
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
