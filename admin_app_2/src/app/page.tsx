"use client";
import { Button } from "@mui/material";
import { useEffect } from "react";

import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const handleLogin = () => {
    router.push("/content");
  };

  return (
    <div
      style={{ display: "flex", flexDirection: "column", alignItems: "center" }}
    >
      <h1>Login page</h1>
      <Button onClick={handleLogin} variant="contained">
        Login
      </Button>
    </div>
  );
}
