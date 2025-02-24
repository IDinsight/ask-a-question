"use client";
import { getLoginWorkspace } from "@/app/workspace-management/api";
import { UserRole } from "@/components/WorkspaceMenu";
import { apiCalls, CustomError } from "@/utils/api";
import { useRouter, useSearchParams } from "next/navigation";
import { ReactNode, createContext, useContext, useState } from "react";

type AuthContextType = {
  token: string | null;
  username: string | null;
  accessLevel: "readonly" | "fullaccess";
  userRole: UserRole | null;
  workspaceName: string | null;
  loginError: string | null;
  login: (username: string, password: string) => void;
  loginWorkspace: (workspaceName: string, currentPage?: string) => void;
  logout: () => void;
  loginGoogle: ({
    client_id,
    credential,
  }: {
    client_id: string;
    credential: string;
  }) => void;
  logoutWorkspace: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

type AuthProviderProps = {
  children: ReactNode;
};

const AuthProvider = ({ children }: AuthProviderProps) => {
  const [username, setUsername] = useState<string | null>(null);
  const getInitialRole = () => {
    if (typeof window !== "undefined") {
      const userRole = localStorage.getItem("userRole");
      return userRole as UserRole | null;
    }
    return null;
  };
  const [userRole, setUserRole] = useState<UserRole | null>(getInitialRole);
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
    token: string,
    accessLevel: string,
    user_role: UserRole,
    workspaceName: string,
  ) => {
    localStorage.setItem("token", token);
    localStorage.setItem("accessLevel", accessLevel);
    localStorage.setItem("workspaceName", workspaceName);
    localStorage.setItem("userRole", user_role);
    setToken((prev) => (prev === token ? `${token} ` : token));
    setUserRole(user_role);

    setWorkspaceName(workspaceName);
  };
  const login = async (username: string, password: string) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/";

    try {
      const { access_token, access_level, user_role, workspace_name } =
        await apiCalls.getLoginToken(username, password);
      localStorage.setItem("username", username);
      setUsername(username);
      setLoginParams(access_token, access_level, user_role, workspace_name);
      router.push(sourcePage);
    } catch (error: CustomError | any) {
      if (error.status === 401) {
        setLoginError(error.message);
        console.error("Login error:", error);
      } else {
        console.error("Login error:", error);
        setLoginError("An unexpected error occurred. Please try again later.");
      }
    }
  };
  const loginWorkspace = async (workspaceName: string, currentPage?: string) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/content";
    try {
      logoutWorkspace();
      const { access_token, access_level, user_role, workspace_name } =
        await getLoginWorkspace(workspaceName, token);
      setLoginParams(access_token, access_level, user_role, workspace_name);
      if (currentPage) {
        router.push(currentPage);
      } else {
        router.push(sourcePage);
      }
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
      .then(({ access_token, access_level, username, user_role, workspace_name }) => {
        localStorage.setItem("username", username);
        setUsername(username);
        setLoginParams(access_token, access_level, user_role, workspace_name);
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
    localStorage.removeItem("userRole");
    localStorage.removeItem("workspaceName");
    setUsername(null);
    setToken(null);
    setUserRole(null);
    setWorkspaceName(null);
    setAccessLevel("readonly");
    router.push("/login");
  };

  const logoutWorkspace = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("accessLevel");
    localStorage.removeItem("userRole");
    localStorage.removeItem("workspaceName");
    setToken(null);
    setUserRole(null);
    setWorkspaceName(null);
  };

  const authValue: AuthContextType = {
    token: token,
    username: username,
    accessLevel: accessLevel,
    userRole: userRole,
    workspaceName: workspaceName,
    loginError: loginError,
    login: login,
    loginWorkspace: loginWorkspace,
    loginGoogle: loginGoogle,
    logout: logout,
    logoutWorkspace: logoutWorkspace,
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
