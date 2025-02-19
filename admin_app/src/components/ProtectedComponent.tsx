"use client";
import { useAuth } from "@/utils/auth";
import { usePathname, useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
import { Layout } from "./Layout";

interface ProtectedComponentProps {
  children: React.ReactNode;
}

const ProtectedComponent: React.FC<ProtectedComponentProps> = ({ children }) => {
  const router = useRouter();
  const { token } = useAuth();
  const pathname = usePathname();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    if (!token) {
      router.push("/login?sourcePage=" + encodeURIComponent(pathname));
    }
  }, [token]);

  // This is to prevent the page from starting to load the children before the token is checked
  useEffect(() => {
    setIsClient(true);
  }, []);
  if (!token || !isClient) {
    return null;
  } else {
    return <>{children}</>;
  }
};

const FullAccessComponent: React.FC<ProtectedComponentProps> = ({ children }) => {
  const router = useRouter();
  const { token, userRole } = useAuth();

  if (token && userRole == "admin") {
    return <>{children}</>;
  } else {
    return (
      <Layout.FlexBox
        sx={{
          justifyContent: "center",
          alignItems: "center",
          height: "70vh",
          typography: "body1",
        }}
      >
        Not Authorised
      </Layout.FlexBox>
    );
  }
};

export { FullAccessComponent, ProtectedComponent };
