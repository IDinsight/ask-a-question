"use client";
import { apiCalls } from "@/utils/api";
import { useRouter, useSearchParams } from "next/navigation";
import { ReactNode, createContext, useContext, useState } from "react";

type AuthContextType = {
  token: string | null;
  user: string | null;
  accessLevel: "readonly" | "fullaccess";
  loginError: string | null;
  login: (username: string, password: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthProviderProps = {
  children: ReactNode;
};

const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<string | null>(null);
  const getInitialToken = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  };

  const [token, setToken] = useState<string | null>(getInitialToken);

  const [loginError, setLoginError] = useState<string | null>(null);
  const [accessLevel, setAccessLevel] = useState<"readonly" | "fullaccess">(
    "readonly",
  );
  const searchParams = useSearchParams();
  const router = useRouter();

  const login = async (username: string, password: string) => {
    const fromPage = searchParams.has("fromPage")
      ? decodeURIComponent(searchParams.get("fromPage") as string)
      : "/";

    apiCalls
      .getLoginToken(username, password)
      .then(({ access_token, access_level }) => {
        localStorage.setItem("token", access_token);

        setUser(username);
        setToken(access_token);
        setAccessLevel(access_level);
        router.push(fromPage);
      })
      .catch((error) => {
        setLoginError("Invalid username or password");
        console.error("Login error:", error);
      });
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    setToken(null);
    setAccessLevel("readonly");
    router.push("/login");
  };

  const authValue: AuthContextType = {
    token: token,
    user: user,
    accessLevel: accessLevel,
    loginError: loginError,
    login: login,
    logout: logout,
  };

  return (
    <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
  );
};

export default AuthProvider;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
