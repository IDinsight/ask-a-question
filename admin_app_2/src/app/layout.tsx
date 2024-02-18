import type { Metadata } from "next";
import { Inter } from "next/font/google";
//import "./globals.css";
import Button from "@mui/material/Button";
import { ThemeProvider, CssBaseline } from "@mui/material";
import theme from "@/theme";
import NavBar from "@/components/NavBar";

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
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <NavBar />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
