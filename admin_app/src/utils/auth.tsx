"use client";
import { getLoginWorkspace } from "@/app/user-management/api";
import { apiCalls } from "@/utils/api";
import { useRouter, useSearchParams } from "next/navigation";
import { ReactNode, createContext, useContext, useState } from "react";

type AuthContextType = {
  token: string | null;
  username: string | null;
  accessLevel: "readonly" | "fullaccess";
  role: "admin" | "user" | null;
  workspaceName: string | null;
  loginError: string | null;
  login: (username: string, password: string) => void;
  loginWorkspace: (username: string, workspaceName: string) => void;
  logout: () => void;
  loginGoogle: ({
    client_id,
    credential,
  }: {
    client_id: string;
    credential: string;
  }) => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthProviderProps = {
  children: ReactNode;
};

const AuthProvider = ({ children }: AuthProviderProps) => {
  const [username, setUsername] = useState<string | null>(null);
  const getInitialRole = () => {
    if (typeof window !== "undefined") {
      const role = localStorage.getItem("role");
      return role === "admin" || role === "user" ? role : null;
    }
    return null;
  };
  const [userRole, setUserRole] = useState<"admin" | "user" | null>(getInitialRole);
  const [workspaceName, setWorkspaceName] = useState<string | null>(null);
  const getInitialToken = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  };
  const [token, setToken] = useState<string | null>(getInitialToken);

  const [loginError, setLoginError] = useState<string | null>(null);

  const getInitialAccessLevel = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("accessLevel") as "readonly" | "fullaccess";
    }
    return "readonly";
  };
  const [accessLevel, setAccessLevel] = useState<"readonly" | "fullaccess">(
    getInitialAccessLevel,
  );

  const searchParams = useSearchParams();
  const router = useRouter();
  const setLoginParams = (
    username: string,
    token: string,
    accessLevel: string,
    is_admin: boolean,
    workspaceName: string,
  ) => {
    const role = is_admin ? "admin" : "user";
    localStorage.setItem("token", token);
    localStorage.setItem("accessLevel", accessLevel);
    localStorage.setItem("role", role);
    localStorage.setItem("workspaceName", workspaceName);
    setUsername(username);
    setToken(token);
    setUserRole(role);
    setUserRole(is_admin ? "admin" : "user");
    setWorkspaceName(workspaceName);
  };
  const login = async (username: string, password: string) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/";

    try {
      const { access_token, access_level, is_admin, workspace_name } =
        await apiCalls.getLoginToken(username, password);
      setLoginParams(username, access_token, access_level, is_admin, workspace_name);
      router.push(sourcePage);
    } catch (error: Error | any) {
      if (error.status === 401) {
        setLoginError("Invalid username or password");
        console.error("Login error:", error);
      } else {
        console.error("Login error:", error);
        setLoginError("An unexpected error occurred. Please try again later.");
      }
    }
  };
  const loginWorkspace = async (username: string, workspaceName: string) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/";
    try {
      const { access_token, access_level, is_admin, workspace_name } =
        await getLoginWorkspace(username, workspaceName, token);
      setLoginParams(username, access_token, access_level, is_admin, workspace_name);
      router.push(sourcePage);
    } catch (error: Error | any) {
      if (error.status === 401) {
        setLoginError("Invalid workspace name");
        console.error("Workspace Login error:", error);
      } else {
        console.error("Login error:", error);
        setLoginError("An unexpected error occurred. Please try again later.");
      }
    }
  };

  const loginGoogle = async ({
    client_id,
    credential,
  }: {
    client_id: string;
    credential: string;
  }) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/";

    apiCalls
      .getGoogleLoginToken({ client_id: client_id, credential: credential })
      .then(({ access_token, access_level, username, is_admin, workspace_name }) => {
        setLoginParams(username, access_token, access_level, is_admin, workspace_name);
        router.push(sourcePage);
      })
      .catch((error) => {
        setLoginError("Invalid Google credentials");
        console.error("Google login error:", error);
      });
  };
  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("accessLevel");
    localStorage.removeItem("role");
    setUsername(null);
    setToken(null);
    setUserRole(null);
    setWorkspaceName(null);
    setAccessLevel("readonly");
    router.push("/login");
  };

  const authValue: AuthContextType = {
    token: token,
    username: username,
    accessLevel: accessLevel,
    role: userRole,
    workspaceName: workspaceName,
    loginError: loginError,
    login: login,
    loginWorkspace: loginWorkspace,
    loginGoogle: loginGoogle,
    logout: logout,
  };

  return <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>;
};

export default AuthProvider;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
