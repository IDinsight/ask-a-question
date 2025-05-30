import { PublicEnvScript } from "next-runtime-env";
import theme from "@/theme";
import AuthProvider from "@/utils/auth";
import { CssBaseline, ThemeProvider } from "@mui/material";
import type { Metadata } from "next";
import React, { Suspense } from "react";
import { inter } from "@/fonts";
import QueryProvider from "@/utils/QueryProvider";

export const metadata: Metadata = {
  title: "Ask A Question",
  description: "Trustworthy answers for communities. Actionable insights for you.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="initial-scale=1, width=device-width" />
        <script src="https://accounts.google.com/gsi/client" async></script>
        <PublicEnvScript />
      </head>
      <body className={inter.className}>
        <QueryProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <Suspense>
              <AuthProvider>{children}</AuthProvider>
            </Suspense>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
