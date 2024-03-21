"use client";
import { useAuth } from "@/utils/auth";
import { usePathname, useRouter } from "next/navigation";
import React, { useEffect } from "react";
import { Layout } from "./Layout";

interface ProtectedComponentProps {
  children: React.ReactNode;
}

const ProtectedComponent: React.FC<ProtectedComponentProps> = ({
  children,
}) => {
  const router = useRouter();
  const { token } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    if (!token) {
      router.push("/login?sourcePage=" + encodeURIComponent(pathname));
    }
  }, [token]);

  return <>{children}</>;
};

const FullAccessComponent: React.FC<ProtectedComponentProps> = ({
  children,
}) => {
  const router = useRouter();
  const { token, accessLevel } = useAuth();

  if (token && accessLevel == "fullaccess") {
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
