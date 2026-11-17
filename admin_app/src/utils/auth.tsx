"use client";
import {
  login as loginRequest,
  loginGoogle as loginGoogleRequest,
  switchWorkspace,
} from "@/client";
import type { AuthenticationDetails } from "@/client/types.gen";
import type { UserRole } from "@/components/features/workspace-management/types";
import { isCustomError } from "@/utils/api";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ReactNode,
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  SessionExpiredError,
  clearTokens,
  getFreshAccessToken,
  getRefreshToken,
  revokeRefreshToken,
  saveTokens,
  syncSessionCookie,
} from "@/lib/api/session";

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
  // Restored from localStorage like the token and role, so it survives a page reload.
  const getInitialWorkspaceName = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("workspaceName");
    }
    return null;
  };
  const [workspaceName, setWorkspaceName] = useState<string | null>(
    getInitialWorkspaceName,
  );
  const getInitialToken = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  };
  const [token, setToken] = useState<string | null>(getInitialToken);

  // Keep the cookie src/proxy.ts reads in line with what's stored. Sign-in and
  // sign-out already set/clear it (session.ts); this covers sessions that
  // started before the cookie existed, so they get it on their next visit.
  useEffect(() => {
    syncSessionCookie();
  }, [token]);

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
  // Cached server data belongs to one user + workspace. Drop it whenever that
  // identity changes, so a new workspace never shows the previous one's data.
  const queryClient = useQueryClient();
  /** Store a login/switch response: token pair plus who and where the user is. */
  const setLoginParams = (details: AuthenticationDetails) => {
    const {
      access_token: token,
      access_level: accessLevel,
      user_role,
      workspace_name: workspaceName,
    } = details;
    queryClient.clear();
    // Access token, refresh token, expiry and the proxy cookie.
    saveTokens(details);
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
      // OAuth2 password form, sent as application/x-www-form-urlencoded.
      const { data } = await loginRequest({ body: { username, password } });
      localStorage.setItem("username", username);
      setUsername(username);
      setLoginParams(data);
      router.push(sourcePage);
    } catch (error) {
      // A 401 arrives as a CustomError (see utils/api.ts).
      if (isCustomError(error) && error.status === 401) {
        setLoginError(error.message);
        console.error("Login error:", error);
      } else {
        console.error("Login error:", error);
        setLoginError("An unexpected error occurred. Please try again later.");
      }
    }
  };
  const loginWorkspace = async (
    workspaceName: string,
    currentPage?: string,
  ) => {
    const sourcePage = searchParams.has("sourcePage")
      ? decodeURIComponent(searchParams.get("sourcePage") as string)
      : "/content";
    // The session we're leaving. Read after any refresh below, since a
    // refresh rotates it.
    let previousRefreshToken: string | null = null;
    try {
      // Refresh first if needed: the switch call must carry a live token.
      const currentToken = await getFreshAccessToken();
      previousRefreshToken = getRefreshToken();
      logoutWorkspace();
      // logoutWorkspace() just removed the token from localStorage, where the
      // API client normally reads it, so pass the current one explicitly.
      const { data } = await switchWorkspace({
        body: { workspace_name: workspaceName },
        auth: currentToken,
      });
      setLoginParams(data);
      if (currentPage) {
        router.push(currentPage);
      } else {
        router.push(sourcePage);
      }
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        // Nothing left to switch with; the tokens are already cleared.
        logout();
      } else if (isCustomError(error) && error.status === 401) {
        setLoginError("Invalid workspace name");
        console.error("Workspace Login error:", error);
      } else {
        console.error("Login error:", error);
        setLoginError("An unexpected error occurred. Please try again later.");
      }
    } finally {
      // The switch issues a brand-new session, and on failure the old tokens
      // are already gone from storage. Either way the old session is unused,
      // so revoke it rather than leave it valid for days.
      revokeRefreshToken(previousRefreshToken);
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

    loginGoogleRequest({ body: { client_id, credential } })
      .then(({ data }) => {
        localStorage.setItem("username", data.username);
        setUsername(data.username);
        setLoginParams(data);
        router.push(sourcePage);
      })
      .catch((error) => {
        setLoginError("Invalid Google credentials");
        console.error("Google login error:", error);
      });
  };
  const logout = () => {
    queryClient.clear();
    // End the session server-side too, so the refresh token can't be reused.
    revokeRefreshToken(getRefreshToken());
    clearTokens();
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
    queryClient.clear();
    clearTokens();
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
