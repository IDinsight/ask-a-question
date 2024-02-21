"use client";
import { useState, useEffect } from "react";
import { Button } from "@mui/material";

import { useRouter } from "next/navigation";
import { useAuth } from "@/utils/auth";

export default function Home() {
  const auth = useAuth();
  const router = useRouter();

  const handleLogin = () => {
    auth.signin("admin", "admin");
  };

  useEffect(() => {
    if (auth.isAuthenticated) {
      router.push("/content");
    }
  }, [auth]);

  return (
    <div align="center">
      <h1>Login page</h1>
      {!auth.isAuthenticated && (
        <Button onClick={handleLogin} variant="contained">
          Login
        </Button>
      )}
    </div>
  );
}
