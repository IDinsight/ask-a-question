import { PublicEnvScript } from "next-runtime-env";

import theme from "@/theme";
import AuthProvider from "@/utils/auth";
import { CssBaseline, ThemeProvider } from "@mui/material";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import React from "react";
import { Suspense } from "react";
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
        <script src="https://accounts.google.com/gsi/client" async></script>
        <PublicEnvScript />
      </head>
      <body className={inter.className}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Suspense>
            <AuthProvider>{children}</AuthProvider>
          </Suspense>
        </ThemeProvider>
      </body>
    </html>
  );
}
