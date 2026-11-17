"use client";
import { useAuth } from "@/utils/auth";
import { usePathname, useRouter } from "next/navigation";
import React, { useEffect } from "react";
import { useIsClient } from "@/hooks/use-browser-state";
import { IconLock } from "@tabler/icons-react";

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

interface ProtectedComponentProps {
  children: React.ReactNode;
}

const ProtectedComponent: React.FC<ProtectedComponentProps> = ({
  children,
}) => {
  const router = useRouter();
  const { token } = useAuth();
  const pathname = usePathname();
  // Don't render children until the token has been checked on the client.
  const isClient = useIsClient();

  useEffect(() => {
    if (!token) {
      router.push("/login?sourcePage=" + encodeURIComponent(pathname));
    }
  }, [token, router, pathname]);

  if (!token || !isClient) {
    return null;
  } else {
    return <>{children}</>;
  }
};

/** Renders children for workspace admins only; everyone else sees a notice. */
const FullAccessComponent: React.FC<ProtectedComponentProps> = ({
  children,
}) => {
  const { token, userRole } = useAuth();

  if (token && userRole == "admin") {
    return <>{children}</>;
  } else {
    return (
      <Empty className="h-[70vh]">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconLock />
          </EmptyMedia>
          <EmptyTitle className="text-base">Not authorised</EmptyTitle>
          <EmptyDescription className="text-sm">
            Only workspace admins can do this.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
};

export { FullAccessComponent, ProtectedComponent };
