import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NavBar } from "../components/NavBar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AAQ Admin",
  description:
    "Application to manage content in the Ask-a-question application",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.className} dark:bg-gradient-to-b dark:from-blue-950 flex flex-col h-screen`}
      >
        <NavBar />
        <div className="flex-1 overflow-y-auto">{children}</div>
      </body>
    </html>
  );
}
